"""
Configuration pytest globale.

Setup en deux temps :
1. Variables d'environnement AVANT tout import applicatif (database.py lève
   ValueError si SQLALCHEMY_DATABASE_URL est absent, dependencies.py lit
   CLERK_JWKS_URL au niveau module).
2. Engine SQLite in-memory partagé via StaticPool → isolation totale de la DB
   de production/dev Neon.
"""
import os

# ── Doit précéder tout import du projet ──────────────────────────────────────
os.environ.setdefault("SQLALCHEMY_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLERK_JWKS_URL", "https://test.example.com/.well-known/jwks.json")
os.environ.setdefault("FMP_API_KEY", "test_fmp_dummy_key")
os.environ.setdefault("ALERT_EMAILS", "test@test.com")
os.environ.setdefault("EMAIL_USER", "test@test.com")
os.environ.setdefault("EMAIL_PASSWORD", "dummy")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import Base
from database import get_db
from dependencies import get_current_user

# ── Engine de test : SQLite in-memory, StaticPool = une seule connexion
#    partagée entre toutes les sessions → données visibles entre fixtures ─────
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def _fake_user():
    """Bypasse la validation JWT Clerk pour tous les tests."""
    return {"sub": "test_user", "is_guest": False}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Recrée toutes les tables avant chaque test, les supprime après.
    Garantit l'isolation : chaque test part d'une base vide.
    """
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def db():
    """Session SQLite isolée pour insérer/lire des données de test."""
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture
def session_factory():
    """Factory de sessions — utilisée dans les tests de seeds qui appellent
    SessionLocal() eux-mêmes (et ferment la session en fin de fonction).
    """
    return TestSessionLocal


@pytest.fixture
def client(db):
    """TestClient FastAPI avec :
    - base SQLite in-memory (pas de connexion à Neon)
    - authentification Clerk bypassée
    """
    from api import app

    def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _fake_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
