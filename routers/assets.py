from fastapi import APIRouter
from assets_config import ASSET_DICTIONARY
from schemas.assets import AssetOut

router = APIRouter(prefix="/api", tags=["assets"])


@router.get("/assets", response_model=list[AssetOut])
def get_assets():
    """
    Retourne le catalogue complet des actifs (ticker → nom).
    Source unique de vérité partagée avec les scripts de seeding.
    """
    return [
        {"ticker": ticker, "name": name}
        for ticker, name in ASSET_DICTIONARY.items()
    ]
