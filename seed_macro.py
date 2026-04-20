"""
Invalide le cache macro (cycle économique + liquidité) dans PostgreSQL,
forçant le prochain appel API à refetcher depuis FRED/yfinance.

    python seed_macro.py
"""
from database import SessionLocal, engine
from models import Base, MacroCache

Base.metadata.create_all(bind=engine)

MACRO_KEYS = ["macro_cycle", "macro_liquidity", "macro_cycle_history"]


def seed_macro():
    db = SessionLocal()
    deleted = 0

    for key in MACRO_KEYS:
        record = db.query(MacroCache).filter(MacroCache.cache_key == key).first()
        if record:
            db.delete(record)
            deleted += 1
            print(f"✅ Cache '{key}' supprimé — sera recalculé au prochain appel API.")
        else:
            print(f"ℹ️  Cache '{key}' absent (rien à faire).")

    db.commit()
    db.close()

    if deleted:
        print(f"\n{deleted} entrée(s) invalidée(s). Appelle /macro/cycle et /macro/liquidity pour regénérer.")
    else:
        print("\nAucun cache à invalider.")


if __name__ == "__main__":
    seed_macro()
