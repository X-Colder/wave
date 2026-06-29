import json
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    data_dir: str = Field(default="./002484", alias="DATA_DIR")
    strategy: str = Field(default="", alias="STRATEGY")

    # Parameter learning: use first N days to optimize params via random search
    train_days: int = 235
    param_search_trials: int = 0

    # Position management
    min_position: float = 0.2
    max_position: float = 0.8
    min_position_delta: float = 0.125

    # Minimum tick interval between two consecutive trades (throttle)
    min_trade_interval: int = 100

    # Cost parameters
    commission_rate: float = 0.001
    slippage_rate: float = 0.0001
    initial_capital: float = 100000.0

    # Market mode: "t1" = A-share T+1, "t0" = T+0 (futures/crypto)
    market_mode: str = "t1"

    # Daily MACD regime parameters (5,10,4 validated across 18 stocks)
    macd_fast: int = 5
    macd_slow: int = 10
    macd_signal: int = 4

    # T+0 specific parameters
    t0_allow_short: bool = False
    t0_max_trades_per_day: int = 20
    t0_intraday_close: bool = True

    model_config = {"env_file": ".env", "populate_by_name": True}


def _load_strategy(strategy_name: str) -> dict:
    """Load strategy params from config/strategies/{name}.json"""
    search_paths = [
        Path("config/strategies") / f"{strategy_name}.json",
        Path(__file__).parent.parent.parent / "config" / "strategies" / f"{strategy_name}.json",
    ]
    for p in search_paths:
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            return data.get("params", {})
    return {}


def load_settings() -> Settings:
    base = Settings()
    strategy_name = base.strategy or os.environ.get("STRATEGY", "")
    if strategy_name:
        overrides = _load_strategy(strategy_name)
        if overrides:
            merged = base.model_dump()
            merged.update({k: v for k, v in overrides.items() if k in merged and v is not None})
            return Settings.model_validate(merged)
    return base


settings = load_settings()
