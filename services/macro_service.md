# services/macro_service.py

## Rôle
Logique métier des indicateurs macroéconomiques : fetch depuis FRED et yfinance, calcul du cycle économique, normalisation de la liquidité M2/BTC, récupération des taux et rendements obligataires, avec mise en cache PostgreSQL.

## Dépendances
- **Internes** : `services.cache_service` (get_cached, get_stale, set_cached)
- **Externes** : `os`, `datetime`, `pandas`, `yfinance`, `fredapi.Fred`, `fastapi.HTTPException`, `sqlalchemy`

## Fonctionnement

### `_get_fred()`
Instancie `fredapi.Fred` avec `FRED_API_KEY` depuis l'environnement. Lève HTTP 500 si la clé est absente.

### `_yoy_and_trend(series)`
Calcule la variation annuelle glissante (YoY) et sa tendance (up/down) sur une série Pandas. Requiert au minimum 14 points mensuels.

### `get_cycle_data(db)` — cache `macro_cycle`, TTL 24h
Récupère INDPRO (production industrielle) et CPIAUCSL (inflation) sur 15 mois depuis FRED. Calcule les YoY et détermine la phase du cycle :
- Expansion : croissance↑, inflation↓
- Surchauffe : croissance↑, inflation↑
- Contraction : croissance↓, inflation↑
- Recession : croissance↓, inflation↓

### `get_liquidity_data(db)` — cache `macro_liquidity`, TTL 24h
Récupère M2SL (FRED) et BTC-USD (yfinance) depuis jan 2020, rééchantillonne en mensuel, aligne les deux séries, et normalise en base 100 (jan 2020 = 100).

### `get_cycle_history(db)` — cache `macro_cycle_history`, TTL 24h
Rejoue le calcul du cycle mois par mois depuis 1946 (~920 points) pour produire un historique complet. Résultat : liste de `{date, growth_yoy, inflation_yoy, phase}`.

### `get_rates_data(db)` — cache `macro_rates_v6`, TTL 6h
Récupère via FRED :
- Taux directeurs : Fed (DFF), BCE (ECBDFR), BoE (IUDSOIA/SONIA). BoJ hardcodé à 0.5 % (jan 2025).
- Rendements obligataires courants : US 2Y/10Y/30Y/3M, Bund 10Y/3M, OAT 10Y/3M, Gilt 10Y/3M.
- Historiques complets depuis 1960 pour graphiques.
- Courbe des taux (spread T10Y2Y).

Les fonctions internes `_latest()` et `_history()` absorbent silencieusement les erreurs FRED (retour None/listes vides).

## Utilisé par
- `routers/macro.py` : importe les 4 fonctions publiques.

## Points d'attention
- `get_rates_data` fait environ 15 appels FRED séquentiels lors d'un cache miss — latence possible de 5-15 s. La mise en cache à 6h est critique.
- `get_stale(db, key)` est le filet de sécurité : si FRED est indisponible, on retourne le cache périmé plutôt que de planter. Pas disponible pour `get_rates_data` (try/except silencieux au moment de `set_cached`).
- yfinance est utilisé uniquement pour BTC-USD dans `get_liquidity_data` — les MultiIndex de colonnes yfinance sont gérés explicitement.
- Le BoJ est hardcodé : à mettre à jour manuellement après chaque décision de la Banque du Japon.
- Les séries FRED ont des délais de publication (INDPRO ~1 mois de lag, CPIAUCSL ~3 semaines) — la phase courante reflète toujours la situation du mois précédent.
