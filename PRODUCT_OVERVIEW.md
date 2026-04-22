# Boursicot — Product Overview

> Document de référence pour l'agent IA product manager.
> Répertorie l'intégralité des vues, visualisations, features et endpoints de l'application.

---

## Sommaire

1. [Architecture générale](#1-architecture-générale)
2. [Pages & Navigation](#2-pages--navigation)
3. [Visualisations](#3-visualisations)
4. [Features utilisateur](#4-features-utilisateur)
5. [Endpoints API](#5-endpoints-api)
6. [Sources de données externes](#6-sources-de-données-externes)
7. [Assets couverts](#7-assets-couverts)
8. [Modèles de données](#8-modèles-de-données)

---

## 1. Architecture générale

| Couche | Technologie |
|--------|-------------|
| Frontend | React 19 + Vite |
| Authentification | Clerk (OAuth, Bearer JWT) |
| Charts | Lightweight Charts (TradingView) |
| Routing | React Router v7 |
| Backend | FastAPI (Python) |
| Base de données | PostgreSQL (SQLAlchemy ORM) |
| Données marché | yfinance (Yahoo Finance) |
| Données macro | FRED API (Federal Reserve) |

**Structure des repos**
- `boursicot-front/` — application React
- `boursicot-api/` — API FastAPI + scripts de seeding + modèles

---

## 2. Pages & Navigation

### 2.1 Pages d'authentification

| Page | Route | Composant |
|------|-------|-----------|
| Connexion | `/login` | `LoginPage.jsx` |
| Inscription | `/register` | `RegisterPage.jsx` |

Toutes les routes sont protégées via `ProtectedRoute.jsx` (redirect → `/login` si non authentifié).

### 2.2 Dashboard principal

Route unique `/` avec un header sticky et trois **onglets de vue** :

| Onglet | `viewMode` | Description |
|--------|------------|-------------|
| Cours de bourse | `chart` | Graphiques de prix + outils techniques |
| Analyse Fondamentale | `fundamentals` | Données financières entreprise |
| Indicateurs Macroéconomiques | `macro` | Cycle économique, taux, liquidité |

### 2.3 Header (`Header.jsx`)

Barre de navigation persistante contenant :
- **Barre de recherche** avec autocomplétion (ticker + nom)
- **Filtres** : TYPE · PAYS · SECTEUR
- **Boutons de navigation** entre les 3 onglets
- **Toggle Dark / Light** theme
- **Bouton profil** Clerk

---

## 3. Visualisations

### 3.1 Onglet "Cours de bourse"

#### TradingChart (`TradingChart.jsx`)
Chart professionnel full technical analysis.

| Élément | Détail |
|---------|--------|
| Type | Candlestick (OHLCV) |
| Couleurs | Hausse `#26a69a` · Baisse `#ef5350` |
| **Indicateurs activables** | |
| Volume | Histogramme coloré sous le graphe |
| MM10 | Ligne `#00bcd4` |
| MM100 | Ligne `#ff9800` |
| MM200 | Ligne `#9c27b0` |
| Bollinger Bands | Bandes `#2962FF` à 50 % d'opacité |
| ATR | Échelle secondaire `#e91e63` |
| **Outils de dessin** | |
| Ligne de tendance | Extensible aux bords |
| Ligne horizontale | |
| Ligne verticale | |
| Rectangle | Filled |
| Fibonacci | 7 niveaux : 0 · 23.6 · 38.2 · 50 · 61.8 · 78.6 · 100 % |
| Palette dessin | 6 couleurs (ambre, rouge, vert, bleu, violet, blanc) |
| Légende crosshair | Close · Volume · MAs · BB · ATR en temps réel |
| Auto-upgrade intervalle | Si dézoom > données : 15m → 1h → 1D |

#### SimpleChart (`SimpleChart.jsx`)
Chart léger pour comparaison multi-actifs.

| Élément | Détail |
|---------|--------|
| Vue solo | Area chart + MM10 · MM100 · MM200 |
| Vue comparaison | Ligne par actif (max 5), couleurs `ASSET_COLORS` |
| Mode normalisé | Base 100 (% depuis premier point commun) |
| Mode individuel | Cours réels sur échelles séparées |
| Badges stats | Nom + prix + % de variation sur fenêtre visible |

**Contrôles communs aux deux charts**

| Type | Options |
|------|---------|
| Intervalle de bougie | 15m · 1h · 1D · 1W |
| Time range | 1W · 1M · 3M · 6M · 1Y · 5Y · ALL |

---

### 3.2 Onglet "Analyse Fondamentale"

#### Vue Solo

**En-tête entreprise**
- Nom · Secteur · Industrie
- Description longue
- Fiche d'identité (7 champs) : Industrie · Siège · IPO date · Effectif · Bourse · Devise · Site web

**6 catégories de MetricCards** (grille 3 colonnes)

| # | Catégorie | Exemples de métriques |
|---|-----------|----------------------|
| 1 | Analyse de Marché | Capitalisation · PER · Rendement Dividende |
| 2 | Santé Financière | Marge Nette · ROE · Dette/Fonds Propres |
| 3 | Valorisation Avancée | Forward PE · Price to Book · EV/EBITDA · PEG |
| 4 | Compte de Résultat & Croissance | Chiffre d'Affaires · EBITDA · Croissance CA · Croissance Bénéfices |
| 5 | Bilan & Liquidité | Trésorerie · Free Cash Flow · Ratio Liquidité |
| 6 | Risque & Marché | Beta · Plus Haut 52w · Plus Bas 52w · Actions Shortées |

Chaque **MetricCard** affiche :
- Valeur courante formatée (M$, Md$, %, x)
- Comparaison à la **moyenne sectorielle** (vert si meilleur, rouge si pire)
- Icône `ℹ` avec tooltip explicatif (`MetricInfo.jsx`)

**3 tableaux d'états financiers** (`FinancialStatement.jsx`)

| # | Section | Indicateurs |
|---|---------|-------------|
| 7 | Compte de Résultat — Historique | CA · Coût des ventes · Bénéfice brut · EBIT · EBITDA · Résultat net · BPA · Charges financières · IS · R&D · SG&A |
| 8 | Bilan Comptable — Historique | Actif total · Passif total · Capitaux propres · Dettes · Actif courant · Trésorerie · Créances · Stocks · Goodwill · Immobilisations · BFR |
| 9 | Flux de Trésorerie — Historique | Flux opérationnel · CapEx · FCF · Flux investissement · Flux financement · Dividendes · Rachats actions · D&A · Résultat net · Variation BFR |

Chaque ligne affiche :
- Valeurs sur **5 ans** (les 4 dernières en colonnes + plein historique en graphe)
- **% YoY** coloré (vert / rouge) entre année N et N-1
- Colonne **Moy. Sectorielle**
- Bouton **↗ "voir plus"** → ouvre `MetricHistoryModal`

**MetricHistoryModal (`MetricHistoryModal.jsx`)**
- Graphique SVG pur (sans dépendance externe)
- Ligne entreprise (bleu `#2962FF` plein)
- Ligne moyenne sectorielle (violet `#8c7ae6` tiretée)
- Abscisse : années · Ordonnée : valeurs auto-scalées
- Tooltip au survol : valeur entreprise + secteur
- Tableau récapitulatif en dessous du graphe

#### Vue Comparaison (2–5 actifs)

- Headers colorés par actif (`ASSET_COLORS`)
- **6 tableaux métriques** : actifs en colonnes · métriques en lignes
  - Highlight vert = meilleure valeur · rouge = pire
  - Logique inversée pour ratios "lower is better" (P/E, P/B, Debt/Equity…)
  - Métriques neutres sans highlight (Market Cap, Beta, 52W)
- **3 tableaux états financiers** avec YoY % change

---

### 3.3 Onglet "Indicateurs Macroéconomiques"

#### EconomicClock (`EconomicClock.jsx`)
Jauge semi-circulaire 180° indiquant la phase du cycle économique.

| Phase | Couleur | Quadrant | Conditions |
|-------|---------|----------|------------|
| Expansion | `#26a69a` | 90–135° | Croissance ↑ · Inflation ↓ |
| Surchauffe | `#ff9800` | 45–90° | Croissance ↑ · Inflation ↑ |
| Contraction | `#ef5350` | 0–45° | Croissance ↓ · Inflation ↑ |
| Récession | `#2962FF` | 135–180° | Croissance ↓ · Inflation ↓ |

Affiche : phase courante · growth_yoy (%) · inflation_yoy (%) · tendances (↑/↓)
Historique : graphe INDPRO + CPIAUCSL depuis **1948**

#### CentralBanksThermometer (`CentralBanksThermometer.jsx`)
4 lignes, une par banque centrale.

| Banque | Pays |
|--------|------|
| Fed | 🇺🇸 États-Unis |
| BCE | 🇪🇺 Zone Euro |
| BoE | 🇬🇧 Royaume-Uni |
| BoJ | 🇯🇵 Japon |

Chaque ligne : taux actuel + barre de jauge (0–8 %) + badge de politique monétaire

| Seuil | Label | Couleur |
|-------|-------|---------|
| < 1 % | Accommodant | Bleu |
| 1–3 % | Neutre | Teal |
| 3–5 % | Restrictif | Ambre |
| > 5 % | Très restrictif | Rouge |

#### YieldCurveChart (`YieldCurveChart.jsx`)

**CurveSnapshot** (SVG)
- Courbe instantanée US (2Y · 10Y · 30Y) + spread 10Y-2Y
- Vert = courbe normale · Rouge = courbe inversée

**SpreadHistory** (Canvas interactif)
- Historique du spread 10Y-2Y depuis **1960**
- Baseline 0 % · Zone rouge = inversion
- Range : 3M · 6M · 1Y · 2Y · 5Y · 10Y · Max
- Stats : min · max · jours d'inversion

#### SovereignSpreadsChart (`SovereignSpreadsChart.jsx`)
10 séries de taux souverains sur un même graphe.

| Série | Couleur |
|-------|---------|
| US 2Y | `#e91e63` |
| US 10Y | `#2962FF` |
| US 30Y | `#9c27b0` |
| US 3M | `#fb8c00` (tirets) |
| Bund 10Y | `#f59e0b` |
| Bund 3M | `#fdd835` (tirets) |
| OAT 10Y | `#26a69a` |
| OAT 3M | `#80cbc4` (tirets) |
| Gilt 10Y | `#ef5350` |
| Gilt 3M | `#ff7043` (tirets) |

Toggle de visibilité par série · Range identique à YieldCurve

#### LiquidityMonitor (`LiquidityMonitor.jsx`)
Graphe 2 lignes normalisées base 100 (depuis 2020-01-01).

| Série | Couleur | Source |
|-------|---------|--------|
| M2 USA | `#60A5FA` | FRED — M2SL |
| Bitcoin | `#F97316` | yfinance BTC-USD |

Corrélation visualisée entre masse monétaire et crypto.

#### AssetWindMatrix (`AssetWindMatrix.jsx`)
Matrice statique phase économique × classes d'actifs.

| Phase | Favorables | Neutres | Défavorables |
|-------|-----------|---------|--------------|
| Expansion | Tech/Croissance · Bitcoin · Crypto | Matières premières · Obligations | — |
| Surchauffe | Matières premières · Énergie · Banques (Value) | — | Obligations · Tech |
| Contraction (Stagflation) | Dollar/Cash · Or | — | Tech · Matières premières |
| Récession | Obligations | Actions défensives | Matières premières · Croissance |

---

## 4. Features utilisateur

### Header
| Feature | Description |
|---------|-------------|
| Recherche | Autocomplétion par ticker et nom d'entreprise |
| Filtre TYPE | stock · index · crypto · commodity |
| Filtre PAYS | International · France · États-Unis · Pays-Bas |
| Filtre SECTEUR | Tous les secteurs présents en DB |
| Dark/Light mode | Toggle theme persistant dans le contexte React |

### Vue Cours de bourse
| Feature | Description |
|---------|-------------|
| Comparaison | Jusqu'à 5 actifs simultanés (CompareBar) |
| Chart trading | Chandelier + indicateurs techniques complets |
| Chart simple | Courbes comparatives normalisées ou à échelle individuelle |
| Dessin technique | 5 outils + palette 6 couleurs + Undo/Clear |
| Fibonacci | Placement automatique des 7 niveaux |
| Auto-upgrade | Passage automatique à l'intervalle supérieur au dézoom |
| Légende hover | Valeurs OHLCV + indicateurs au curseur |

### Vue Analyse Fondamentale
| Feature | Description |
|---------|-------------|
| Fiche identité | 7 données clés + lien cliquable site web |
| 60+ métriques | Groupées en 6 catégories avec codes couleur vs secteur |
| États financiers | 5 ans d'historique (Income · Balance · Cash Flow) |
| Graphe historique | Modal SVG par ligne d'état financier (bouton ↗) |
| Moyenne sectorielle | Comparaison dynamique par secteur |
| YoY change | % variation N / N-1 coloré |
| Vue comparaison | Tableau multi-actifs avec highlight meilleur/pire |
| Tooltips métriques | Explication de chaque indicateur au clic ℹ |

### Vue Macroéconomiques
| Feature | Description |
|---------|-------------|
| Cycle économique | Phase courante + tendances growth/inflation |
| Historique depuis 1948 | INDPRO + CPIAUCSL sur ~900 points |
| Taux directeurs | 4 banques centrales avec jauges visuelles |
| Courbe des taux | Snapshot + historique spread 10Y-2Y depuis 1960 |
| Dettes souveraines | 10 séries avec toggle de visibilité |
| Liquidité M2 vs BTC | Corrélation normalisée depuis 2020 |
| Wind Matrix | Guide d'allocation par phase économique |

---

## 5. Endpoints API

Base : `VITE_API_URL` (ex : `http://localhost:8000`)
Toutes les routes requièrent `Authorization: Bearer <clerk_jwt>`.

### Prices

```
GET /api/prices
  ?ticker=  (ex: AAPL, AI.PA)
  ?interval= 15m | 1h | 1D | 1W  (défaut: 1D)
  ?limit=   (optionnel)
  → [{time, open, high, low, close, volume, interval}, ...]
```

### Fundamentals

```
GET /api/fundamentals
  → [Company, ...]  (liste complète)

GET /api/fundamentals/{ticker}
  → Company

GET /api/fundamentals/sector-averages/{sector}
  → {
      market_analysis:    { metric_name: avg, ... },
      financial_health:   { ... },
      advanced_valuation: { ... },
      income_growth:      { ... },
      balance_cash:       { ... },
      risk_market:        { ... },
      income_stmt_data:   { metric_name: avg, ... },
      balance_sheet_data: { ... },
      cashflow_data:      { ... }
    }

GET /api/fundamentals/sector-averages/{sector}/history
  → {
      income_stmt_data:   { metric_name: { "2021": avg, "2022": avg, ... }, ... },
      balance_sheet_data: { ... },
      cashflow_data:      { ... }
    }
```

### Macro

```
GET /macro/cycle          (cache 24h)
  → { phase, growth_yoy, inflation_yoy, growth_trend, inflation_trend }

GET /macro/cycle/history  (cache 24h)
  → { history: { dates: [], indpro: [], cpi: [] } }

GET /macro/liquidity      (cache 24h)
  → { dates: [], m2_normalized: [], btc_normalized: [] }

GET /macro/rates          (cache 6h)
  → {
      central_banks: [{ name, rate, last_update }, ...],
      yield_curve:   { dates: [], values: [] },
      bond_yields:   [{ name, rate }, ...],
      history:       { us2y, us10y, us30y, us3m, bund10y, bund3m,
                       oat10y, oat3m, gilt10y, gilt3m }
    }
```

### Assets & Search

```
GET /api/assets
  → [{ ticker, name, country, sector }, ...]

GET /api/search?q=
  → [Company, ...]  (max 10, recherche ILIKE sur ticker + name)
```

---

## 6. Sources de données externes

### FRED (Federal Reserve Economic Data)

| Série FRED | Nom | Utilisé dans |
|------------|-----|-------------|
| INDPRO | Industrial Production Index | Cycle économique (growth) |
| CPIAUCSL | Consumer Price Index | Cycle économique (inflation) |
| M2SL | Masse monétaire M2 | Liquidity Monitor |
| FEDFUNDS | Taux directeur Fed | Banques centrales |
| ECBDHBB | Taux BCE | Banques centrales |
| SONIA | Taux BoE | Banques centrales |
| JPNRRDF | Taux BoJ | Banques centrales |
| DGS2, DGS10, DGS30 | Treasuries US 2Y/10Y/30Y | Yield Curve + Spreads |
| DGS3MO | Treasury US 3M | Spreads souverains |
| IRLTLT01DEM156N | Bund 10Y | Spreads souverains |
| IRLTLT01FRM156N | OAT 10Y (France) | Spreads souverains |
| IRLTLT01GBM156N | Gilt 10Y (UK) | Spreads souverains |
| IRLTST01DEM / FRM / GBM | Bund/OAT/Gilt 3M | Spreads souverains |

### yfinance (Yahoo Finance)

| Usage | Données |
|-------|---------|
| Prix historiques | OHLCV · intervalles 15m/1h/1D/1W · tous les 64 tickers |
| États financiers | Income Statement · Balance Sheet · Cash Flow (5 ans annuels) |
| Données entreprise | `stock.info` → ratios, marge, croissance, employés, description… |
| BTC-USD | Prix quotidien pour Liquidity Monitor |

### Clerk

| Usage |
|-------|
| Authentification OAuth |
| Génération Bearer JWT |
| Gestion des profils utilisateurs |

---

## 7. Assets couverts

**Total : 64 tickers actifs**

### CAC 40 (41 actifs — actions françaises)
`AC.PA` `AI.PA` `AIR.PA` `MT.AS` `CS.PA` `BNP.PA` `EN.PA` `BVI.PA` `CAP.PA` `CA.PA`
`ACA.PA` `BN.PA` `DSY.PA` `ENGI.PA` `EL.PA` `ERF.PA` `ENX.PA` `RMS.PA` `KER.PA` `OR.PA`
`LR.PA` `MC.PA` `ML.PA` `ORA.PA` `RI.PA` `PUB.PA` `RNO.PA` `SAF.PA` `SGO.PA` `SAN.PA`
`SU.PA` `GLE.PA` `STLAP.PA` `STMPA.PA` `HO.PA` `TTE.PA` `URW.PA` `VIE.PA` `DG.PA`
`ABVX.PA` `DIM.PA`

### Magnificent 7 (actions US)
`AAPL` `MSFT` `GOOGL` `AMZN` `META` `NVDA` `TSLA`

### Indices boursiers
| Ticker | Indice |
|--------|--------|
| ^FCHI | CAC 40 |
| ^GSPC | S&P 500 |
| ^IXIC | Nasdaq Composite |
| ^DJI | Dow Jones |
| ^STOXX50E | Euro Stoxx 50 |
| ^N225 | Nikkei 225 |
| ^VIX | CBOE Volatility Index |

### Crypto
| Ticker | Actif |
|--------|-------|
| BTC-USD | Bitcoin |

### Énergie
| Ticker | Actif |
|--------|-------|
| CL=F | Pétrole brut WTI |
| BZ=F | Pétrole Brent |
| NG=F | Gaz naturel |

### Métaux précieux
| Ticker | Actif |
|--------|-------|
| GC=F | Or (Gold Futures) |
| SI=F | Argent (Silver Futures) |

### Matières premières agricoles
| Ticker | Actif |
|--------|-------|
| ZC=F | Maïs (Corn Futures) |
| ZW=F | Blé (Wheat Futures) |
| CT=F | Coton (Cotton Futures) |

---

## 8. Modèles de données

### Table `companies`

```
ticker          TEXT  UNIQUE  — identifiant principal
name            TEXT
sector          TEXT
industry        TEXT
description     TEXT
country / city / website / employees / exchange / currency / ipo_date

market_analysis    JSON  — [{name, val, unit}, ...]
financial_health   JSON
advanced_valuation JSON
income_growth      JSON
balance_cash       JSON
risk_market        JSON

income_stmt_data   JSON  — {years: [date, ...], items: [{name, vals: [f, ...], unit}]}
balance_sheet_data JSON
cashflow_data      JSON
```

### Table `prices`

```
ticker    TEXT
date      DATETIME
interval  TEXT       — "15m" | "1h" | "1D" | "1W"
open_price / high_price / low_price / close_price  FLOAT
volume    BIGINT
UNIQUE CONSTRAINT (ticker, date, interval)
```

### Table `macro_cache`

```
cache_key   TEXT  UNIQUE   — "macro_cycle" | "macro_liquidity" | "macro_rates_v6"
data_json   TEXT
updated_at  DATETIME       — TTL contrôlé en code (24h cycle/liquidité, 6h taux)
```

---

*Dernière mise à jour : 2026-04-22*
