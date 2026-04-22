from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from collections import defaultdict
import models

router = APIRouter(prefix="/api", tags=["fundamentals"])

METRIC_CATEGORIES = [
    "market_analysis",
    "financial_health",
    "advanced_valuation",
    "income_growth",
    "balance_cash",
    "risk_market",
]

STMT_CATEGORIES = [
    "income_stmt_data",
    "balance_sheet_data",
    "cashflow_data",
]

# Champs scalaires de dividends_data à moyenner
DIVIDEND_SCALAR_FIELDS = [
    "dividend_yield",
    "dividend_rate",
    "payout_ratio",
    "five_year_avg_yield",
]


@router.get("/fundamentals")
def get_fundamentals(db: Session = Depends(get_db)):
    """Récupère la liste des entreprises et leurs indicateurs financiers complets."""
    return db.query(models.Company).all()


@router.get("/fundamentals/sector-averages/{sector}")
def get_sector_averages(sector: str, db: Session = Depends(get_db)):
    """
    Retourne la moyenne sectorielle de chaque métrique pour un secteur donné.
    Format : { "market_analysis": { "P/E Ratio": 25.3, ... }, ... }
    """
    companies = db.query(models.Company).filter(models.Company.sector == sector).all()
    if not companies:
        return {}

    result = {}
    for cat in METRIC_CATEGORIES:
        # Accumule les valeurs par nom de métrique
        buckets: dict[str, list[float]] = defaultdict(list)
        for company in companies:
            metrics = getattr(company, cat) or []
            for m in metrics:
                val = m.get("val")
                if val is not None and val != 0:
                    buckets[m["name"]].append(val)
        result[cat] = {
            name: sum(vals) / len(vals)
            for name, vals in buckets.items()
            if vals
        }

    # Moyennes sectorielles pour les états financiers (valeur la plus récente = vals[0])
    for stmt_cat in STMT_CATEGORIES:
        buckets: dict[str, list[float]] = defaultdict(list)
        for company in companies:
            stmt = getattr(company, stmt_cat) or {}
            items = stmt.get("items") or []
            for item in items:
                vals = item.get("vals") or []
                if vals and vals[0] is not None and vals[0] != 0:
                    buckets[item["name"]].append(vals[0])
        result[stmt_cat] = {
            name: sum(v) / len(v)
            for name, v in buckets.items()
            if v
        }

    # Moyennes sectorielles pour les dividendes
    div_scalar_buckets: dict[str, list[float]] = defaultdict(list)
    for company in companies:
        dd = company.dividends_data or {}
        for field in DIVIDEND_SCALAR_FIELDS:
            val = dd.get(field)
            if val is not None and val != 0:
                div_scalar_buckets[field].append(float(val))
    result["dividends_data"] = {
        field: round(sum(vals) / len(vals), 2)
        for field, vals in div_scalar_buckets.items()
        if vals
    }

    return result


@router.get("/fundamentals/sector-averages/{sector}/history")
def get_sector_history(sector: str, db: Session = Depends(get_db)):
    """
    Retourne l'historique annuel des moyennes sectorielles pour les états financiers.
    Format : {
      "income_stmt_data": {
        "Chiffre d'Affaires": { "2021": 120e9, "2022": 135e9, ... },
        ...
      },
      ...
    }
    """
    companies = db.query(models.Company).filter(models.Company.sector == sector).all()
    if not companies:
        return {}

    result = {}
    for stmt_cat in STMT_CATEGORIES:
        # metric_name → year_str → [val, val, ...]
        metric_history: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for company in companies:
            stmt = getattr(company, stmt_cat) or {}
            years = stmt.get("years") or []
            items = stmt.get("items") or []
            for item in items:
                for i, year in enumerate(years):
                    if i < len(item["vals"]):
                        val = item["vals"][i]
                        if val is not None and val != 0:
                            year_key = str(year)[:4]
                            metric_history[item["name"]][year_key].append(val)

        result[stmt_cat] = {
            name: {
                year: sum(vals) / len(vals)
                for year, vals in year_vals.items()
            }
            for name, year_vals in metric_history.items()
        }

    # Historique annuel des dividendes par secteur
    year_div_buckets: dict[str, list[float]] = defaultdict(list)
    for company in companies:
        dd = company.dividends_data or {}
        annual = dd.get("annual") or {}
        years = annual.get("years") or []
        items = annual.get("items") or []
        for item in items:
            vals = item.get("vals") or []
            for i, year in enumerate(years):
                if i < len(vals) and vals[i] is not None and vals[i] != 0:
                    year_div_buckets[str(year)].append(float(vals[i]))

    result["dividends_data"] = {
        "annual_dividend": {
            year: round(sum(vals) / len(vals), 4)
            for year, vals in year_div_buckets.items()
            if vals
        }
    }

    return result


@router.get("/fundamentals/{ticker}")
def get_company(ticker: str, db: Session = Depends(get_db)):
    """Récupère les données fondamentales d'une seule entreprise par son ticker exact."""
    company = db.query(models.Company).filter(models.Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' introuvable")
    return company
