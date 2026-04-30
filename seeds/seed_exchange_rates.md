# seeds/seed_exchange_rates.py

## Rôle
Charge les taux de change forex (EURUSD, GBPUSD, JPYUSD, CHFUSD) dans la table `exchange_rates` depuis frankfurter.app.

## Dépendances
- `requests` — HTTP GET vers frankfurter.app
- `database.py` — SessionLocal
- `models.py` — ExchangeRate

## Fonctionnement
Un seul appel GET vers `https://api.frankfurter.app/latest?from=EUR&to=USD,GBP,JPY,CHF`.

La réponse donne les taux en base EUR. Les paires USD sont dérivées :
- `EURUSD` = `rates['USD']` directement
- `GBPUSD` = `EURUSD / rates['GBP']` (1 GBP = EURUSD/GBPEUR)
- `JPYUSD` = `EURUSD / rates['JPY']`
- `CHFUSD` = `EURUSD / rates['CHF']`

Pour chaque paire : upsert (update si existe, insert si nouveau). Commit unique en fin de script.

## Utilisé par
- `.github/workflows/refresh_exchange_rates.yml` — cron lun–ven 7h UTC
- Résultat consommé par `routers/exchange_rates.py` → `GET /api/exchange-rates`

## Points d'attention
- frankfurter.app retourne les taux BCE à J-1 (fin de journée précédente) — pas de taux en temps réel
- Si `EURUSD` est absent de la réponse, le script s'arrête avec `sys.exit(1)` — log visible dans GitHub Actions
- Remplace FMP pour le forex : FMP free plan ne supporte pas `/stable/quotes/EURUSD` (404) ni `/api/v3/fx` (403)
- 0 impact sur le budget FMP (250 calls/jour)
