from fastapi import APIRouter, Depends, Query
from ..dependencies import get_result
from ..core.models import BacktestResult

router = APIRouter()


@router.get("/trades")
async def list_trades(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    result: BacktestResult = Depends(get_result),
):
    trades = result.trades
    total = len(trades)

    sell_trades = [t for t in trades if t.position_delta < 0]
    buy_trades = [t for t in trades if t.position_delta > 0]
    profitable_sells = [t for t in sell_trades if t.realized_pnl > 0]
    losing_sells = [t for t in sell_trades if t.realized_pnl <= 0]

    avg_profit = (
        sum(t.realized_pnl / t.capital_after for t in profitable_sells if t.capital_after > 0)
        / len(profitable_sells) if profitable_sells else 0.0
    )
    avg_loss = (
        sum(abs(t.realized_pnl / t.capital_after) for t in losing_sells if t.capital_after > 0)
        / len(losing_sells) if losing_sells else 0.0
    )

    start = (page - 1) * size
    end = start + size
    page_trades = trades[start:end]

    items = []
    for t in page_trades:
        is_sell = t.position_delta < 0
        items.append({
            "id": t.trade_id,
            "time": t.time.isoformat(),
            "action": "加仓" if t.position_delta > 0 else "减仓",
            "price": round(t.price, 4),
            "position_before": round(t.position_before * 100, 1),
            "position_after": round(t.position_after * 100, 1),
            "position_delta": round(t.position_delta * 100, 1),
            "direction": t.direction,
            "signal_score": round(t.signal_score, 4),
            "speed": round(t.speed, 4),
            "pnl": round(t.realized_pnl, 2),
            "pnl_type": "盈亏" if is_sell else "佣金",
            "return_pct": (
                round(t.realized_pnl / t.capital_after, 6) if t.capital_after else 0
            ),
            "capital_after": round(t.capital_after, 2),
        })

    return {
        "stats": {
            "total_adjustments": total,
            "buy_count": len(buy_trades),
            "sell_count": len(sell_trades),
            "profitable_sells": len(profitable_sells),
            "losing_sells": len(losing_sells),
            "total_realized_pnl": round(sum(t.realized_pnl for t in trades), 2),
            "avg_profit": round(avg_profit, 6),
            "avg_loss": round(avg_loss, 6),
        },
        "trades": items,
        "total": total,
        "page": page,
        "size": size,
    }
