from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

# Création des tables au cas où (sécurité)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Boursicot API")

# --- CONFIGURATION CORS ---
# Indispensable pour autoriser React (qui tourne sur le port 3000) à discuter avec l'API (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, mets "http://localhost:3000" ou l'URL de ton front
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

# --- ROUTES DE L'API ---

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Boursicot Pro !"}

@app.get("/api/fundamentals")
def get_fundamentals(db: Session = Depends(get_db)):
    """
    Récupère toutes les entreprises et leurs données fondamentales (JSON inclus).
    FastAPI convertit automatiquement les objets SQLAlchemy en JSON.
    """
    companies = db.query(models.Company).all()
    return companies

@app.get("/api/prices")
def get_prices(
    ticker: str = Query(None, description="Filtrer par action (ex: AAPL)"),
    interval: str = Query("1D", description="Filtrer par intervalle (1h, 1D, 1W)"),
    db: Session = Depends(get_db)
):
    """
    Récupère l'historique des prix.
    L'API est désormais optimisée pour ne renvoyer QUE les données demandées par le front.
    """
    # 1. On prépare la requête de base
    query = db.query(models.Price)
    
    # 2. On applique les filtres dynamiquement
    if ticker:
        query = query.filter(models.Price.ticker == ticker)
    
    if interval:
        query = query.filter(models.Price.interval == interval)
        
    # 3. On trie chronologiquement (très important pour les graphiques !)
    prices = query.order_by(models.Price.date.asc()).all()
    
    # 4. Formatage de la réponse pour correspondre exactement à ce que React attend
    result = []
    for p in prices:
        result.append({
            "ticker": p.ticker,
            "date": p.date,
            "interval": p.interval, # Ajouté pour faciliter le debug côté React
            "open": p.open_price,
            "high": p.high_price,
            "low": p.low_price,
            "close": p.close_price,
            "volume": p.volume
        })
    return result