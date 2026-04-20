import os
import json
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from fredapi import Fred

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/macro", tags=["macro"])


# ── Helpers cache PostgreSQL ──────────────────────────────────────────────────

def get_cached(db: Session, key: str, max_age_hours: int = 24):
    record = db.query(models.MacroCache).filter(models.MacroCache.cache_key == key).first()
    if not record:
        return None
    if datetime.utcnow() - record.updated_at > timedelta(hours=max_age_hours):
        return None
    return json.loads(record.data_json)


def set_cached(db: Session, key: str, data: dict):
    record = db.query(models.MacroCache).filter(models.MacroCache.cache_key == key).first()
    if record:
        record.data_json  = json.dumps(data, ensure_ascii=False)
        record.updated_at = datetime.utcnow()
    else:
        record = models.MacroCache(cache_key=key, data_json=json.dumps(data, ensure_ascii=False))
        db.add(record)
    db.commit()


# ── GET /macro/cycle ──────────────────────────────────────────────────────────

@router.get("/cycle")
def get_macro_cycle(db: Session = Depends(get_db)):
    """
    Phase du cycle économique basée sur INDPRO (croissance) et CPIAUCSL
    (inflation) depuis la FRED. Résultat mis en cache 24h.
    """
    cached = get_cached(db, "macro_cycle")
    if cached:
        return cached

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FRED_API_KEY manquant dans les variables d'environnement")

    try:
        fred  = Fred(api_key=api_key)
        start = datetime.now() - timedelta(days=15 * 31)
        end   = datetime.now()
        indpro = fred.get_series("INDPRO",   observation_start=start, observation_end=end).dropna()
        cpi    = fred.get_series("CPIAUCSL", observation_start=start, observation_end=end).dropna()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur FRED : {exc}")

    def yoy_and_trend(series):
        if len(series) < 14:
            raise HTTPException(status_code=500, detail=f"Historique insuffisant ({len(series)} mois, 14 requis)")
        curr     = float(series.iloc[-1])
        prev     = float(series.iloc[-2])
        yr_ago   = float(series.iloc[-13])
        yr_ago_p = float(series.iloc[-14])
        yoy_curr = (curr - yr_ago)   / yr_ago   * 100
        yoy_prev = (prev - yr_ago_p) / yr_ago_p * 100
        return round(yoy_curr, 2), ("up" if yoy_curr > yoy_prev else "down")

    growth_yoy,    growth_trend    = yoy_and_trend(indpro)
    inflation_yoy, inflation_trend = yoy_and_trend(cpi)

    if   growth_trend == "up"   and inflation_trend == "down": phase = "Expansion"
    elif growth_trend == "up"   and inflation_trend == "up":   phase = "Surchauffe"
    elif growth_trend == "down" and inflation_trend == "up":   phase = "Contraction"
    else:                                                        phase = "Recession"

    result = {
        "phase":           phase,
        "growth_yoy":      growth_yoy,
        "inflation_yoy":   inflation_yoy,
        "growth_trend":    growth_trend,
        "inflation_trend": inflation_trend,
    }
    set_cached(db, "macro_cycle", result)
    return result


# ── GET /macro/liquidity ──────────────────────────────────────────────────────

@router.get("/liquidity")
def get_macro_liquidity(db: Session = Depends(get_db)):
    """
    M2SL (FRED) et BTC-USD (yfinance) normalisés base 100 depuis jan 2020,
    rééchantillonnés au mois. Résultat mis en cache 24h.
    """
    cached = get_cached(db, "macro_liquidity")
    if cached:
        return cached

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FRED_API_KEY manquant dans les variables d'environnement")

    start_date = "2020-01-01"

    try:
        fred   = Fred(api_key=api_key)
        m2_raw = fred.get_series("M2SL", observation_start=start_date).dropna()
        m2     = m2_raw.resample("MS").last()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur FRED M2SL : {exc}")

    try:
        btc_df = yf.Ticker("BTC-USD").history(start=start_date, auto_adjust=True)
        if btc_df.empty:
            raise ValueError("Aucune donnée retournée pour BTC-USD")
        btc = btc_df["Close"].resample("MS").last().dropna()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur yfinance BTC : {exc}")

    df = pd.DataFrame({"m2": m2, "btc": btc}).dropna()
    if len(df) < 2:
        raise HTTPException(status_code=500, detail=f"Trop peu de points après alignement ({len(df)})")

    base_m2  = df["m2"].iloc[0]
    base_btc = df["btc"].iloc[0]
    df["m2_norm"]  = df["m2"]  / base_m2  * 100
    df["btc_norm"] = df["btc"] / base_btc * 100

    result = {
        "dates":          [d.strftime("%Y-%m-%d") for d in df.index],
        "m2_normalized":  [round(float(v), 2) for v in df["m2_norm"]],
        "btc_normalized": [round(float(v), 2) for v in df["btc_norm"]],
    }
    set_cached(db, "macro_liquidity", result)
    return result


