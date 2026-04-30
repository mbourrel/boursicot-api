# api.py

## Rôle
Point d'entrée principal de l'application FastAPI : initialise l'app, configure le CORS, enregistre les routers et crée les tables en base au démarrage.

## Dépendances
- **Internes** : `database.engine`, `models`, `dependencies.get_current_user`, `routers.prices`, `routers.fundamentals`, `routers.search`, `routers.macro`, `routers.assets`, `routers.exchange_rates`
- **Externes** : `fastapi`, `fastapi.middleware.cors`, `python-dotenv`

## Fonctionnement
1. Charge les variables d'environnement via `load_dotenv()`.
2. Appelle `models.Base.metadata.create_all(bind=engine)` pour créer les tables manquantes à chaque démarrage (idempotent).
3. Instancie `FastAPI` avec `get_current_user` en dépendance globale — toutes les routes héritent de la vérification JWT/guest.
4. Configure le middleware CORS à partir de la variable d'environnement `ALLOWED_ORIGINS` (défaut : `localhost:5173` et `localhost:3000`). `allow_credentials=False` est volontaire (pas de cookies).
5. Monte les six routers sous leurs préfixes respectifs.
6. Expose un healthcheck `GET /` retournant `{"status": "online", ...}`.

## Utilisé par
- Serveur ASGI (Uvicorn/Gunicorn) via `uvicorn api:app`.
- GitHub Actions pour démarrer l'API en production.

## Points d'attention
- `get_current_user` est en dépendance **globale** : même le healthcheck `GET /` y passe, mais l'implémentation dégrade silencieusement en guest (ne bloque pas).
- Les origines CORS sont lues depuis l'env à l'import — un redémarrage est nécessaire pour les modifier.
- `create_all` ne fait pas de migrations : utiliser Alembic si le schéma évolue.
