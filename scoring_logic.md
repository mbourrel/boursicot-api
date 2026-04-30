# scoring_logic.py

## Rôle
Moteur de scoring d'investissement : calcule 6 scores dimensionnels (0-10) + une note globale pondérée + un verdict textuel pour chaque entreprise, en se comparant aux moyennes sectorielles.

## Dépendances
- **Internes** : aucune (module autonome, pas d'import projet)
- **Externes** : aucune (Python pur)

## Fonctionnement

### Utilitaires internes
- `_get_val(metrics_list, name)` : extrait une valeur depuis une liste `[{"name", "val", "unit"}]` ; retourne `None` si absente ou égale à 0.
- `_sector_avg(companies, cat, metric_name)` : calcule la moyenne d'une métrique sur une liste de `Company` du même secteur.
- `_clamp(v, lo, hi)` : borne une valeur entre 0 et 10.
- `_ratio_score(company_val, sector_val, invert, neutral)` : transforme un ratio entreprise/secteur en score 0-10. ratio=1 → 5 (moyenne), ratio=2 → 10 (deux fois mieux). `invert=True` pour les métriques où moins = mieux (ex. : Dette/FP).

### Scores individuels
| Score | Métriques utilisées | Source champs Company |
|---|---|---|
| `health` | Marge Nette, ROE, Dette/FP, Ratio Liquidité | `financial_health`, `balance_cash` |
| `valuation` | PER vs secteur, Forward PE vs PER | `market_analysis`, `advanced_valuation` |
| `growth` | Croissance CA, Croissance Bénéfices | `income_growth` |
| `dividend` | payout_ratio (optimal 40-60%), dividend_yield vs secteur | `dividends_data` |
| `momentum` | Prix vs MM50, Prix vs MM200, Golden/Death cross | `risk_market` |
| `efficiency` | ROE + Marge Nette vs secteur + tendance historique marge | `financial_health`, `income_stmt_data` |
| `complexity` | Market Cap (taille), Beta (volatilité) | `market_analysis`, `risk_market` |

### Note globale et verdict
Pondérations : health 25 %, valuation 20 %, growth 20 %, efficiency 15 %, dividend 10 %, momentum 10 %.
(`complexity` n'est **pas** inclus dans la note globale — indicateur informatif uniquement.)

**Verdict (MIF2-compliant depuis 2026-04-30) :**
≥7.5 → "Profil Fort" | ≥6.0 → "Profil Solide" | ≥4.5 → "Profil Neutre" | ≥3.0 → "Profil Prudent" | <3.0 → "Profil Fragile"

Les anciens verdicts ("Excellent", "Bon", "À éviter") ont été renommés car ils constituaient un langage de recommandation d'investissement contraire à la directive MIF2.

### `compute_scores(company, sector_companies)`
Fonction publique unique. Retourne un dict avec les 9 clés : health, valuation, growth, dividend, momentum, efficiency, complexity, global_score, verdict.

## Utilisé par
- `seeds/seed_fundamentals.py` : pré-calcule et stocke les scores dans `Company.scores_json` après chaque seed.
- `routers/fundamentals.py` : fallback compute à la volée si `scores_json` est `None`.

## Points d'attention
- Si une métrique est absente (`None`) ou nulle, sa contribution est **omise** de la moyenne — le score ne pénalise pas l'absence de données, mais peut être biaisé vers 5 si peu de métriques sont disponibles.
- `_score_dividend` retourne **5.0 neutre** pour les sociétés sans dividende — ne pas interpréter un score de 5 comme une distribution modérée.
- `_score_momentum` requiert que `Prix Actuel`, `MM50`, `MM200` soient dans `risk_market` ; ces champs ne sont **pas** seedés par `seed_fundamentals.py` (yfinance `.info` ne les fournit pas directement) — résultat : momentum souvent à 5.0 par défaut.
- Les plages de normalisation pour `growth` sont hardcodées (+20 % à +50 % CA, -30 % à +50 % bénéfices) — à réviser si le marché change de régime.
