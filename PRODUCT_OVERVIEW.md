# Boursicot Pro — Product Overview

> **Dernière mise à jour :** 2026-04-28
> **Mainteneur :** Mateo
> **Stack :** React 19 / FastAPI / PostgreSQL / yFinance / Clerk Auth

---

## 1. Vision Produit

Boursicot Pro est une plateforme d'analyse financière pédagogique destinée aux investisseurs particuliers. L'objectif est de rendre lisible et actionnable l'analyse fondamentale et macro-économique, en combinant des données financières brutes avec une couche d'explication adaptée au niveau de l'utilisateur.

**Positionnement :** Entre le screener technique brut (type TradingView) et le conseiller financier humain. Boursicot explique *pourquoi* une métrique est importante, pas seulement *ce qu'elle vaut*.

---

## 2. Architecture Technique

```
boursicot-front/          React 19 + Vite 8 + Clerk Auth
  src/
    components/
      Fundamentals.jsx         Vue principale analyse fondamentale (solo + comparaison)
      fundamentals/
        ScoreDashboard.jsx     6 jauges SVG + radar chart + MethodologyModal
        MetricInfo.jsx         Tooltip pédagogique 2 niveaux (C'est quoi / Pourquoi)
        MetricCard.jsx         Carte métrique avec comparaison sectorielle
        MetricHistoryModal.jsx Graphique historique métrique vs secteur
        MethodologyModal.jsx   Explication de la méthodologie des scores
        FinancialStatement.jsx Tableaux financiers historiques
      CompareBar.jsx           Sélecteur multi-actifs (jusqu'à 5)
      Header.jsx               Navigation + toggle Débutant/Avancé
      TradingChart.jsx         Graphiques OHLCV (lightweight-charts)
      MacroEnvironment.jsx     Indicateurs macroéconomiques
    constants/
      metricExplanations.js    43 métriques documentées {what, why}
      pillars.js               6 piliers de scoring avec métriques associées
    hooks/
      useFundamentals.js       Fetch multi-symboles parallèle
      useSectorAverages.js     Moyennes sectorielles
      useSectorHistory.js      Historique sectoriel

boursicot-api/            FastAPI + SQLAlchemy + PostgreSQL
  routers/
    fundamentals.py       Données entreprises + scores temps réel
    prices.py             OHLCV multi-intervalle
    search.py             Recherche par nom/ticker
    assets.py             Filtres TYPE/PAYS/SECTEUR
    macro.py              Indicateurs macroéconomiques (cache 24h)
  scoring_logic.py        Calcul des 6 piliers + global_score + verdict
  models.py               Company, Price, MacroCache
  seeds/                  Scripts de peuplement (yFinance)
```

---

## 3. Vues Implémentées

| Vue | Accès | Statut |
|-----|-------|--------|
| **Cours de Bourse** | Bouton "Cours de Bourse" | ✅ Fonctionnel — OHLCV 15m/1h/1D/1W, dessin technique |
| **Analyse Fondamentale — Solo** | Sélection d'un actif | ✅ Fonctionnel — scores, métriques, états financiers |
| **Analyse Fondamentale — Comparaison** | Bouton "+ Comparer" (max 5 actifs) | ✅ Fonctionnel — tableaux comparatifs, Synthèse Scores, Radar Chart |
| **Indicateurs Macroéconomiques** | Bouton "Indicateurs Macro" | ✅ Fonctionnel — données macro cachées 24h |
| **Analyse Avancée** | Toggle dans l'en-tête | ✅ Toggle binaire (Débutant/Avancé) — contrôle la visibilité des états financiers historiques |

---

## 4. Système de Scoring

Le scoring est calculé **en temps réel** à chaque appel `GET /api/fundamentals/{ticker}` par `compute_scores()`. Il compare l'entreprise aux autres acteurs de son secteur présents en base.

### 6 Piliers + Score Global

| Pilier | Poids | Métriques sources |
|--------|-------|-------------------|
| **Santé** | 25 % | Marge Nette, ROE, Dette/Fonds Propres, Ratio de Liquidité |
| **Valorisation** | 20 % | PER vs secteur, Forward PE |
| **Croissance** | 20 % | Évolution CA YoY, Évolution Bénéfices YoY |
| **Efficacité** | 15 % | ROE vs secteur, Marge vs secteur, tendance marge 5 ans |
| **Dividende** | 10 % | Payout Ratio (optimal 40-60 %), Rendement vs secteur |
| **Momentum** | 10 % | Prix vs MM50, Prix vs MM200, Golden/Death Cross |

**Complexité** (indicateur séparé) : Capitalisation + Beta → badge Simple / Modéré / Avancé.

**Verdict** : ≥ 7.5 → Excellent · ≥ 6.0 → Bon · ≥ 4.5 → Correct · ≥ 3.0 → Risqué · < 3.0 → À éviter.

