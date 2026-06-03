import numpy as np
from typing import List, Dict, Optional
from .models import WindowFeature, PatternKey

# All 6 feature attributes used for bucketing
_FEATURE_ATTRS = [
    "force_ratio",
    "price_momentum",
    "trade_acceleration",
    "force_ratio_delta",
    "momentum_delta",
    "acceleration_delta",
]


class PatternBucket:
    """
    Assigns WindowFeature objects to 6-dimensional pattern buckets.
    Static features (force_ratio, price_momentum, trade_acceleration) use num_bins buckets.
    Delta features (force_ratio_delta, momentum_delta, acceleration_delta) also use num_bins buckets.
    Total patterns: num_bins^6 (default 3^6 = 729).
    """

    def __init__(self, num_bins: int = 3):
        self.num_bins = num_bins
        self._edges: Dict[str, np.ndarray] = {}
        self._fitted = False

    def fit(self, features: List[WindowFeature]) -> None:
        if not features:
            return

        quantiles = np.linspace(0, 100, self.num_bins + 1)

        for attr in _FEATURE_ATTRS:
            vals = np.array([getattr(f, attr) for f in features], dtype=float)
            edges = np.percentile(vals, quantiles)
            edges[0] = -np.inf
            edges[-1] = np.inf
            self._edges[attr] = edges

        self._fitted = True

    def transform(self, feature: WindowFeature) -> Optional[PatternKey]:
        if not self._fitted:
            return None

        def _bin(attr: str) -> int:
            edges = self._edges[attr]
            val = getattr(feature, attr)
            b = int(np.searchsorted(edges[1:-1], val))
            return min(b, self.num_bins - 1)

        return PatternKey(
            force_bin=_bin("force_ratio"),
            momentum_bin=_bin("price_momentum"),
            accel_bin=_bin("trade_acceleration"),
            force_delta_bin=_bin("force_ratio_delta"),
            momentum_delta_bin=_bin("momentum_delta"),
            accel_delta_bin=_bin("acceleration_delta"),
        )

    def is_fitted(self) -> bool:
        return self._fitted

    def clone_fitted(self) -> "PatternBucket":
        new = PatternBucket(self.num_bins)
        for attr, edges in self._edges.items():
            new._edges[attr] = edges.copy()
        new._fitted = self._fitted
        return new
