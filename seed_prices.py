"""
Recharge l'historique des prix (OHLCV) pour tous les tickers sur tous les intervalles.
Lance uniquement ce script pour rafraîchir les cours sans toucher aux fondamentaux.

    python seed_prices.py
    python seed_prices.py AAPL          # un seul ticker
    python seed_prices.py AAPL MSFT     # plusieurs tickers
"""
import sys
import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database import SessionLocal, engine
from models import Base, Price
from seed_utils import TICKERS, clean_dataframe

Base.metadata.create_all(bind=engine)


def seed_prices(tickers: list[str]):
    db = SessionLocal()
    print(f"Chargement des prix pour {len(tickers)} ticker(s)...\n")

    for ticker in tickers:
        try:
            print(f"-> {ticker}...")
            stock = yf.Ticker(ticker)

            df_1w_raw  = stock.history(period="10y",  interval="1wk")
            df_1d_raw  = stock.history(period="10y",  interval="1d")
            df_1h_raw  = stock.history(period="730d", interval="1h")
            df_15m_raw = stock.history(period="60d",  interval="15m")

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
                print(f"   ✅ {len(records)} bougies insérées/mises à jour.")
            else:
                print(f"   ⚠️  Aucun enregistrement valide pour {ticker}")

        except Exception as e:
            print(f"   ❌ Erreur {ticker} : {e}")
            db.rollback()
            continue

    print("\nPrix chargés.")
    db.close()


if __name__ == "__main__":
    # Accepte une liste de tickers en argument, sinon traite tous les tickers
    targets = sys.argv[1:] if len(sys.argv) > 1 else TICKERS
    seed_prices(targets)
