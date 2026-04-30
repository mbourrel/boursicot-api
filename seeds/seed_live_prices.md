# seeds/seed_live_prices.py

## Rôle
Rafraîchit les prix live (close_price + variation journalière en %) pour tous les tickers via FMP, en mettant à jour les champs `live_price`, `live_change_pct`, `live_price_at` de la table `companies`. Conçu pour un cron 2x/jour.

## Dépendances
- **Internes** : `database.SessionLocal`, `models.Company`, `seed_utils.TICKERS`, `config.FMP_API_KEY`, `config.FMP_STABLE`
- **Externes** : `httpx`, `python-dotenv`, `time`, `datetime`, `sys`, `os`

## Fonctionnement

### Mapping FMP (`FMP_TICKER_MAP`)
Convertit les symboles yfinance vers les symboles FMP pour les actifs non-actions :
- `BTC-USD` → `BTCUSD`
- `GC=F` → `GCUSD` (Or)
- `SI=F` → `SIUSD` (Argent)
- `CL=F` → `USOIL` (Pétrole WTI)
- `BZ=F` → `BZUSD` (Brent)
- `NG=F` → `NATGAS`
- `ZC=F` → `ZCUSD`, `ZW=F` → `ZWUSD`, `CT=F` → `CTUSD`

### Routing des endpoints FMP
- **`QUOTE_TICKERS`** (indices + crypto + commodities) → `FMP_STABLE/quote` — supporte les symboles non-actions.
- **Actions** (tout le reste) → `FMP_STABLE/profile` — retourne price + changePercentage.

### `fetch_price(client, ticker)`
Fait un GET FMP avec timeout 8s. Retourne `(price, change_pct)` ou `(None, None)` en cas d'erreur. La clé de variation est `changePercentage` pour les deux endpoints.

### `seed_live_prices(tickers)`
Itère sur les tickers avec un `httpx.Client` partagé (keep-alive). Pour chaque ticker avec un prix valide, met à jour la Company correspondante en DB. Pause 0.1s entre tickers. Affiche un résumé OK/KO.

En fin de run, affiche un **log de budget FMP estimé** :
```
Termine : 64 OK / 0 echecs — 64 calls FMP utilises ce run
Budget journalier estimé (2 runs) : 128/250 calls (51%) → 122 restants
```
Budget FMP : 1 call par ticker → ~64 calls/run → ~128 calls/jour sur 250 autorisés (plan gratuit).

## Utilisé par
- GitHub Actions : cron 2x/jour (9h et 17h30 heure Paris, avec décalage été/hiver).

## Points d'attention
- Ce script n'écrit que dans la table `companies` (champs live_*) — pas dans la table `prices`.
- Les tickers absents de `companies` (actifs dans le catalogue mais non seedés en fondamentaux) sont loggués `SKIP` sans erreur.
- FMP plan gratuit : certains symboles de commodities (ZC=F, ZW=F, CT=F) peuvent retourner des données vides ou incorrectes — vérifier périodiquement.
- `live_price_at` est stocké en UTC naïf (`datetime.now(timezone.utc).replace(tzinfo=None)`) — cohérent avec le reste de l'application.
- Si `FMP_API_KEY` est vide, le script sort immédiatement avec `sys.exit(1)` (fail-fast, contrairement à `config.py` qui ne lève pas d'erreur).
- Le script charge `.env` depuis `../` (relatif au fichier) — s'assurer que le `.env` est bien à la racine du projet en production (GitHub Actions).
