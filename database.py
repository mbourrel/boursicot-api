from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- TEST EN DUR : On court-circuite le fichier .env ---
SQLALCHEMY_DATABASE_URL = "postgresql://boursicot_db_user:vbzcSb6Hfl5LcMWn0GqGanIKjT49zknI@dpg-d798hfffte5s739hq55g-a.frankfurt-postgres.render.com/boursicot_db?sslmode=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()