from typing import Literal, Optional
from pydantic import BaseModel


class MacroCycleOut(BaseModel):
    phase: Literal["Expansion", "Surchauffe", "Contraction", "Recession", "Récession"]
    growth_yoy: float
    inflation_yoy: float
    growth_trend: Literal["up", "down"]
    inflation_trend: Literal["up", "down"]


class CycleHistoryPoint(BaseModel):
    date: str
    growth_yoy: float
    inflation_yoy: float
    phase: str


class MacroCycleHistoryOut(BaseModel):
    history: list[CycleHistoryPoint]


class MacroLiquidityOut(BaseModel):
    dates: list[str]
    m2_normalized: list[float]
    btc_normalized: list[float]


class RatePoint(BaseModel):
    name: str
    rate: Optional[float] = None
    last_update: Optional[str] = None


class HistorySeries(BaseModel):
    dates: list[str]
    values: list[float]


class MacroRatesOut(BaseModel):
    central_banks: list[RatePoint]
    bond_yields: list[RatePoint]
    history: dict[str, HistorySeries]
    yield_curve: HistorySeries
