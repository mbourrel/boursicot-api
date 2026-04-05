import os
from dotenv import load_dotenv

load_dotenv() # Charge le fichier .env en local (ignoré sur Render)

# Récupère l'URL de Render, ou utilise une locale par défaut si on est sur ton PC
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. On crée le "moteur" qui va physiquement se connecter à PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. On prépare une "usine à sessions" (chaque fois qu'un utilisateur demandera un graphique, on lui ouvrira une session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. On prépare le moule pour créer nos futures tables (Company, Prices, etc.)
Base = declarative_base()