# api.py

## Rôle
Point d'entrée principal de l'application FastAPI : initialise l'app, configure le CORS, enregistre les routers et crée les tables en base au démarrage.

## Dépendances
- **Internes** : `database.engine`, `models`, `dependencies.get_current_user`, `routers.*` (×6)
- **Externes** : `fastapi`, `fastapi.middleware.cors`, `slowapi`, `python-dotenv`

## Fonctionnement
1. Charge les variables d'environnement via `load_dotenv()`.
2. Appelle `models.Base.metadata.create_all(bind=engine)` pour créer les tables manquantes à chaque démarrage (idempotent).
3. Configure le **rate limiter** `slowapi` : 120 req/min par IP, monté sur `app.state.limiter` avec handler `RateLimitExceeded`.
4. Instancie `FastAPI` avec `get_current_user` en dépendance globale — toutes les routes héritent de la vérification JWT/guest.
5. Configure le middleware CORS : origines lues depuis `ALLOWED_ORIGINS` (env), méthodes limitées à `GET` et `OPTIONS` (API read-only), `allow_credentials=False`.
6. Monte les six routers sous leurs préfixes respectifs.
7. Expose un healthcheck `GET /` retournant `{"status": "online", ...}`.

## Utilisé par
- Serveur ASGI (Uvicorn/Gunicorn) via `uvicorn api:app`.
- GitHub Actions pour démarrer l'API en production.

## Points d'attention
- `get_current_user` est en dépendance **globale** : même le healthcheck `GET /` y passe, mais l'implémentation dégrade silencieusement en guest (ne bloque pas).
- Les origines CORS sont lues depuis l'env à l'import — un redémarrage est nécessaire pour les modifier.
- `allow_methods=["GET", "OPTIONS"]` uniquement — toute requête POST/PUT/DELETE sera rejetée par le CORS avant d'atteindre les routes.
- Le rate limiting `slowapi` utilise l'IP réelle via `get_remote_address`. Si l'API est derrière un proxy (Render), s'assurer que `X-Forwarded-For` est correctement transmis.
- `create_all` ne fait pas de migrations DDL sur les tables existantes : utiliser `seeds/migrate_db.py` pour les changements de schéma.
