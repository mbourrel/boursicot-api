from pydantic import BaseModel


class AssetOut(BaseModel):
    ticker: str
    name: str
