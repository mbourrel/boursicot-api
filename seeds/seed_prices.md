# seeds/seed_prices.py

## Rôle
Rafraîchit les bougies OHLCV récentes pour tous les tickers (ou une sélection) en utilisant de courtes fenêtres temporelles. Conçu pour les crons GitHub Actions 3x/jour.

## Dépendances
- **Internes** : `database.SessionLocal`, `database.engine`, `models.Base`, `models.Price`, `seed_utils.TICKERS`, `seed_utils.clean_dataframe`
- **Externes** : `yfinance`, `pandas`, `sqlalchemy.dialects.postgresql.insert`, `time`, `sys`, `os`

## Fonctionnement

### Fenêtres de fetch (PERIODS)
```
1W  → 1mo   (~4 bougies hebdo)
1D  → 5d    (~5 bougies journalières)
1h  → 7d    (~56 bougies horaires)
15m → 2d    (~52 bougies 15 min)
```
Ces fenêtres couvrent largement l'intervalle entre deux runs (max 8h en pratique).

### `insert_recent(db, records)`
Upsert PostgreSQL via `ON CONFLICT DO UPDATE` sur la contrainte `uix_ticker_date_interval`. Met à jour OHLCV si la bougie existe déjà (correction des bougies en cours de formation).

### `seed_prices(tickers)`
Pour chaque ticker :
1. Fetch les 4 intervalles en parallèle via yfinance.
2. Nettoie et concatène les DataFrames via `clean_dataframe()`.
3. Déduplique par `(ticker, date, interval)` (set `seen`).
4. Appelle `insert_recent()`.
5. Ouvre/ferme une session DB par ticker pour libérer les connexions.
6. Pause 0.5s entre tickers.

### Invocation
- Sans arguments : tous les tickers de `TICKERS`.
- Avec arguments : `python seeds/seed_prices.py AAPL MSFT` (sélection).

## Utilisé par
- GitHub Actions : cron 3x/jour (ex. 8h, 13h, 18h heure Paris).
- `seed_prices_init.py` (le script initial utilise une logique similaire mais des fenêtres historiques).

## Points d'attention
- Ce script ne touche **pas** aux fondamentaux ni aux prix live — il n'écrit que dans la table `prices`.
- L'intervalle yfinance `1wk` correspond à `1W` en interne : la conversion est faite inline avec `.lower().replace('1w', '1wk')`.
- yfinance limite les intervalles court-terme : 15m disponible sur 60j max, 1h sur ~730j. Au-delà, utiliser `seed_prices_init.py`.
- La déduplication en mémoire (`seen`) évite les doublons dans un même batch mais ne protège pas contre des runs concurrents — la contrainte DB est le filet final.
- `db.rollback()` en cas d'exception et `db.close()` dans `finally` — la session est proprement gérée même en cas d'erreur réseau.
