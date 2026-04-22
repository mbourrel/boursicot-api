"""
Logique métier pour les indicateurs macroéconomiques.
Sépare le fetch/calcul (FRED, yfinance) du routeur HTTP.
"""
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from fredapi import Fred
from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.cache_service import get_cached, get_stale, set_cached


def _get_fred() -> Fred:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="FRED_API_KEY manquant dans les variables d'environnement",
        )
    return Fred(api_key=api_key)


def _yoy_and_trend(series):
    if len(series) < 14:
        raise HTTPException(
            status_code=500,
            detail=f"Historique insuffisant ({len(series)} mois, 14 requis)",
        )
    curr     = float(series.iloc[-1])
    prev     = float(series.iloc[-2])
    yr_ago   = float(series.iloc[-13])
    yr_ago_p = float(series.iloc[-14])
    yoy_curr = (curr - yr_ago)   / yr_ago   * 100
    yoy_prev = (prev - yr_ago_p) / yr_ago_p * 100
    return round(yoy_curr, 2), ("up" if yoy_curr > yoy_prev else "down")


# ── Cycle économique ──────────────────────────────────────────────────────────

def get_cycle_data(db: Session) -> dict:
    cached = get_cached(db, "macro_cycle")
    if cached:
        return cached

    fred  = _get_fred()
    start = datetime.now() - timedelta(days=15 * 31)
    end   = datetime.now()

    try:
        indpro = fred.get_series("INDPRO",   observation_start=start, observation_end=end).dropna()
        cpi    = fred.get_series("CPIAUCSL", observation_start=start, observation_end=end).dropna()
    except Exception as exc:
        stale = get_stale(db, "macro_cycle")
        if stale:
            return stale
        raise HTTPException(status_code=502, detail=f"Erreur FRED : {exc}")

    growth_yoy,    growth_trend    = _yoy_and_trend(indpro)
    inflation_yoy, inflation_trend = _yoy_and_trend(cpi)

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


# ── Liquidité M2 vs BTC ───────────────────────────────────────────────────────

def get_liquidity_data(db: Session) -> dict:
    cached = get_cached(db, "macro_liquidity")
    if cached:
        return cached

    fred       = _get_fred()
    start_date = "2020-01-01"

    try:
        m2_raw = fred.get_series("M2SL", observation_start=start_date).dropna()
        m2     = m2_raw.resample("MS").last()
    except Exception as exc:
        stale = get_stale(db, "macro_liquidity")
        if stale:
            return stale
        raise HTTPException(status_code=502, detail=f"Erreur FRED M2SL : {exc}")

    try:
        btc_raw = yf.download("BTC-USD", start=start_date, auto_adjust=True, progress=False)
        if btc_raw is None or btc_raw.empty:
            raise ValueError("Aucune donnée retournée pour BTC-USD")
        if isinstance(btc_raw.columns, pd.MultiIndex):
            close_col = btc_raw["Close"].iloc[:, 0]
        else:
            close_col = btc_raw["Close"]
        btc = close_col.resample("MS").last().dropna()
    except Exception as exc:
        stale = get_stale(db, "macro_liquidity")
        if stale:
            return stale
        raise HTTPException(status_code=502, detail=f"Erreur yfinance BTC : {exc}")

    df = pd.DataFrame({"m2": m2, "btc": btc}).dropna()
    if len(df) < 2:
        raise HTTPException(
            status_code=500,
            detail=f"Trop peu de points après alignement ({len(df)})",
        )

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


# ── Taux directeurs & rendements obligataires ────────────────────────────────

