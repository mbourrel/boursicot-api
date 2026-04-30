"""
Met à jour les taux de change (EURUSD, GBPUSD, JPYUSD, CHFUSD).
Source : frankfurter.app (taux BCE officiels) — gratuit, sans clé API,
         0 impact sur le budget FMP.
1 seul appel par exécution.

    python seeds/seed_exchange_rates.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
from database import SessionLocal, engine
from models import Base, ExchangeRate

Base.metadata.create_all(bind=engine)

# GET /latest?from=EUR&to=USD,GBP,JPY,CHF
# Réponse : {"base":"EUR","date":"...","rates":{"USD":1.085,"GBP":0.85,"JPY":163,"CHF":0.94}}
FRANKFURTER_URL = "https://api.frankfurter.app/latest"


def seed_exchange_rates():
    try:
        resp = requests.get(
            FRANKFURTER_URL,
            params={"from": "EUR", "to": "USD,GBP,JPY,CHF"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Erreur frankfurter.app : {e}")
        sys.exit(1)

    eur_rates = data.get("rates", {})
    eur_usd = eur_rates.get("USD")
    if not eur_usd:
        print("❌ Taux EURUSD absent de la réponse")
        sys.exit(1)

    # Dériver toutes les paires en USD depuis la base EUR
    pairs = {
        "EURUSD": eur_usd,
        "GBPUSD": eur_usd / eur_rates["GBP"] if eur_rates.get("GBP") else None,
        "JPYUSD": eur_usd / eur_rates["JPY"] if eur_rates.get("JPY") else None,
        "CHFUSD": eur_usd / eur_rates["CHF"] if eur_rates.get("CHF") else None,
    }

    db = SessionLocal()
    updated = 0
    now = datetime.utcnow()

    for symbol, price in pairs.items():
        if price is None:
            print(f"   ⚠️  {symbol} : taux absent")
            continue

        existing = db.query(ExchangeRate).filter(ExchangeRate.pair == symbol).first()
        if existing:
            existing.rate       = float(price)
            existing.updated_at = now
        else:
            db.add(ExchangeRate(pair=symbol, rate=float(price), updated_at=now))

        print(f"   ✅ {symbol} = {price:.6f}")
        updated += 1

    db.commit()
    db.close()
    print(f"\nTaux mis à jour : {updated}/{len(pairs)}")


if __name__ == "__main__":
    seed_exchange_rates()
