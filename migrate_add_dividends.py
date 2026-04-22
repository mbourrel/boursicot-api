"""
Migration : ajout de la colonne dividends_data sur la table companies.
Lance une seule fois :  python migrate_add_dividends.py
"""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS dividends_data JSONB"))
        conn.commit()
        print("OK  Colonne 'dividends_data' ajoutee (ou deja presente).")
    except Exception as e:
        print(f"ERR dividends_data : {e}")

print("\nMigration terminee. Lance maintenant : python seed_fundamentals.py")
