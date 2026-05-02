from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from assets_config import ASSET_DICTIONARY
from schemas.assets import AssetOut
from database import get_db
from models import Company

router = APIRouter(prefix="/api", tags=["assets"])


@router.get("/assets", response_model=list[AssetOut])
def get_assets(db: Session = Depends(get_db)):
    """
    Retourne le catalogue complet des actifs (ticker → nom + country + sector).
    Source unique de vérité partagée avec les scripts de seeding.
    """
    companies = db.query(Company.ticker, Company.country, Company.sector, Company.asset_class).all()
    company_map = {c.ticker: c for c in companies}

    return [
        {
            "ticker":      ticker,
            "name":        name,
            "country":     company_map[ticker].country     if ticker in company_map else None,
            "sector":      company_map[ticker].sector      if ticker in company_map else None,
            "asset_class": company_map[ticker].asset_class if ticker in company_map else None,
        }
        for ticker, name in ASSET_DICTIONARY.items()
    ]
