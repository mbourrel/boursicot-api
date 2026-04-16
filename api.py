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