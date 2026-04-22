import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fredapi import Fred
from sqlalchemy.orm import Session

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


@router.get("/debug/cb-series")
def debug_cb_series():
    """Diagnostic temporaire : teste les séries FRED candidates pour BoE et BoJ."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return {"error": "FRED_API_KEY manquant"}

    fred = Fred(api_key=api_key)
    end   = datetime.now()
    start = end - timedelta(days=365)

    candidates = [
        ("BoE", "IRSTCB01GBM156N"),
        ("BoE", "BOERUKM"),
        ("BoE", "INTGBRSTM193N"),
        ("BoE", "IUDSOIA"),
        ("BoJ", "IRSTCB01JPM156N"),
        ("BoJ", "INTJPNSTM193N"),
        ("BoJ", "IRSTJPRESXNPT"),
    ]

    results = []
    for bank, sid in candidates:
        try:
            s = fred.get_series(sid, observation_start=start, observation_end=end).dropna()
            results.append({
                "bank": bank, "series": sid,
                "status": "empty" if s.empty else "ok",
                "last_value": None if s.empty else round(float(s.iloc[-1]), 3),
                "last_date": None if s.empty else s.index[-1].strftime("%Y-%m-%d"),
                "n_points": len(s),
            })
        except Exception as e:
            results.append({"bank": bank, "series": sid, "status": "error", "detail": str(e)})

    return {"results": results}
