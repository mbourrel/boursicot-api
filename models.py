from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from database import Base

# --- TABLE DES ENTREPRISES ---
class Company(Base):
    __tablename__ = "companies"

    ticker = Column(String, primary_key=True, index=True) 
    name = Column(String, nullable=False)                 
    sector = Column(String)                               
    
    # Résumé
    description = Column(String)                          
    
    # Anciennes catégories
    market_analysis = Column(JSON)                        
    financial_health = Column(JSON)                       
    
    # --- NOUVELLES CATÉGORIES ---
    advanced_valuation = Column(JSON)                     # Valorisation Avancée (P/B, PEG, etc.)
    income_growth = Column(JSON)                          # Compte de Résultat & Croissance (CA, EBITDA...)
    balance_cash = Column(JSON)                           # Bilan & Liquidité (Trésorerie, Cash flow...)
    risk_market = Column(JSON)                            # Risque & Marché (Beta, Volatilité, Short...)

# --- TABLE DES PRIX HISTORIQUES ---
class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("companies.ticker"), index=True)
    date = Column(DateTime, index=True)       # <-- MODIFIÉ : DateTime pour conserver les heures
    interval = Column(String, index=True)     # <-- NOUVEAU : '1h', '1D', '1W'
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)