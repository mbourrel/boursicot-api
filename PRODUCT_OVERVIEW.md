# Boursicot Pro — Product Overview

> **Dernière mise à jour :** 2026-04-30
> **Mainteneur :** Mateo
> **Stack :** React 19 / FastAPI / PostgreSQL Neon / yFinance / FMP / Clerk Auth

---

## 1. Vision Produit

Boursicot Pro est une plateforme d'analyse financière pédagogique destinée aux investisseurs particuliers. L'objectif est de rendre lisible et actionnable l'analyse fondamentale et macro-économique, en combinant des données financières brutes avec une couche d'explication adaptée au niveau de l'utilisateur.

**Positionnement :** Entre le screener technique brut (type TradingView) et le conseiller financier humain. Boursicot explique *pourquoi* une métrique est importante, pas seulement *ce qu'elle vaut*.

**Conformité MIF2 :** La plateforme fournit des informations à titre indicatif uniquement. Les scores mesurent la performance relative d'une entreprise dans son secteur — ils ne constituent pas un conseil en investissement. Le disclaimer est affiché en permanence dans le Header et sous chaque ScoreDashboard.

---

## 2. Architecture Technique

```
boursicot-front/          React 19 + Vite 8 + Clerk Auth
  src/
    components/
      Header.jsx               Navigation, filtres, devise, thème, disclaimer MIF2
      Fundamentals.jsx         Vue principale analyse fondamentale (solo + comparaison)
      fundamentals/
        ScoreDashboard.jsx     6 jauges SVG + note globale + verdict + disclaimer MIF2
        MetricCard.jsx         Carte métrique avec comparaison sectorielle
        MetricInfo.jsx         Tooltip pédagogique 2 niveaux (C'est quoi / Pourquoi)
        FinancialStatement.jsx Tableaux financiers historiques
        MethodologyModal.jsx   Explication de la méthodologie des scores
      TradingChart.jsx         Graphiques OHLCV avancés (lightweight-charts)
      SimpleChart.jsx          Graphique ligne multi-actifs simplifié
      MacroEnvironment.jsx     Agrège tous les widgets macro
      EconomicClock.jsx        Jauge 4-phase + historique depuis 1948
      LiquidityMonitor.jsx     M2 vs BTC normalisés
      CentralBanksThermometer  Taux directeurs Fed/BCE/BoE/BoJ
      YieldCurveChart.jsx      Spread 10Y-2Y + snapshot courbe
      SovereignSpreadsChart    Rendements souverains multi-pays
      AssetWindMatrix.jsx      Matrice phase -> classes d'actifs
      CompareBar.jsx           Sélecteur multi-actifs (jusqu'à 5)
      SourceTag.jsx            Label source de données (10px, discret)
    context/
      CurrencyContext.jsx      Toggle devise LOCAL / EUR / USD
      ThemeContext.jsx         Dark / light mode
    hooks/
      useFundamentals.js       Fetch multi-symboles parallèle
      useSectorAverages.js     Moyennes sectorielles
      useSectorHistory.js      Historique sectoriel (mode avancé uniquement)
      usePrices.js             OHLCV + indicateurs côté client
      useExchangeRates.js      Taux forex (silent fail)
      useRetryFetch.js         Retry exponentiel générique
    utils/
      formatFinancialValue.js  Conversion devise + formatage montants
      analytics.js             PostHog init + events + RGPD
    api/                       Couche fetch centralisée (authFetch + Clerk token)

boursicot-api/            FastAPI + SQLAlchemy 2 + PostgreSQL Neon
  api.py                  Entrée ASGI — CORS, rate limiting (120/min), auth globale
  config.py               Constantes FMP centralisées (API_KEY, STABLE, V3)
  models.py               Company (+ index sector), Price, MacroCache (JSONB), ExchangeRate
  dependencies.py         JWT Clerk — guest fallback si token absent/invalide
  scoring_logic.py        6 piliers + note globale + verdict (MIF2-compliant)
  assets_config.py        Catalogue 64 tickers (source unique de vérité)
  routers/                fundamentals, prices, search, assets, macro, exchange_rates
  services/               macro_service, cache_service (JSONB natif)
  seeds/                  seed_fundamentals, seed_live_prices, seed_prices,
                          seed_macro, seed_exchange_rates, migrate_db
```

---

## 3. Vues Implémentées

| Vue | Accès | Statut |
|-----|-------|--------|
| **Cours de Bourse** | Bouton "Cours de bourse" | ✅ OHLCV 15m/1h/1D/1W, BB, ATR, outils dessin |
| **Analyse Fondamentale — Solo** | Sélection d'un actif | ✅ Scores pré-calculés, métriques, états financiers |
| **Analyse Fondamentale — Comparaison** | Bouton "+ Comparer" (max 5) | ✅ Tableaux comparatifs, Radar Chart 6 axes |
| **Indicateurs Macroéconomiques** | Bouton "Indicateurs Macro" | ✅ Cycle, liquidité, taux, spreads souverains |
| **Mode Débutant / Avancé** | Toggle dans le Header | ✅ Masque états financiers et appels API lourds en mode débutant |
| **Multi-devise** | Sélecteur LOCAL / EUR / USD | ✅ Conversion temps réel via taux BCE (frankfurter.app) |

