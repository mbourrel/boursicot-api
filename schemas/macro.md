# schemas/macro.py

## Rôle
Définit les modèles Pydantic de réponse pour les quatre endpoints `/macro/*`, garantissant la validation des types et la documentation OpenAPI automatique.

## Dépendances
- **Internes** : aucune
- **Externes** : `pydantic`, `typing`

## Fonctionnement
Six modèles Pydantic :

| Modèle | Utilisé par | Description |
|---|---|---|
| `MacroCycleOut` | `GET /macro/cycle` | Phase + YoY croissance/inflation + tendances |
| `CycleHistoryPoint` | (composant de `MacroCycleHistoryOut`) | Un point mensuel du cycle historique |
| `MacroCycleHistoryOut` | `GET /macro/cycle/history` | Liste de `CycleHistoryPoint` |
| `MacroLiquidityOut` | `GET /macro/liquidity` | Listes parallèles dates/M2_norm/BTC_norm |
| `RatePoint` | (composant de `MacroRatesOut`) | Un taux avec nom, valeur, date de mise à jour, indicateur stale |
| `HistorySeries` | (composant de `MacroRatesOut`) | Série temporelle {dates, values} |
| `MacroRatesOut` | `GET /macro/rates` | Taux directeurs + rendements + historiques + courbe des taux |

`MacroCycleOut.phase` utilise `Literal` pour restreindre aux valeurs connues, mais inclut à la fois `"Recession"` (EN, utilisé dans `get_cycle_data`) et `"Récession"` (FR, utilisé dans `get_cycle_history`) — incohérence à surveiller.

`RatePoint.stale` permet au frontend d'afficher un indicateur visuel pour les données hardcodées (ex. : BoJ).

## Utilisé par
- `routers/macro.py` : les quatre endpoints utilisent ces modèles comme `response_model`.

## Points d'attention
- `MacroCycleOut.phase` accepte `"Recession"` ET `"Récession"` — à harmoniser dans `macro_service.py` pour n'utiliser qu'une seule orthographe.
- `RatePoint.rate` et `RatePoint.last_update` sont `Optional` — une valeur `None` est valide si FRED n'a pas retourné de données pour cette série.
- `MacroRatesOut.history` est `dict[str, HistorySeries]` avec des clés hardcodées (`us2y`, `us10y`, etc.) — le frontend dépend de ces noms exacts.
- L'ajout de nouveaux endpoints macro nécessite la création de nouveaux schémas ici.
