# routers/assets.py

## Rôle
Router FastAPI exposant le catalogue complet des actifs suivis (ticker → nom + pays + secteur), en fusionnant `assets_config.ASSET_DICTIONARY` avec les métadonnées DB.

## Dépendances
- **Internes** : `assets_config.ASSET_DICTIONARY`, `schemas.assets.AssetOut`, `database.get_db`, `models.Company`
- **Externes** : `fastapi`, `sqlalchemy`

## Fonctionnement

### `GET /api/assets`
1. Interroge la table `companies` pour récupérer uniquement les colonnes `ticker`, `country`, `sector` (requête légère).
2. Construit un `company_map {ticker: row}` pour lookup O(1).
3. Itère sur `ASSET_DICTIONARY` dans l'ordre de déclaration et construit la liste de réponse en enrichissant chaque entrée avec `country` et `sector` depuis la DB (ou `None` si le ticker n'est pas encore seedé en fondamentaux).

Retourne une `list[AssetOut]` validée par Pydantic.

## Utilisé par
- Frontend Boursicot : fetch au démarrage pour construire la liste de navigation des actifs, les filtres par pays/secteur, et la barre de recherche.

## Points d'attention
- Les actifs présents dans `ASSET_DICTIONARY` mais absents de `companies` (ex. indices, crypto non seedés) auront `country=None` et `sector=None` — le frontend doit gérer ces cas.
- L'ordre de la réponse reflète l'ordre de `ASSET_DICTIONARY` (CAC 40 → M7 → indices → crypto → commodities) — modifier `assets_config.py` change l'ordre affiché.
- Pas de pagination — le catalogue entier est retourné d'un coup (~64 entrées, acceptable).
- `AssetOut` ne valide que 4 champs : si on ajoute des champs à la réponse, mettre à jour le schéma.
