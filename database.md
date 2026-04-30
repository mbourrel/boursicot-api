# database.py

## Rôle
Configure la connexion SQLAlchemy à la base PostgreSQL (Neon) et expose le moteur, la session factory, et la dépendance FastAPI `get_db`.

## Dépendances
- **Internes** : aucune
- **Externes** : `sqlalchemy` (create_engine, sessionmaker, declarative_base), `python-dotenv`, `os`

## Fonctionnement
1. Charge `.env` via `load_dotenv()`.
2. Lit `SQLALCHEMY_DATABASE_URL` depuis l'environnement et lève `ValueError` si absente — fail-fast au démarrage plutôt qu'une erreur cryptique à la première requête.
3. Crée `engine` (pool de connexions SQLAlchemy synchrone).
4. Crée `SessionLocal` avec `autocommit=False` et `autoflush=False` — les commits sont explicites dans le code.
5. Expose `Base = declarative_base()` (doublon historique ; la `Base` canonique est dans `models.py`).
6. `get_db()` : générateur FastAPI — ouvre une session, la `yield`, puis la ferme dans `finally` même en cas d'exception.

## Utilisé par
- `api.py` (import de `engine` pour `create_all`)
- Tous les routers via `Depends(get_db)` pour obtenir une session
- Tous les scripts de seed (import direct de `SessionLocal` et `engine`)

## Points d'attention
- L'URL doit inclure le paramètre `sslmode=require` pour Neon (géré dans le `.env`, pas dans le code).
- `Base` déclarée ici est un vestige — elle n'est pas utilisée pour les modèles réels (ceux-ci utilisent leur propre `Base` de `models.py`). Ne pas mixer les deux.
- Pas de pool asyncio : l'application est synchrone. Si on passe à `async`, il faudra `create_async_engine` + `AsyncSession`.
- En production, le pool par défaut de SQLAlchemy (5 connexions) peut saturer sous charge — configurer `pool_size` et `max_overflow` si nécessaire.
