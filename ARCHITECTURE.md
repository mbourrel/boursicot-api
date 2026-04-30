# ARCHITECTURE.md — Boursicot Pro

**Dernière mise à jour :** 2026-04-30
**Auditeur :** Claude Code (Sonnet 4.6)

---

## 1. Stack technique

### Backend
- **Framework :** FastAPI 0.135.3
- **Base de données :** PostgreSQL — Neon (EU Frankfurt, serverless, remplace Render Free)
- **Python :** 3.11
- **Sources de données :**
  - yfinance 1.2.0 — fondamentaux + OHLCV historiques
  - Financial Modeling Prep (FMP) `/stable/` — prix live 2×/jour (250 calls/j gratuit)
  - FRED (Federal Reserve Economic Data) via fredapi 0.5.1 — indicateurs macroéconomiques
  - frankfurter.app (BCE) — taux de change EUR/USD/GBP/JPY/CHF, gratuit, sans clé
- **Auth :** Clerk (JWT RS256 validation, guest fallback)
- **Orchestration :** GitHub Actions (6 workflows cron)

### Frontend
- **Framework :** React 19.2.4
- **Build/Dev :** Vite 8.0.8
- **Charting :** Lightweight-charts 5.1.0 (OHLCV + indicateurs techniques)
- **UI :** Lucide-react 1.7.0 (icônes)
- **Auth :** Clerk React 5.61.5
- **Analytics :** PostHog 1.372.1 (event tracking)
- **Routing :** React Router DOM 7.14.1

### Déploiement
- Backend : Render.com (Python app)
- Frontend : Render.com / Vercel (static site)
- Base de données : Neon (serverless PostgreSQL, EU Frankfurt)

---

## 2. Architecture générale

### Flux de données de bout en bout

```
┌──────────────────────────────────────────────────────────────────────┐
│                   ACQUISITION (GitHub Actions Crons)                 │
│                                                                       │
│  yfinance             FMP /stable/        FRED/fredapi               │
│  ├─ seed_fundamentals (1×/sem lundi 7h)                              │
│  │  → Bilans, ratios, 4 ans historiques, dividendes                  │
│  │  → Passe de scoring post-seed → scores_json en DB                 │
│  │                                                                   │
│  ├─ seed_prices (8×/jour, 2h écart)                                  │
│  │  → OHLCV 15m/1h/1D/1W — 5 jours glissants                        │
│  │                                                                   │
│  ├─ seed_live_prices (2×/jour: 09h, 17h30 Paris)  → 64 tickers      │
│  │  → close_price + daily_change_pct → stocké en DB                  │
│  │                                                                   │
│  ├─ seed_exchange_rates (lun–ven 8h)    frankfurter.app              │
│  │  → EURUSD, GBPUSD, JPYUSD, CHFUSD → exchange_rates table         │
│  │                                                                   │
│  └─ seed_macro (1×/sem lundi 7h30)            → FRED on-demand      │
│     → Invalide macro_cache → force refetch FRED                      │
└──────────────────────────────────────────────────────────────────────┘
                                ↓
        ┌──────────────────────────────────────────┐
        │              PostgreSQL (Neon)           │
        │  • companies      (64 rows)              │
        │  • prices         (~1.1M rows)           │
        │  • macro_cache    (TTL 24h/6h)           │
        │  • exchange_rates (4 paires forex)       │
        └──────────────────────────────────────────┘
                                ↓
        ┌──────────────────────────────────────────┐
        │             FastAPI Backend              │
        │  /api/fundamentals/{ticker}              │
        │  /api/prices?ticker&interval             │
        │  /macro/{cycle,rates,liquidity}          │
        │  /api/exchange-rates                     │
        │  /api/search  /api/assets                │
        │  + scoring_logic.py (cache DB priorité) │
        └──────────────────────────────────────────┘
                                ↓
        ┌──────────────────────────────────────────┐
        │            React Frontend                │
        │  TradingChart / SimpleChart              │
        │  Fundamentals + ScoreDashboard           │
        │  MacroEnvironment                        │
        │  Comparaison multi-actifs                │
        │  Toggle devise LOCAL / EUR / USD         │
        └──────────────────────────────────────────┘
                                ↓
                        PostHog Analytics
```

