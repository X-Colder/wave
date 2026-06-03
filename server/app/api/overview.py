from fastapi import APIRouter, Depends
import numpy as np
from ..dependencies import get_result
from ..core.models import BacktestResult

router = APIRouter()


@router.get("/overview")
async def get_overview(result: BacktestResult = Depends(get_result)):
    equity_data = []
    peak = 0.0
    for t, v in result.equity_curve:
        peak = max(peak, v)
        dd = (v - peak) / peak if peak > 0 else 0.0
        equity_data.append({
            "date": t.strftime("%Y-%m-%d %H:%M"),
            "equity": round(v, 2),
            "drawdown": round(dd, 6),
        })

    initial = result.equity_curve[0][1] if result.equity_curve else 100000
    final = result.equity_curve[-1][1] if result.equity_curve else 100000
    total_return = (final - initial) / initial

    m = result.metrics

    metrics = {
        "total_return": round(total_return, 6),
        "annual_return": round(m.get("annualized_return", 0), 6),
        "max_drawdown": round(m.get("max_drawdown", 0), 6),
        "sharpe_ratio": round(m.get("sharpe_ratio", 0), 4),
        "win_rate": round(m.get("win_rate", 0), 4),
        "profit_loss_ratio": round(m.get("profit_loss_ratio", 0), 4),
        # Adjustment counts
        "total_adjustments": int(m.get("total_adjustments", 0)),
        "buy_adjustments": int(m.get("buy_adjustments", 0)),
        "sell_adjustments": int(m.get("sell_adjustments", 0)),
        "profitable_sells": int(m.get("profitable_sells", 0)),
        "losing_sells": int(m.get("losing_sells", 0)),
        # P&L
        "total_realized_pnl": round(m.get("total_realized_pnl", 0), 2),
        "realized_pnl_from_sells": round(m.get("realized_pnl_from_sells", 0), 2),
        # Position metrics
        "avg_position_ratio": round(m.get("avg_position_ratio", 0), 4),
        "position_turnover": round(m.get("position_turnover", 0), 4),
        # Legacy alias for frontend
        "total_trades": int(m.get("total_trades", 0)),
        "final_capital": round(m.get("final_capital", initial), 2),
    }

    monthly = [
        {"month": k, "return": round(v, 6)}
        for k, v in sorted(result.monthly_returns.items())
    ]

    # Learned parameters from Phase 1 optimisation
    lp = result.learned_params
    learned_params = {k: round(float(v), 6) for k, v in lp.items()} if lp else {}

    return {
        "equity_curve": equity_data,
        "metrics": metrics,
        "monthly_returns": monthly,
        "learned_params": learned_params,
    }
