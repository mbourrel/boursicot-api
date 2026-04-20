"""
Rafraîchit uniquement les bougies RÉCENTES pour tous les tickers.
Conçu pour les crons GitHub Actions (3x/jour). Durée ~3 min pour 63 tickers.

    python seed_prices.py
    python seed_prices.py AAPL          # un seul ticker
    python seed_prices.py AAPL MSFT     # plusieurs tickers

Pour le chargement initial complet (depuis 1998), utiliser seed_prices_init.py.
"""
import sys
import time
import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import SessionLocal, engine
from models import Base, Price
from seed_utils import TICKERS, clean_dataframe

Base.metadata.create_all(bind=engine)

# Fenêtres courtes : couvrent largement l'intervalle entre deux runs (max 8h)
PERIODS = {
    '1W':  '1mo',   # ~4 bougies hebdo
    '1D':  '5d',    # ~5 bougies journalières
    '1h':  '7d',    # ~56 bougies horaires
    '15m': '2d',    # ~52 bougies 15min
}


def insert_recent(db, records: list):
    if not records:
        return
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


def seed_prices(tickers: list[str]):
    print(f"Rafraîchissement des prix récents pour {len(tickers)} ticker(s)...\n")

    for ticker in tickers:
        db = SessionLocal()
        try:
            print(f"-> {ticker}...")
            stock = yf.Ticker(ticker)

            cleaned_dfs = []
            for interval, period in PERIODS.items():
                df_raw = stock.history(period=period, interval=interval.lower().replace('1w', '1wk'))
                cleaned = clean_dataframe(df_raw, interval)
                if cleaned is not None and not cleaned.empty:
                    cleaned_dfs.append(cleaned)

            if not cleaned_dfs:
                print(f"   ⚠️  Aucune donnée reçue pour {ticker}")
                continue

            df_final = pd.concat(cleaned_dfs, ignore_index=True)
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

            insert_recent(db, records)
            print(f"   ✅ {len(records)} bougies mises à jour.")

        except Exception as e:
            print(f"   ❌ Erreur {ticker} : {e}")
            db.rollback()
        finally:
            db.close()

        time.sleep(0.5)

    print("\nRafraîchissement terminé.")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    seed_prices(targets)
