from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from collections import defaultdict
import httpx
import models
from scoring_logic import compute_scores
from config import FMP_API_KEY, FMP_V3 as FMP_BASE

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
    Format : { "company_count": N, "market_analysis": { "P/E Ratio": 25.3, ... }, ... }
    """
    companies = db.query(models.Company).filter(models.Company.sector == sector).all()
    if not companies:
        return {}

    result = {"company_count": len(companies)}
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
    """Récupère les données fondamentales d'une seule entreprise par son ticker exact.
    Inclut un objet `scores` calculé à la volée via les moyennes sectorielles."""
    company = db.query(models.Company).filter(models.Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' introuvable")

    # Sérialiser en dict pour pouvoir y injecter les scores calculés
    result = {col.name: getattr(company, col.name) for col in company.__table__.columns}
    result.pop("scores_json", None)  # champ interne, non exposé au frontend

    # Scores : lecture du cache pré-calculé, fallback compute à la volée si absent
    if company.scores_json:
        result["scores"] = company.scores_json
    else:
        if company.sector:
            sector_companies = (
                db.query(models.Company)
                .filter(models.Company.sector == company.sector)
                .all()
            )
        else:
            sector_companies = [company]
        result["scores"] = compute_scores(company, sector_companies)

    # ── Prix actuel + variation journalière ───────────────────────────────
    # Source 1 (priorité) : live_price seedé en DB par le cron FMP 2x/jour
    close_price      = company.live_price
    daily_change_pct = company.live_change_pct

    # Source 2 (fallback) : "Prix Actuel" seedé dans risk_market
    if close_price is None:
        risk      = company.risk_market or []
        prix_item = next((m for m in risk if m.get("name") == "Prix Actuel"), None)
        close_price = prix_item["val"] if prix_item and prix_item.get("val") else None

    result["close_price"]      = close_price
    result["daily_change_pct"] = daily_change_pct

    return result


# ── Proxy FMP (test) ──────────────────────────────────────────────────────────
@router.get("/fundamentals/fmp-proxy/{ticker}")
def fmp_proxy(ticker: str):
    """
    Endpoint de test : interroge Financial Modeling Prep et retourne les données
    dans le même format de réponse que /fundamentals/{ticker}.
    Nécessite la variable d'environnement FMP_API_KEY.
    Ne touche pas à la base de données locale.
    """
    if not FMP_API_KEY:
        raise HTTPException(status_code=503, detail="FMP_API_KEY non configurée")

    try:
        with httpx.Client(timeout=10) as client:
            profile  = client.get(f"{FMP_BASE}/profile/{ticker}",    params={"apikey": FMP_API_KEY}).json()
            ratios   = client.get(f"{FMP_BASE}/ratios-ttm/{ticker}",  params={"apikey": FMP_API_KEY}).json()
            growth   = client.get(f"{FMP_BASE}/financial-growth/{ticker}", params={"apikey": FMP_API_KEY, "limit": 1}).json()
            quote    = client.get(f"{FMP_BASE}/quote/{ticker}",       params={"apikey": FMP_API_KEY}).json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur FMP : {e}")

    p = profile[0]  if profile  else {}
    r = ratios[0]   if ratios   else {}
    g = growth[0]   if growth   else {}
    q = quote[0]    if quote    else {}

    return {
        "ticker":   ticker,
        "name":     p.get("companyName"),
        "sector":   p.get("sector"),
        "industry": p.get("industry"),
        "currency": p.get("currency"),
        "exchange": p.get("exchangeShortName"),
        "website":  p.get("website"),
        "description": p.get("description"),
        # ── métriques scoring ──────────────────────────────────────────────
        "market_analysis": [
            {"name": "Capitalisation", "val": p.get("mktCap"),                                 "unit": "$"},
            {"name": "PER",            "val": r.get("peRatioTTM"),                              "unit": "x"},
            {"name": "Rendement Div",  "val": round((r.get("dividendYieldTTM") or 0) * 100, 2),"unit": "%"},
        ],
        "financial_health": [
            {"name": "Marge Nette",         "val": round((r.get("netProfitMarginTTM") or 0) * 100, 2), "unit": "%"},
            {"name": "ROE",                 "val": round((r.get("returnOnEquityTTM")  or 0) * 100, 2), "unit": "%"},
            {"name": "Dette/Fonds Propres", "val": r.get("debtEquityRatioTTM"),                        "unit": "%"},
        ],
        "advanced_valuation": [
            {"name": "Forward PE",    "val": r.get("forwardPETTM") or r.get("priceEarningsRatioTTM"), "unit": "x"},
            {"name": "Price to Book", "val": r.get("priceToBookRatioTTM"),                            "unit": "x"},
            {"name": "EV / EBITDA",   "val": r.get("enterpriseValueMultipleTTM"),                     "unit": "x"},
            {"name": "PEG Ratio",     "val": r.get("priceEarningsToGrowthRatioTTM"),                  "unit": "x"},
        ],
        "income_growth": [
            {"name": "Croissance CA",        "val": round((g.get("revenueGrowth")    or 0) * 100, 2), "unit": "%"},
            {"name": "Croissance Bénéfices", "val": round((g.get("netIncomeGrowth")  or 0) * 100, 2), "unit": "%"},
        ],
        "balance_cash": [
            {"name": "Ratio Liquidité", "val": r.get("currentRatioTTM"), "unit": "x"},
        ],
        "risk_market": [
            {"name": "Beta",          "val": p.get("beta"),              "unit": "x"},
            {"name": "Plus Haut 52w", "val": q.get("yearHigh"),          "unit": "$"},
            {"name": "Plus Bas 52w",  "val": q.get("yearLow"),           "unit": "$"},
            {"name": "Prix Actuel",   "val": q.get("price"),             "unit": "$"},
        ],
        # ── prix temps réel ──────────────────────────────────────────────
        "close_price":       q.get("price"),
        "daily_change_pct":  q.get("changesPercentage"),
        # ── scores : non calculés ici, nécessitent les données sectorielles
        "scores": None,
        "_source": "fmp",
    }