---

## 4. Système de Scoring

Les scores sont **pré-calculés** lors du seed hebdomadaire et mis en cache dans `Company.scores_json`. L'API les lit directement sans recalcul — fallback compute à la volée uniquement si `scores_json` est null.

### 6 Piliers + Score Global

| Pilier | Poids | Métriques sources |
|--------|-------|-------------------|
| **Santé** | 25 % | Marge Nette, ROE, Dette/Fonds Propres, Ratio de Liquidité |
| **Valorisation** | 20 % | PER vs secteur, Forward PE |
| **Croissance** | 20 % | Évolution CA YoY, Évolution Bénéfices YoY |
| **Efficacité** | 15 % | ROE vs secteur, Marge vs secteur, tendance marge 5 ans |
| **Dividende** | 10 % | Payout Ratio (optimal 40–60 %), Rendement vs secteur |
| **Momentum** | 10 % | Prix vs MM50, Prix vs MM200, Golden/Death Cross |

**Complexité** (indicateur séparé, hors note globale) : Capitalisation + Beta → badge Simple / Modéré / Avancé.

### Verdicts (MIF2-compliant)

| Score | Verdict | Couleur |
|-------|---------|---------|
| ≥ 7.5 | Profil Fort | `#26a69a` (teal) |
| ≥ 6.0 | Profil Solide | `#26a69a` (teal) |
| ≥ 4.5 | Profil Neutre | `#ff9800` (orange) |
| ≥ 3.0 | Profil Prudent | `#ef5350` (rouge) |
| < 3.0 | Profil Fragile | `#ef5350` (rouge) |

> Les anciens verdicts ("Excellent", "Bon", "À éviter") ont été renommés en avril 2026 pour se conformer à MIF2 : le langage actionnable (achat/vente implicite) est remplacé par des profils descriptifs.

### Disclaimer MIF2
Affiché à deux niveaux :
1. **Header** (toutes les vues) : ligne 10px permanente sous la barre de navigation.
2. **ScoreDashboard** : ligne pleine largeur sous la grille de scores, toujours visible sans clic.

---

## 5. Couche Pédagogique

