# routers/fundamentals.py

## Rôle
Router FastAPI exposant les données fondamentales des entreprises : liste complète, moyennes sectorielles (snapshot et historique), fiche individuelle avec scores, et proxy de test vers FMP.

## Dépendances
- **Internes** : `database.get_db`, `models`, `scoring_logic.compute_scores`, `config.FMP_API_KEY`, `config.FMP_V3`
- **Externes** : `fastapi`, `sqlalchemy`, `httpx`, `collections.defaultdict`

## Fonctionnement

### `GET /api/fundamentals`
Retourne toutes les entrées de la table `companies` sans transformation. Utilisé par le frontend pour la liste des actions.

### `GET /api/fundamentals/sector-averages/{sector}`
Calcule à la volée les moyennes sectorielles pour les 6 catégories de métriques, les 3 états financiers (valeur la plus récente, `vals[0]`), et les 4 champs scalaires de dividendes. Retourne un dict plat `{metric_name: moyenne}` par catégorie.

### `GET /api/fundamentals/sector-averages/{sector}/history`
Calcule les moyennes sectorielles **par année** pour les états financiers et les dividendes annuels. Retourne un dict `{metric_name: {année: moyenne}}` — utilisé par les graphiques historiques sectoriels.

### `GET /api/fundamentals/{ticker}`
Fiche complète d'une entreprise :
1. Sérialise la ligne `Company` en dict (hors `scores_json`).
2. Injecte `scores` : lecture du cache `scores_json` si présent, sinon compute à la volée avec `compute_scores()`.
3. Résout le prix actuel : priorité `live_price` (DB, cron FMP), fallback `Prix Actuel` dans `risk_market` (seed fondamentaux).
4. Retourne les champs `close_price` et `daily_change_pct`.

### `GET /api/fundamentals/fmp-proxy/{ticker}`
Endpoint de test/debug uniquement. Interroge FMP en temps réel (profile + ratios TTM + financial-growth + quote) et retourne les données dans le même format que la fiche individuelle. Ne touche pas à la DB. `scores` est toujours `null` (pas de données sectorielles disponibles ici).

## Utilisé par
- Frontend Boursicot : liste des actions, fiche détaillée, graphiques sectoriels.

## Points d'attention
- L'ordre des routes est important : `/sector-averages/{sector}` et `/sector-averages/{sector}/history` doivent être déclarés **avant** `/{ticker}` pour ne pas être capturés comme paramètre `ticker`.
- `scores_json` est exclu de la réponse individuelle (`result.pop("scores_json", None)`) — seul `scores` (calculé ou caché) est exposé.
- Le fallback compute-à-la-volée charge tous les `Company` du même secteur en une requête N+1 — acceptable car `scores_json` devrait être peuplé par le seed hebdomadaire.
- Le proxy FMP est un endpoint ouvert (pas de guard supplémentaire) — ne le laisser en production que si la clé FMP est budgétée.
- `httpx.Client` est synchrone avec timeout 10s — une latence FMP peut bloquer un worker.
