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
from collections import defaultdict
from datetime import datetime, timezone

import httpx
import yfinance as yf
from dotenv import load_dotenv
from sqlalchemy.orm.attributes import flag_modified

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from database import SessionLocal
from models import Company
from seed_utils import TICKERS
from config import FMP_API_KEY, FMP_STABLE
from scoring_logic import compute_scores, is_scorable
from utils.fmp_monitor import check_and_increment, get_count

FMP_PROFILE = f"{FMP_STABLE}/profile"
FMP_QUOTE   = f"{FMP_STABLE}/quote"

# Mapping Yahoo Finance → symbole FMP pour non-actions.
# Les indices gardent leur ^ prefix (supporté nativement par FMP).
# Les actions et ETF européens n'ont pas besoin de mapping (même symbole dans les deux systèmes).
FMP_TICKER_MAP: dict[str, str] = {
    # Crypto
    "BTC-USD": "BTCUSD",
    "ETH-USD": "ETHUSD",
    # Metaux precieux
    "GC=F":    "GCUSD",      # Or
    "SI=F":    "SIUSD",      # Argent
    # Energie — FMP utilise USOIL/UKOIL pour petrole, NATGAS pour gaz
    "CL=F":    "USOIL",      # Petrole WTI
    "BZ=F":    "BZUSD",      # Petrole Brent
    "NG=F":    "NATGAS",     # Gaz Naturel
    # Cereales
    "ZW=F":    "ZWUSD",      # Ble
}

# Tickers qui utilisent /stable/quote au lieu de /stable/profile
# (indices + crypto + matieres premieres)
QUOTE_TICKERS = set(FMP_TICKER_MAP.keys()) | {
    "^FCHI", "^GSPC", "^IXIC", "^DJI", "^STOXX50E", "^N225", "^VIX",
}


def fetch_price(client: httpx.Client, ticker: str) -> tuple[float | None, float | None]:
    """Retourne (price, change_pct) depuis FMP ou (None, None) en cas d'erreur ou circuit ouvert."""
    status, count = check_and_increment()
    if status == "blocked":
        return None, None

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


def _refresh_momentum(ticker: str) -> dict:
    """
    Calcule MM50, MM200 et Performance 1 an depuis yfinance history.
    Utilisé pour les actifs non-actions (indices, crypto, matières premières)
    dont les fondamentaux ne sont pas re-seedés fréquemment.
    Retourne un dict avec les clés mm50, mm200, perf_1y (ou None si indisponible).
    """
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 2:
            return {}
        closes = hist['Close']
        mm50  = round(float(closes.tail(50).mean()), 4) if len(closes) >= 50  else None
        mm200 = round(float(closes.mean()), 4)           if len(closes) >= 200 else None
        perf  = round(float(closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2)
        return {"mm50": mm50, "mm200": mm200, "perf_1y": perf}
    except Exception as e:
        print(f"   WARN momentum yf {ticker}: {e}")
        return {}


def _update_risk_market(company, updates: dict) -> None:
    """
    Met à jour les entrées MM50, MM200 et Performance 1an dans le JSON risk_market.
    Crée les entrées si elles n'existent pas encore.
    """
    if not updates:
        return
    risk = list(company.risk_market or [])
    name_map = {
        "mm50":        ("MM50",             "$"),
        "mm200":       ("MM200",            "$"),
        "perf_1y":     ("Performance 1an",  "%"),
        "prix_actuel": ("Prix Actuel",      "$"),
    }
    for key, (metric_name, unit) in name_map.items():
        val = updates.get(key)
        if val is None:
            continue
        entry = next((m for m in risk if m.get("name") == metric_name), None)
        if entry:
            entry["val"] = val
        else:
            risk.append({"name": metric_name, "val": val, "unit": unit})
    company.risk_market = risk
    flag_modified(company, "risk_market")


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

                    # Refresh MM50/MM200/Perf1an via yfinance pour TOUS les tickers.
                    # Pas de coût FMP — yfinance est gratuit.
                    # Permet de garder le momentum des actions synchronisé avec le prix live.
                    momentum = _refresh_momentum(ticker)
                    # Injecte aussi le prix live dans risk_market["Prix Actuel"]
                    # pour que _score_momentum() utilise un prix frais (et non stale).
                    momentum["prix_actuel"] = price
                    _update_risk_market(company, momentum)

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

    # ── Second passage : recompute scores_json avec MM50/MM200 frais ──────────
    # Zéro appel FMP supplémentaire — utilise uniquement les données déjà en DB.
    print("\nRecalcul des scores avec le momentum frais...")
    all_companies = db.query(Company).all()
    by_sector: dict[str, list] = defaultdict(list)
    for c in all_companies:
        if c.sector:
            by_sector[c.sector].append(c)

    score_ok = score_skip = 0
    for company in all_companies:
        if not is_scorable(company.ticker) or not company.sector:
            score_skip += 1
            continue
        sector_companies = by_sector.get(company.sector, [company])
        company.scores_json = compute_scores(company, sector_companies)
        score_ok += 1

    db.commit()
    print(f"  Scores : {score_ok} recalculés / {score_skip} ignorés (non-scorables ou sans secteur)")

    db.close()
    total_calls = ok + ko
    daily_count = get_count()
    daily_left  = 250 - daily_count
    daily_pct   = round(daily_count / 250 * 100)
    warn        = " !! ATTENTION : quota journalier depasse !" if daily_count > 250 else (
                  " !! Circuit breaker actif ce run." if daily_count >= 245 else (
                  " -- Alerte envoyée (>85%)." if daily_count >= 210 else ""))
    print(
        f"\nTermine : {ok} OK / {ko} echecs — {total_calls} appels FMP ce run\n"
        f"Compteur journalier : {daily_count}/250 ({daily_pct}%) -> {daily_left} restants{warn}"
    )


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else (list(TICKERS.keys()) if isinstance(TICKERS, dict) else list(TICKERS))
    seed_live_prices(targets)
