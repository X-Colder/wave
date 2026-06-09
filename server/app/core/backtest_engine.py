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
    "ema_short_period": 80,
    "ema_long_period": 200,
    "accel_period": 10,
    "size_ema_period": 100,
    "direction_threshold": 0.03,
    "large_order_mult": 2.0,
    "w_flow": 0.5,
    "w_accel": 0.25,
    "w_large_order": 0.25,
}


def _normalize_weights(params: dict) -> dict:
    """Ensure w_flow + w_accel + w_large_order == 1.0."""
    total = params["w_flow"] + params["w_accel"] + params["w_large_order"]
    if total > 0:
        params["w_flow"] /= total
        params["w_accel"] /= total
        params["w_large_order"] /= total
    return params


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _signed_strength(value: float, threshold: float = 0.03) -> float:
    if value > threshold:
        return min((value - threshold) / (1.0 - threshold), 1.0)
    if value < -threshold:
        return -min((-value - threshold) / (1.0 - threshold), 1.0)
    return 0.0


class TrendSignalAnalyzer:
    """
    Continuous multi-scale trend signal.

    The analyzer treats trend direction, strength, reversal, and recent-vs-prior
    coverage as signal components. It is intentionally independent from signal
    flip counts; every evaluated tick gets a fresh view across 20/50/100/200
    tick windows.
    """

    _WINDOWS = (
        (20, 0.28, 140.0),
        (50, 0.26, 95.0),
        (100, 0.23, 70.0),
        (200, 0.23, 50.0),
    )

    def __init__(self) -> None:
        self._previous_score = 0.0

    def evaluate(
        self,
        i: int,
        prices: np.ndarray,
        flows: np.ndarray,
        size_ema: np.ndarray,
        flow_sig: float,
        norm_short: float,
        norm_long: float,
    ) -> dict:
        tick_price = float(prices[i])
        avg_size = max(float(size_ema[i]), 1.0)
        components: Dict[int, float] = {}
        weighted_score = 0.0

        for window, weight, price_scale in self._WINDOWS:
            start = max(0, i - window)
            base_price = max(float(prices[start]), 1e-9)
            price_score = (tick_price - base_price) / base_price * price_scale
            actual_window = max(i - start + 1, 1)
            flow_score = float(np.sum(flows[start:i + 1])) / (actual_window * avg_size)
            component = _clip(price_score * 0.65 + flow_score * 0.35)
            components[window] = component
            weighted_score += component * weight

        recent_score = _clip(components[20] * 0.62 + components[50] * 0.38)
        anchor_score = _clip(components[100] * 0.38 + components[200] * 0.62)
        coverage_score = 0.0
        reversal_score = 0.0

        if recent_score * anchor_score < 0 and abs(recent_score) > 0.06:
            coverage_score = _clip(abs(recent_score) - abs(anchor_score), -1.0, 1.0)
            if coverage_score > -0.08:
                reversal_score = np.sign(recent_score) * min(
                    abs(recent_score) / max(abs(anchor_score) + 0.08, 0.08),
                    1.0,
                )

        score = (
            weighted_score * 0.55
            + recent_score * 0.18
            + anchor_score * 0.10
            + flow_sig * 0.10
            + norm_short * 0.04
            + norm_long * 0.03
        )
        if reversal_score:
            score = score * 0.82 + reversal_score * 0.18

        score = _clip(score)
        delta = score - self._previous_score
        self._previous_score = score

        trend_speed = _clip(
            abs(recent_score - anchor_score) * 0.65 + abs(delta) * 2.0,
            0.0,
            1.0,
        )
        trend_strength = abs(score)

        if score > 0.04:
            direction = "up"
        elif score < -0.04:
            direction = "down"
        else:
            direction = "neutral"

        return {
            "trend_score": score,
            "trend_strength": trend_strength,
            "trend_speed": trend_speed,
            "trend_delta": delta,
            "trend_direction": direction,
            "recent_score": recent_score,
            "anchor_score": anchor_score,
            "coverage_score": coverage_score,
            "reversal_score": reversal_score,
            "components": components,
        }


