# services/cache_service.py

## Rôle
Helpers génériques de lecture/écriture du cache PostgreSQL (table `macro_cache`), extraits pour être réutilisables par tous les services.

## Dépendances
- **Internes** : `models.MacroCache`
- **Externes** : `json`, `datetime`, `sqlalchemy`

## Fonctionnement

### `get_cached(db, key, max_age_hours=24)`
Cherche la ligne `cache_key == key` dans `macro_cache`. Retourne `None` si absente ou si `updated_at` est plus vieux que `max_age_hours`. Sinon désérialise et retourne le dict Python.

### `get_stale(db, key)`
Retourne le cache même si périmé. Utilisé comme fallback quand la source externe (FRED, yfinance) est indisponible — vaut mieux des données anciennes que HTTP 502.

### `set_cached(db, key, data)`
Upsert : met à jour `data_json` et `updated_at` si la ligne existe, sinon crée un nouvel enregistrement. Commit immédiat.

## Utilisé par
- `services/macro_service.py` : les quatre fonctions publiques utilisent ces helpers pour lire/écrire leur cache respectif.

## Points d'attention
- La comparaison de fraîcheur utilise `datetime.utcnow()` côté Python et `updated_at` stocké sans timezone — les deux doivent rester en UTC naïf pour être comparables.
- `set_cached` fait un `db.commit()` immédiat — ne pas l'appeler à l'intérieur d'une transaction englobante sans en tenir compte.
- Les données sont sérialisées en JSON texte dans `data_json` (colonne `String`, pas `JSON`) — pas de validation de type à la lecture.
- Si deux workers tentent un `set_cached` concurrent sur la même clé, un des deux peut écraser l'autre (pas de verrou). Acceptable pour du cache de données macros (idempotent).
- Clés actuellement utilisées : `macro_cycle`, `macro_liquidity`, `macro_cycle_history`, `macro_rates_v6`.
