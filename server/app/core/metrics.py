import numpy as np
from typing import List, Dict, Tuple
from datetime import date
from .models import Trade


def annualized_return(equity_curve: List[Tuple], initial_capital: float) -> float:
    if len(equity_curve) < 2:
        return 0.0
    total_days = (equity_curve[-1][0].date() - equity_curve[0][0].date()).days
    if total_days <= 0:
        return 0.0
    final_equity = equity_curve[-1][1]
    total_return = (final_equity - initial_capital) / initial_capital
    years = total_days / 365.0
    return (1 + total_return) ** (1 / years) - 1


def max_drawdown(equity_curve: List[Tuple]) -> float:
    if len(equity_curve) == 0:
        return 0.0
    values = np.array([e[1] for e in equity_curve])
    peak = np.maximum.accumulate(values)
    drawdowns = (values - peak) / peak
    return float(np.min(drawdowns))


def sharpe_ratio(trades: List[Trade], risk_free_rate: float = 0.03) -> float:
    """
    Sharpe ratio based on realized P&L from sell-side adjustments.
    Only reduce-position trades generate realized returns.
    """
    sell_trades = [t for t in trades if t.position_delta < 0 and t.capital_after > 0]
    if len(sell_trades) < 2:
        return 0.0
    # Use realized_pnl / capital_after as the per-trade return
    rets = np.array([
        t.realized_pnl / t.capital_after for t in sell_trades
    ])
    mean_ret = np.mean(rets)
    std_ret = np.std(rets, ddof=1)
    if std_ret == 0:
        return 0.0
    first_time = sell_trades[0].time
    last_time = sell_trades[-1].time
    span_days = max((last_time.date() - first_time.date()).days, 1)
    trades_per_day = len(sell_trades) / span_days
    annualized_mean = mean_ret * trades_per_day * 252
    annualized_std = std_ret * np.sqrt(trades_per_day * 252)
    return (annualized_mean - risk_free_rate) / annualized_std


def win_rate(trades: List[Trade]) -> float:
    """Win rate = fraction of sell-side adjustments with positive realized P&L."""
    sell_trades = [t for t in trades if t.position_delta < 0]
    if len(sell_trades) == 0:
        return 0.0
    wins = sum(1 for t in sell_trades if t.realized_pnl > 0)
    return wins / len(sell_trades)


def profit_loss_ratio(trades: List[Trade]) -> float:
    """Average profit / average loss for sell-side adjustments."""
    sell_trades = [t for t in trades if t.position_delta < 0 and t.capital_after > 0]
    if len(sell_trades) == 0:
        return 0.0
    ret_vals = [t.realized_pnl / t.capital_after for t in sell_trades]
    wins = [r for r in ret_vals if r > 0]
    losses = [abs(r) for r in ret_vals if r < 0]
    if len(losses) == 0:
        return float("inf") if wins else 0.0
    if len(wins) == 0:
        return 0.0
    return float(np.mean(wins) / np.mean(losses))


def avg_position_ratio(trades: List[Trade]) -> float:
    """Time-weighted average position ratio (approximated by trade-count weighting)."""
    if not trades:
        return 0.0
    # Weight by time between consecutive trades (simple approximation)
    ratios = [t.position_after for t in trades]
    return float(np.mean(ratios))


def monthly_returns(trades: List[Trade], initial_capital: float) -> Dict[str, float]:
    if len(trades) == 0:
        return {}

    from collections import defaultdict
    monthly_pnl: Dict[str, float] = defaultdict(float)

    for t in trades:
        # All trades contribute realized_pnl (buys have negative realized_pnl = commission cost)
        key = t.time.strftime("%Y-%m")
        monthly_pnl[key] += t.realized_pnl

    result = {}
    capital = initial_capital
    for month in sorted(monthly_pnl.keys()):
        pnl = monthly_pnl[month]
        ret = pnl / capital if capital > 0 else 0.0
        result[month] = ret
        capital += pnl

    return result


def compute_all_metrics(
    trades: List[Trade],
    equity_curve: List[Tuple],
    initial_capital: float,
) -> Dict[str, float]:
    buy_trades = [t for t in trades if t.position_delta > 0]
    sell_trades = [t for t in trades if t.position_delta < 0]
    profitable_sells = [t for t in sell_trades if t.realized_pnl > 0]
    losing_sells = [t for t in sell_trades if t.realized_pnl <= 0]

    total_realized_pnl = sum(t.realized_pnl for t in trades)

    # Average position ratio (weighted by count)
    avg_pos = avg_position_ratio(trades) if trades else 0.0

    # Position turnover: sum of absolute position changes
    position_turnover = sum(abs(t.position_delta) for t in trades)

    return {
        "annualized_return": annualized_return(equity_curve, initial_capital),
        "max_drawdown": max_drawdown(equity_curve),
        "sharpe_ratio": sharpe_ratio(trades),
        "win_rate": win_rate(trades),
        "profit_loss_ratio": profit_loss_ratio(trades),
        "total_adjustments": float(len(trades)),
        "buy_adjustments": float(len(buy_trades)),
        "sell_adjustments": float(len(sell_trades)),
        "profitable_sells": float(len(profitable_sells)),
        "losing_sells": float(len(losing_sells)),
        "total_realized_pnl": total_realized_pnl,
        "realized_pnl_from_sells": sum(t.realized_pnl for t in sell_trades),
        "avg_position_ratio": avg_pos,
        "position_turnover": position_turnover,
        "final_capital": equity_curve[-1][1] if equity_curve else initial_capital,
        # Legacy aliases kept for frontend overview compatibility
        "total_trades": float(len(sell_trades)),
    }
