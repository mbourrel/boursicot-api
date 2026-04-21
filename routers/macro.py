import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fredapi import Fred
from sqlalchemy.orm import Session

from database import get_db
from services.macro_service import get_cycle_data, get_liquidity_data, get_cycle_history
from schemas.macro import MacroCycleOut, MacroCycleHistoryOut, MacroLiquidityOut

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/cycle", response_model=MacroCycleOut)
def get_macro_cycle(db: Session = Depends(get_db)):
    """Phase du cycle économique (INDPRO + CPIAUCSL, FRED). Cache 24 h."""
    return get_cycle_data(db)


@router.get("/liquidity", response_model=MacroLiquidityOut)
def get_macro_liquidity(db: Session = Depends(get_db)):
    """M2SL vs BTC-USD normalisés base 100 depuis jan 2020. Cache 24 h."""
    return get_liquidity_data(db)


@router.get("/cycle/history", response_model=MacroCycleHistoryOut)
def get_macro_cycle_history(db: Session = Depends(get_db)):
    """Historique mensuel du cycle depuis 1948 (~920 points). Cache 24 h."""
    return get_cycle_history(db)


@router.get("/ping")
def macro_ping():
    """Diagnostic : vérifie que la clé FRED est configurée et accessible."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "detail": "FRED_API_KEY absent des variables d'environnement"}
    try:
        fred = Fred(api_key=api_key)
        test = fred.get_series(
            "FEDFUNDS",
            observation_start=datetime.now() - timedelta(days=60),
            observation_end=datetime.now(),
        )
        return {"status": "ok", "fred_key_valid": True, "sample_points": len(test)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
