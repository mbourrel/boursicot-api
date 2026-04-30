# seeds/seed_prices_init.py

## Rôle
Chargement initial complet de l'historique des prix depuis 1998 pour tous les tickers. À lancer une seule fois lors de la mise en production ou après une remise à zéro de la table `prices`.

## Dépendances
- **Internes** : `database.SessionLocal`, `database.engine`, `models.Base`, `models.Price`, `seed_utils.TICKERS`, `seed_utils.clean_dataframe`
- **Externes** : `yfinance`, `pandas`, `sqlalchemy.dialects.postgresql.insert`, `time`, `sys`, `os`

## Fonctionnement

### Constantes
- `CHUNK_SIZE = 200` : taille des lots d'insertion pour éviter les timeouts PostgreSQL/Neon.
- `CHUNK_SLEEP = 0.3` : pause entre chunks (ms).
- `RETRY_DELAYS = [5, 15, 30]` : délais de retry en secondes.

### Fenêtres de fetch historiques
```
1W  → depuis 1998-01-01 (toute l'histoire disponible)
1D  → depuis 1998-01-01 (toute l'histoire disponible)
1h  → 730 jours (limite yfinance)
15m → 60 jours (limite yfinance)
```

### `insert_in_chunks(db, records)`
Découpe la liste de records en lots de `CHUNK_SIZE` et fait un upsert PostgreSQL par lot, avec pause entre chunks. Même logique `ON CONFLICT DO UPDATE` que `seed_prices.py`.

### `insert_with_retry(records, ticker)`
Tente l'insertion avec jusqu'à 3 retries (délais 5s, 15s, 30s). Ouvre une nouvelle session DB à chaque tentative. Retourne `True` si succès, `False` après épuisement des retries.

### `seed_prices_init(tickers)`
Pour chaque ticker :
1. Fetch les 4 intervalles sur les fenêtres maximales.
2. Nettoyage, déduplication, construction des records.
3. Insertion chunked avec retry.
4. Pause 0.5s entre tickers.

## Utilisé par
- Administrateur/déploiement : invocation manuelle unique.
- En cas de reset complet de la table `prices`.

## Points d'attention
- **Ne pas relancer sur une table non-vide** sans intention délibérée — les upserts mettront à jour toutes les bougies existantes (coûteux en temps et en I/O DB).
- Durée estimée : 30-60 minutes pour 63 tickers avec une connexion Neon standard.
- yfinance peut rate-limiter sur de nombreux appels rapides — la pause 0.5s est le minimum; augmenter si des erreurs 429 apparaissent.
- Les données horaires (1h) et 15min sont limitées par yfinance à 730j et 60j respectivement — l'historique court-terme ne remonte donc pas à 1998.
- Différence clé avec `seed_prices.py` : fenêtres longues + chunking + retry. Même format d'upsert en DB.
