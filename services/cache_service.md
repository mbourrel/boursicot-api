# services/cache_service.py

## Role
Helpers generiques de lecture/ecriture du cache PostgreSQL (table `macro_cache`), extraits pour etre reutilisables par tous les services.

## Dependances
- **Internes** : `models.MacroCache`
- **Externes** : `datetime`, `sqlalchemy` (plus de `json` depuis 2026-04-30)

## Fonctionnement

### `get_cached(db, key, max_age_hours=24)`
Cherche la ligne `cache_key == key` dans `macro_cache`. Retourne `None` si absente ou si `updated_at` est plus vieux que `max_age_hours`. Sinon retourne directement `record.data_json` (deja un dict Python — SQLAlchemy deserialise automatiquement la colonne JSONB).

### `get_stale(db, key)`
Retourne le cache meme si perime. Utilise comme fallback quand la source externe (FRED, yfinance) est indisponible — vaut mieux des donnees anciennes que HTTP 502.

### `set_cached(db, key, data)`
Upsert : assigne `record.data_json = data` (dict Python) directement — SQLAlchemy serialise vers JSONB. Met a jour `updated_at`. Commit immediat.

## Utilise par
- `services/macro_service.py` : les quatre fonctions publiques utilisent ces helpers pour lire/ecrire leur cache respectif.

## Points d'attention
- **Plus de `json.dumps/loads`** depuis la migration de `data_json` vers colonne `JSON` (JSONB Postgres). SQLAlchemy gere la serialisation automatiquement.
- La comparaison de fraicheur utilise `datetime.utcnow()` cote Python et `updated_at` stocke sans timezone — les deux doivent rester en UTC naif pour etre comparables.
- `set_cached` fait un `db.commit()` immediat — ne pas l'appeler a l'interieur d'une transaction englobante sans en tenir compte.
- Si deux workers tentent un `set_cached` concurrent sur la meme cle, un des deux peut ecraser l'autre (pas de verrou). Acceptable pour du cache de donnees macros (idempotent).
- Cles actuellement utilisees : `macro_cycle`, `macro_liquidity`, `macro_cycle_history`, `macro_rates_v6`.
