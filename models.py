from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    sector = Column(String)
    description = Column(String)

    market_analysis   = Column(JSON)
    financial_health  = Column(JSON)
    advanced_valuation = Column(JSON)
    income_growth     = Column(JSON)
    balance_cash      = Column(JSON)
    risk_market       = Column(JSON)

class Price(Base):
    __tablename__ = "prices"

    id       = Column(Integer,  primary_key=True, index=True)
    ticker   = Column(String,   index=True, nullable=False)
    date     = Column(DateTime, index=True, nullable=False)
    interval = Column(String,   index=True, nullable=False)

    open_price  = Column(Float)
    high_price  = Column(Float)
    low_price   = Column(Float)
    close_price = Column(Float)
    volume      = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("ticker", "date", "interval", name="uix_ticker_date_interval"),
    )

class MacroCache(Base):
    """Cache PostgreSQL pour les endpoints /macro/* - TTL configurable (defaut 24h)."""
    __tablename__ = "macro_cache"

    id         = Column(Integer,     primary_key=True, index=True)
    cache_key  = Column(String(255), unique=True, nullable=False, index=True)
    data_json  = Column(String,      nullable=False)
    updated_at = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
