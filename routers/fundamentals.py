from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/api", tags=["fundamentals"])


@router.get("/fundamentals")
def get_fundamentals(db: Session = Depends(get_db)):
    """Récupère la liste des entreprises et leurs indicateurs financiers complets."""
    return db.query(models.Company).all()


@router.get("/fundamentals/{ticker}")
def get_company(ticker: str, db: Session = Depends(get_db)):
    """Récupère les données fondamentales d'une seule entreprise par son ticker exact."""
    company = db.query(models.Company).filter(models.Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' introuvable")
    return company