### Score caching (ajout 2026-04-28)
- `companies.scores_json` — colonne JSON nullable, pré-calculée après chaque seed_fundamentals
- `GET /api/fundamentals/{ticker}` lit `scores_json` en priorité, recalcule à la volée si null
- Élimine le problème N+1 (chargement de toutes les companies du secteur à chaque requête)

### Multi-devise (ajout 2026-04-28)
- Toggle global LOCAL / EUR / USD dans le Header (visible en vue Fundamentals)
- `CurrencyContext` expose `{targetCurrency, setTargetCurrency, rates, updatedAt}`
- `formatFinancialValue(value, unit, sourceCurrency, targetCurrency, rates)` : convertit uniquement les valeurs monétaires (`unit='$'`), jamais les ratios (`%` ou `x`)
- Taux forex : frankfurter.app → `exchange_rates` table → `/api/exchange-rates` → `useExchangeRates` hook

---

## 3. Organisation du code

### 3.1 Backend (`boursicot-api/`)

| Fichier | Rôle |
|---------|------|
| `api.py` | Point d'entrée FastAPI. Setup CORS, auth globale (Clerk guest/token), include_router ×6 |
| `models.py` | 4 modèles SQLAlchemy : Company, Price, MacroCache, ExchangeRate |
| `database.py` | Connexion PostgreSQL Neon + SessionLocal + get_db |
| `config.py` | Constantes FMP centralisées : FMP_API_KEY, FMP_STABLE, FMP_V3 |
| `dependencies.py` | JWT validation Clerk — guest fallback si token absent/expiré |
| `scoring_logic.py` | 6 fonctions de score + pondération (Health/Valuation/Growth/Efficiency/Dividend/Momentum) |
| `assets_config.py` | Source unique : 64 tickers (ASSET_DICTIONARY + TICKERS list) |
| `seed_utils.py` | Parseurs yfinance (DataFrame→JSON), maps traduction EN→FR |
| `routers/fundamentals.py` | GET /api/fundamentals/* — Company + scores (cache DB → fallback compute) + sector-averages |
| `routers/prices.py` | GET /api/prices — OHLCV par ticker + intervalle |
| `routers/macro.py` | GET /macro/{cycle,rates,liquidity} — délègue à macro_service |
| `routers/assets.py` | GET /api/assets — Catalogue complet |
| `routers/search.py` | GET /api/search?q — ILIKE sur ticker/name |
| `routers/exchange_rates.py` | GET /api/exchange-rates — 4 paires forex depuis DB |
| `services/macro_service.py` | Fetch FRED/yfinance, calcul phase (4×4 Growth/Inflation), normalisation M2/BTC |
| `services/cache_service.py` | get_cached (TTL), get_stale (fallback), set_cached |
| `schemas/macro.py` | Pydantic schemas MacroCycleOut, MacroRatesOut, MacroLiquidityOut |
| `schemas/assets.py` | Pydantic schema AssetOut |
| `seeds/seed_fundamentals.py` | yfinance → companies (1×/semaine) + passe scoring → scores_json |
| `seeds/seed_prices.py` | yfinance → prices table, 5 jours glissants (8×/jour) |
| `seeds/seed_prices_init.py` | Chargement initial 10 ans — exécution manuelle unique |
| `seeds/seed_live_prices.py` | FMP → companies.live_price (2×/jour) via config.py + FMP_TICKER_MAP |
| `seeds/seed_macro.py` | Invalide macro_cache (1×/semaine) |
| `seeds/seed_exchange_rates.py` | frankfurter.app → exchange_rates table (lun–ven 8h) |

### 3.2 Frontend (`boursicot-front/src/`)

| Fichier | Rôle |
|---------|------|
| `index.jsx` | ClerkProvider + BrowserRouter + ThemeProvider + CurrencyProvider + PostHog init |
| `App.jsx` | Router racine — Dashboard protégé (chart / fundamentals / macro) |
| `components/Header.jsx` | Recherche filtrée, view toggles, toggle devise LOCAL/EUR/USD, Clerk UserButton |
| `components/TradingChart.jsx` | Lightweight-charts OHLC + MA10/100/200, BB, ATR, Volume + outils dessin |
| `components/SimpleChart.jsx` | Lightweight-charts simplifié — comparaisons multi-actifs |
| `components/Fundamentals.jsx` | Vue solo (métriques, scores, états financiers) + comparaison (tables, radar 6D) |
| `components/MacroEnvironment.jsx` | Agrège EconomicClock + CentralBanksThermometer + YieldCurve + Liquidity + AssetWindMatrix |
| `components/EconomicClock.jsx` | Jauge 4-phase + historique INDPRO/CPI (1948–2025, ~920 pts) |
| `components/AssetWindMatrix.jsx` | Matrice phase→actifs (Fidelity/Ray Dalio) avec explications dépliables |
| `components/CentralBanksThermometer.jsx` | Fed, BCE, BoE, BoJ — taux directeurs + barre visuelle |
| `components/YieldCurveChart.jsx` | Courbe des taux US + historique spread T10Y2Y |
| `components/SovereignSpreadsChart.jsx` | Spreads OAT/Bund/Gilt vs US, historique par série |
| `components/LiquidityMonitor.jsx` | M2 vs BTC normalisés (base 100, depuis jan 2020) |
| `components/CompareBar.jsx` | Barre de sélection multi-actifs, couleurs ASSET_COLORS |
| `components/SourceTag.jsx` | Label source de données — 10px, right-aligned, 65% opacity |
| `components/fundamentals/ScoreDashboard.jsx` | 6 jauges circulaires + note globale + verdict + complexité |
| `components/fundamentals/MetricCard.jsx` | 1 métrique : valeur + benchmark sectoriel + delta % |
| `components/fundamentals/MetricInfo.jsx` | Tooltip pédagogique 2 niveaux (C'est quoi / Pourquoi) |
| `components/fundamentals/FinancialStatement.jsx` | Tableau OHLCV financier avec historique annuel |
| `context/CurrencyContext.jsx` | Context global devise : targetCurrency + rates + updatedAt |
| `context/ThemeContext.jsx` | Context global thème dark/light |
| `hooks/useFundamentals.js` | Promise.all sur N symboles → {dataMap, loading, errors} |
| `hooks/usePrices.js` | GET /api/prices → rawData + calcul indicators (MA, BB, ATR) côté client |
| `hooks/useMacro.js` | useRetryFetch → {cycleData, cycleHistory, liquidityData} |
| `hooks/useRates.js` | useRetryFetch → taux directeurs + rendements obligataires |
| `hooks/useExchangeRates.js` | GET /api/exchange-rates → {rates, updatedAt}, silent fail |
| `hooks/useRetryFetch.js` | Retry exponentiel (5s base, max 4 tentatives) |
| `hooks/useAssets.js` | GET /api/assets → catalogue complet |
| `api/config.js` | API_URL + authFetch (Clerk token injecté automatiquement) |
| `api/fundamentals.js` | fetchFundamentals, fetchSectorAverages, fetchSectorHistory |
| `api/prices.js` | fetchPrices(ticker, interval) |
| `api/macro.js` | fetchMacroAll, fetchMacroRates |
| `api/exchange_rates.js` | fetchExchangeRates |
| `api/assets.js` | fetchAssets |
| `utils/formatFinancialValue.js` | Conversion devise + formatage montants. Règle : ne jamais convertir % ou x |
| `utils/analytics.js` | PostHog init + identifyUser + captureEvent |

### 3.3 GitHub Actions Workflows

| Workflow | Cron | Script | Fréquence |
|----------|------|--------|-----------|
| `refresh_fundamentals.yml` | lun 7h UTC | seed_fundamentals.py | 1×/semaine |
| `refresh_prices.yml` | lun–ven, 8×/jour | seed_prices.py | 8×/jour |
| `refresh_live_prices.yml` | lun–ven 8h + 16h30 UTC | seed_live_prices.py | 2×/jour |
| `refresh_exchange_rates.yml` | lun–ven 7h UTC | seed_exchange_rates.py | 1×/jour |
| `refresh_macro.yml` | lun 7h30 UTC | seed_macro.py | 1×/semaine |

---

## 4. Schéma de base de données

```
companies
─────────────────────────────────────────────────
ticker          VARCHAR  PK
name            VARCHAR
sector          VARCHAR
industry        VARCHAR
description     TEXT
country         VARCHAR
city            VARCHAR
website         VARCHAR
employees       INTEGER
exchange        VARCHAR
currency        VARCHAR
ipo_date        VARCHAR
market_analysis     JSON   [{name, val, unit}, ...]
financial_health    JSON
advanced_valuation  JSON
income_growth       JSON
balance_cash        JSON
risk_market         JSON
balance_sheet_data  JSON   {years, items: [{name, vals, unit}]}
income_stmt_data    JSON
cashflow_data       JSON
dividends_data      JSON
scores_json         JSON   {health, valuation, growth, ...} nullable — cache pré-calculé
live_price          FLOAT
live_change_pct     FLOAT
live_price_at       DATETIME

prices
─────────────────────────────────────────────────
id              INTEGER  PK
ticker          VARCHAR  INDEX
date            VARCHAR
interval        VARCHAR  (15m | 1h | 1D | 1W)
open/high/low/close  FLOAT
volume          BIGINT
UC: (ticker, date, interval)
INDEX: idx_prices_ticker_interval_date (ticker, interval, date DESC)

macro_cache
─────────────────────────────────────────────────
cache_key       VARCHAR  PK
data_json       JSON
updated_at      DATETIME
TTL: 24h (cycle, liquidity) · 6h (rates)

exchange_rates
─────────────────────────────────────────────────
id              INTEGER  PK
pair            VARCHAR  UNIQUE  (EURUSD | GBPUSD | JPYUSD | CHFUSD)
rate            FLOAT    (valeur en USD pour 1 unité de la devise)
updated_at      DATETIME
```

---

## 5. Calcul des scores

**Entrée :** Company + sector_companies (même secteur en DB)
**Cache :** `scores_json` pré-calculé lors de chaque seed_fundamentals (lundi)
**Fallback :** recalcul à la volée si `scores_json` est null

**6 piliers pondérés :**

| Pilier | Poids | Métriques clés |
|--------|-------|----------------|
| Health | 25% | Marge Nette, ROE, Dette/FP |
| Valuation | 20% | PER, PEG, EV/EBITDA |
| Growth | 20% | Croissance CA, Croissance Bénéfices |
| Efficiency | 15% | FCF, Trésorerie, Ratio Liquidité |
| Dividend | 10% | Rendement Div, Payout Ratio |
| Momentum | 10% | Beta, Haut/Bas 52w |

**Verdict (MIF2-compliant) :** Profil Fort (≥7.5) · Profil Solide (≥6) · Profil Neutre (≥4.5) · Profil Prudent (≥3) · Profil Fragile (<3)
**Complexité :** fonction de Market Cap + Beta → niveau d'investisseur requis

---

## 6. Conversion multi-devise

**Toggle :** Header → LOCAL / EUR / USD (visible uniquement en vue Fundamentals)
**Règle fondamentale :** seules les valeurs monétaires (`unit='$'`) sont converties. Les ratios (`%`, `x`) ne sont jamais convertis.

**Pipeline :**
1. `seed_exchange_rates.py` → frankfurter.app → `exchange_rates` table
2. `GET /api/exchange-rates` → rates dict `{EURUSD: 1.085, GBPUSD: ...}`
3. `useExchangeRates` hook → silent fail si endpoint indisponible
4. `CurrencyContext` → distribue `{targetCurrency, rates}` globalement
5. `formatFinancialValue(value, unit, sourceCurrency, targetCurrency, rates)` :
   - LOCAL → affichage dans la devise d'origine du ticker
   - USD → conversion via `toUSD(value, srcCurrency, rates)`
   - EUR → conversion USD puis `/= rates['EURUSD']`

---

## 7. Décisions techniques

### Architecture hybride yfinance / FMP
yfinance (gratuit, illimité) → historique OHLCV en volume (1.1M lignes). FMP (250 calls/j) → live prices <1 min via API structurée. Incompatibles en termes de volume : 64 tickers × 4 intervalles = 256 calls/seeding, dépasse le quota FMP pour l'historique.

### Score caching vs calcul à la volée
Les scores dépendent de la comparaison sectorielle. Pré-calculés lors du seed_fundamentals hebdomadaire, stockés dans `scores_json`. Fallback compute à la volée si null (première mise en prod, ticker manquant). Élimine le N+1 : plus besoin de charger tout le secteur à chaque GET /fundamentals/{ticker}.

### Neon vs Render PostgreSQL
Migration mai 2026 : Render Free PostgreSQL expirait le 05/05/2026. Neon offre 512MB gratuit en serverless, connexion poolée, EU Frankfurt (latence réduite vs US East Render). 1 133 351 lignes migrées via pg_dump/psql Docker.

### frankfurter.app vs FMP pour forex
FMP free plan : `/stable/quotes/EURUSD` → 404, `/api/v3/fx` → 403. frankfurter.app : taux BCE officiels, gratuit, sans clé, 0 impact budget FMP. Choix naturel.

### PostgreSQL index sur prices
`CREATE INDEX CONCURRENTLY idx_prices_ticker_interval_date ON prices(ticker, interval, date DESC)` — sans lock table, améliore 10–50× les requêtes OHLCV par ticker/intervalle.

### config.py — centralisation FMP
Avant : `FMP_API_KEY = os.getenv("FMP_API_KEY", "")` répété dans 3 fichiers. Après : `from config import FMP_API_KEY, FMP_STABLE, FMP_V3`. Source unique de vérité.

### Retry yfinance (seed_fundamentals)
`_fetch_info(ticker, max_retries=3)` : backoff 2s → 4s → 8s. yfinance retourne occasionnellement des erreurs réseau transitoires — le retry évite de skipper un ticker entier lors du seed hebdomadaire.

### Lightweight-charts vs TradingView Widget
Open source, pas de paywall, ~500kb gzipped, customisation complète (outils dessin custom). Indicateurs (BB, ATR, MA) calculés côté client dans `usePrices.js`.

### Rate limiting — slowapi (ajout 2026-04-30)
`slowapi 0.1.9` configuré avec `default_limits=["120/minute"]` par IP. Monté via `app.state.limiter` + handler `RateLimitExceeded`. Protège contre les appels massifs sans bloquer les utilisateurs légitimes (120 req/min ≫ usage normal).

### Verdicts MIF2 (ajout 2026-04-30)
Les anciens verdicts ("Excellent", "Bon", "À éviter") constituaient un langage de recommandation d'investissement contraire à MIF2. Renommés en profils descriptifs ("Profil Fort/Fragile") qui mesurent l'entreprise sans orienter une décision d'achat/vente.

### Index SQL companies(sector) (ajout 2026-04-30)
`CREATE INDEX ix_companies_sector ON companies(sector)` — accélère les requêtes de moyennes sectorielles dans `sector-averages` et le fallback `compute_scores()`. Appliqué via `seeds/migrate_db.py`.

### MacroCache.data_json STRING → JSONB (ajout 2026-04-30)
`data_json` était stocké en TEXT (sérialisé manuellement via `json.dumps/loads`). Migré vers `JSONB` natif PostgreSQL : meilleure perf (parsing côté DB), validation automatique du JSON, suppression du code de sérialisation dans `cache_service.py`.

---

## 8. Points forts

1. **Score caching** — `scores_json` élimine le N+1 sectoriel, latence /fundamentals divisée par ~10
2. **Multi-devise** — toggle LOCAL/EUR/USD dans le Header, conversion propre via formatFinancialValue
3. **Index DB** — `prices(ticker, interval, date DESC)` → requêtes OHLCV 10–50× plus rapides
4. **Retry yfinance** — backoff exponentiel dans seed_fundamentals, plus de skip silencieux
5. **Config centralisée** — `config.py` évite la duplication FMP_API_KEY/URL
6. **Source labeling** — SourceTag sur chaque panel (FRED/Yahoo Finance/FMP/Boursicot)
7. **Neon serverless** — DB EU Frankfurt, 512MB gratuit, survit à l'expiration Render Free
8. **Fallback multi-niveaux** — scores_json → compute, get_cached → get_stale, live_price → risk_market
9. **Macro sophistiquée** — cycle 4×4 depuis 1948, spreads souverains, liquidité M2/BTC normalisée
10. **Auth dégradée** — Guest fallback → pas de blocage si Clerk indisponible
11. **Rate limiting** — slowapi 120 req/min par IP, protection contre les appels massifs
12. **MIF2 compliance** — verdicts en profils descriptifs + disclaimer visible sous chaque ScoreDashboard
13. **MacroCache JSONB** — colonne native Postgres, plus de json.dumps/loads manuel
14. **Index sector** — `ix_companies_sector` accélère les moyennes sectorielles

---

## 9. Faiblesses et dette technique

### Critiques

1. **Absence totale de tests** — Aucun unittest backend (models, scoring, cache). Aucun test d'intégration. Testing Library présent frontend mais non utilisé.

2. **Scoring inutilisable indices/crypto** — ^GSPC, BTCUSD, commodités n'ont pas de données fondamentales yfinance → scores à 5.0 par défaut.

3. **Budget FMP tendu** — 128 calls/jour sur 250 (51%). Aucune vérification du quota avant exécution. Pas de fallback si FMP sature.

4. **Données OHLCV fragmentées** — Seulement 5 jours glissants en continu. Initialisation complète (10 ans) requiert exécution manuelle. Pas de vérification des gaps.

5. **Momentum désynchronisé** — Le pilier momentum utilise les ratios stockés (Prix Actuel, MM50/200 en JSON) non mis à jour par seed_live_prices → drift progressif.

6. **BoJ hardcodé** — Taux Banque du Japon figé (jan 2025) dans CentralBanksThermometer.

7. ~~**Pas de rate limiting API**~~ — **Résolu 2026-04-30** : slowapi 120 req/min par IP.

### Couplages fragiles

- `seed_live_prices.py` ↔ `assets_config.py` : FMP_TICKER_MAP hardcodé, pas de fallback si symbole FMP change
- `scoring_logic.py` ↔ `models.py` : structure JSON des 6 blocs dépendante de champs nommés en dur
- `TradingChart.jsx` : indicateurs recalculés côté client à chaque fetch

---

## 10. Risques

### Sécurité

| Risque | Sévérité | Détail |
|--------|----------|--------|
| JWT sans audience | Faible | `verify_aud=False` → guest fallback permissif (acceptable MVP) |
| ~~Pas de rate limiting~~ | ~~Moyen~~ | **Résolu** : slowapi 120 req/min (2026-04-30) |
| Search ILIKE | Faible | SQLAlchemy immunise l'injection SQL mais pas de validation longueur |

### Budget API

| Source | Limite | Utilisation | Marge |
|--------|--------|-------------|-------|
| FMP | 250 calls/jour | 128/jour (2 crons) | 49% — épuisé si tests manuels |
| FRED | Gratuit illimité | ~3 req/cache miss | Large |
| yfinance | Gratuit (scraping) | 64 tickers × 1×/semaine | Fragile (anti-scraping) |
| frankfurter.app | Gratuit illimité | 1 req/jour | Large |
| Clerk | 1k users gratuit | ~10 req/session | Large |

---

## 11. Roadmap

### Déjà implémenté (depuis audit 2026-04-28)
- ✅ Index PostgreSQL `prices(ticker, interval, date DESC)`
- ✅ Score caching `scores_json` + passe post-seed
- ✅ Multi-devise LOCAL/EUR/USD (CurrencyContext + formatFinancialValue)
- ✅ Exchange rates table + seed_exchange_rates + /api/exchange-rates
- ✅ Migration DB Render → Neon
- ✅ config.py centralisation FMP
- ✅ Retry exponentiel yfinance dans seed_fundamentals
- ✅ Source labels (SourceTag) sur tous les panels

### Implémenté (audit 2026-04-30)
- ✅ Rate limiting slowapi 120 req/min par IP
- ✅ CORS restreint à GET/OPTIONS (API read-only)
- ✅ Verdicts MIF2 (Profil Fort/Solide/Neutre/Prudent/Fragile)
- ✅ Disclaimer MIF2 dans Header.jsx + sous ScoreDashboard
- ✅ Index SQL `ix_companies_sector`
- ✅ MacroCache.data_json migré STRING → JSONB natif Postgres
- ✅ cache_service.py nettoyé (plus de json.dumps/loads manuel)
- ✅ useSectorHistory désactivé en mode débutant (économie d'appel API)
- ✅ Budget FMP loggé en fin de run (estimation 2 runs/jour)
- ✅ seeds/migrate_db.py — migration DDL idempotente
- ✅ web-vitals mis à jour 2.x → 4.x

### Priorités restantes

| Priorité | Action | Effort |
|----------|--------|--------|
| 1 | **Tests intégration** — pytest (seed + endpoints + macro fallback) | 2 jours |
| 2 | **Monitoring FMP quota** — logger calls, alert si >85% budget/jour | 1 jour |
| 3 | **Fallback yfinance** — mode dégradé 503 si FMP indisponible | 1 jour |
| 4 | **BoJ live** — fetch FRED IRSTCB01JPM156N au lieu de hardcode | 0.5 jour |
| 5 | **Normalisation devise dans scoring** — scores comparables CAC40 vs Mag7 | 3 jours |
