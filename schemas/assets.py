from pydantic import BaseModel
from typing import Optional


class AssetOut(BaseModel):
    ticker: str
    name: str
    country: Optional[str] = None
    sector: Optional[str] = None
    asset_class: Optional[str] = None