# ── GET /macro/cycle/history ─────────────────────────────────────────────────

@router.get("/cycle/history")
def get_macro_cycle_history(db: Session = Depends(get_db)):
    """
    Historique mensuel du cycle économique sur les 5 dernières années.
    Chaque point contient : date, growth_yoy (INDPRO), inflation_yoy (CPI), phase.
    """
    cached = get_cached(db, "macro_cycle_history")
    if cached:
        return cached

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FRED_API_KEY manquant dans les variables d'environnement")

    try:
        fred  = Fred(api_key=api_key)
        # Depuis jan 1997 : 13 mois de marge avant 1998 pour calculer les YoY dès jan 1998
        # INDPRO disponible depuis 1919, CPIAUCSL depuis 1947 — pas de limite côté FRED
        start = "1997-01-01"
        end   = datetime.now()
        indpro = fred.get_series("INDPRO",   observation_start=start, observation_end=end).dropna()
        cpi    = fred.get_series("CPIAUCSL", observation_start=start, observation_end=end).dropna()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur FRED : {exc}")

    df = pd.DataFrame({"indpro": indpro, "cpi": cpi}).dropna()

    if len(df) < 14:
        raise HTTPException(status_code=500, detail=f"Historique insuffisant ({len(df)} mois, 14 requis)")

    history = []
    for i in range(13, len(df)):
        g_curr   = float(df["indpro"].iloc[i])
        g_prev   = float(df["indpro"].iloc[i - 1])
        g_yr     = float(df["indpro"].iloc[i - 12])
        g_yr_p   = float(df["indpro"].iloc[i - 13])

        c_curr   = float(df["cpi"].iloc[i])
        c_prev   = float(df["cpi"].iloc[i - 1])
        c_yr     = float(df["cpi"].iloc[i - 12])
        c_yr_p   = float(df["cpi"].iloc[i - 13])

        growth_yoy      = (g_curr - g_yr)   / g_yr   * 100
        growth_yoy_prev = (g_prev - g_yr_p) / g_yr_p * 100
        cpi_yoy         = (c_curr - c_yr)   / c_yr   * 100
        cpi_yoy_prev    = (c_prev - c_yr_p) / c_yr_p * 100

        growth_trend    = "up" if growth_yoy > growth_yoy_prev else "down"
        inflation_trend = "up" if cpi_yoy    > cpi_yoy_prev    else "down"

        if   growth_trend == "up"   and inflation_trend == "down": phase = "Expansion"
        elif growth_trend == "up"   and inflation_trend == "up":   phase = "Surchauffe"
        elif growth_trend == "down" and inflation_trend == "up":   phase = "Contraction"
        else:                                                        phase = "Récession"

        history.append({
            "date":          df.index[i].strftime("%Y-%m-%d"),
            "growth_yoy":    round(growth_yoy, 2),
            "inflation_yoy": round(cpi_yoy, 2),
            "phase":         phase,
        })

    # Historique complet depuis 1998 — pas de troncature
    result = {"history": history}
    set_cached(db, "macro_cycle_history", result)
    return result


# ── GET /macro/ping ───────────────────────────────────────────────────────────

@router.get("/ping")
def macro_ping():
    """Diagnostic : vérifie que la clé FRED est configurée et accessible."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return {"status": "error", "detail": "FRED_API_KEY absent des variables d'environnement"}
    try:
        fred = Fred(api_key=api_key)
        test = fred.get_series("FEDFUNDS",
                               observation_start=datetime.now() - timedelta(days=60),
                               observation_end=datetime.now())
        return {"status": "ok", "fred_key_valid": True, "sample_points": len(test)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
