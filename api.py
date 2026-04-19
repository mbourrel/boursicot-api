from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from typing import List, Optional

# Création des tables si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Boursicot Pro API")

# --- CONFIGURATION CORS ---
# Crucial pour que ton front-end Vercel puisse communiquer avec ton back-end Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DÉPENDANCE DE BASE DE DONNÉES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@app.get("/")
def read_root():
    return {"status": "online", "message": "API Boursicot Pro opérationnelle"}

@app.get("/api/fundamentals")
def get_fundamentals(db: Session = Depends(get_db)):
    """
    Récupère la liste des entreprises et leurs indicateurs financiers complets.
    """
    companies = db.query(models.Company).all()
    return companies

@app.get("/api/prices")
def get_prices(
    ticker: str = Query(..., description="Le ticker de l'action (ex: AAPL, AI.PA)"),
    interval: str = Query("1D", description="Intervalle souhaité : 15m, 1h, 1D, 1W"),
    limit: Optional[int] = Query(None, description="Nombre max de bougies à retourner"),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des prix pour un ticker et un intervalle donnés.
    Optimisé pour les graphiques Lightweight Charts.
    """
    # 1. Requête filtrée
    query = db.query(models.Price).filter(
        models.Price.ticker == ticker,
        models.Price.interval == interval
    )
    
    # 2. Tri chronologique (essentiel pour l'affichage du graphique)
    query = query.order_by(models.Price.date.asc())

    # 3. Application d'une limite si nécessaire (pour alléger le chargement mobile)
    if limit:
        # Si on demande une limite, on prend les X dernières bougies
        # (on doit d'abord trier par desc pour le limit, puis ré-ordonner en asc pour le graph)
        prices = query.order_by(models.Price.date.desc()).limit(limit).all()
        prices.reverse() # On remet dans l'ordre chronologique
    else:
        prices = query.all()

    if not prices:
        raise HTTPException(status_code=404, detail=f"Aucune donnée trouvée pour {ticker} en intervalle {interval}")

    # 4. Formatage ultra-rapide pour JSON
    # Lightweight Charts attend des objets avec 'time', 'open', 'high', 'low', 'close'
    return [
        {
            "time": p.date.isoformat(), # Format ISO pour une compatibilité parfaite
            "open": p.open_price,
            "high": p.high_price,
            "low": p.low_price,
            "close": p.close_price,
            "volume": p.volume,
            "interval": p.interval
        }
        for p in prices
    ]

@app.get("/api/fundamentals/{ticker}")
def get_company(ticker: str, db: Session = Depends(get_db)):
    """
    Récupère les données fondamentales d'une seule entreprise par son ticker exact.
    """
    company = db.query(models.Company).filter(models.Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' introuvable")
    return company

@app.get("/api/search")
def search_tickers(q: str, db: Session = Depends(get_db)):
    """
    Route utilitaire pour chercher une action par son nom ou son ticker.
    """
    results = db.query(models.Company).filter(
        (models.Company.ticker.ilike(f"%{q}%")) | 
        (models.Company.name.ilike(f"%{q}%"))
    ).limit(10).all()
    return results


# =============================================================================
# ENVIRONNEMENT MACRO GLOBAL
# =============================================================================

import os
import json
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from fredapi import Fred

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

@app.get("/macro/cycle")
def get_macro_cycle(db: Session = Depends(get_db)):
    """
    Phase du cycle economique basee sur INDPRO (croissance) et CPIAUCSL
    (inflation) depuis la FRED. Resultat mis en cache 24h.
    """
    cached = get_cached(db, "macro_cycle")
    if cached:
        return cached

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FRED_API_KEY manquant dans les variables d environnement")

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

@app.get("/macro/liquidity")
def get_macro_liquidity(db: Session = Depends(get_db)):
    """
    M2SL (FRED) et BTC-USD (yfinance) normalises base 100 depuis jan 2020,
    reechantillonnes au mois. Resultat mis en cache 24h.
    """
    cached = get_cached(db, "macro_liquidity")
    if cached:
        return cached

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="FRED_API_KEY manquant dans les variables d environnement")

    start_date = "2020-01-01"

    try:
        fred   = Fred(api_key=api_key)
        m2_raw = fred.get_series("M2SL", observation_start=start_date).dropna()
        m2     = m2_raw.resample("MS").last()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur FRED M2SL : {exc}")

    try:
        btc_df = yf.download("BTC-USD", start=start_date, auto_adjust=True, progress=False)
        if btc_df.empty:
            raise ValueError("Aucune donnee retournee pour BTC-USD")
        close = btc_df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.squeeze()
        btc = close.resample("MS").last().dropna()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erreur yfinance BTC : {exc}")

    df = pd.DataFrame({"m2": m2, "btc": btc}).dropna()
    if len(df) < 2:
        raise HTTPException(status_code=500, detail=f"Trop peu de points apres alignement ({len(df)})")

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
