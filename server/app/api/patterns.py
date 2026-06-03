from fastapi import APIRouter, Depends
from ..dependencies import get_result
from ..core.models import BacktestResult

router = APIRouter()


@router.get("/patterns")
async def list_patterns(result: BacktestResult = Depends(get_result)):
    """
    Returns the learned EMA parameters from the Phase 1 random-search optimisation,
    together with a brief description of each parameter.
    """
    lp = result.learned_params or {}

    param_descriptions = {
        "ema_short_period": "Short EMA period (ticks) — fast signal window",
        "ema_long_period": "Long EMA period (ticks) — slow trend window",
        "accel_period": "Acceleration EMA period — rate-of-change smoothing",
        "size_ema_period": "Order-size EMA period — baseline for large-order detection",
        "direction_threshold": "Normalised flow threshold to confirm a directional signal",
        "large_order_mult": "Multiple of avg order size to classify a tick as large",
        "w_flow": "Weight assigned to flow-direction score in signal composition",
        "w_accel": "Weight assigned to acceleration score in signal composition",
        "w_large_order": "Weight assigned to large-order streak score in signal composition",
    }

    params = []
    for k, desc in param_descriptions.items():
        params.append({
            "name": k,
            "value": round(float(lp.get(k, 0)), 6),
            "description": desc,
        })

    return {
        "learned_params": params,
        "total": len(params),
    }
