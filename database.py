import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- CHARGEMENT DU FICHIER .ENV ---
# Cela va chercher l'URL dans ton fichier .env au lieu de l'écrire en dur
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

# Sécurité pour vérifier que l'URL est bien chargée
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("⚠️ L'URL de la base de données est introuvable. Vérifie ton fichier .env !")

# Création du moteur SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()