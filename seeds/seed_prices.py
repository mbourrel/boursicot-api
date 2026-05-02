"""
Rafraîchit uniquement les bougies RÉCENTES pour tous les tickers.
Conçu pour les crons GitHub Actions (3x/jour). Durée ~3 min pour 63 tickers.

    python seeds/seed_prices.py
    python seeds/seed_prices.py AAPL          # un seul ticker
    python seeds/seed_prices.py AAPL MSFT     # plusieurs tickers

Pour le chargement initial complet (depuis 1998), utiliser seeds/seed_prices_init.py.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf
from sqlalchemy import text
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

# Politique de rétention — intervalles courts uniquement (1D et 1W conservés indéfiniment)
RETENTION = {
    '15m': timedelta(days=30),    # 1 mois glissant
    '1h':  timedelta(days=365),   # 1 an glissant
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
    purge_old_prices()


def purge_old_prices():
    """
    Supprime les bougies intraday antérieures aux seuils de rétention.

    Stratégie : DELETE ticker par ticker pour exploiter l'index unique
    (ticker, date, interval) et maintenir des verrous courts sur la table —
    chaque commit libère le verrou avant de passer au ticker suivant.

    Intervalles 1D et 1W : conservés indéfiniment (aucune suppression).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoffs = {iv: now - delta for iv, delta in RETENTION.items()}

    db = SessionLocal()
    total = {iv: 0 for iv in RETENTION}
    try:
        for ticker in TICKERS:
            for iv, cutoff in cutoffs.items():
                result = db.execute(
                    text(
                        "DELETE FROM prices "
                        "WHERE ticker = :ticker AND interval = :interval AND date < :cutoff"
                    ),
                    {"ticker": ticker, "interval": iv, "cutoff": cutoff},
                )
                total[iv] += result.rowcount
            db.commit()   # verrou libéré ticker par ticker

        print(
            f"Purge rétention : "
            f"{total['15m']} bougies 15m supprimées (> 30j) | "
            f"{total['1h']} bougies 1h supprimées (> 1an)"
        )
    except Exception as e:
        print(f"❌ Erreur purge rétention : {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    seed_prices(targets)