**Biais de groupe :** Signalé dans la `MethodologyModal` — si un secteur contient peu d'entreprises, le score est plus sensible aux extrêmes.

### Palette de couleurs standardisée

| Valeur | Couleur |
|--------|---------|
| ≥ 7 — Favorable | `#26a69a` (teal) |
| 4–7 — Neutre | `#ff9800` (orange) |
| < 4 — Défavorable | `#ef5350` (rouge) |

---

## 5. Couche Pédagogique

### Tooltips métriques (`MetricInfo.jsx`)
- **43 métriques documentées** dans `metricExplanations.js`
- Format : `{ what: "C'est quoi ?", why: "Pourquoi c'est important ?" }`
- Rendu : tooltip portal positionné intelligemment (évite les débordements d'écran)
- Lacune actuelle : métriques de `risk_market` (MM50, MM200, Prix Actuel) non couvertes

### Modal Méthodologie (`MethodologyModal.jsx`)
- Accessible via "Définition des indicateurs" dans le `ScoreDashboard`
- Contenu : 6 piliers, échelle de lecture, avertissement biais de groupe
- Prop `sector` pour contextualiser le message

---

## 6. Données — Sources et Refresh

| Donnée | Source | Fréquence de refresh |
|--------|--------|----------------------|
| OHLCV (15m, 1h, 1D, 1W) | yFinance → table `prices` | Cron GitHub Actions toutes les 2h (8h–22h Paris) |
| Fondamentaux (ratios, états financiers) | yFinance → table `companies` | Manuel / à la demande |
| Moyennes sectorielles | Calculées en temps réel depuis `companies` | Par requête |
| Scores | Calculés en temps réel | Par requête |
| Macro | APIs externes → `macro_cache` | Cache 24h |

**Prix dans les cartes de comparaison :**
- Source primaire : dernière clôture 1D dans `prices`
- Fallback : "Prix Actuel" stocké dans `risk_market` lors du dernier seed fondamentaux

---

## 7. Univers d'Actifs

~63 tickers couverts à ce jour. Filtres disponibles : TYPE (action, ETF...), PAYS, SECTEUR.

---

## 8. Authentification

Clerk (SSO) — `ProtectedRoute` sur toutes les vues. Routes publiques : `/login`, `/register`.

---

## 9. Roadmap — Ce qui manque

### 🔴 Priorité haute

| Feature | Description | Composants impactés |
|---------|-------------|---------------------|
| **Profils utilisateurs** (Explorateur / Stratège) | Remplacer le toggle binaire Débutant/Avancé par un système de profil persistant. L'Explorateur voit les tooltips pédagogiques en priorité ; le Stratège voit les données brutes et les états financiers. | `Header.jsx`, `Fundamentals.jsx` (à découper), table `user_profile` à créer |
| **Refactoring `Fundamentals.jsx`** | Fichier > 500 lignes, impossible à faire évoluer pour les profils. À diviser en `SoloView.jsx` + `ComparisonView.jsx` + sous-composants | `Fundamentals.jsx` |
| **Prix temps réel fiables** | `daily_change_pct` reste null tant que `seed_prices` n'a pas tourné. Étudier un endpoint dédié `/api/quote/{ticker}` pour le dernier tick | `routers/prices.py`, `Fundamentals.jsx` |

### 🟠 Priorité moyenne

| Feature | Description |
|---------|-------------|
| **Watchlist / Alertes** | Permettre à un utilisateur de suivre des actifs et recevoir des alertes sur seuils de score |
| **Tooltips `risk_market`** | Documenter MM50, MM200, Prix Actuel dans `metricExplanations.js` |
| **Cache scoring** | Mettre en cache `compute_scores()` (Redis ou colonne en base) pour éviter les recalculs sur les secteurs larges |
| **Onboarding** | Parcours guidé première connexion adapté au profil choisi |

### 🟡 Priorité basse / Nice-to-have

| Feature | Description |
|---------|-------------|
| **Screener** | Filtrer les actifs par seuils de score (ex : Santé > 7 ET Valorisation > 6) |
| **Export PDF** | Générer un rapport d'analyse pour un actif |
| **Mode mobile** | L'UI actuelle n'est pas responsive sur petits écrans |
| **Historique des scores** | Tracker l'évolution du score d'un actif dans le temps |

---

## 10. Dette Technique Connue

| Sujet | Impact | Urgence |
|-------|--------|---------|
| `Fundamentals.jsx` monolithique (> 500 lignes) | Bloque l'ajout des profils | 🔴 Haute |
| Scoring recalculé à chaque requête | Performance si > 500 sociétés/secteur | 🟠 Moyenne |
| Pas de tests automatisés front ni back | Régressions silencieuses | 🟠 Moyenne |
| `ASSET_COLORS` dupliqué entre `CompareBar.jsx` et `Fundamentals.jsx` | Désync possible | 🟡 Faible |
| Tooltips manquants sur métriques `risk_market` | Expérience pédagogique incomplète | 🟡 Faible |
