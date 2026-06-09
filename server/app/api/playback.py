"""
Playback API — returns per-tick animation frames for a single trading day.

Sampling strategy:
  - One frame every SAMPLE_INTERVAL ticks (default 50).
  - Trade-event ticks are always preserved, even if they fall between sample points.
  - Each frame carries: tick_index, time, price, signal, position,
    trend_structure, capital, and an optional trade event dict.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from typing import List, Optional, Dict, Any

import pandas as pd

from ..dependencies import get_result, get_engine
from ..core.models import BacktestResult
from ..core.backtest_engine import BacktestEngine
from ..core.flow_engine import FlowEngine
from ..utils.time_utils import MORNING_START, MORNING_END, AFTERNOON_START, AFTERNOON_END

router = APIRouter()

SAMPLE_INTERVAL = 50  # ticks per frame for animation


def _filter_trading(df):
    """Return only ticks within official trading hours."""
    t = df["Datetime"].dt.time
    mask = (
        ((t >= MORNING_START) & (t <= MORNING_END)) |
        ((t >= AFTERNOON_START) & (t <= AFTERNOON_END))
    )
    return df[mask].reset_index(drop=True)


@router.get("/playback/{date_str}")
async def get_playback(
    date_str: str,
    result: BacktestResult = Depends(get_result),
    engine: BacktestEngine = Depends(get_engine),
) -> Dict[str, Any]:
    """
    Return full tick-by-tick playback data for one trading day.

    Frames are sampled every SAMPLE_INTERVAL ticks; trade-event frames are
    always included regardless of whether they fall on a sample boundary.

    Response schema:
      {
        "date": "2020-02-25",
        "frames": [
          {
            "tick_index": int,
            "time": "HH:MM:SS",
            "price": float,
            "signal": float,
            "position": float,       # 0..1 ratio
            "trend_structure": str,  # "higher_low" | "lower_low" | "flat"
            "signal_trend": str,     # "weakening" | "strengthening" | "neutral"
            "capital": float,
            "event": null | {
              "action": str,         # "buy" | "sell" | trailing_stop label ...
              "delta": float,
              "pnl": float
            }
          },
          ...
        ],
        "summary": {
          "open": float,
          "high": float,
          "low": float,
          "close": float,
          "total_trades": int,
          "day_pnl": float
        }
      }
    """
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")

    signals_raw = result.daily_signals.get(d)
    if signals_raw is None:
        raise HTTPException(status_code=404, detail=f"Date {date_str} not found in backtest results")

    # Load raw tick data
    df = engine.loader.get_cached(d)
    if df is None or len(df) == 0:
        raise HTTPException(status_code=404, detail=f"No tick data for {date_str}")

    trading_df = _filter_trading(df)
    if len(trading_df) == 0:
        raise HTTPException(status_code=404, detail=f"No trading-hours ticks for {date_str}")

    # Re-run flow engine to get per-tick signal / trend_structure arrays
    fe = FlowEngine(result.learned_params)
    tick_data = fe.process_day(d, df)

    if not tick_data:
        raise HTTPException(status_code=404, detail=f"Flow engine returned no data for {date_str}")

    n = len(tick_data["prices"])
    times_arr = tick_data["times"]
    prices_arr = tick_data["prices"]
    signal_arr = tick_data["signal_score"]
    trend_arr = tick_data["trend_structure"]
    signal_trend_arr = tick_data["signal_trend"]

    # Build a lookup: time string -> trade event from signals_raw
    # signals_raw contains both "sample" entries and trade entries (buy/sell/adjust labels)
    trade_events_by_time: Dict[str, Dict[str, Any]] = {}
    day_pnl = 0.0
    trade_count = 0

    for s in signals_raw:
        action = s.get("action", "sample")
        if action not in ("sample",):
            t_str = s.get("time", "")
            trade_events_by_time[t_str] = {
                "action": action,
                "delta": s.get("delta", 0.0),
                "pnl": s.get("realized_pnl", 0.0),
            }
            day_pnl += s.get("realized_pnl", 0.0)
            if action in ("buy", "sell"):
                trade_count += 1

    # Reconstruct position and capital timeline from signals_raw for each sampled tick.
    # signals_raw is already time-ordered; interpolate position/capital between events.
    # Build a quick time -> (position, capital) map from signals_raw
    pos_cap_by_time: Dict[str, tuple] = {}
    last_position = 0.0
    last_capital = 100000.0  # default; will be overridden by first event

    for s in signals_raw:
        t_str = s.get("time", "")
        pos = s.get("position", last_position)
        # "capital_after" not stored in signals dict; derive from realized_pnl accumulation
        pos_cap_by_time[t_str] = (pos, s.get("realized_pnl", 0.0))
        last_position = pos

    # Walk the equity curve for the day to get capital snapshots
    # The equity curve stores (datetime, capital); filter to this day
    day_equity: List[tuple] = [
        (ts, cap)
        for ts, cap in result.equity_curve
        if hasattr(ts, "date") and ts.date() == d
    ]
    # Build capital interpolation: create a sorted list of (tick_index, capital)
    # by matching equity curve timestamps to the nearest tick
    price_times = [
        pd.Timestamp(times_arr[i]).to_pydatetime() for i in range(n)
    ]

    def _find_capital_at(tick_dt) -> float:
        """Return the last known capital at or before tick_dt."""
        cap = 100000.0
        for ts, c in day_equity:
            if ts <= tick_dt:
                cap = c
            else:
                break
        return cap

    # Determine which tick indices are "trade event" ticks
    trade_tick_indices = set()
    for idx in range(n):
        t_str = pd.Timestamp(times_arr[idx]).strftime("%H:%M:%S")
        if t_str in trade_events_by_time:
            trade_tick_indices.add(idx)

    # Build position timeline by walking signals_raw in tick order
    # Reconstruct position at each tick via nearest preceding signal
    sig_timeline: List[tuple] = []  # (time_str, position)
    for s in signals_raw:
        sig_timeline.append((s.get("time", ""), s.get("position", 0.0)))
    # Sort by time string (HH:MM:SS strings sort lexicographically correctly)
    sig_timeline.sort(key=lambda x: x[0])

    def _position_at(time_str: str) -> float:
        """Return position at or before time_str."""
        pos = 0.0
        for ts, p in sig_timeline:
            if ts <= time_str:
                pos = p
            else:
                break
        return pos

    # Build frames
    frames: List[Dict[str, Any]] = []
    for i in range(n):
        is_sample = (i % SAMPLE_INTERVAL == 0)
        is_trade = (i in trade_tick_indices)
        if not (is_sample or is_trade):
            continue

        tick_dt = price_times[i]
        time_str = tick_dt.strftime("%H:%M:%S")
        pos = _position_at(time_str)
        cap = _find_capital_at(tick_dt)

        event = trade_events_by_time.get(time_str)

        frames.append({
            "tick_index": i,
            "time": time_str,
            "price": round(float(prices_arr[i]), 4),
            "signal": round(float(signal_arr[i]), 4),
            "position": round(float(pos), 4),
            "trend_structure": str(trend_arr[i]),
            "signal_trend": str(signal_trend_arr[i]),
            "capital": round(float(cap), 2),
            "event": event,
        })

    # Summary stats
    all_prices = prices_arr
    summary = {
        "open": round(float(all_prices[0]), 4),
        "high": round(float(all_prices.max()), 4),
        "low": round(float(all_prices.min()), 4),
        "close": round(float(all_prices[-1]), 4),
        "total_trades": trade_count,
        "day_pnl": round(day_pnl, 2),
    }

    return {
        "date": date_str,
        "frames": frames,
        "summary": summary,
    }
