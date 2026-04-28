"""
Rafraîchit les prix live (close_price + daily_change_pct) pour tous les tickers
via FMP /stable/quote. Conçu pour un cron 2x/jour (9h et 17h30 Paris).

FMP /stable/quote supporte : actions, indices (^FCHI...), crypto et matières premières.
Seuls BTC-USD et les symboles Yahoo =F (GC=F...) sont mappés vers les équivalents FMP.
Les indices gardent le préfixe ^ tel quel.

Budget : 1 call FMP par ticker → 64 calls par run → 128/250 calls/jour.
Supporte jusqu'à 125 tickers avec 2 runs/jour avant d'atteindre la limite.

    python seeds/seed_live_prices.py
    python seeds/seed_live_prices.py AI.PA AIR.PA   # tickers spécifiques
"""
import sys
import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

# Charge .env si présent (dev local)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database import SessionLocal
from models import Company
from seed_utils import TICKERS

FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_URL     = "https://financialmodelingprep.com/stable/quote"

# Mapping Yahoo Finance → FMP uniquement pour les symboles incompatibles.
# Les indices (^FCHI, ^GSPC...) sont supportés nativement par FMP avec leur ^ prefix.
FMP_TICKER_MAP: dict[str, str] = {
    # Crypto
    "BTC-USD": "BTCUSD",
    # Metaux precieux
    "GC=F":    "GCUSD",
    "SI=F":    "SIUSD",
    # Energie
    "CL=F":    "CLUSD",
    "BZ=F":    "BZUSD",
    "NG=F":    "NGUSD",
    # Matieres premieres agricoles
    "ZC=F":    "ZCUSD",
    "ZW=F":    "ZWUSD",
    "CT=F":    "CTUSD",
}


def fetch_price(client: httpx.Client, ticker: str) -> tuple[float | None, float | None]:
    """Retourne (price, change_pct) depuis FMP /stable/quote ou (None, None) en cas d'erreur."""
    fmp_symbol = FMP_TICKER_MAP.get(ticker, ticker)
    try:
        resp = client.get(FMP_URL, params={"symbol": fmp_symbol, "apikey": FMP_API_KEY}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                q = data[0]
                price  = q.get("price")
                change = q.get("changePercentage")
                return price, (round(change, 2) if change is not None else None)
    except Exception as e:
        print(f"   WARN {ticker}: {e}")
    return None, None


def seed_live_prices(tickers: list[str]):
    if not FMP_API_KEY:
        print("ERREUR : FMP_API_KEY non definie. Ajoutez-la dans .env ou les variables d'environnement.")
        sys.exit(1)

    db  = SessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ok = ko = 0

    print(f"Refresh prix live pour {len(tickers)} ticker(s) — {now.strftime('%Y-%m-%d %H:%M')} UTC\n")

    with httpx.Client(timeout=8) as client:
        for ticker in tickers:
            price, change = fetch_price(client, ticker)

            if price is not None:
                company = db.query(Company).filter(Company.ticker == ticker).first()
                if company:
                    company.live_price      = price
                    company.live_change_pct = change
                    company.live_price_at   = now
                    db.commit()
                    sign  = "+" if (change or 0) >= 0 else ""
                    fmp_s = FMP_TICKER_MAP.get(ticker, ticker)
                    label = ticker if fmp_s == ticker else f"{ticker} ({fmp_s})"
                    print(f"  OK  {label:<22} {price} | {sign}{change} %")
                    ok += 1
                else:
                    print(f"  SKIP {ticker:<18} absent de la table companies")
                    ko += 1
            else:
                print(f"  FAIL {ticker:<18} pas de donnee FMP")
                ko += 1

            time.sleep(0.1)  # courtoisie API

    db.close()
    print(f"\nTermine : {ok} OK / {ko} echecs — {ok + ko} calls FMP utilises")


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else (list(TICKERS.keys()) if isinstance(TICKERS, dict) else list(TICKERS))
    seed_live_prices(targets)
