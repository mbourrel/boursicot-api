"""
Recharge les données fondamentales (ratios, bilans, etc.) pour tous les tickers.
Lance uniquement ce script pour mettre à jour les fondamentaux sans toucher aux prix.

    python seeds/seed_fundamentals.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from collections import defaultdict
import yfinance as yf


def _fetch_info(ticker: str, max_retries: int = 3) -> dict:
    """Appelle yf.Ticker(ticker).info avec backoff exponentiel (2s, 4s, 8s)."""
    delay = 2
    last_exc: Exception = RuntimeError("no attempts")
    for attempt in range(1, max_retries + 1):
        try:
            return yf.Ticker(ticker).info
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                print(f"   ⚠️  {ticker} tentative {attempt}/{max_retries} — {e} (retry dans {delay}s)")
                time.sleep(delay)
                delay *= 2
    raise last_exc
from database import SessionLocal, engine
from models import Base, Company
from seed_utils import (
    TICKERS, BALANCE_SHEET_MAP, INCOME_STMT_MAP, CASHFLOW_MAP,
    parse_financial_df,
)
from scoring_logic import compute_scores
from assets_config import ETF_TICKERS

Base.metadata.create_all(bind=engine)

# Mapping yFinance quoteType → classe interne Boursicot
QUOTE_TYPE_MAP: dict[str, str] = {
    "EQUITY":         "stock",
    "CRYPTOCURRENCY": "crypto",
    "ETF":            "etf",
    "MUTUALFUND":     "etf",
    "INDEX":          "index",
    "FUTURE":         "commodity",
}


def seed_fundamentals():
    db = SessionLocal()
    print(f"Chargement des fondamentaux pour {len(TICKERS)} tickers...\n")

    for ticker in TICKERS:
        try:
            print(f"-> {ticker}...")
            stock = yf.Ticker(ticker)
            info  = _fetch_info(ticker)

            name        = info.get("shortName", ticker)
            sector      = info.get("sector", "Inconnu")
            industry    = info.get("industry") or None
            description = info.get("longBusinessSummary", "Description non disponible.")
            country     = info.get("country") or None
            city        = info.get("city") or None
            website     = info.get("website") or None
            employees   = info.get("fullTimeEmployees") or None
            exchange    = info.get("exchange") or None
            currency    = info.get("currency") or None

            ipo_date = info.get("ipoDate") or None
            if not ipo_date:
                try:
                    first_ts = info.get("firstTradeDateEpochUtc")
                    if first_ts:
                        from datetime import datetime, timezone
                        ipo_date = datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    pass

            quote_type  = info.get("quoteType", "")
            asset_class = QUOTE_TYPE_MAP.get(quote_type, "stock")
            if ticker in ETF_TICKERS:   # override manuel si yFinance classerait mal
                asset_class = "etf"

            market_analysis = [
                {"name": "Capitalisation", "val": info.get("marketCap", 0),                                    "unit": "$"},
                {"name": "PER",            "val": round(info.get("trailingPE", 0) or 0, 2),                    "unit": "x"},
                {"name": "Rendement Div",  "val": round((lambda dy: dy if dy > 0.5 else dy * 100)(info.get("dividendYield", 0) or 0), 2), "unit": "%"},
            ]
            financial_health = [
                {"name": "Marge Nette",        "val": round((info.get("profitMargins", 0) or 0) * 100, 2),     "unit": "%"},
                {"name": "ROE",                "val": round((info.get("returnOnEquity", 0) or 0) * 100, 2),    "unit": "%"},
                {"name": "Dette/Fonds Propres","val": round(info.get("debtToEquity", 0) or 0, 2),              "unit": "%"},
            ]
            advanced_valuation = [
                {"name": "Forward PE",    "val": round(info.get("forwardPE", 0) or 0, 2),                      "unit": "x"},
                {"name": "Price to Book", "val": round(info.get("priceToBook", 0) or 0, 2),                    "unit": "x"},
                {"name": "EV / EBITDA",   "val": round(info.get("enterpriseToEbitda", 0) or 0, 2),             "unit": "x"},
                {"name": "PEG Ratio",     "val": round(info.get("pegRatio", 0) or 0, 2),                       "unit": "x"},
            ]
            income_growth = [
                {"name": "Chiffre d'Affaires",    "val": info.get("totalRevenue", 0),                           "unit": "$"},
                {"name": "EBITDA",                "val": info.get("ebitda", 0),                                 "unit": "$"},
                {"name": "Croissance CA",         "val": round((info.get("revenueGrowth", 0) or 0) * 100, 2),  "unit": "%"},
                {"name": "Croissance Bénéfices",  "val": round((info.get("earningsGrowth", 0) or 0) * 100, 2), "unit": "%"},
            ]
            balance_cash = [
                {"name": "Trésorerie Totale", "val": info.get("totalCash", 0),                                  "unit": "$"},
                {"name": "Free Cash Flow",    "val": info.get("freeCashflow", 0),                               "unit": "$"},
                {"name": "Ratio Liquidité",   "val": round(info.get("currentRatio", 0) or 0, 2),               "unit": "x"},
            ]
            risk_market = [
                {"name": "Beta",             "val": round(info.get("beta", 0) or 0, 2),                         "unit": "x"},
                {"name": "Plus Haut 52w",    "val": round(info.get("fiftyTwoWeekHigh", 0) or 0, 2),             "unit": "$"},
                {"name": "Plus Bas 52w",     "val": round(info.get("fiftyTwoWeekLow", 0) or 0, 2),              "unit": "$"},
                {"name": "Actions Shortées", "val": round((info.get("shortPercentOfFloat", 0) or 0) * 100, 2),  "unit": "%"},
            ]

            try:
                balance_sheet_data = parse_financial_df(stock.balance_sheet, BALANCE_SHEET_MAP)
            except Exception:
                balance_sheet_data = None
            try:
                income_stmt_data = parse_financial_df(stock.income_stmt, INCOME_STMT_MAP)
            except Exception:
                income_stmt_data = None
            try:
                cashflow_data = parse_financial_df(stock.cashflow, CASHFLOW_MAP)
            except Exception:
                cashflow_data = None

            # Données de dividendes
            try:
                dividends_series = stock.dividends
                annual_divs = {}
                if not dividends_series.empty:
                    for date, amount in dividends_series.items():
                        year = str(date.year)
                        annual_divs[year] = annual_divs.get(year, 0) + float(amount)

                sorted_years = sorted(annual_divs.keys(), reverse=True)[:10]
                annual_vals  = [round(annual_divs[y], 4) for y in sorted_years]

                ex_div_ts  = info.get("exDividendDate")
                ex_div_str = None
                if ex_div_ts:
                    from datetime import datetime, timezone
                    try:
                        ex_div_str = datetime.fromtimestamp(ex_div_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    except Exception:
                        pass

                last_div = info.get("lastDividendValue") or None
                if last_div:
                    last_div = round(float(last_div), 4)

                last_div_date_ts  = info.get("lastDividendDate")
                last_div_date_str = None
                if last_div_date_ts:
                    from datetime import datetime, timezone
                    try:
                        last_div_date_str = datetime.fromtimestamp(last_div_date_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    except Exception:
                        pass

                five_yr = info.get("fiveYearAvgDividendYield") or 0
                payout  = info.get("payoutRatio") or 0

                # Historique actions en circulation (balance sheet)
                shares_history = None
                try:
                    bs = stock.balance_sheet
                    if bs is not None and not bs.empty:
                        candidates = [r for r in bs.index if any(k in str(r) for k in ('Share Issued', 'Ordinary Shares Number', 'Common Stock Equity'))]
                        if candidates:
                            row_data = bs.loc[candidates[0]].dropna()
                            sh_years = [str(d.year) for d in sorted(row_data.index, reverse=True)][:10]
                            sh_vals  = [round(float(row_data[d]) / 1_000_000, 2) for d in sorted(row_data.index, reverse=True)][:10]
                            if sh_years:
                                shares_history = {"years": sh_years, "vals": sh_vals}
                except Exception:
                    pass

                # Historique des stock splits
                stock_splits = None
                try:
                    splits = stock.splits
                    if not splits.empty:
                        stock_splits = [
                            {"date": d.strftime("%Y-%m-%d"), "ratio": float(v)}
                            for d, v in sorted(splits.items(), reverse=True)
                        ]
                except Exception:
                    pass

                dividends_data = {
                    "dividend_yield":      round((info.get("dividendYield") or 0) * 100, 2),
                    "dividend_rate":       round(info.get("dividendRate") or 0, 4),
                    "payout_ratio":        round(float(payout) * 100, 2) if payout else 0,
                    "five_year_avg_yield": round(float(five_yr), 2),
                    "ex_dividend_date":    ex_div_str,
                    "last_dividend_value": last_div,
                    "last_dividend_date":  last_div_date_str,
                    "shares_history":      shares_history,
                    "stock_splits":        stock_splits,
                    "annual": {
                        "years": sorted_years,
                        "items": [
                            {"name": "Dividende Annuel", "vals": annual_vals, "unit": info.get("currency", "$")}
                        ] if sorted_years else [],
                    },
                }
            except Exception:
                dividends_data = None

            company = db.query(Company).filter(Company.ticker == ticker).first()
            if company:
                company.name = name
                company.sector = sector
                company.industry = industry
                company.asset_class = asset_class
                company.description = description
                company.country = country
                company.city = city
                company.website = website
                company.employees = employees
                company.exchange = exchange
                company.currency = currency
                company.ipo_date = ipo_date
                company.market_analysis = market_analysis
                company.financial_health = financial_health
                company.advanced_valuation = advanced_valuation
                company.income_growth = income_growth
                company.balance_cash = balance_cash
                company.risk_market = risk_market
                company.balance_sheet_data = balance_sheet_data
                company.income_stmt_data = income_stmt_data
                company.cashflow_data = cashflow_data
                company.dividends_data = dividends_data
            else:
                company = Company(
                    ticker=ticker, name=name, sector=sector, industry=industry,
                    asset_class=asset_class,
                    description=description, country=country, city=city,
                    website=website, employees=employees, exchange=exchange,
                    currency=currency, ipo_date=ipo_date,
                    market_analysis=market_analysis, financial_health=financial_health,
                    advanced_valuation=advanced_valuation, income_growth=income_growth,
                    balance_cash=balance_cash, risk_market=risk_market,
                    balance_sheet_data=balance_sheet_data,
                    income_stmt_data=income_stmt_data,
                    cashflow_data=cashflow_data,
                    dividends_data=dividends_data,
                )
                db.add(company)

            db.commit()
            print(f"   ✅ {name}")

        except Exception as e:
            print(f"   ❌ Erreur {ticker} : {e}")
            db.rollback()
            continue

        time.sleep(0.5)

    print("\nFondamentaux chargés.")

    # ── Passe de scoring ──────────────────────────────────────────────────────
    # Pré-calcule les scores pour toutes les companies et les stocke en DB.
    # Évite le recalcul N+1 à chaque requête GET /api/fundamentals/{ticker}.
    print("\nCalcul et mise en cache des scores...")
    all_companies = db.query(Company).all()

    sector_map = defaultdict(list)
    for c in all_companies:
        sector_map[c.sector or "Inconnu"].append(c)

    scored = 0
    for company in all_companies:
        sector_companies = sector_map.get(company.sector or "Inconnu", [company])
        try:
            company.scores_json = compute_scores(company, sector_companies)
            scored += 1
        except Exception as e:
            print(f"   ⚠️  Score {company.ticker} : {e}")

    db.commit()
    print(f"✅ Scores mis en cache pour {scored}/{len(all_companies)} companies.")

    db.close()


if __name__ == "__main__":
    seed_fundamentals()
