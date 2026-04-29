from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api", tags=["exchange-rates"])


@router.get("/exchange-rates")
def get_exchange_rates(db: Session = Depends(get_db)):
    """
    Retourne les taux de change courants mis à jour 1x/jour via FMP.
    Format : { "rates": { "EURUSD": 1.08, "GBPUSD": 1.27, ... }, "updated_at": "2026-04-29T08:00:00" }
    """
    rows = db.query(models.ExchangeRate).all()
    if not rows:
        return {"rates": {}, "updated_at": None}

    rates = {}
    updated_at = None
    for r in rows:
        rates[r.pair] = r.rate
        if updated_at is None or r.updated_at > updated_at:
            updated_at = r.updated_at

    return {
        "rates": rates,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }
