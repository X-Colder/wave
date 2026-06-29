from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class DailyRegime:
    regime: str
    max_position_scale: float
    min_position_override: float
    dif: float
    dea: float
    histogram: float
    divergence: Optional[str]
    refuel: bool


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    result = np.empty_like(values)
    alpha = 2.0 / (period + 1)
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1.0 - alpha) * result[i - 1]
    return result


class DailyRegimeClassifier:

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self._prev_dif: Optional[float] = None

    def compute_macd(self, closes: np.ndarray):
        ema_fast = _ema(closes, self.fast)
        ema_slow = _ema(closes, self.slow)
        dif = ema_fast - ema_slow
        dea = _ema(dif, self.signal)
        histogram = (dif - dea) * 2
        return dif, dea, histogram

    def detect_divergence(
        self, prices: np.ndarray, dif: np.ndarray, window: int = 60
    ) -> Optional[str]:
        if len(prices) < window:
            return None

        p = prices[-window:]
        d = dif[-window:]
        mid = window // 2

        p_left_min_idx = int(np.argmin(p[:mid]))
        p_right_min_idx = mid + int(np.argmin(p[mid:]))
        if p[p_right_min_idx] < p[p_left_min_idx] and d[p_right_min_idx] > d[p_left_min_idx]:
            return "bottom"

        p_left_max_idx = int(np.argmax(p[:mid]))
        p_right_max_idx = mid + int(np.argmax(p[mid:]))
        if p[p_right_max_idx] > p[p_left_max_idx] and d[p_right_max_idx] < d[p_left_max_idx]:
            return "top"

        return None

    def detect_refuel(self, dif: np.ndarray, dea: np.ndarray, histogram: np.ndarray, window: int = 10) -> bool:
        if len(dif) < window:
            return False
        recent_dif = dif[-window:]
        recent_dea = dea[-window:]
        recent_hist = histogram[-window:]
        if not np.all(recent_dif > 0):
            return False
        if not np.all(recent_dif > recent_dea):
            return False
        if np.any(recent_hist < 0):
            return False
        if recent_hist[-1] < recent_hist[0] and recent_hist[-1] > 0:
            return True
        return False

    def classify(self, daily_closes: List[float]) -> DailyRegime:
        n = len(daily_closes)
        if n < self.slow + self.signal:
            return DailyRegime(
                regime="NEUTRAL", max_position_scale=0.3,
                min_position_override=0.0,
                dif=0.0, dea=0.0, histogram=0.0,
                divergence=None, refuel=False,
            )

        closes = np.array(daily_closes, dtype=np.float64)
        dif_arr, dea_arr, hist_arr = self.compute_macd(closes)

        dif = float(dif_arr[-1])
        dea = float(dea_arr[-1])
        histogram = float(hist_arr[-1])
        prev_dif = self._prev_dif if self._prev_dif is not None else dif
        self._prev_dif = dif

        divergence = self.detect_divergence(closes, dif_arr)
        refuel = self.detect_refuel(dif_arr, dea_arr, hist_arr)

        dif_crossed_up = prev_dif <= 0 and dif > 0
        dif_crossed_down = prev_dif >= 0 and dif < 0

        if divergence == "bottom" and dif < 0:
            return DailyRegime(
                regime="BOTTOM_DIVERGENCE", max_position_scale=0.3,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=refuel,
            )

        if divergence == "top" and dif > 0:
            return DailyRegime(
                regime="TOP_DIVERGENCE", max_position_scale=0.2,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=refuel,
            )

        if dif_crossed_up:
            return DailyRegime(
                regime="TURNING_UP", max_position_scale=0.4,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=refuel,
            )

        if dif_crossed_down:
            return DailyRegime(
                regime="TURNING_DOWN", max_position_scale=0.15,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=refuel,
            )

        if dif > 0 and dea > 0:
            if refuel:
                return DailyRegime(
                    regime="STRONG_BULL", max_position_scale=1.0,
                    min_position_override=0.15,
                    dif=dif, dea=dea, histogram=histogram,
                    divergence=divergence, refuel=True,
                )
            if dif > dea:
                return DailyRegime(
                    regime="BULL", max_position_scale=1.0,
                    min_position_override=0.1,
                    dif=dif, dea=dea, histogram=histogram,
                    divergence=divergence, refuel=False,
                )
            else:
                return DailyRegime(
                    regime="BULL_PULLBACK", max_position_scale=0.6,
                    min_position_override=0.0,
                    dif=dif, dea=dea, histogram=histogram,
                    divergence=divergence, refuel=False,
                )

        if dif < 0 and dea < 0:
            return DailyRegime(
                regime="BEAR", max_position_scale=0.0,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=False,
            )

        if dif > 0 and dea <= 0:
            return DailyRegime(
                regime="TURNING_UP", max_position_scale=0.4,
                min_position_override=0.0,
                dif=dif, dea=dea, histogram=histogram,
                divergence=divergence, refuel=False,
            )

        return DailyRegime(
            regime="TURNING_DOWN", max_position_scale=0.15,
            min_position_override=0.0,
            dif=dif, dea=dea, histogram=histogram,
            divergence=divergence, refuel=False,
        )
