from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, BigInteger
from database import Base

class Company(Base):
    __tablename__ = "companies"
    
    ticker = Column(String, primary_key=True, index=True)
    name = Column(String)
    sector = Column(String)
    description = Column(String)
    
    # Stockage des données fondamentales sous forme de listes JSON
    market_analysis = Column(JSON, default=list)
    financial_health = Column(JSON, default=list)
    advanced_valuation = Column(JSON, default=list)
    income_growth = Column(JSON, default=list)
    balance_cash = Column(JSON, default=list)
    risk_market = Column(JSON, default=list)

class Price(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(DateTime, index=True)
    interval = Column(String, index=True) # ex: '1h', '1D', '1W'
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(BigInteger) # <--- LA CORRECTION EST ICI (BigInteger au lieu de Integer)