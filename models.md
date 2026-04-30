# models.py

## Rôle
Définit les quatre modèles SQLAlchemy qui constituent le schéma PostgreSQL de Boursicot : `Company`, `Price`, `MacroCache`, et `ExchangeRate`.

## Dépendances
- **Internes** : aucune
- **Externes** : `sqlalchemy` (Column, types, UniqueConstraint, declarative_base), `datetime`

## Fonctionnement

### `Company`
Table `companies` — une ligne par ticker d'action/ETF.
- **Champs scalaires** : ticker (PK métier unique), name, sector, industry, description, country, city, website, employees, exchange, currency, ipo_date.
- **Champs JSON de métriques** (6 catégories) : `market_analysis`, `financial_health`, `advanced_valuation`, `income_growth`, `balance_cash`, `risk_market`. Format : liste de `{"name": str, "val": float, "unit": str}`.
- **Champs JSON d'états financiers** (3) : `balance_sheet_data`, `income_stmt_data`, `cashflow_data`. Format : `{"years": [...], "items": [{"name": str, "vals": [...], "unit": str}]}`.
- **Prix live** : `live_price`, `live_change_pct`, `live_price_at` — alimentés par le cron `seed_live_prices` 2x/jour via FMP.
- **Dividendes** : `dividends_data` (JSON) — contient yield, rate, payout_ratio, historique annuel.
- **Scores pré-calculés** : `scores_json` (JSON nullable) — stocke le résultat de `compute_scores()` pour éviter le recalcul à chaque requête.

### `Price`
Table `prices` — historique OHLCV multi-intervalles.
- Colonnes : ticker, date (DateTime), interval (str : `1D`, `1W`, `1h`, `15m`), open/high/low/close/volume.
- Contrainte unique `uix_ticker_date_interval` sur (ticker, date, interval) — permet l'upsert PostgreSQL.

### `MacroCache`
Table `macro_cache` — cache PostgreSQL pour les endpoints `/macro/*`.
- Colonnes : cache_key (unique), data_json (texte sérialisé), updated_at.
- Le TTL est géré par le service (`cache_service.py`), pas par la table elle-même.

### `ExchangeRate`
Table `exchange_rates` — taux de change courants (EURUSD, GBPUSD, JPYUSD, CHFUSD).
- Une ligne par paire de devises, mise à jour 1x/jour par `seed_exchange_rates`.

## Utilisé par
- `database.py` (import de `Base` — doublon historique, non utilisé en pratique)
- `api.py` (`Base.metadata.create_all`)
- Tous les routers et scripts de seed (import direct des classes)
- `scoring_logic.py` (accès aux attributs de `Company`)

## Points d'attention
- Les colonnes JSON (`market_analysis`, etc.) ne sont pas typées côté Python : une donnée malformée passera l'insert mais cassera le scoring silencieusement.
- `live_price_at` est stocké en UTC sans timezone (naïf) — cohérent avec `datetime.utcnow()` utilisé partout.
- `scores_json` peut être `None` pour les tickers seedés avant l'introduction du scoring — le router `fundamentals` gère ce cas avec un fallback compute à la volée.
- `Volume` est `BigInteger` : ne pas le mapper vers `int` Python sur 32 bits pour les tickers à fort volume.
