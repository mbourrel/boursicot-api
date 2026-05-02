from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
import models

router = APIRouter(prefix="/api", tags=["prices"])


@router.get("/prices")
def get_prices(
    ticker: str = Query(..., description="Le ticker de l'action (ex: AAPL, AI.PA)"),
    interval: str = Query("1D", description="Intervalle souhaité : 15m, 1h, 1D, 1W"),
    limit: Optional[int] = Query(None, description="Nombre max de bougies à retourner"),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des prix pour un ticker et un intervalle donnés.
    Optimisé pour les graphiques Lightweight Charts.
    """
    query = db.query(models.Price).filter(
        models.Price.ticker == ticker,
        models.Price.interval == interval,
        models.Price.open_price.isnot(None),
        models.Price.high_price.isnot(None),
        models.Price.low_price.isnot(None),
        models.Price.close_price.isnot(None),
    ).order_by(models.Price.date.asc())

    if limit:
        prices = query.order_by(models.Price.date.desc()).limit(limit).all()
        prices.reverse()
    else:
        prices = query.all()

    if not prices:
        return []

    return [
        {
            "time":     p.date.isoformat(),
            "open":     p.open_price,
            "high":     p.high_price,
            "low":      p.low_price,
            "close":    p.close_price,
            "volume":   p.volume,
            "interval": p.interval,
        }
        for p in prices
    ]
