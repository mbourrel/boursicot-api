from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from collections import defaultdict
import httpx
import models
from scoring_logic import compute_scores, is_scorable
from config import FMP_API_KEY, FMP_V3 as FMP_BASE, EQUITY_RISK_PREMIUM

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


@router.get("/screener")
def get_screener(db: Session = Depends(get_db)):
    """
    Endpoint léger pour le Screener Pédagogique.
    Retourne uniquement les champs nécessaires : ticker, name, sector,
    scores pré-calculés (scores_json), prix live et flag is_scorable.
    Exclut tous les champs lourds (états financiers, métriques JSON détaillées).
    """
    companies = db.query(models.Company).all()
    result = []
    for c in companies:
        scorable = is_scorable(c.ticker)
        result.append({
            "ticker":          c.ticker,
            "name":            c.name,
            "sector":          c.sector,
            "country":         c.country,
            "asset_class":     c.asset_class,
            "is_scorable":     scorable,
            "scores":          c.scores_json if scorable else None,
            "live_price":      c.live_price,
            "live_change_pct": c.live_change_pct,
        })
    return result


# Taux sans risque de référence par devise (OAT/Bund/US 10Y approximatifs)
_RF_FALLBACK = {"USD": 0.045, "EUR": 0.030, "GBP": 0.040, "CAD": 0.035, "JPY": 0.010}
_RF_BOND_NAME = {"USD": "US 10Y", "EUR": "Bund 10Y", "GBP": "Gilt 10Y"}


def _compute_valuation_defaults(company, db) -> dict:
    # ── 1. Taux sans risque ───────────────────────────────────────────────────
    currency = (company.currency or "USD").upper()
    risk_free = _RF_FALLBACK.get(currency, 0.045)

    bond_name = _RF_BOND_NAME.get(currency)
    if bond_name:
        try:
            cache_row = db.query(models.MacroCache).filter(
                models.MacroCache.cache_key == "macro_rates_v6"
            ).first()
            if cache_row and cache_row.data_json:
                match = next(
                    (b for b in cache_row.data_json.get("bond_yields", [])
                     if b.get("name") == bond_name and b.get("rate") is not None),
                    None,
                )
                if match:
                    risk_free = match["rate"] / 100
        except Exception:
            pass

    # ── 2. WACC via CAPM ──────────────────────────────────────────────────────
    beta = next(
        (m["val"] for m in (company.risk_market or [])
         if m.get("name") == "Beta" and m.get("val") is not None),
        None,
    )
    if beta is not None:
        default_wacc = round(min(0.15, max(0.05, risk_free + beta * EQUITY_RISK_PREMIUM)), 4)
    else:
        default_wacc = 0.08

    # ── 3. Croissance FCF (CAGR sur la période disponible) ───────────────────
    default_growth = 0.05
    try:
        cf_items = (company.cashflow_data or {}).get("items") or []
        fcf_entry = next((x for x in cf_items if x.get("name") == "Free Cash Flow"), None)
        if fcf_entry:
            vals = [v for v in (fcf_entry.get("vals") or []) if v is not None and v != 0]
            if len(vals) >= 2 and vals[-1] > 0 and vals[0] > 0:
                n = len(vals) - 1
                cagr = (vals[0] / vals[-1]) ** (1 / n) - 1
                default_growth = round(min(0.15, max(0.0, cagr)), 4)
    except Exception:
        pass

    # ── 4. P/E moyen sectoriel ────────────────────────────────────────────────
    default_pe = 15.0
    try:
        own_per = next(
            (m["val"] for m in (company.market_analysis or [])
             if m.get("name") == "PER" and m.get("val") and m["val"] > 0),
            None,
        )
        if company.sector:
            sector_cos = (
                db.query(models.Company)
                .filter(models.Company.sector == company.sector)
                .all()
            )
            pers = [
                next((m["val"] for m in (c.market_analysis or [])
                      if m.get("name") == "PER" and m.get("val") and m["val"] > 0), None)
                for c in sector_cos
            ]
            pers = [p for p in pers if p is not None]
            if pers:
                default_pe = round(min(50, max(5, sum(pers) / len(pers))), 1)
            elif own_per is not None:
                default_pe = round(min(50, max(5, own_per)), 1)
        elif own_per is not None:
            default_pe = round(min(50, max(5, own_per)), 1)
    except Exception:
        pass

    return {
        "default_wacc":   default_wacc,
        "default_growth": default_growth,
        "default_pe":     default_pe,
    }


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

    # Scores : non applicable pour indices, cryptos et matières premières
    if not is_scorable(ticker):
        result["scores"] = {"is_scorable": False}
    elif company.scores_json:
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

    result["close_price"]        = close_price
    result["daily_change_pct"]   = daily_change_pct
    result["valuation_defaults"] = _compute_valuation_defaults(company, db)

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
