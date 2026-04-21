from typing import Literal
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
