# Ajoute BigInteger à tes imports SQLAlchemy
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    sector = Column(String)
    description = Column(String)
    
    # Données financières stockées en JSON
    market_analysis = Column(JSON)
    financial_health = Column(JSON)
    advanced_valuation = Column(JSON)
    income_growth = Column(JSON)
    balance_cash = Column(JSON)
    risk_market = Column(JSON)

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(DateTime, index=True, nullable=False)
    interval = Column(String, index=True, nullable=False) # Ex: '1D', '1h', '15m', '1W'
    
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    
    # --- MODIFICATION ICI : On passe de Integer à BigInteger ---
    volume = Column(BigInteger)

    # Sécurité : Empêche les doublons exacts dans la base de données
    __table_args__ = (
        UniqueConstraint('ticker', 'date', 'interval', name='uix_ticker_date_interval'),
    )