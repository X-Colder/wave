from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from ..dependencies import get_result, get_engine
from ..core.models import BacktestResult
from ..core.backtest_engine import BacktestEngine
from ..utils.time_utils import MORNING_START, MORNING_END, AFTERNOON_START, AFTERNOON_END

router = APIRouter()


@router.get("/intraday/dates")
async def list_dates(result: BacktestResult = Depends(get_result)):
    dates = sorted(result.daily_signals.keys())
    return {"dates": [d.isoformat() for d in dates]}


@router.get("/intraday/{date_str}")
async def get_intraday(
    date_str: str,
    result: BacktestResult = Depends(get_result),
    engine: BacktestEngine = Depends(get_engine),
):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    signals_raw = result.daily_signals.get(d)
    if signals_raw is None:
        raise HTTPException(status_code=404, detail="Date not found")

    # Raw tick chart data (sampled at most 2000 points)
    df = engine.loader.get_cached(d)
    ticks = []
    if df is not None:
        trading = df[
            (
                (df["Datetime"].dt.time >= MORNING_START) &
                (df["Datetime"].dt.time <= MORNING_END)
            ) | (
                (df["Datetime"].dt.time >= AFTERNOON_START) &
                (df["Datetime"].dt.time <= AFTERNOON_END)
            )
        ]
        step = max(1, len(trading) // 2000)
        sampled = trading.iloc[::step]
        ticks = [
            {
                "time": row["Datetime"].strftime("%H:%M:%S"),
                "price": float(row["Price"]),
                "volume": int(row["Volume"]),
            }
            for _, row in sampled.iterrows()
        ]

    # Split signals into feature samples (action=="sample") and trade events
    features = []
    signals = []
    for s in signals_raw:
        action = s.get("action", "sample")

        if action == "sample":
            features.append({
                "time": s.get("time", ""),
                "price": s.get("price", 0),
                "norm_short": round(s.get("norm_short", 0), 4),
                "norm_long": round(s.get("norm_long", 0), 4),
                "signal_score": round(s.get("signal_score", 0), 4),
                "final_score": round(s.get("final_score", s.get("position_signal", 0)), 4),
                "direction": s.get("direction", "neutral"),
                "position": round(s.get("position", 0) * 100, 1),
            })

        elif action in ("buy", "sell"):
            signals.append({
                "time": s.get("time", ""),
                "price": s.get("price", 0),
                "type": action,
                "action": action,
                "reason": s.get("reason", action),
                "direction": s.get("direction", "neutral"),
                "signal_score": round(s.get("signal_score", 0), 4),
                "final_score": round(s.get("final_score", s.get("position_signal", 0)), 4),
                "speed": round(s.get("speed", 0), 4),
                "position_before": round(s.get("position_before", 0) * 100, 1),
                "position_after": round(s.get("position_after", 0) * 100, 1),
                "delta": round(s.get("delta", 0) * 100, 1),
                "realized_pnl": round(s.get("realized_pnl", 0), 2),
            })

    return {
        "date": date_str,
        "ticks": ticks,
        "features": features,
        "signals": signals,
    }
