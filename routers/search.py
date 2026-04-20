from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search_tickers(q: str, db: Session = Depends(get_db)):
    """Route utilitaire pour chercher une action par son nom ou son ticker."""
    return db.query(models.Company).filter(
        (models.Company.ticker.ilike(f"%{q}%")) |
        (models.Company.name.ilike(f"%{q}%"))
    ).limit(10).all()
