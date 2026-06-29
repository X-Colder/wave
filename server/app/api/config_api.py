import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from ..dependencies import rebuild_result
from ..config import settings as global_settings, _load_strategy


router = APIRouter()

STRATEGIES_DIR = Path(__file__).parent.parent.parent.parent / "config" / "strategies"


class RerunRequest(BaseModel):
    strategy: Optional[str] = None
    train_days: Optional[int] = None
    param_search_trials: Optional[int] = None
    min_position: Optional[float] = None
    max_position: Optional[float] = None
    min_position_delta: Optional[float] = None
    min_trade_interval: Optional[int] = None
    commission_rate: Optional[float] = None
    slippage_rate: Optional[float] = None
    initial_capital: Optional[float] = None
    market_mode: Optional[str] = None
    macd_fast: Optional[int] = None
    macd_slow: Optional[int] = None
    macd_signal: Optional[int] = None


def _current_config() -> dict:
    return {
        "strategy": global_settings.strategy,
        "data_dir": global_settings.data_dir,
        "train_days": global_settings.train_days,
        "param_search_trials": global_settings.param_search_trials,
        "min_position": global_settings.min_position,
        "max_position": global_settings.max_position,
        "min_position_delta": global_settings.min_position_delta,
        "min_trade_interval": global_settings.min_trade_interval,
        "commission_rate": global_settings.commission_rate,
        "slippage_rate": global_settings.slippage_rate,
        "initial_capital": global_settings.initial_capital,
        "market_mode": global_settings.market_mode,
        "macd_fast": global_settings.macd_fast,
        "macd_slow": global_settings.macd_slow,
        "macd_signal": global_settings.macd_signal,
    }


@router.get("/config")
async def get_config():
    return _current_config()


@router.get("/strategies")
async def list_strategies():
    strategies = []
    if STRATEGIES_DIR.exists():
        for f in sorted(STRATEGIES_DIR.glob("*.json")):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                strategies.append({
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "created": data.get("created", ""),
                    "backtest": data.get("backtest", {}),
                    "notes": data.get("notes", ""),
                })
            except Exception:
                continue
    return {"strategies": strategies, "current": global_settings.strategy or "default"}


@router.post("/config/rerun")
async def rerun(req: RerunRequest):
    from ..config import Settings

    current = _current_config()

    if req.strategy:
        strategy_params = _load_strategy(req.strategy)
        if strategy_params:
            current.update({k: v for k, v in strategy_params.items() if k in current and v is not None})
            current["strategy"] = req.strategy

    overrides = {k: v for k, v in req.model_dump().items() if v is not None and k != "strategy"}
    current.update(overrides)

    new_settings = Settings.model_validate(current)
    await rebuild_result(new_settings)

    return {"status": "ok", "strategy": current.get("strategy", ""), "config": current}
