# assets_config.py

## Rôle
Source unique de vérité pour le catalogue complet des actifs suivis par Boursicot : actions CAC 40, Magnificent 7, indices, crypto, métaux précieux, énergie et matières premières agricoles.

## Dépendances
- **Internes** : aucune
- **Externes** : aucune (Python pur)

## Fonctionnement
Expose deux objets :

- `ASSET_DICTIONARY : dict[str, str]` — mapping `ticker → nom lisible`. Organisé par catégorie avec des commentaires inline. Contient actuellement ~64 entrées.
- `TICKERS : list[str]` — liste dérivée de `ASSET_DICTIONARY.keys()`, dans l'ordre d'insertion du dict. Utilisée comme référence par tous les scripts de seed.

Catégories présentes :
- CAC 40 (39 actions dont 2 bonus hors-index)
- Les 7 Fantastiques / Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA)
- Indices (^FCHI, ^GSPC, ^IXIC, ^DJI, ^STOXX50E, ^N225, ^VIX)
- Crypto (BTC-USD)
- Métaux précieux (GC=F, SI=F)
- Énergie (CL=F, BZ=F, NG=F)
- Matières premières agricoles (ZC=F, ZW=F, CT=F)

## Utilisé par
- `seed_utils.py` : importe `TICKERS` et le ré-exporte pour les scripts de seed.
- `seeds/seed_fundamentals.py`, `seeds/seed_prices.py`, `seeds/seed_prices_init.py`, `seeds/seed_live_prices.py` : itèrent sur `TICKERS`.
- `routers/assets.py` : importe `ASSET_DICTIONARY` pour construire la réponse `/api/assets`.

## Points d'attention
- Toute modification du catalogue (ajout/suppression de ticker) doit être faite **ici uniquement** — les scripts de seed et l'endpoint `/api/assets` s'adaptent automatiquement.
- Les symboles yfinance et FMP ne sont pas toujours identiques (ex. : `BTC-USD` yfinance → `BTCUSD` FMP, `GC=F` → `GCUSD`). Le mapping de conversion est dans `seeds/seed_live_prices.py` (`FMP_TICKER_MAP`).
- Les indices (^FCHI, etc.) ne sont **pas** seedés en fondamentaux (yfinance renvoie des données incomplètes pour eux) — ils apparaissent dans le catalogue mais pas dans la table `companies`.
- L'ordre du dict détermine l'ordre affiché dans le frontend via `/api/assets`.
