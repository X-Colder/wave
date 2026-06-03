from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Tuple, Optional


@dataclass
class Trade:
    trade_id: int
    day: date
    time: datetime
    action: str              # "adjust"
    price: float             # Execution price (with slippage applied)
    position_before: float   # Position ratio before adjustment (0~1)
    position_after: float    # Position ratio after adjustment (0~1)
    position_delta: float    # Change amount (positive=buy, negative=sell)
    direction: str           # Direction signal at time of trade
    speed: float             # abs(signal_score)
    signal_score: float      # Combined signal score -1~+1
    realized_pnl: float      # Realized P&L (negative for commission on buys)
    capital_after: float


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[Tuple[datetime, float]]
    metrics: Dict[str, float]
    monthly_returns: Dict[str, float]
    daily_signals: Dict[date, List[dict]]   # per-day sampled flow states
    learned_params: Dict[str, float]        # best params found by random search
