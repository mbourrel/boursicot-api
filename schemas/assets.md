# schemas/assets.py

## Rôle
Définit le modèle Pydantic de réponse pour l'endpoint `/api/assets`, représentant un actif du catalogue avec ses métadonnées de base.

## Dépendances
- **Internes** : aucune
- **Externes** : `pydantic`, `typing`

## Fonctionnement
Un seul modèle `AssetOut` avec quatre champs :
- `ticker : str` — symbole yfinance (ex. `AAPL`, `AI.PA`, `^GSPC`).
- `name : str` — nom lisible (ex. `"Apple"`, `"Air Liquide"`).
- `country : Optional[str]` — pays de cotation, `None` pour les actifs non seedés en fondamentaux (indices, crypto).
- `sector : Optional[str]` — secteur GICS, `None` pour les mêmes cas.

## Utilisé par
- `routers/assets.py` : `response_model=list[AssetOut]` sur `GET /api/assets`.

## Points d'attention
- `name` est non-nullable dans le modèle (pas d'`Optional`) — mais il provient de `ASSET_DICTIONARY` où toutes les valeurs sont définies, donc pas de risque en pratique.
- `country` et `sector` sont `Optional` car les actifs non-actions (indices, crypto, commodities) ne sont généralement pas en table `companies` — le frontend doit traiter `None` comme "non disponible".
- Modèle minimal intentionnellement : pour des informations détaillées, le frontend appelle `/api/fundamentals/{ticker}`.
