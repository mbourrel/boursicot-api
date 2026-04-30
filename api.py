import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import engine
import models
from dependencies import get_current_user

from routers import prices, fundamentals, search, macro, assets, exchange_rates

# Création des tables si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title="Boursicot Pro API",
    dependencies=[Depends(get_current_user)],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(prices.router)
app.include_router(fundamentals.router)
app.include_router(search.router)
app.include_router(macro.router)
app.include_router(assets.router)
app.include_router(exchange_rates.router)


@app.get("/")
def read_root():
    return {"status": "online", "message": "API Boursicot Pro opérationnelle"}
