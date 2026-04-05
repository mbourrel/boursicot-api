from fastapi import FastAPI, Depends
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
    allow_origins=["*"],  # En production, mets "http://localhost:3000"
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
def get_prices(db: Session = Depends(get_db)):
    """
    Récupère l'historique des prix.
    On traduit 'open_price' en 'open' pour correspondre aux attentes de React.
    """
    prices = db.query(models.Price).all()
    
    # Formatage de la réponse pour correspondre exactement à ce que React attend
    result = []
    for p in prices:
        result.append({
            "ticker": p.ticker,
            "date": p.date,
            "open": p.open_price,   # Traduction ici
            "high": p.high_price,   # Traduction ici
            "low": p.low_price,     # Traduction ici
            "close": p.close_price, # Traduction ici
            "volume": p.volume
        })
    return result