import random
import logging
import numpy as np
import pandas as pd
from datetime import date, datetime, time as dtime
from typing import List, Dict, Tuple, Optional

from .models import Trade, BacktestResult
from .data_loader import DataLoader
from .flow_engine import FlowEngine
from .metrics import compute_all_metrics, monthly_returns
from ..config import Settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Parameter search space                                                        #
# --------------------------------------------------------------------------- #
_PARAM_GRID = {
    "ema_short_period":  [30, 50, 80],
    "ema_long_period":   [150, 200, 300],
    "accel_period":      [10, 20, 30],
    "size_ema_period":   [50, 100, 150],
    "direction_threshold": [0.03, 0.05, 0.08],
    "large_order_mult":  [2.0, 3.0, 5.0],
    "w_flow":            [0.3, 0.4, 0.5],
    "w_accel":           [0.15, 0.2, 0.3],
    "w_large_order":     [0.2, 0.3, 0.4],
}

_DEFAULT_PARAMS = {
    "ema_short_period": 50,
    "ema_long_period": 200,
    "accel_period": 20,
    "size_ema_period": 100,
    "direction_threshold": 0.05,
    "large_order_mult": 3.0,
    "w_flow": 0.4,
    "w_accel": 0.2,
    "w_large_order": 0.4,
}


def _normalize_weights(params: dict) -> dict:
    """Ensure w_flow + w_accel + w_large_order == 1.0."""
    total = params["w_flow"] + params["w_accel"] + params["w_large_order"]
    if total > 0:
        params["w_flow"] /= total
        params["w_accel"] /= total
        params["w_large_order"] /= total
    return params




