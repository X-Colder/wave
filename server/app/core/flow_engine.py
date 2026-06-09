import numpy as np
import pandas as pd
from datetime import date
from typing import Dict

from ..utils.time_utils import MORNING_START, MORNING_END, AFTERNOON_START, AFTERNOON_END


def _filter_trading_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only ticks within official trading hours."""
    t = df["Datetime"].dt.time
    mask = (
        ((t >= MORNING_START) & (t <= MORNING_END)) |
        ((t >= AFTERNOON_START) & (t <= AFTERNOON_END))
    )
    return df[mask].reset_index(drop=True)


class FlowEngine:
    """
    Per-tick EMA-based order flow engine with large-order detection.

    All computation is done via numpy arrays (vectorized where possible).
    EMA recurrences require a forward loop, but the loop body is trivial
    arithmetic so it stays well within budget even for ~8000 ticks/day.

    Returns a dict of numpy arrays (one entry per trading tick) rather than
    a list of objects, to avoid Python object overhead.
    """

    def __init__(self, params: dict):
        period_s = params.get("ema_short_period", 50)
        period_l = params.get("ema_long_period", 200)
        period_a = params.get("accel_period", 20)
        period_sz = params.get("size_ema_period", 100)

        self.alpha_short = 2.0 / (period_s + 1)
        self.alpha_long = 2.0 / (period_l + 1)
        self.alpha_accel = 2.0 / (period_a + 1)
        self.alpha_size = 2.0 / (period_sz + 1)

        self.direction_threshold = params.get("direction_threshold", 0.05)
        self.large_mult = params.get("large_order_mult", 3.0)

        # Signal composition weights (already normalized outside if needed)
        self.w_flow = params.get("w_flow", 0.4)
        self.w_accel = params.get("w_accel", 0.2)
        self.w_large = params.get("w_large_order", 0.4)

    def process_day(self, day: date, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        Process one day's tick data with EMA-based signals.

        Returns a dict of aligned numpy arrays:
          times, prices, volumes, sides (+1/-1),
          flow_ema_short, flow_ema_long,
          norm_short, norm_long, norm_accel,
          order_sizes, size_ema,
          is_large (bool), large_buy_streak, large_sell_streak,
          signal_score, direction (str array), speed,
          trend_structure (str array: "higher_low"/"lower_low"/"flat"),
          signal_trend (str array: "weakening"/"strengthening"/"neutral")
        """
        trading_df = _filter_trading_hours(df)
        n = len(trading_df)
        if n == 0:
            return {}

        prices = trading_df["Price"].values.astype(np.float64)
        volumes = trading_df["Volume"].values.astype(np.float64)
        sides = np.where(trading_df["Type"].values == "B", 1.0, -1.0)

        flows = prices * volumes * sides
        order_sizes = prices * volumes

        # ------------------------------------------------------------------ #
        # EMA recurrences                                                      #
        # ------------------------------------------------------------------ #
        a_s = self.alpha_short
        a_l = self.alpha_long
        a_a = self.alpha_accel
        a_sz = self.alpha_size

        flow_ema_s = np.empty(n, dtype=np.float64)
        flow_ema_l = np.empty(n, dtype=np.float64)
        size_ema = np.empty(n, dtype=np.float64)
        accel_ema = np.empty(n, dtype=np.float64)

        flow_ema_s[0] = flows[0]
        flow_ema_l[0] = flows[0]
        size_ema[0] = order_sizes[0]
        accel_ema[0] = 0.0

        for i in range(1, n):
            flow_ema_s[i] = a_s * flows[i] + (1.0 - a_s) * flow_ema_s[i - 1]
            flow_ema_l[i] = a_l * flows[i] + (1.0 - a_l) * flow_ema_l[i - 1]
            size_ema[i] = a_sz * order_sizes[i] + (1.0 - a_sz) * size_ema[i - 1]
            slope_change = flow_ema_s[i] - flow_ema_s[i - 1]
            accel_ema[i] = a_a * slope_change + (1.0 - a_a) * accel_ema[i - 1]

        # ------------------------------------------------------------------ #
        # Normalisation                                                        #
        # ------------------------------------------------------------------ #
        norm = np.maximum(size_ema, 1.0)
        norm_short = flow_ema_s / norm
        norm_long = flow_ema_l / norm
        norm_accel = accel_ema / norm

        # ------------------------------------------------------------------ #
        # Large-order detection                                                #
        # ------------------------------------------------------------------ #
        is_large = order_sizes > size_ema * self.large_mult

        large_buy_streak = np.zeros(n, dtype=np.float64)
        large_sell_streak = np.zeros(n, dtype=np.float64)
        for i in range(n):
            prev_b = large_buy_streak[i - 1] if i > 0 else 0.0
            prev_s = large_sell_streak[i - 1] if i > 0 else 0.0
            if is_large[i]:
                if sides[i] > 0:
                    large_buy_streak[i] = prev_b + 1.0
                    large_sell_streak[i] = 0.0
                else:
                    large_sell_streak[i] = prev_s + 1.0
                    large_buy_streak[i] = 0.0
            else:
                large_buy_streak[i] = max(0.0, prev_b - 0.1)
                large_sell_streak[i] = max(0.0, prev_s - 0.1)

        # ------------------------------------------------------------------ #
        # Signal composition                                                   #
        # ------------------------------------------------------------------ #
        lb = large_buy_streak
        ls = large_sell_streak
        large_score = np.where(
            lb > 1, np.minimum(lb / 5.0, 1.0),
            np.where(ls > 1, -np.minimum(ls / 5.0, 1.0), 0.0)
        )

        flow_score = np.clip((norm_short + norm_long) / 2.0, -1.0, 1.0)
        accel_score = np.clip(norm_accel * 10.0, -1.0, 1.0)

        signal_score = np.clip(
            flow_score * self.w_flow +
            accel_score * self.w_accel +
            large_score * self.w_large,
            -1.0, 1.0
        )
        speed = np.abs(signal_score)

        # ------------------------------------------------------------------ #
        # Direction classification (vectorised)                               #
        # ------------------------------------------------------------------ #
        th = self.direction_threshold
        ns = norm_short
        nl = norm_long

        direction = np.full(n, "neutral", dtype=object)
        direction[(ns > th) & (nl > th)] = "up"
        direction[(ns < -th) & (nl < -th)] = "down"
        direction[(nl > th) & (ns < -th)] = "pullback"
        direction[(nl < -th) & (ns > th)] = "bounce"

        # ------------------------------------------------------------------ #
        # Trend structure: higher_low / lower_low detection                   #
        # Rolling window of 200 ticks; compare current rolling_low against    #
        # the previous recorded rolling_low to classify trend structure.      #
        # ------------------------------------------------------------------ #
        rolling_low_window = 200
        trend_structure = np.full(n, "flat", dtype=object)

        prev_low: float = prices[0]  # last recorded rolling_low

        for i in range(n):
            start = max(0, i - rolling_low_window + 1)
            current_rolling_low = float(np.min(prices[start: i + 1]))

            if current_rolling_low > prev_low:
                trend_structure[i] = "higher_low"
            elif current_rolling_low < prev_low:
                trend_structure[i] = "lower_low"
                prev_low = current_rolling_low  # update on new low
            else:
                trend_structure[i] = "flat"

        # ------------------------------------------------------------------ #
        # Signal trend: weakening vs strengthening via slow EMA of signal     #
        # alpha=0.005 => very slow EMA captures the "drift" direction         #
        # ------------------------------------------------------------------ #
        alpha_slow = 0.005
        signal_ema_slow = np.empty(n, dtype=np.float64)
        signal_ema_slow[0] = signal_score[0]
        for i in range(1, n):
            signal_ema_slow[i] = (
                alpha_slow * signal_score[i] + (1.0 - alpha_slow) * signal_ema_slow[i - 1]
            )

        # weakening: |signal| moving toward 0 relative to its slow EMA
        signal_trend = np.full(n, "neutral", dtype=object)
        abs_sig = np.abs(signal_score)
        abs_ema = np.abs(signal_ema_slow)
        signal_trend[abs_sig < abs_ema] = "weakening"
        signal_trend[abs_sig > abs_ema] = "strengthening"

        return {
            "times": trading_df["Datetime"].values,
            "prices": prices,
            "volumes": volumes,
            "sides": sides,
            "flows": flows,
            "flow_ema_short": flow_ema_s,
            "flow_ema_long": flow_ema_l,
            "norm_short": norm_short,
            "norm_long": norm_long,
            "norm_accel": norm_accel,
            "order_sizes": order_sizes,
            "size_ema": size_ema,
            "is_large": is_large,
            "large_buy_streak": large_buy_streak,
            "large_sell_streak": large_sell_streak,
            "signal_score": signal_score,
            "direction": direction,
            "speed": speed,
            "trend_structure": trend_structure,
            "signal_trend": signal_trend,
        }
