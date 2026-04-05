import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# 1. On charge les secrets du fichier .env
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. On crée le "moteur" qui va physiquement se connecter à PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. On prépare une "usine à sessions" (chaque fois qu'un utilisateur demandera un graphique, on lui ouvrira une session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. On prépare le moule pour créer nos futures tables (Company, Prices, etc.)
Base = declarative_base()