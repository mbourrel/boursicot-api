# seeds/seed_macro.py

## Rôle
Invalide le cache macro dans PostgreSQL pour les clés `macro_cycle` et `macro_cycle_history`, forçant leur recalcul au prochain appel API depuis FRED.

## Dépendances
- **Internes** : `database.SessionLocal`, `database.engine`, `models.Base`, `models.MacroCache`
- **Externes** : `sys`, `os`

## Fonctionnement

### `seed_macro()`
1. Itère sur `MACRO_KEYS = ["macro_cycle", "macro_cycle_history"]`.
2. Pour chaque clé : cherche l'entrée dans `macro_cache`, la supprime si elle existe, ou log "absent" si elle n'existe pas.
3. Commit global.
4. Affiche un résumé du nombre d'entrées invalidées.

L'effet : le prochain appel aux endpoints `GET /macro/cycle` et `GET /macro/cycle/history` ira chercher des données fraîches chez FRED, puis remettra l'entrée en cache.

**Note** : `macro_liquidity` et `macro_rates_v6` ne sont **pas** invalidés par ce script.

## Utilisé par
- En manuel : `python seeds/seed_macro.py` (après une mise à jour de la logique de calcul du cycle, ou pour forcer un refresh immédiat).
- Potentiellement en cron mensuel si on veut s'assurer que le cache reflète les dernières publications FRED.

## Points d'attention
- Ce script **supprime** les lignes de cache (DELETE) plutôt que de les mettre à jour — le prochain appel API supportera donc la latence de recalcul (fetch FRED + calcul).
- `macro_liquidity` (M2 + BTC) et `macro_rates_v6` (taux directeurs) ne sont pas couverts — à ajouter à `MACRO_KEYS` si on veut les invalider aussi.
- Le script ne valide pas si les données seront bien recalculées après l'invalidation (nécessite que `FRED_API_KEY` soit disponible au runtime de l'API).
- À appeler **avant** de pousser une modification de `macro_service.py` en production pour éviter que l'ancien cache soit servi.
