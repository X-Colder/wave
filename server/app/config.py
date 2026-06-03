from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    data_dir: str = Field(default="./002484", alias="DATA_DIR")

    # Parameter learning: use first N days to optimize params via random search
    train_days: int = 60
    param_search_trials: int = 50

    # Position management
    min_position: float = 0.2
    max_position: float = 0.8
    min_position_delta: float = 0.05

    # Minimum tick interval between two consecutive trades (throttle)
    min_trade_interval: int = 100

    # Cost parameters
    commission_rate: float = 0.001
    slippage_rate: float = 0.0001
    initial_capital: float = 100000.0

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()