class TrendRegimeTracker:
    """
    Persistent trend-segment tracker.

    This is not a fixed post-signal observation window. It carries the active
    trend segment across ticks and days, updates the segment extreme, and
    measures how much the opposite move has covered the active trend.
    """

    def __init__(self, state: Optional[dict] = None):
        state = state or {}
        self.direction = state.get("direction", "neutral")
        self.start_price = float(state.get("start_price", 0.0))
        self.extreme_price = float(state.get("extreme_price", 0.0))
        self.start_step = int(state.get("start_step", 0))
        self.extreme_step = int(state.get("extreme_step", 0))
        self.step = int(state.get("step", 0))
        self.last_price = float(state.get("last_price", 0.0))

    def to_state(self) -> dict:
        return {
            "direction": self.direction,
            "start_price": self.start_price,
            "extreme_price": self.extreme_price,
            "start_step": self.start_step,
            "extreme_step": self.extreme_step,
            "step": self.step,
            "last_price": self.last_price,
        }

    def update(self, price: float, flow_signal: float, trend_score: float) -> dict:
        self.step += 1

        if self.start_price <= 0:
            self.start_price = price
            self.extreme_price = price
            self.start_step = self.step
            self.extreme_step = self.step
            self.last_price = price
            return self._snapshot("neutral", 0.0, 0.0, 0.0, 0.0)

        move_from_start = (price - self.start_price) / self.start_price
        if self.direction == "neutral":
            if move_from_start <= -0.006 or trend_score < -0.12:
                self.direction = "down"
                self.extreme_price = price
                self.extreme_step = self.step
            elif move_from_start >= 0.006 or trend_score > 0.12:
                self.direction = "up"
                self.extreme_price = price
                self.extreme_step = self.step

        if self.direction == "down":
            if price < self.extreme_price:
                self.extreme_price = price
                self.extreme_step = self.step

            down_move = min((self.extreme_price - self.start_price) / self.start_price, 0.0)
            rebound = max((price - self.extreme_price) / self.extreme_price, 0.0)
            cover_ratio = min(rebound / max(abs(down_move), 1e-6), 2.0)
            down_speed = abs(down_move) / max(self.extreme_step - self.start_step, 1)
            rebound_speed = rebound / max(self.step - self.extreme_step, 1)
            speed_ratio = min(rebound_speed / max(down_speed, 1e-6), 2.0)
            flow_reversal = _clip((flow_signal + 0.15) / 0.45, 0.0, 1.0)
            reversal_score = _clip(
                min(cover_ratio, 1.0) * 0.50
                + min(speed_ratio / 1.5, 1.0) * 0.30
                + flow_reversal * 0.20,
                0.0,
                1.0,
            )

            if cover_ratio >= 0.72 and speed_ratio >= 0.55 and flow_signal > -0.05:
                regime = "uptrend"
                self.direction = "up"
                self.start_price = self.extreme_price
                self.start_step = self.extreme_step
                self.extreme_price = price
                self.extreme_step = self.step
            elif cover_ratio >= 0.45 or reversal_score >= 0.58:
                regime = "reversal_watch"
            elif cover_ratio >= 0.25 or reversal_score >= 0.42:
                regime = "down_exhaustion"
            else:
                regime = "downtrend"

            self.last_price = price
            return self._snapshot(regime, down_move, rebound, cover_ratio, speed_ratio, reversal_score)

        if self.direction == "up":
            if price > self.extreme_price:
                self.extreme_price = price
                self.extreme_step = self.step

            up_move = max((self.extreme_price - self.start_price) / self.start_price, 0.0)
            pullback = max((self.extreme_price - price) / self.extreme_price, 0.0)
            cover_ratio = min(pullback / max(up_move, 1e-6), 2.0)
            up_speed = up_move / max(self.extreme_step - self.start_step, 1)
            pullback_speed = pullback / max(self.step - self.extreme_step, 1)
            speed_ratio = min(pullback_speed / max(up_speed, 1e-6), 2.0)

            if cover_ratio >= 0.72 and speed_ratio >= 0.70 and flow_signal < 0.05:
                regime = "downtrend"
                self.direction = "down"
                self.start_price = self.extreme_price
                self.start_step = self.extreme_step
                self.extreme_price = price
                self.extreme_step = self.step
            elif cover_ratio >= 0.45:
                regime = "up_exhaustion"
            else:
                regime = "uptrend"

            self.last_price = price
            return self._snapshot(regime, up_move, pullback, cover_ratio, speed_ratio)

        self.last_price = price
        return self._snapshot("neutral", 0.0, 0.0, 0.0, 0.0)

    def _snapshot(
        self,
        regime: str,
        active_move: float,
        opposite_move: float,
        cover_ratio: float,
        speed_ratio: float,
        reversal_score: float = 0.0,
    ) -> dict:
        return {
            "regime": regime,
            "active_direction": self.direction,
            "active_move": active_move,
            "opposite_move": opposite_move,
            "cover_ratio": cover_ratio,
            "speed_ratio": speed_ratio,
            "reversal_score": reversal_score,
            "segment_ticks": max(self.step - self.start_step, 0),
            "extreme_age": max(self.step - self.extreme_step, 0),
        }




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

        # Phase 1: learn parameters from the first train_days days.
        # Keep the historical cap so the default report covers the 14-month
        # out-of-sample window used by the dashboard comparisons.
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
            highest_since_entry: float = avg_price
            regime_tracker = TrendRegimeTracker(carry_state.get("trend_state"))
        else:
            position = 0.0
            avg_price = 0.0
            sellable = 0.0
            highest_since_entry = 0.0
            regime_tracker = TrendRegimeTracker()

        today_bought: float = 0.0
        last_trade_tick: int = -(s.min_trade_interval + 1)

        data = flow_engine.process_day(day, df)
        if not data:
            return trades, signals, capital, _carry_out(
                position, avg_price, regime_tracker.to_state()
            )

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
        trend_analyzer = TrendSignalAnalyzer()

        for i in range(0, n, EVAL_INTERVAL):
            tick_price = float(prices[i])
            tick_time = pd.Timestamp(times[i]).to_pydatetime()
            sig = float(signal_scores[i])
            direction = str(directions[i])
            spd = float(speeds[i])
            trend_struct = str(trend_structures[i])
            signal_trend = str(signal_trends[i])

            # ------------------------------------------------------------------ #
            # Continuous trend signal                                             #
            # ------------------------------------------------------------------ #
            ns = float(norm_short_arr[i])
            nl = float(norm_long_arr[i])
            trend = trend_analyzer.evaluate(
                i=i,
                prices=prices,
                flows=flows,
                size_ema=size_ema,
                flow_sig=sig,
                norm_short=ns,
                norm_long=nl,
            )
            trend_score = float(trend["trend_score"])
            trend_strength = float(trend["trend_strength"])
            trend_speed = float(trend["trend_speed"])
            trend_delta = float(trend["trend_delta"])
            trend_direction = str(trend["trend_direction"])
            cover_score = float(trend["coverage_score"])
            reversal_score = float(trend["reversal_score"])
            recent_score = float(trend["recent_score"])
            anchor_score = float(trend["anchor_score"])

            start_50 = max(0, i - 50)
            start_200 = max(0, i - 200)
            start_500 = max(0, i - 500)
            avg_size = max(float(size_ema[i]), 1.0)
            flow_50 = float(np.sum(flows[start_50:i + 1])) / (50.0 * avg_size)
            flow_200 = float(np.sum(flows[start_200:i + 1])) / (200.0 * avg_size)
            flow_500 = float(np.sum(flows[start_500:i + 1])) / (500.0 * avg_size)
            price_50 = (tick_price - float(prices[start_50])) / float(prices[start_50]) * 100
            price_200 = (tick_price - float(prices[start_200])) / float(prices[start_200]) * 50
            legacy_score = _clip(
                sig * 0.25
                + flow_50 * 0.15
                + flow_200 * 0.10
                + flow_500 * 0.05
                + ns * 0.10
                + nl * 0.05
                + price_50 * 0.15
                + price_200 * 0.15
            )
            position_signal = legacy_score
            signal_strength = abs(position_signal)
            if position_signal > 0.04:
                signal_direction = "up"
            elif position_signal < -0.04:
                signal_direction = "down"
            else:
                signal_direction = "neutral"
            regime = regime_tracker.update(tick_price, sig, trend_score)

            # ------------------------------------------------------------------ #
            # Map score to target position                                         #
            # ------------------------------------------------------------------ #
            min_pos = s.min_position
            max_pos = s.max_position
            if position_signal > 0:
                target = min_pos + (max_pos - min_pos) * min(position_signal, 1.0)
            elif position_signal < -0.1:
                target = min_pos
            else:
                target = position

            trade_reason = "signal"

            if position > 0 and avg_price > 0:
                highest_since_entry = max(highest_since_entry, tick_price)

            stop_target: Optional[float] = None
            if position > min_pos and sellable > 0 and avg_price > 0 and highest_since_entry > 0:
                high_drawdown = (tick_price - highest_since_entry) / highest_since_entry
                entry_return = (tick_price - avg_price) / avg_price
                peak_return = (highest_since_entry - avg_price) / avg_price

                if entry_return <= -0.028:
                    stop_target = min_pos
                elif peak_return >= 0.050 and high_drawdown <= -0.028:
                    stop_target = max(min_pos, position - 0.35)
                elif peak_return >= 0.030 and high_drawdown <= -0.018:
                    stop_target = max(min_pos, position - 0.20)

            if stop_target is not None and stop_target < target:
                target = stop_target
                trade_reason = "trailing_stop"

            if trade_reason == "trailing_stop" and regime["regime"] in {
                "down_exhaustion",
                "reversal_watch",
            }:
                if entry_return > -0.028:
                    target = max(target, position - 0.15)

            if trade_reason == "signal" and target < position:
                reduction = position - target
                trend_protect = 0.0
                if regime["regime"] == "reversal_watch":
                    trend_protect = 0.88
                elif regime["regime"] == "down_exhaustion":
                    trend_protect = 0.75
                elif regime["regime"] == "uptrend":
                    trend_protect = 0.70
                elif trend_struct == "higher_low" or anchor_score > 0.08:
                    trend_protect = 0.65
                elif anchor_score > 0 and recent_score > -0.25:
                    trend_protect = 0.45
                elif recent_score > 0 and trend_delta > -0.08:
                    trend_protect = 0.35

                if (
                    regime["regime"] == "downtrend"
                    and trend_struct == "lower_low"
                    and recent_score < -0.12
                ):
                    trend_protect = 0.0

                if trend_protect > 0:
                    target = position - reduction * (1.0 - trend_protect)

            if regime["regime"] == "reversal_watch" and position_signal > -0.05:
                target = max(target, min(max_pos, position + 0.20, 0.55))
            elif regime["regime"] == "uptrend" and regime["reversal_score"] >= 0.55:
                target = max(target, min(max_pos, 0.65))

            # Periodic signal snapshot (every 100 ticks)
            if i % 100 == 0:
                signals.append({
                    "time": tick_time.strftime("%H:%M:%S"),
                    "price": round(tick_price, 4),
                    "direction": signal_direction,
                    "signal_score": round(sig, 4),
                    "speed": round(max(spd, trend_speed), 4),
                    "norm_short": round(ns, 4),
                    "norm_long": round(nl, 4),
                    "position": round(position, 4),
                    "trend_structure": trend_struct,
                    "signal_trend": signal_trend,
                    "trend_score": round(trend_score, 4),
                    "trend_strength": round(trend_strength, 4),
                    "trend_speed": round(trend_speed, 4),
                    "trend_delta": round(trend_delta, 4),
                    "legacy_score": round(legacy_score, 4),
                    "position_signal": round(position_signal, 4),
                    "recent_score": round(recent_score, 4),
                    "anchor_score": round(anchor_score, 4),
                    "coverage_score": round(cover_score, 4),
                    "reversal_score": round(reversal_score, 4),
                    "regime": regime["regime"],
                    "regime_cover": round(regime["cover_ratio"], 4),
                    "regime_speed": round(regime["speed_ratio"], 4),
                    "regime_reversal_score": round(regime["reversal_score"], 4),
                    "target_position": round(target, 4),
                    "action": "sample",
                })

            # Open-auction protection: no trading before MIN_TICKS
            if i < MIN_TICKS:
                continue

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
            # Adjust toward target (only on significant change)                 #
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

            # Only act on meaningful changes; continuous trend updates can
            # still resize in 5% steps when strength changes persist.
            if abs(delta) < max(s.min_position_delta, 0.05):
                continue

            # Minimum trade interval
            if (i - last_trade_tick) < s.min_trade_interval:
                continue
            elif delta < 0:
                actual_sell = min(abs(delta), sellable)
                delta = -actual_sell

            # (checks already above)

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
                highest_since_entry = max(highest_since_entry, tick_price)

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
                if position <= min_pos:
                    highest_since_entry = tick_price

            last_trade_tick = i

            trade = Trade(
                trade_id=0,   # assigned in _run_full
                day=day,
                time=tick_time,
                action=trade_reason,
                price=exec_price,
                position_before=position_before,
                position_after=position,
                position_delta=delta,
                direction=signal_direction,
                speed=max(spd, trend_speed),
                signal_score=position_signal,
                realized_pnl=realized_pnl,
                capital_after=capital,
            )
            trades.append(trade)

            signals.append({
                "time": tick_time.strftime("%H:%M:%S"),
                "price": round(exec_price, 4),
                "direction": signal_direction,
                "signal_score": round(sig, 4),
                "speed": round(max(spd, trend_speed), 4),
                "norm_short": round(float(norm_short_arr[i]), 4),
                "norm_long": round(float(norm_long_arr[i]), 4),
                "position": round(position, 4),
                "trend_structure": trend_struct,
                "signal_trend": signal_trend,
                "trend_score": round(trend_score, 4),
                "trend_strength": round(trend_strength, 4),
                "trend_speed": round(trend_speed, 4),
                "trend_delta": round(trend_delta, 4),
                "legacy_score": round(legacy_score, 4),
                "position_signal": round(position_signal, 4),
                "recent_score": round(recent_score, 4),
                "anchor_score": round(anchor_score, 4),
                "coverage_score": round(cover_score, 4),
                "reversal_score": round(reversal_score, 4),
                "regime": regime["regime"],
                "regime_cover": round(regime["cover_ratio"], 4),
                "regime_speed": round(regime["speed_ratio"], 4),
                "regime_reversal_score": round(regime["reversal_score"], 4),
                "target_position": round(target, 4),
                "action": "buy" if delta > 0 else trade_reason,
                "position_before": round(position_before, 4),
                "position_after": round(position, 4),
                "delta": round(delta, 4),
                "realized_pnl": round(realized_pnl, 2),
            })

        return trades, signals, capital, _carry_out(
            position, avg_price, regime_tracker.to_state()
        )

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


def _carry_out(
    position: float,
    avg_price: float,
    trend_state: Optional[dict] = None,
) -> Optional[dict]:
    if position > 0.01:
        return {
            "position_ratio": position,
            "avg_entry_price": avg_price,
            "trend_state": trend_state or {},
        }
    return None
