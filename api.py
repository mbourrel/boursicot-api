from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models

from routers import prices, fundamentals, search, macro

# Création des tables si elles n'existent pas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Boursicot Pro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router)
app.include_router(fundamentals.router)
app.include_router(search.router)
app.include_router(macro.router)


@app.get("/")
def read_root():
    return {"status": "online", "message": "API Boursicot Pro opérationnelle"}
