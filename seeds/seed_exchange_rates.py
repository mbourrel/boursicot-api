"""
Met à jour les taux de change (EURUSD, GBPUSD, JPYUSD, CHFUSD) depuis FMP.
1 seul appel API par exécution — budget : 1 call/jour sur 250.

    python seeds/seed_exchange_rates.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from datetime import datetime
from database import SessionLocal, engine
from models import Base, ExchangeRate

Base.metadata.create_all(bind=engine)

FMP_API_KEY = os.getenv("FMP_API_KEY")
# /api/v3/fx retourne toutes les paires forex en un seul appel
# Format réponse : [{"ticker": "EUR/USD", "bid": 1.085, "ask": 1.086, ...}, ...]
FMP_FX_URL  = "https://financialmodelingprep.com/api/v3/fx"
PAIRS       = {"EURUSD", "GBPUSD", "JPYUSD", "CHFUSD"}


def seed_exchange_rates():
    if not FMP_API_KEY:
        print("❌ FMP_API_KEY manquante — vérifiez les secrets GitHub / variables Render")
        sys.exit(1)

    try:
        resp = requests.get(FMP_FX_URL, params={"apikey": FMP_API_KEY}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Erreur FMP : {e}")
        sys.exit(1)

    if not data:
        print("❌ Réponse FMP vide")
        sys.exit(1)

    db = SessionLocal()
    updated = 0
    now = datetime.utcnow()

    for item in data:
        # ticker format: "EUR/USD" → on normalise en "EURUSD"
        ticker = item.get("ticker", "").replace("/", "")
        # taux mid = moyenne bid/ask ; fallback sur bid seul
        bid  = item.get("bid")
        ask  = item.get("ask")
        if bid is not None and ask is not None:
            price = (float(bid) + float(ask)) / 2
        elif bid is not None:
            price = float(bid)
        else:
            price = None

        symbol = ticker

        if symbol not in PAIRS or price is None:
            continue

        existing = db.query(ExchangeRate).filter(ExchangeRate.pair == symbol).first()
        if existing:
            existing.rate       = float(price)
            existing.updated_at = now
        else:
            db.add(ExchangeRate(pair=symbol, rate=float(price), updated_at=now))

        print(f"   ✅ {symbol} = {price}")
        updated += 1

    db.commit()
    db.close()
    print(f"\nTaux mis à jour : {updated}/{len(PAIRS)}")


if __name__ == "__main__":
    seed_exchange_rates()
