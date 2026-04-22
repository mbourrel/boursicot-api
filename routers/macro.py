from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from database import get_db
from services.macro_service import get_cycle_data, get_liquidity_data, get_cycle_history, get_rates_data
from schemas.macro import MacroCycleOut, MacroCycleHistoryOut, MacroLiquidityOut, MacroRatesOut

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


@router.get("/rates", response_model=MacroRatesOut)
def get_macro_rates(db: Session = Depends(get_db)):
    """Taux directeurs (Fed, BCE, BoE, BoJ) + rendements obligataires (US, DE, FR, UK). Cache 6 h."""
    return get_rates_data(db)
