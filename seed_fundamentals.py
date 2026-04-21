"""
Recharge les données fondamentales (ratios, bilans, etc.) pour tous les tickers.
Lance uniquement ce script pour mettre à jour les fondamentaux sans toucher aux prix.

    python seed_fundamentals.py
"""
import time
import yfinance as yf
from database import SessionLocal, engine
from models import Base, Company
from seed_utils import (
    TICKERS, BALANCE_SHEET_MAP, INCOME_STMT_MAP, CASHFLOW_MAP,
    parse_financial_df,
)

Base.metadata.create_all(bind=engine)


def seed_fundamentals():
    db = SessionLocal()
    print(f"Chargement des fondamentaux pour {len(TICKERS)} tickers...\n")

    for ticker in TICKERS:
        try:
            print(f"-> {ticker}...")
            stock = yf.Ticker(ticker)
            info  = stock.info

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

            # Date d'IPO : yfinance expose "ipoDate" sur certains titres,
            # sinon on tente de récupérer la première date connue via history.
            ipo_date = info.get("ipoDate") or None
            if not ipo_date:
                try:
                    first_ts = info.get("firstTradeDateEpochUtc")
                    if first_ts:
                        from datetime import datetime, timezone
                        ipo_date = datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    pass

            market_analysis = [
                {"name": "Capitalisation", "val": info.get("marketCap", 0),                                    "unit": "$"},
                {"name": "PER",            "val": round(info.get("trailingPE", 0) or 0, 2),                    "unit": "x"},
                {"name": "Rendement Div",  "val": round((_dy := (info.get("dividendYield", 0) or 0)) if _dy > 0.5 else _dy * 100, 2), "unit": "%"},
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

            company = db.query(Company).filter(Company.ticker == ticker).first()
            if company:
                company.name = name
                company.sector = sector
                company.industry = industry
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
            else:
                company = Company(
                    ticker=ticker, name=name, sector=sector, industry=industry,
                    description=description, country=country, city=city,
                    website=website, employees=employees, exchange=exchange,
                    currency=currency, ipo_date=ipo_date,
                    market_analysis=market_analysis, financial_health=financial_health,
                    advanced_valuation=advanced_valuation, income_growth=income_growth,
                    balance_cash=balance_cash, risk_market=risk_market,
                    balance_sheet_data=balance_sheet_data,
                    income_stmt_data=income_stmt_data,
                    cashflow_data=cashflow_data,
                )
                db.add(company)

            db.commit()
            print(f"   ✅ {name}")

        except Exception as e:
            print(f"   ❌ Erreur {ticker} : {e}")
            db.rollback()
            continue

        time.sleep(0.5)  # anti rate-limit Yahoo Finance

    print("\nFondamentaux chargés.")
    db.close()


if __name__ == "__main__":
    seed_fundamentals()
