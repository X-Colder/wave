import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.backtest_engine import BacktestEngine
from .dependencies import set_result
from .api.router import router

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting pipeline: loading data and running backtest")
    loop = asyncio.get_event_loop()
    engine = BacktestEngine(settings)
    result = await loop.run_in_executor(None, engine.run)
    set_result(result, engine)
    logger.info(
        f"Pipeline complete: {len(result.trades)} trades, "
        f"final capital={result.metrics.get('final_capital', 0):.2f}"
    )
    yield
    logger.info("Shutting down")


app = FastAPI(title="Wave Pattern Backtest API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