def get_rates_data(db: Session) -> dict:
    cached = get_cached(db, "macro_rates_v6", max_age_hours=6)
    if cached:
        return cached

    fred = _get_fred()
    end        = datetime.now()
    start_cur  = end - timedelta(days=90)
    start_hist = "1960-01-01"  # FRED retourne tout l'historique disponible selon la série

    def _latest(series_id: str, start=start_cur):
        """Retourne (valeur_actuelle, date_str) ou (None, None) en cas d'erreur."""
        try:
            s = fred.get_series(series_id, observation_start=start, observation_end=end).dropna()
            if s.empty:
                return None, None
            return round(float(s.iloc[-1]), 3), s.index[-1].strftime("%Y-%m-%d")
        except Exception:
            return None, None

    def _history(series_id: str):
        """Retourne {dates, values} sur 2 ans ou listes vides en cas d'erreur."""
        try:
            s = fred.get_series(series_id, observation_start=start_hist, observation_end=end).dropna()
            return {
                "dates":  [d.strftime("%Y-%m-%d") for d in s.index],
                "values": [round(float(v), 3) for v in s],
            }
        except Exception:
            return {"dates": [], "values": []}

    # ── Taux directeurs ──────────────────────────────────────────────────────
    fed_rate,  fed_date  = _latest("DFF")
    ecb_rate,  ecb_date  = _latest("ECBDFR")
    # BoE : IUDSOIA = SONIA (proxy quasi-parfait du Bank Rate, publié quotidiennement)
    boe_rate,  boe_date  = _latest("IUDSOIA")
    # BoJ : aucune série FRED fiable et récente — taux hardcodé (relevé jan 2025)
    boj_rate,  boj_date  = 0.5, "2025-01-24"

    # ── Rendements obligataires courants ─────────────────────────────────────
    us2y,    us2y_date    = _latest("DGS2")
    us10y,   us10y_date   = _latest("DGS10")
    us30y,   us30y_date   = _latest("DGS30")
    # Taux 3 mois (marché monétaire) — FRED : DGS3MO (US) et IRLTST01 OCDE (Europe/UK)
    us3m,    us3m_date    = _latest("DGS3MO")
    bund10y, bund10y_date = _latest("IRLTLT01DEM156N")
    bund3m,  bund3m_date  = _latest("IRLTST01DEM156N")
    oat10y,  oat10y_date  = _latest("IRLTLT01FRM156N")
    oat3m,   oat3m_date   = _latest("IRLTST01FRM156N")
    gilt10y, gilt10y_date = _latest("IRLTLT01GBM156N")
    gilt3m,  gilt3m_date  = _latest("IRLTST01GBM156N")

    # ── Historiques pour graphiques ──────────────────────────────────────────
    result = {
        "central_banks": [
            {"name": "Fed (US)",    "rate": fed_rate,  "last_update": fed_date,  "stale": False},
            {"name": "BCE",         "rate": ecb_rate,  "last_update": ecb_date,  "stale": False},
            {"name": "BoE (UK)",    "rate": boe_rate,  "last_update": boe_date,  "stale": False},
            {"name": "BoJ (Japon)", "rate": boj_rate,  "last_update": boj_date,  "stale": True},  # hardcodé
        ],
        "bond_yields": [
            {"name": "US 2Y",      "rate": us2y,    "last_update": us2y_date},
            {"name": "US 10Y",     "rate": us10y,   "last_update": us10y_date},
            {"name": "US 30Y",     "rate": us30y,   "last_update": us30y_date},
            {"name": "US 3M",      "rate": us3m,    "last_update": us3m_date},
            {"name": "Bund 10Y",   "rate": bund10y, "last_update": bund10y_date},
            {"name": "Bund 3M",    "rate": bund3m,  "last_update": bund3m_date},
            {"name": "OAT 10Y",    "rate": oat10y,  "last_update": oat10y_date},
            {"name": "OAT 3M",     "rate": oat3m,   "last_update": oat3m_date},
            {"name": "Gilt 10Y",   "rate": gilt10y, "last_update": gilt10y_date},
            {"name": "Gilt 3M",    "rate": gilt3m,  "last_update": gilt3m_date},
        ],
        "history": {
            "us2y":    _history("DGS2"),
            "us10y":   _history("DGS10"),
            "us30y":   _history("DGS30"),
            "us3m":    _history("DGS3MO"),
            "bund10y": _history("IRLTLT01DEM156N"),
            "bund3m":  _history("IRLTST01DEM156N"),
            "oat10y":  _history("IRLTLT01FRM156N"),
            "oat3m":   _history("IRLTST01FRM156N"),
            "gilt10y": _history("IRLTLT01GBM156N"),
            "gilt3m":  _history("IRLTST01GBM156N"),
        },
        "yield_curve": _history("T10Y2Y"),
    }

    try:
        set_cached(db, "macro_rates_v6", result)
    except Exception:
        pass

    return result


# ── Historique du cycle ───────────────────────────────────────────────────────

def get_cycle_history(db: Session) -> dict:
    cached = get_cached(db, "macro_cycle_history")
    if cached:
        return cached

    fred  = _get_fred()
    start = "1946-01-01"
    end   = datetime.now()

    try:
        indpro = fred.get_series("INDPRO",   observation_start=start, observation_end=end).dropna()
        cpi    = fred.get_series("CPIAUCSL", observation_start=start, observation_end=end).dropna()
    except Exception as exc:
        stale = get_stale(db, "macro_cycle_history")
        if stale:
            return stale
        raise HTTPException(status_code=502, detail=f"Erreur FRED : {exc}")

    df = pd.DataFrame({"indpro": indpro, "cpi": cpi}).dropna()
    if len(df) < 14:
        raise HTTPException(
            status_code=500,
            detail=f"Historique insuffisant ({len(df)} mois, 14 requis)",
        )

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

    result = {"history": history}
    set_cached(db, "macro_cycle_history", result)
    return result
