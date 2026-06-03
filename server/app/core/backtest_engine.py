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


def _compute_target(
    signal: float,
    direction: str,
    current_position: float,
    tick_time: datetime,
    day: date,
    min_pos: float,
    max_pos: float,
) -> float:
    """
    Map signal score and direction to a target position ratio.

    Ranges:
      up:       0.5 + signal * 0.3  → ~50-80%
      down:     min_pos
      pullback: current * 0.85 floored at min_pos + 0.05
      bounce:   min_pos
      neutral:  unchanged
    Also applies an end-of-day time decay from 14:30 onward.
    """
    t = tick_time.time()

    if direction == "up":
        target = 0.5 + signal * 0.3        # signal 0~1 → 50-80%
    elif direction == "down":
        target = min_pos
    elif direction == "pullback":
        target = max(current_position * 0.85, min_pos + 0.05)
    elif direction == "bounce":
        target = min_pos
    else:  # neutral
        target = current_position

    # End-of-day decay: linearly cap from 0.5 → min_pos over the last 30 min
    if t >= dtime(14, 30):
        remaining_secs = (
            datetime.combine(day, dtime(15, 0)) -
            datetime.combine(day, t)
        ).total_seconds()
        max_eod = min_pos + (0.5 - min_pos) * (remaining_secs / 1800.0)
        target = min(target, max_eod)

    return max(min_pos, min(target, max_pos))


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

        # Phase 2: full backtest with learned params
        logger.info(f"Phase 2: running full backtest over {len(trading_days)} days")
        trades, equity_curve, daily_signals = self._run_full(trading_days, best_params)

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
        Simulate one trading day tick-by-tick.

        T+1 constraint:
          - ``sellable`` is initialised from the previous day's position.
          - Shares bought today (``today_bought``) may NOT be sold today.
          - New buys today are capped at ``sellable + 0.3`` to limit intraday risk.

        Trade throttle:
          - ``last_trade_tick`` prevents trades within ``min_trade_interval`` ticks
            of each other.

        Signal sampling:
          - Every 200 ticks a snapshot is appended to ``signals`` for the intraday
            API, regardless of whether a trade occurred.
        """
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

        today_bought: float = 0.0          # shares bought today (not yet sellable)
        last_trade_tick: int = -(s.min_trade_interval + 1)

        # Dynamic TP/SL state
        entry_price_for_tp_sl: float = avg_price if position > 0 else 0.0
        base_tp: float = 0.01   # initial take-profit 1%
        base_sl: float = 0.005  # initial stop-loss 0.5%
        highest_since_entry: float = avg_price if position > 0 else 0.0

        data = flow_engine.process_day(day, df)
        if not data:
            return trades, signals, capital, _carry_out(position, avg_price)

        n = len(data["prices"])
        times = data["times"]
        prices = data["prices"]
        norm_short = data["norm_short"]
        norm_long = data["norm_long"]
        signal_scores = data["signal_score"]
        directions = data["direction"]
        speeds = data["speed"]

        for i in range(n):
            sig = float(signal_scores[i])
            direction = str(directions[i])
            spd = float(speeds[i])
            tick_time = pd.Timestamp(times[i]).to_pydatetime()
            tick_price = float(prices[i])

            # Sample every 200 ticks for the intraday API
            if i % 200 == 0:
                signals.append({
                    "time": tick_time.strftime("%H:%M:%S"),
                    "price": round(tick_price, 4),
                    "direction": direction,
                    "signal_score": round(sig, 4),
                    "speed": round(spd, 4),
                    "norm_short": round(float(norm_short[i]), 4),
                    "norm_long": round(float(norm_long[i]), 4),
                    "position": round(position, 4),
                    "action": "sample",
                })

            # --- Dynamic TP/SL check (every tick, no throttle) ---
            if position > s.min_position and entry_price_for_tp_sl > 0 and sellable > 0:
                current_ret = (tick_price - entry_price_for_tp_sl) / entry_price_for_tp_sl
                highest_since_entry = max(highest_since_entry, tick_price)

                # Dynamic TP: expand in accelerating uptrend
                dynamic_tp = base_tp * (1.0 + spd) if direction == 'up' else base_tp
                # Trailing: if price has risen significantly, raise stop to lock profit
                trailing_stop = (highest_since_entry - entry_price_for_tp_sl) / entry_price_for_tp_sl * 0.5
                # Dynamic SL: shrink in expanding downtrend
                dynamic_sl = base_sl * (0.5 if direction == 'down' and spd > 0.3 else 1.0)
                effective_sl = max(dynamic_sl, trailing_stop)

                tp_hit = current_ret >= dynamic_tp
                sl_hit = current_ret <= -effective_sl

                if (tp_hit or sl_hit) and (i - last_trade_tick) >= 30:
                    sell_ratio = min(position - s.min_position, sellable)
                    if sell_ratio >= 0.05:
                        exec_price = tick_price * (1.0 - s.slippage_rate)
                        commission = sell_ratio * capital * s.commission_rate
                        gross_ret = (exec_price - avg_price) / avg_price if avg_price > 0 else 0.0
                        realized_pnl = sell_ratio * capital * gross_ret - commission
                        position_before = position

                        capital += realized_pnl
                        position -= sell_ratio
                        position = max(0.0, position)
                        sellable = max(0.0, sellable - sell_ratio)
                        last_trade_tick = i

                        trade = Trade(
                            trade_id=0, day=day, time=tick_time,
                            action="adjust", price=exec_price,
                            position_before=position_before,
                            position_after=position,
                            position_delta=-sell_ratio,
                            direction=direction, speed=spd,
                            signal_score=sig, realized_pnl=realized_pnl,
                            capital_after=capital,
                        )
                        trades.append(trade)
                        signals.append({
                            "time": tick_time.strftime("%H:%M:%S"),
                            "price": round(exec_price, 4),
                            "direction": direction,
                            "signal_score": round(sig, 4),
                            "speed": round(spd, 4),
                            "norm_short": round(float(norm_short[i]), 4),
                            "norm_long": round(float(norm_long[i]), 4),
                            "position": round(position, 4),
                            "action": "tp" if tp_hit else "sl",
                            "position_before": round(position_before, 4),
                            "position_after": round(position, 4),
                            "delta": round(-sell_ratio, 4),
                            "realized_pnl": round(realized_pnl, 2),
                        })

                        # Reset TP/SL for remaining position
                        if position > s.min_position:
                            entry_price_for_tp_sl = tick_price
                            highest_since_entry = tick_price
                        continue

            # Throttle: skip signal-based trades if too soon
            if (i - last_trade_tick) < s.min_trade_interval:
                continue

            # --- Signal-based position adjustment ---
            # Only reduce on strong negative signal (not mild wobbles)
            target = _compute_target(
                sig, direction, position,
                tick_time, day,
                s.min_position, s.max_position,
            )

            # If we have TP/SL protecting the position, only allow signal-based sell
            # when signal is strongly bearish (< -0.3)
            if position > s.min_position and target < position:
                if sig > -0.3:
                    continue  # mild negative → let TP/SL handle it

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

            if abs(delta) < s.min_position_delta:
                continue

            # Execute trade
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

                # Reset TP/SL anchor on new entry/add
                entry_price_for_tp_sl = avg_price
                highest_since_entry = tick_price
                # Adjust TP/SL based on current speed
                base_tp = 0.008 + spd * 0.012  # speed 0→0.8%, speed 1→2%
                base_sl = 0.005 - spd * 0.002  # speed 0→0.5%, speed 1→0.3%
                base_sl = max(base_sl, 0.003)

            else:  # sell
                sell_ratio = abs(delta)
                exec_price = tick_price * (1.0 - s.slippage_rate)
                commission = sell_ratio * capital * s.commission_rate

                gross_ret = (exec_price - avg_price) / avg_price if avg_price > 0 else 0.0
                realized_pnl = sell_ratio * capital * gross_ret - commission

                capital += realized_pnl
                position += delta
                position = max(0.0, position)
                sellable = max(0.0, sellable - sell_ratio)

            last_trade_tick = i

            trade = Trade(
                trade_id=0,          # assigned in _run_full
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

            # Add trade event to signals as well
            signals.append({
                "time": tick_time.strftime("%H:%M:%S"),
                "price": round(exec_price, 4),
                "direction": direction,
                "signal_score": round(sig, 4),
                "speed": round(spd, 4),
                "norm_short": round(float(norm_short[i]), 4),
                "norm_long": round(float(norm_long[i]), 4),
                "position": round(position, 4),
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