class BacktestEngine:
    """
    Two-phase backtesting engine:

    Phase 1 – random-search parameter optimisation over the first ``train_days``
              trading days (default 60).  50 random parameter combinations are
              evaluated; the one that maximises total realised PnL is kept.

    Phase 2 – full backtest over all trading days using the learned parameters.

    Trade decisions are made tick-by-tick (per-tick EMA signals from FlowEngine).
    To avoid over-trading, a minimum tick interval between consecutive trades is
    enforced (``min_trade_interval``, default 100 ticks ≈ a few minutes).
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = DataLoader(settings.data_dir)

    # ----------------------------------------------------------------------- #
    # Public entry point                                                        #
    # ----------------------------------------------------------------------- #

    def run(self) -> BacktestResult:
        trading_days = self.loader.discover_trading_days()
        if not trading_days:
            return self._empty_result()

        s = self.settings

        # Phase 1: learn parameters from the first train_days days
        train_count = min(s.train_days, max(1, len(trading_days) // 3))
        train_days_list = trading_days[:train_count]

        logger.info(
            f"Phase 1: optimising params over {len(train_days_list)} training days "
            f"({s.param_search_trials} trials)"
        )
        best_params = self._optimize_params(train_days_list)
        logger.info(f"Best params: {best_params}")

        # Phase 2: backtest only on post-training days (out-of-sample)
        test_days = trading_days[train_count:]
        logger.info(f"Phase 2: running backtest over {len(test_days)} test days (out-of-sample)")
        trades, equity_curve, daily_signals = self._run_full(test_days, best_params)

        metrics = compute_all_metrics(trades, equity_curve, s.initial_capital)
        monthly_rets = monthly_returns(trades, s.initial_capital)

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
            monthly_returns=monthly_rets,
            daily_signals=daily_signals,
            learned_params=best_params,
        )

    # ----------------------------------------------------------------------- #
    # Phase 1: parameter optimisation                                           #
    # ----------------------------------------------------------------------- #

    def _optimize_params(self, train_days_list: List[date]) -> dict:
        rng = random.Random(42)
        best_pnl = -float("inf")
        best_params = _DEFAULT_PARAMS.copy()

        for trial in range(self.settings.param_search_trials):
            params = {k: rng.choice(v) for k, v in _PARAM_GRID.items()}
            params = _normalize_weights(params)

            pnl = self._evaluate_params(params, train_days_list)
            if pnl > best_pnl:
                best_pnl = pnl
                best_params = params.copy()
                logger.debug(f"Trial {trial}: pnl={pnl:.2f}, params={params}")

        return best_params

    def _evaluate_params(self, params: dict, days_list: List[date]) -> float:
        """Run a lightweight backtest and return total realised PnL."""
        engine = FlowEngine(params)
        capital = self.settings.initial_capital
        carry: Optional[dict] = None
        total_pnl = 0.0

        for d in days_list:
            df = self.loader.load_day(d)
            if df is None or len(df) == 0:
                continue
            trades, _, capital, carry = self._trade_day(d, df, capital, carry, engine, params)
            total_pnl += sum(t.realized_pnl for t in trades)

        return total_pnl

    # ----------------------------------------------------------------------- #
    # Phase 2: full backtest                                                    #
    # ----------------------------------------------------------------------- #

    def _run_full(
        self,
        trading_days: List[date],
        params: dict,
    ) -> Tuple[List[Trade], List[Tuple[datetime, float]], Dict[date, List[dict]]]:
        s = self.settings
        engine = FlowEngine(params)

        trades: List[Trade] = []
        equity_curve: List[Tuple[datetime, float]] = []
        daily_signals: Dict[date, List[dict]] = {}
        capital = s.initial_capital
        carry: Optional[dict] = None
        trade_id = 0

        # Initial equity point
        equity_curve.append((
            datetime.combine(trading_days[0], dtime(9, 30)),
            capital,
        ))

        for d in trading_days:
            df = self.loader.load_day(d)
            if df is None or len(df) == 0:
                continue

            day_trades, day_signals, capital, carry = self._trade_day(
                d, df, capital, carry, engine, params
            )

            for t in day_trades:
                trade_id += 1
                t.trade_id = trade_id
                trades.append(t)
                equity_curve.append((t.time, t.capital_after))

            daily_signals[d] = day_signals

            if not day_trades:
                equity_curve.append((datetime.combine(d, dtime(15, 0)), capital))

        return trades, equity_curve, daily_signals

    # ----------------------------------------------------------------------- #
    # Per-day tick-by-tick simulation                                           #
    # ----------------------------------------------------------------------- #

    def _trade_day(
        self,
        day: date,
        df: pd.DataFrame,
        starting_capital: float,
        carry_state: Optional[dict],
        flow_engine: FlowEngine,
        params: dict,
    ) -> Tuple[List[Trade], List[dict], float, Optional[dict]]:
        """
        Simulate one trading day using a unified multi-scale trend score.

        Every EVAL_INTERVAL ticks the engine computes a trend score from
        short/mid/long price momentum and net flow, maps that score to a
        target position ratio, then adjusts toward the target.

        T+1 constraint:
          - ``sellable`` is initialised from the previous day's position.
          - Shares bought today (``today_bought``) may NOT be sold today.
          - New buys today are capped at ``sellable + 0.3`` to limit intraday risk.

        Signal sampling:
          - Every 100 ticks a snapshot is appended to ``signals`` for the intraday
            API, regardless of whether a trade occurred.

        Protection window:
          - No trades are evaluated before MIN_TICKS (300) to avoid open-auction noise.
        """
        EVAL_INTERVAL = 10   # evaluate target position every N ticks
        MIN_TICKS = 300      # no-trade window at open

        s = self.settings
        trades: List[Trade] = []
        signals: List[dict] = []
        capital = starting_capital

        # Initialise position from overnight carry
        if carry_state:
            position: float = carry_state["position_ratio"]
            avg_price: float = carry_state["avg_entry_price"]
            sellable: float = carry_state["position_ratio"]
        else:
            position = 0.0
            avg_price = 0.0
            sellable = 0.0

        today_bought: float = 0.0
        last_trade_tick: int = -(s.min_trade_interval + 1)

        data = flow_engine.process_day(day, df)
        if not data:
            return trades, signals, capital, _carry_out(position, avg_price)

        prices = data["prices"]
        flows = data["flows"]
        times = data["times"]
        size_ema = data["size_ema"]
        # Keep legacy signal fields for the signal snapshot record
        signal_scores = data["signal_score"]
        directions = data["direction"]
        speeds = data["speed"]
        norm_short_arr = data["norm_short"]
        norm_long_arr = data["norm_long"]
        trend_structures = data["trend_structure"]
        signal_trends = data["signal_trend"]

        n = len(prices)

        for i in range(0, n, EVAL_INTERVAL):
            tick_price = float(prices[i])
            tick_time = pd.Timestamp(times[i]).to_pydatetime()
            sig = float(signal_scores[i])
            direction = str(directions[i])
            spd = float(speeds[i])
            trend_struct = str(trend_structures[i])
            signal_trend = str(signal_trends[i])

            # Periodic signal snapshot (every 100 ticks)
            if i % 100 == 0:
                signals.append({
                    "time": tick_time.strftime("%H:%M:%S"),
                    "price": round(tick_price, 4),
                    "direction": direction,
                    "signal_score": round(sig, 4),
                    "speed": round(spd, 4),
                    "norm_short": round(float(norm_short_arr[i]), 4),
                    "norm_long": round(float(norm_long_arr[i]), 4),
                    "position": round(position, 4),
                    "trend_structure": trend_struct,
                    "signal_trend": signal_trend,
                    "action": "sample",
                })

            # Open-auction protection: no trading before MIN_TICKS
            if i < MIN_TICKS:
                continue

            # ------------------------------------------------------------------ #
            # Multi-scale trend score                                              #
            # ------------------------------------------------------------------ #

            # Short term: last 50 ticks
            start_50 = max(0, i - 50)
            price_50_ago = float(prices[start_50])
            trend_short = (tick_price - price_50_ago) / price_50_ago
            flow_short = float(np.sum(flows[start_50:i + 1]))

            # Mid term: last 200 ticks
            start_200 = max(0, i - 200)
            price_200_ago = float(prices[start_200])
            trend_mid = (tick_price - price_200_ago) / price_200_ago
            flow_mid = float(np.sum(flows[start_200:i + 1]))

            # Long term: last 500 ticks
            start_500 = max(0, i - 500)
            price_500_ago = float(prices[start_500])
            trend_long = (tick_price - price_500_ago) / price_500_ago

            # Normalise price changes
            norm_s = trend_short * 100   # 1% → 1.0
            norm_m = trend_mid * 50      # 2% → 1.0
            norm_l = trend_long * 30     # 3% → 1.0

            # Normalise flow relative to average trade size
            avg_size = max(float(size_ema[i]), 1.0)
            flow_score_short = flow_short / (50.0 * avg_size)
            flow_score_mid = flow_mid / (200.0 * avg_size)

            # Composite score in [-1, +1]
            trend_score = (
                norm_s * 0.35
                + norm_m * 0.25
                + norm_l * 0.15
                + flow_score_short * 0.15
                + flow_score_mid * 0.10
            )
            trend_score = max(-1.0, min(1.0, trend_score))

            # ------------------------------------------------------------------ #
            # Map score to target position                                         #
            # ------------------------------------------------------------------ #
            min_pos = s.min_position
            max_pos = s.max_position

            if trend_score > 0:
                # Positive trend: scale position from min_pos up to max_pos
                target = min_pos + (max_pos - min_pos) * min(trend_score, 1.0)
            elif trend_score < -0.1:
                # Confirmed downtrend: retreat to floor
                target = min_pos
            else:
                # Weak / ambiguous trend (-0.1 to 0): hold current
                target = position

            # End-of-day decay: linearly cap to min_pos over last 30 min (14:30-15:00)
            t = tick_time.time()
            if t >= dtime(14, 30):
                remaining = (
                    datetime.combine(day, dtime(15, 0))
                    - datetime.combine(day, t)
                ).total_seconds()
                max_eod = min_pos + (0.5 - min_pos) * (remaining / 1800.0)
                target = min(target, max_eod)

            target = max(min_pos, min(target, max_pos))

            # ------------------------------------------------------------------ #
            # Adjust toward target                                                 #
            # ------------------------------------------------------------------ #
            delta = target - position

            # T+1 constraint on buys
            if delta > 0:
                max_buy = sellable + 0.3
                target = min(target, max_buy)
                delta = target - position

            # T+1 constraint on sells: only sellable shares
            elif delta < 0:
                actual_sell = min(abs(delta), sellable)
                delta = -actual_sell

            # Ignore micro-adjustments below threshold; still record sample
            if abs(delta) < s.min_position_delta:
                continue

            # Minimum trade interval throttle
            if (i - last_trade_tick) < s.min_trade_interval:
                continue

            # ------------------------------------------------------------------ #
            # Execute trade                                                        #
            # ------------------------------------------------------------------ #
            position_before = position
            realized_pnl: float

            if delta > 0:
                exec_price = tick_price * (1.0 + s.slippage_rate)
                commission = abs(delta) * capital * s.commission_rate

                if position > 0 and avg_price > 0:
                    old_val = position * avg_price
                    new_val = delta * exec_price
                    avg_price = (old_val + new_val) / (position + delta)
                else:
                    avg_price = exec_price

                position += delta
                today_bought += delta
                capital -= commission
                realized_pnl = -commission

            else:  # sell
                sell_qty = abs(delta)
                exec_price = tick_price * (1.0 - s.slippage_rate)
                commission = sell_qty * capital * s.commission_rate

                gross_ret = (exec_price - avg_price) / avg_price if avg_price > 0 else 0.0
                realized_pnl = sell_qty * capital * gross_ret - commission

                capital += realized_pnl
                position += delta
                position = max(0.0, position)
                sellable = max(0.0, sellable - sell_qty)

            last_trade_tick = i

            trade = Trade(
                trade_id=0,   # assigned in _run_full
                day=day,
                time=tick_time,
                action="adjust",
                price=exec_price,
                position_before=position_before,
                position_after=position,
                position_delta=delta,
                direction=direction,
                speed=spd,
                signal_score=sig,
                realized_pnl=realized_pnl,
                capital_after=capital,
            )
            trades.append(trade)

            signals.append({
                "time": tick_time.strftime("%H:%M:%S"),
                "price": round(exec_price, 4),
                "direction": direction,
                "signal_score": round(sig, 4),
                "speed": round(spd, 4),
                "norm_short": round(float(norm_short_arr[i]), 4),
                "norm_long": round(float(norm_long_arr[i]), 4),
                "position": round(position, 4),
                "trend_structure": trend_struct,
                "signal_trend": signal_trend,
                "action": "buy" if delta > 0 else "sell",
                "position_before": round(position_before, 4),
                "position_after": round(position, 4),
                "delta": round(delta, 4),
                "realized_pnl": round(realized_pnl, 2),
            })

        return trades, signals, capital, _carry_out(position, avg_price)

    @staticmethod
    def _empty_result() -> BacktestResult:
        from .metrics import compute_all_metrics, monthly_returns
        return BacktestResult(
            trades=[],
            equity_curve=[],
            metrics=compute_all_metrics([], [], 100000.0),
            monthly_returns={},
            daily_signals={},
            learned_params={},
        )


def _carry_out(position: float, avg_price: float) -> Optional[dict]:
    if position > 0.01:
        return {"position_ratio": position, "avg_entry_price": avg_price}
    return None
