import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Récupère l'URL (soit locale pour le dev, soit Render pour le déploiement)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Si l'URL n'est pas trouvée, on met une sécurité pour éviter le "None"
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()