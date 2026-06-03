from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..dependencies import rebuild_result
from ..config import settings as global_settings

router = APIRouter()


class RerunRequest(BaseModel):
    train_days: Optional[int] = None
    param_search_trials: Optional[int] = None
    min_position: Optional[float] = None
    max_position: Optional[float] = None
    min_position_delta: Optional[float] = None
    min_trade_interval: Optional[int] = None
    commission_rate: Optional[float] = None
    slippage_rate: Optional[float] = None
    initial_capital: Optional[float] = None


@router.get("/config")
async def get_config():
    return {
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
    }


@router.post("/config/rerun")
async def rerun(req: RerunRequest):
    from ..config import Settings

    overrides = {k: v for k, v in req.model_dump().items() if v is not None}
    current = {
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
    }
    current.update(overrides)

    new_settings = Settings.model_validate(current)
    await rebuild_result(new_settings)

    return {"status": "ok", "config": current}
