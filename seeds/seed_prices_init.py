"""
Chargement INITIAL de l'historique complet des prix depuis 1998.
À lancer UNE SEULE FOIS (ou après une remise à zéro de la table prices).
Peut prendre 30-60 minutes selon la connexion et la charge de la DB.

    python seeds/seed_prices_init.py
    python seeds/seed_prices_init.py AAPL          # un seul ticker
    python seeds/seed_prices_init.py AAPL MSFT     # plusieurs tickers
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import SessionLocal, engine
from models import Base, Price
from seed_utils import TICKERS, clean_dataframe

Base.metadata.create_all(bind=engine)

CHUNK_SIZE   = 200
CHUNK_SLEEP  = 0.3
RETRY_DELAYS = [5, 15, 30]


def insert_in_chunks(db, records: list):
    total = len(records)
    for i in range(0, total, CHUNK_SIZE):
        chunk = records[i:i + CHUNK_SIZE]
        stmt  = pg_insert(Price).values(chunk)
        stmt  = stmt.on_conflict_do_update(
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
        if i + CHUNK_SIZE < total:
            time.sleep(CHUNK_SLEEP)


def insert_with_retry(records: list, ticker: str) -> bool:
    for attempt, delay in enumerate([0] + RETRY_DELAYS, start=1):
        if delay:
            print(f"   ⏳ Retry {attempt - 1}/3 dans {delay}s...")
            time.sleep(delay)
        db = SessionLocal()
        try:
            insert_in_chunks(db, records)
            return True
        except Exception as exc:
            db.rollback()
            print(f"   ⚠️  Tentative {attempt} échouée : {exc}")
        finally:
            db.close()
    return False


def seed_prices_init(tickers: list[str]):
    print(f"Chargement historique complet pour {len(tickers)} ticker(s)...\n")

    for ticker in tickers:
        try:
            print(f"-> {ticker}...")
            stock = yf.Ticker(ticker)

            df_1w_raw  = stock.history(start="1998-01-01", interval="1wk")
            df_1d_raw  = stock.history(start="1998-01-01", interval="1d")
            df_1h_raw  = stock.history(period="730d",      interval="1h")
            df_15m_raw = stock.history(period="60d",       interval="15m")

            cleaned_dfs = [
                clean_dataframe(df_1w_raw,  '1W'),
                clean_dataframe(df_1d_raw,  '1D'),
                clean_dataframe(df_1h_raw,  '1h'),
                clean_dataframe(df_15m_raw, '15m'),
            ]
            dfs = [df for df in cleaned_dfs if df is not None and not df.empty]

            if not dfs:
                print(f"   ⚠️  Aucune donnée reçue pour {ticker}")
                continue

            df_final = pd.concat(dfs, ignore_index=True)
            df_final = df_final.dropna(subset=['Close', 'Open', 'High', 'Low'])
            df_final = df_final.fillna(0)

            records = []
            seen    = set()

            for _, row in df_final.iterrows():
                if 'Date' not in row or pd.isna(row['Date']):
                    continue
                date_val     = row['Date'].to_pydatetime()
                interval_val = row['interval']
                key = (ticker, date_val, interval_val)
                if key in seen:
                    continue
                seen.add(key)
                records.append({
                    "ticker":      ticker,
                    "date":        date_val,
                    "interval":    interval_val,
                    "open_price":  float(row["Open"]),
                    "high_price":  float(row["High"]),
                    "low_price":   float(row["Low"]),
                    "close_price": float(row["Close"]),
                    "volume":      int(row["Volume"]),
                })

            if records:
                n_chunks = (len(records) - 1) // CHUNK_SIZE + 1
                ok = insert_with_retry(records, ticker)
                if ok:
                    print(f"   ✅ {len(records)} bougies ({n_chunks} chunk(s)).")
                else:
                    print(f"   ❌ {ticker} : échec après 3 tentatives.")
            else:
                print(f"   ⚠️  Aucun enregistrement valide pour {ticker}")

        except Exception as e:
            print(f"   ❌ Erreur {ticker} : {e}")

        time.sleep(0.5)

    print("\nChargement initial terminé.")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    seed_prices_init(targets)
