from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# On récupère le dossier actuel de api.py (...\fake_data\bourse)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ROUTE 1 : PRIX ---
@app.get("/api/prices")
def get_prices():
    # historical_prices.json est dans le même dossier
    file_path = os.path.join(BASE_DIR, "historical_prices.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Fichier de prix non trouvé : {str(e)}"}

# --- ROUTE 2 : FONDAMENTAUX ---
@app.get("/api/fundamentals")
def get_fundamentals():
    # SIMPLIFIÉ : fundamentals_seed.json est maintenant dans le même dossier !
    file_path = os.path.join(BASE_DIR, "fundamentals_seed.json")
    
    try:
        if not os.path.exists(file_path):
             return {"error": f"Fichier introuvable. Le backend cherche ici : {file_path}"}
             
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Erreur de lecture : {str(e)}"}