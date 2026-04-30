"""
Rafraîchit les prix live (close_price + daily_change_pct) pour tous les tickers via FMP.
Conçu pour un cron 2x/jour (9h et 17h30 Paris).

Endpoints FMP utilisés :
  - /stable/profile  → actions (EU .PA/.AS + US) — plan gratuit OK
  - /stable/quote    → indices (^GSPC...), crypto (BTCUSD), matières premières

Budget : 1 call FMP par ticker → 64 calls par run → 128/250 calls/jour.

    python seeds/seed_live_prices.py
    python seeds/seed_live_prices.py AI.PA AIR.PA   # tickers spécifiques
"""
import sys
import os
import time
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database import SessionLocal
from models import Company
from seed_utils import TICKERS
from config import FMP_API_KEY, FMP_STABLE

FMP_PROFILE = f"{FMP_STABLE}/profile"
FMP_QUOTE   = f"{FMP_STABLE}/quote"

# Mapping Yahoo Finance → symbole FMP pour non-actions.
# Les indices gardent leur ^ prefix (supporté nativement par FMP).
# Les actions n'ont pas besoin de mapping (même symbole dans les deux systèmes).
FMP_TICKER_MAP: dict[str, str] = {
    # Crypto
    "BTC-USD": "BTCUSD",
    # Metaux precieux
    "GC=F":    "GCUSD",      # Or
    "SI=F":    "SIUSD",      # Argent
    # Energie — FMP utilise USOIL/UKOIL pour petrole, NATGAS pour gaz
    "CL=F":    "USOIL",      # Petrole WTI
    "BZ=F":    "BZUSD",      # Petrole Brent
    "NG=F":    "NATGAS",     # Gaz Naturel
    # Cereales et soft commodities (disponibilite FMP gratuite limitee)
    "ZC=F":    "ZCUSD",      # Mais
    "ZW=F":    "ZWUSD",      # Ble
    "CT=F":    "CTUSD",      # Coton
}

# Tickers qui utilisent /stable/quote au lieu de /stable/profile
# (indices + crypto + matieres premieres)
QUOTE_TICKERS = set(FMP_TICKER_MAP.keys()) | {
    "^FCHI", "^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^N225", "^VIX",
}


def fetch_price(client: httpx.Client, ticker: str) -> tuple[float | None, float | None]:
    """Retourne (price, change_pct) depuis FMP ou (None, None) en cas d'erreur."""
    if ticker in QUOTE_TICKERS:
        url       = FMP_QUOTE
        fmp_sym   = FMP_TICKER_MAP.get(ticker, ticker)
        price_key = "price"
        chg_key   = "changePercentage"
    else:
        url       = FMP_PROFILE
        fmp_sym   = ticker
        price_key = "price"
        chg_key   = "changePercentage"

    try:
        resp = client.get(url, params={"symbol": fmp_sym, "apikey": FMP_API_KEY}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                p = data[0]
                price  = p.get(price_key)
                change = p.get(chg_key)
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
                    print(f"  OK  {label:<24} {price} | {sign}{change} %")
                    ok += 1
                else:
                    print(f"  SKIP {ticker:<20} absent de la table companies")
                    ko += 1
            else:
                print(f"  FAIL {ticker:<20} pas de donnee FMP")
                ko += 1

            time.sleep(0.1)

    db.close()
    total_calls  = ok + ko
    budget_used  = total_calls * 2          # 2 runs/jour max (9h + 17h30)
    budget_left  = 250 - budget_used
    budget_pct   = round(budget_used / 250 * 100)
    warn         = " ⚠️  ATTENTION : budget dépassé !" if budget_used > 250 else ""
    print(
        f"\nTermine : {ok} OK / {ko} echecs — {total_calls} calls FMP utilises ce run\n"
        f"Budget journalier estimé (2 runs) : {budget_used}/250 calls ({budget_pct}%) "
        f"→ {budget_left} restants{warn}"
    )


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else (list(TICKERS.keys()) if isinstance(TICKERS, dict) else list(TICKERS))
    seed_live_prices(targets)
