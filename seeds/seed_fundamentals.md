# seeds/seed_fundamentals.py

## Rôle
Script de seeding hebdomadaire qui recharge les données fondamentales (ratios, bilans, dividendes) pour tous les tickers via yfinance, puis pré-calcule et stocke les scores d'investissement en base.

## Dépendances
- **Internes** : `database.SessionLocal`, `database.engine`, `models.Base`, `models.Company`, `seed_utils.TICKERS`, `seed_utils.BALANCE_SHEET_MAP`, `seed_utils.INCOME_STMT_MAP`, `seed_utils.CASHFLOW_MAP`, `seed_utils.parse_financial_df`, `scoring_logic.compute_scores`
- **Externes** : `yfinance`, `time`, `collections.defaultdict`, `sys`, `os`

## Fonctionnement

### `_fetch_info(ticker, max_retries=3)`
Appelle `yf.Ticker(ticker).info` avec backoff exponentiel (2s, 4s, 8s) en cas d'échec réseau. Lève l'exception après 3 tentatives.

### `seed_fundamentals()`
**Phase 1 — Fetch et upsert fondamentaux** (un ticker à la fois, pause 0.5s) :
1. Pour chaque ticker de `TICKERS`, appelle yfinance `.info` + `.balance_sheet` + `.income_stmt` + `.cashflow`.
2. Construit les 6 listes de métriques JSON (`market_analysis`, `financial_health`, etc.) à partir des champs `.info`.
3. Transforme les DataFrames yfinance en JSON structuré via `parse_financial_df()`.
4. Upsert dans `companies` : update si le ticker existe déjà, insert sinon.
5. Commit après chaque ticker — un echec n'annule pas les tickers précédents.

**Phase 2 — Pré-calcul des scores** :
1. Charge toutes les `Company` en une seule requête.
2. Groupe par secteur (`sector_map`).
3. Pour chaque company, appelle `compute_scores(company, sector_companies)` et stocke le résultat dans `company.scores_json`.
4. Un seul `db.commit()` global pour tous les scores.

## Utilisé par
- GitHub Actions : cron hebdomadaire (ex. dimanche nuit).
- En manuel : `python seeds/seed_fundamentals.py`.

## Points d'attention
- Le script modifie les **fondamentaux uniquement**, pas `live_price`/`live_change_pct` (gérés par `seed_live_prices`).
- Les tickers d'indices (^FCHI, etc.) et de commodities ne retournent pas de données fondamentales via yfinance `.info` — ils sont ignorés silencieusement par le bloc `except` mais comptent dans `TICKERS`.
- Le backoff 2/4/8s est par ticker, pas global — un timeout massif peut faire durer le script 30+ minutes sur 63 tickers.
- La passe de scoring en phase 2 est groupée par secteur : les tickers sans secteur (`None`) sont regroupés sous `"Inconnu"` et se comparent entre eux (biais possible).
- Ne pas lancer en parallèle avec `seed_prices` sur la même DB — les deux font des commits et peuvent interférer sur la table `companies`.
