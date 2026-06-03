from typing import Optional
from .core.models import BacktestResult
from .core.backtest_engine import BacktestEngine
from .config import Settings, settings as default_settings
import asyncio

_result: Optional[BacktestResult] = None
_engine: Optional[BacktestEngine] = None


def get_result() -> BacktestResult:
    if _result is None:
        raise RuntimeError("Backtest result not initialized")
    return _result


def get_engine() -> BacktestEngine:
    if _engine is None:
        raise RuntimeError("Engine not initialized")
    return _engine


def set_result(result: BacktestResult, engine: BacktestEngine) -> None:
    global _result, _engine
    _result = result
    _engine = engine


async def rebuild_result(new_settings: Settings) -> None:
    loop = asyncio.get_event_loop()
    engine = BacktestEngine(new_settings)
    result = await loop.run_in_executor(None, engine.run)
    set_result(result, engine)
