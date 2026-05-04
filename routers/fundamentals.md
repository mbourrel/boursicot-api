# routers/fundamentals.py

## Rôle
Router FastAPI exposant les données fondamentales des entreprises et le screener pédagogique : liste complète, moyennes sectorielles (snapshot et historique), fiche individuelle avec scores, screener léger, et proxy de test vers FMP.

## Dépendances
- **Internes** : `database.get_db`, `models`, `scoring_logic.compute_scores`, `scoring_logic.is_scorable`, `config.FMP_API_KEY`, `config.FMP_V3`, `config.EQUITY_RISK_PREMIUM`
- **Externes** : `fastapi`, `sqlalchemy`, `httpx`, `collections.defaultdict`

## Fonctionnement

### `GET /api/fundamentals`
Retourne toutes les entrées de la table `companies` sans transformation.

### `GET /api/fundamentals/sector-averages/{sector}`
Calcule à la volée les moyennes sectorielles pour les 6 catégories de métriques, les 3 états financiers (valeur la plus récente, `vals[0]`), et les 4 champs scalaires de dividendes. Retourne un dict plat `{metric_name: moyenne}` par catégorie.

### `GET /api/fundamentals/sector-averages/{sector}/history`
Calcule les moyennes sectorielles **par année** pour les états financiers et les dividendes annuels. Retourne un dict `{metric_name: {année: moyenne}}` — utilisé par les graphiques historiques sectoriels.

### `GET /api/screener`
Endpoint léger pour le Screener Pédagogique. Retourne uniquement `{ticker, name, sector, country, asset_class, is_scorable, scores, live_price, live_change_pct}`. N'expose aucun blob JSON lourd (états financiers, métriques détaillées). Les scores sont `null` pour les actifs non-scorables (indices, crypto, commodities). Le filtrage géographique, sectoriel et par score est effectué côté client dans `useScreener.js`.

### `GET /api/fundamentals/{ticker}`
Fiche complète d'une entreprise :
1. Sérialise la ligne `Company` en dict (hors `scores_json`).
2. Injecte `scores` : lecture du cache `scores_json` si présent, sinon compute à la volée avec `compute_scores()`.
3. Résout le prix actuel : priorité `live_price` (DB, cron FMP), fallback `Prix Actuel` dans `risk_market`.
4. Retourne les champs `close_price` et `daily_change_pct`.
5. Injecte `valuation_defaults` via `_compute_valuation_defaults(company, db)` (voir ci-dessous).

#### Champ `valuation_defaults` (ajout 2026-05-04)
```json
{
  "default_wacc":       0.085,   // CAPM : rf + β × 5.5%, fallback 0.08
  "default_growth":     0.07,    // TCAC FCF sur 5 ans, borné [0 %, 15 %]
  "default_pe":         18.4,    // P/E moyen sectoriel, borné [5, 50]
  "sector_ev_ebitda":   11.2     // EV/EBITDA moyen sectoriel, borné [3, 30]
}
```

### `_compute_valuation_defaults(company, db)` — helper interne
Calcule les valeurs par défaut pour le Laboratoire d'Évaluation Théorique (ValuationLab) :

1. **Taux sans risque** : lu depuis `macro_cache["macro_rates_v6"].bond_yields` selon la devise (`US 10Y`, `Bund 10Y`, `Gilt 10Y`). Fallbacks codés : `USD 4.5 %`, `EUR 3 %`, `GBP 4 %`, `CAD 3.5 %`, `JPY 1 %`.
2. **WACC** : `rf + beta × EQUITY_RISK_PREMIUM` (5,5 %). Fallback `0.08` si `beta` absent. Borné `[0.04, 0.20]`.
3. **Croissance FCF** : TCAC sur les 5 derniers exercices de `Free Cash Flow` dans `cashflow_data`. Borné `[0, 0.15]`. Fallback `0.05`.
4. **P/E sectoriel** : moyenne des `per` des entreprises du même secteur (table `companies`). Requête unique réutilisée pour EV/EBITDA. Borné `[5, 50]`. Fallback `15`.
5. **EV/EBITDA sectoriel** : moyenne des `ev_ebitda` du même secteur, issu de la même requête. Borné `[3, 30]`. Fallback `10`.

### `GET /api/fundamentals/fmp-proxy/{ticker}`
Endpoint de test/debug uniquement. Interroge FMP en temps réel et retourne les données dans le même format que la fiche individuelle. Ne touche pas à la DB. `scores` est toujours `null`.

## Utilisé par
- Frontend Boursicot : liste des actions, fiche détaillée, graphiques sectoriels, Screener Pédagogique.

## Points d'attention
- L'ordre des routes est important : `/sector-averages/{sector}` et `/sector-averages/{sector}/history` doivent être déclarés **avant** `/{ticker}` pour ne pas être capturés comme paramètre `ticker`. `/screener` doit aussi être déclaré avant `/{ticker}`.
- `scores_json` est exclu de la réponse individuelle (`result.pop("scores_json", None)`) — seul `scores` (calculé ou caché) est exposé.
- Le fallback compute-à-la-volée charge tous les `Company` du même secteur — acceptable car `scores_json` devrait être peuplé par le seed hebdomadaire.
- Le proxy FMP est un endpoint ouvert — ne pas le laisser en production sans restriction supplémentaire si la clé FMP est budgétée.
