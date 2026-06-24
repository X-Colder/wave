from fastapi import APIRouter, Depends, Query
from datetime import time as dtime
from ..dependencies import get_result, get_engine
from ..core.models import BacktestResult
from ..core.backtest_engine import BacktestEngine

router = APIRouter()


@router.get("/trades")
async def list_trades(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    sort_by: str = Query(default=""),
    sort_order: str = Query(default="desc"),
    result: BacktestResult = Depends(get_result),
    engine: BacktestEngine = Depends(get_engine),
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

    # Pre-compute high_after_pct for all trades (needed for sorting)
    all_items = []
    for t in trades:
        is_sell = t.position_delta < 0
        item = {
            "id": t.trade_id,
            "time": t.time.isoformat(),
            "action": "加仓" if t.position_delta > 0 else "减仓",
            "side": "buy" if t.position_delta > 0 else "sell",
            "reason": t.action,
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
            "high_after": None,
            "high_after_pct": None,
            "ticks_to_high": None,
        }

        if is_sell:
            df = engine.loader.get_cached(t.day)
            if df is not None:
                mask = ((df['Datetime'].dt.time >= dtime(9, 30)) & (df['Datetime'].dt.time <= dtime(11, 30))) | \
                       ((df['Datetime'].dt.time >= dtime(13, 0)) & (df['Datetime'].dt.time <= dtime(15, 0)))
                tdf = df[mask]
                after = tdf[tdf['Datetime'] > t.time]
                if len(after) > 0:
                    prices_after = after['Price'].values
                    high_idx = prices_after.argmax()
                    high_price = float(prices_after[high_idx])
                    item["high_after"] = round(high_price, 4)
                    item["high_after_pct"] = round((high_price - t.price) / t.price * 100, 2)
                    item["ticks_to_high"] = int(high_idx)

        all_items.append(item)

    # Sort if requested
    if sort_by:
        reverse = sort_order == "desc"
        def sort_key(x):
            v = x.get(sort_by)
            if v is None:
                return float('-inf') if reverse else float('inf')
            return v
        all_items.sort(key=sort_key, reverse=reverse)

    page_items = all_items[start:end]

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
        "trades": page_items,
        "total": total,
        "page": page,
        "size": size,
    }
