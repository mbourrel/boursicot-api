"""
Migration : ajout des colonnes d'identité sur la table companies.
Lance une seule fois :  python migrate_add_identity.py
"""
from database import engine
from sqlalchemy import text

COLUMNS = [
    ("industry",  "VARCHAR"),
    ("country",   "VARCHAR"),
    ("city",      "VARCHAR"),
    ("website",   "VARCHAR"),
    ("employees", "INTEGER"),
    ("exchange",  "VARCHAR"),
    ("currency",  "VARCHAR"),
    ("ipo_date",  "VARCHAR"),
]

with engine.connect() as conn:
    for col, col_type in COLUMNS:
        try:
            conn.execute(text(f"ALTER TABLE companies ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            print(f"✅  Colonne '{col}' ajoutée (ou déjà présente).")
        except Exception as e:
            print(f"❌  {col} : {e}")
    conn.commit()

print("\nMigration terminée. Lance maintenant : python seed_fundamentals.py")
