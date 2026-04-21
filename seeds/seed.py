"""
Script de seeding monolithique (legacy — préférer seed_fundamentals.py + seed_prices_init.py).
Charge fondamentaux ET historique des prix en une seule passe.

    python seeds/seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import SessionLocal, engine
from models import Base, Company, Price
from seed_utils import (
    TICKERS, BALANCE_SHEET_MAP, INCOME_STMT_MAP, CASHFLOW_MAP,
    parse_financial_df, clean_dataframe,
)

print("Vérification/création des tables PostgreSQL...")
Base.metadata.create_all(bind=engine)


def importer_donnees():
    db = SessionLocal()
    print("Démarrage du téléchargement massif des données...")

    for ticker in TICKERS:
        try:
            print(f"\n-> Traitement de l'action {ticker}...")
            stock = yf.Ticker(ticker)
            info = stock.info

            name = info.get("shortName", ticker)
            sector = info.get("sector", "Inconnu")
            description = info.get("longBusinessSummary", "Description non disponible.")

            market_analysis = [
                {"name": "Capitalisation", "val": info.get("marketCap", 0), "unit": "$"},
                {"name": "PER", "val": round(info.get("trailingPE", 0) or 0, 2), "unit": "x"},
                {"name": "Rendement Div", "val": round((info.get("dividendYield", 0) or 0) * 100, 2), "unit": "%"}
            ]
            financial_health = [
                {"name": "Marge Nette", "val": round((info.get("profitMargins", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "ROE", "val": round((info.get("returnOnEquity", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "Dette/Fonds Propres", "val": round(info.get("debtToEquity", 0) or 0, 2), "unit": "%"}
            ]
            advanced_valuation = [
                {"name": "Forward PE", "val": round(info.get("forwardPE", 0) or 0, 2), "unit": "x"},
                {"name": "Price to Book", "val": round(info.get("priceToBook", 0) or 0, 2), "unit": "x"},
                {"name": "EV / EBITDA", "val": round(info.get("enterpriseToEbitda", 0) or 0, 2), "unit": "x"},
                {"name": "PEG Ratio", "val": round(info.get("pegRatio", 0) or 0, 2), "unit": "x"}
            ]
            income_growth = [
                {"name": "Chiffre d'Affaires", "val": info.get("totalRevenue", 0), "unit": "$"},
                {"name": "EBITDA", "val": info.get("ebitda", 0), "unit": "$"},
                {"name": "Croissance CA", "val": round((info.get("revenueGrowth", 0) or 0) * 100, 2), "unit": "%"},
                {"name": "Croissance Bénéfices", "val": round((info.get("earningsGrowth", 0) or 0) * 100, 2), "unit": "%"}
            ]
            balance_cash = [
                {"name": "Trésorerie Totale", "val": info.get("totalCash", 0), "unit": "$"},
                {"name": "Free Cash Flow", "val": info.get("freeCashflow", 0), "unit": "$"},
                {"name": "Ratio Liquidité", "val": round(info.get("currentRatio", 0) or 0, 2), "unit": "x"}
            ]
            risk_market = [
                {"name": "Beta", "val": round(info.get("beta", 0) or 0, 2), "unit": "x"},
                {"name": "Plus Haut 52w", "val": round(info.get("fiftyTwoWeekHigh", 0) or 0, 2), "unit": "$"},
                {"name": "Plus Bas 52w", "val": round(info.get("fiftyTwoWeekLow", 0) or 0, 2), "unit": "$"},
                {"name": "Actions Shortées", "val": round((info.get("shortPercentOfFloat", 0) or 0) * 100, 2), "unit": "%"}
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
                company.description = description
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
                    ticker=ticker, name=name, sector=sector, description=description,
                    market_analysis=market_analysis, financial_health=financial_health,
                    advanced_valuation=advanced_valuation, income_growth=income_growth,
                    balance_cash=balance_cash, risk_market=risk_market,
                    balance_sheet_data=balance_sheet_data,
                    income_stmt_data=income_stmt_data,
                    cashflow_data=cashflow_data,
                )
                db.add(company)
            db.commit()

            print(f"    Récupération de l'historique des prix...")
            df_1w_raw  = stock.history(period="10y", interval="1wk")
            df_1d_raw  = stock.history(period="10y", interval="1d")
            df_1h_raw  = stock.history(period="730d", interval="1h")
            df_15m_raw = stock.history(period="60d",  interval="15m")

            cleaned_dfs = [
                clean_dataframe(df_1w_raw,  '1W'),
                clean_dataframe(df_1d_raw,  '1D'),
                clean_dataframe(df_1h_raw,  '1h'),
                clean_dataframe(df_15m_raw, '15m'),
            ]
            dfs = [df for df in cleaned_dfs if df is not None and not df.empty]

            if dfs:
                df_final = pd.concat(dfs, ignore_index=True)
                df_final = df_final.dropna(subset=['Close', 'Open', 'High', 'Low'])
                df_final = df_final.fillna(0)

                prices_to_insert = []
                seen_records = set()

                for _, row in df_final.iterrows():
                    if 'Date' not in row or pd.isna(row['Date']):
                        continue
                    date_val     = row['Date'].to_pydatetime()
                    interval_val = row['interval']
                    record_key   = (ticker, date_val, interval_val)
                    if record_key not in seen_records:
                        seen_records.add(record_key)
                        prices_to_insert.append(Price(
                            ticker=ticker, date=date_val, interval=interval_val,
                            open_price=float(row["Open"]), high_price=float(row["High"]),
                            low_price=float(row["Low"]),   close_price=float(row["Close"]),
                            volume=int(row["Volume"]),
                        ))

                if prices_to_insert:
                    records = [
                        {"ticker": p.ticker, "date": p.date, "interval": p.interval,
                         "open_price": p.open_price, "high_price": p.high_price,
                         "low_price": p.low_price, "close_price": p.close_price, "volume": p.volume}
                        for p in prices_to_insert
                    ]
                    stmt = pg_insert(Price).values(records)
                    stmt = stmt.on_conflict_do_update(
                        constraint="uix_ticker_date_interval",
                        set_={
                            "open_price":  stmt.excluded.open_price,
                            "high_price":  stmt.excluded.high_price,
                            "low_price":   stmt.excluded.low_price,
                            "close_price": stmt.excluded.close_price,
                            "volume":      stmt.excluded.volume,
                        }
                    )
                    db.execute(stmt)
                    db.commit()
                    print(f"    ✅ {len(prices_to_insert)} bougies insérées/mises à jour.")

        except Exception as e:
            print(f"    ❌ Erreur lors du traitement de {ticker} : {e}")
            db.rollback()
            continue

    print("\nOpération terminée ! Ton terminal est prêt.")
    db.close()


if __name__ == "__main__":
    importer_donnees()