### Tooltips métriques (`MetricInfo.jsx`)
- **43 métriques documentées** dans `constants/metricExplanations.js`
- Format : `{ what: "C'est quoi ?", why: "Pourquoi c'est important ?" }`
- Rendu : tooltip portal positionné intelligemment (évite les débordements d'écran)

### Modal Méthodologie (`MethodologyModal.jsx`)
- Accessible via "Définition des indicateurs" dans le `ScoreDashboard`
- Contenu : 6 piliers, échelle de lecture, avertissement biais de groupe, disclaimer non-conseil

---

## 6. Données — Sources et Refresh

| Donnée | Source | Fréquence |
|--------|--------|-----------|
| OHLCV (15m, 1h, 1D, 1W) | yFinance → table `prices` | Cron 8×/jour (lun–ven) |
| Fondamentaux + scores | yFinance + FMP → `companies` + `scores_json` | Cron 1×/semaine (lundi 7h UTC) |
| Prix live (close + var %) | FMP `/stable/quote` + `/stable/profile` | Cron 2×/jour (9h + 17h30 Paris) |
| Taux de change | frankfurter.app (BCE) → `exchange_rates` | Cron 1×/jour (lun–ven) |
| Indicateurs macro | FRED + yFinance → `macro_cache` (JSONB) | Cache 24h, invalidé lundi 7h30 UTC |

**Budget FMP :** 64 calls/run × 2 runs/jour = 128/250 calls autorisés (51 %). Loggé en fin de chaque run `seed_live_prices`.

**Source labeling :** chaque panel affiche sa source via `SourceTag.jsx` (FRED, Yahoo Finance, FMP, Boursicot).

---

## 7. Univers d'Actifs

**64 tickers couverts :**
- Actions CAC 40 : 40 tickers
- Actions US (Mag7) : 7 tickers
- Indices (^GSPC, ^IXIC, ^DJI, ^STOXX50E, ^N225, ^VIX…) : 7 tickers
- Crypto : BTC-USD
- Métaux précieux : Or, Argent
- Énergie : Pétrole WTI, Brent, Gaz Naturel
- Agricoles : Maïs, Blé, Coton

Filtres disponibles dans le Header : TYPE, PAYS, SECTEUR.

---

## 8. Sécurité & Conformité

| Aspect | Implémentation |
|--------|---------------|
| **Auth** | Clerk JWT RS256 — guest fallback si token absent/invalide |
| **Rate limiting** | slowapi 120 req/min par IP (depuis 2026-04-30) |
| **CORS** | GET + OPTIONS uniquement — API read-only |
| **SQL injection** | SQLAlchemy ORM — paramètres auto-échappés |
| **Clés API** | Côté backend uniquement (FMP, FRED, Clerk JWKS) — jamais exposées au frontend |
| **MIF2** | Verdicts descriptifs + disclaimer permanent (Header + ScoreDashboard) |

---

## 9. Roadmap

### Complété (depuis la mise en production initiale)
- ✅ Vues : Cours de bourse, Fondamentaux solo/comparaison, Macro
- ✅ Scoring 6 piliers + ScoreDashboard orbit layout
- ✅ Mode débutant / avancé
- ✅ Score caching (scores_json en DB — élimine le N+1 sectoriel)
- ✅ Multi-devise LOCAL/EUR/USD (CurrencyContext + frankfurter.app)
- ✅ Source labels (SourceTag) sur tous les panels
- ✅ Index PostgreSQL prices(ticker, interval, date DESC)
- ✅ Migration DB Render → Neon (EU Frankfurt, serverless)
- ✅ config.py centralisation FMP
- ✅ Retry exponentiel yfinance (seed_fundamentals)
- ✅ Rate limiting slowapi 120 req/min
- ✅ CORS restreint GET/OPTIONS
- ✅ Verdicts MIF2 (Profil Fort/Solide/Neutre/Prudent/Fragile)
- ✅ Disclaimer MIF2 permanent (Header + ScoreDashboard)
- ✅ Index SQL companies(sector)
- ✅ MacroCache.data_json STRING → JSONB natif Postgres
- ✅ useSectorHistory désactivé en mode débutant
- ✅ Budget FMP loggé en fin de run

### Priorité haute

| Feature | Description | Composants impactés |
|---------|-------------|---------------------|
| **Tests automatisés** | pytest backend (seeds, endpoints, scoring, cache) + Testing Library frontend | Tous |
| **Profils utilisateurs** (Explorateur / Stratège) | Remplacer le toggle binaire par un profil persistant. Explorateur = tooltips prioritaires ; Stratège = données brutes + états financiers | `Header.jsx`, `Fundamentals.jsx`, table `user_profile` |
| **Refactoring `Fundamentals.jsx`** | 703 lignes, duplication solo/compare. Découper en `SoloView`, `ComparisonView`, `RadarChart` | `Fundamentals.jsx` |

### Priorité moyenne

| Feature | Description |
|---------|-------------|
| **Cache OHLCV** | Mettre en cache les prix historiques yfinance (MacroCache, TTL 15 min) pour éviter les appels répétés côté API |
| **BoJ live** | Remplacer le taux Banque du Japon hardcodé par `FRED IRSTCB01JPM156N` |
| **Monitoring FMP** | Webhook/email si budget > 85 % du quota journalier |
| **Watchlist / Alertes** | Suivi d'actifs + alertes sur seuils de score |
| **Versioning API** | Préfixer les routes `/api/v1/` pour préparer l'ouverture à des clients tiers |

### Priorité basse / Nice-to-have

| Feature | Description |
|---------|-------------|
| **Screener** | Filtrer les actifs par seuils de score (ex : Santé > 7 ET Valorisation > 6) |
| **Export PDF** | Rapport d'analyse pour un actif |
| **Mode mobile** | L'UI n'est pas responsive sur petits écrans |
| **Historique des scores** | Tracker l'évolution du score dans le temps |
| **Normalisation devise dans scoring** | Rendre les scores comparables entre CAC 40 (EUR) et Mag7 (USD) |

---

## 10. Dette Technique

| Sujet | Impact | Urgence |
|-------|--------|---------|
| `Fundamentals.jsx` — 703 lignes, duplication solo/compare | Bloque l'ajout des profils utilisateurs | 🔴 Haute |
| Absence de tests automatisés (front + back) | Régressions silencieuses après chaque changement | 🔴 Haute |
| yfinance — SPOF sans SLA | Si Yahoo bloque le scraping, les fondamentaux ne sont plus mis à jour | 🟠 Moyenne |
| Scores indices/crypto à 5.0 par défaut | Scoring inutilisable pour ^GSPC, BTCUSD, commodités | 🟠 Moyenne |
| Momentum désynchronisé | MM50/MM200 stockés en JSON, non mis à jour par seed_live_prices | 🟠 Moyenne |
| OHLCV — 5 jours glissants seulement | Gaps possibles si cron échoue, pas de vérification | 🟡 Faible |
| `ASSET_COLORS` dupliqué `CompareBar` / `Fundamentals` | Risque de désynchronisation des couleurs | 🟡 Faible |
| Tooltips manquants sur métriques `risk_market` | Expérience pédagogique incomplète (MM50, MM200) | 🟡 Faible |
