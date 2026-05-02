"""
Migration DDL idempotente — à exécuter une seule fois sur la base existante.

Opérations :
  1. CREATE INDEX IF NOT EXISTS ix_companies_sector — accélère les requêtes sectoriales
  2. ALTER TABLE macro_cache ALTER COLUMN data_json TYPE JSONB — remplace le TEXT brut
     par un vrai type JSON natif (meilleure perf + validation Postgres)
  3. ALTER TABLE companies ADD COLUMN IF NOT EXISTS asset_class VARCHAR
     — classe d'actif dérivée du quoteType yFinance ('stock'|'crypto'|'etf'|'index'|'commodity')

Usage :
    python seeds/migrate_db.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("SQLALCHEMY_DATABASE_URL n'est pas défini")

engine = create_engine(DATABASE_URL)

MIGRATIONS = [
    (
        "ix_companies_sector",
        "CREATE INDEX IF NOT EXISTS ix_companies_sector ON companies(sector);",
    ),
    (
        "macro_cache.data_json -> JSONB",
        """
        ALTER TABLE macro_cache
          ALTER COLUMN data_json TYPE JSONB
          USING data_json::jsonb;
        """,
    ),
    (
        "companies.asset_class",
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS asset_class VARCHAR;",
    ),
    (
        "idx_prices_ticker_interval_date",
        # Optimise les DELETE de la purge de rétention (ticker, interval, date range).
        # L'index existant uix_ticker_date_interval (ticker, date, interval) couvre déjà
        # les purges par ticker, mais cet index complémentaire accélère les scans
        # sur (ticker, interval) → date en cas de requêtes analytiques futures.
        "CREATE INDEX IF NOT EXISTS idx_prices_ticker_interval_date "
        "ON prices(ticker, interval, date DESC);",
    ),
]

def run():
    with engine.connect() as conn:
        for label, sql in MIGRATIONS:
            print(f"  > {label}... ", end="", flush=True)
            try:
                conn.execute(text(sql))
                conn.commit()
                print("OK")
            except Exception as e:
                conn.rollback()
                print(f"SKIP ({e})")

if __name__ == "__main__":
    print("Migrations DDL Boursicot")
    run()
    print("Termine")
