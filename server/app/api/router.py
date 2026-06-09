from fastapi import APIRouter
from .overview import router as overview_router
from .patterns import router as patterns_router
from .trades import router as trades_router
from .intraday import router as intraday_router
from .config_api import router as config_router
from .playback import router as playback_router

router = APIRouter(prefix="/api")

router.include_router(overview_router)
router.include_router(patterns_router)
router.include_router(trades_router)
router.include_router(intraday_router)
router.include_router(config_router)
router.include_router(playback_router)


@router.get("/health")
async def health():
    return {"status": "ok"}
