import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from dependencies import get_current_user

from routers import prices, fundamentals, search, macro, assets

# Création des tables si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Boursicot Pro API",
    dependencies=[Depends(get_current_user)],
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(prices.router)
app.include_router(fundamentals.router)
app.include_router(search.router)
app.include_router(macro.router)
app.include_router(assets.router)


@app.get("/")
def read_root():
    return {"status": "online", "message": "API Boursicot Pro opérationnelle"}
