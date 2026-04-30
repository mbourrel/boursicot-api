# dependencies.py

## Rôle
Implémente la dépendance d'authentification FastAPI `get_current_user` basée sur les JWT Clerk, avec dégradation silencieuse en mode guest.

## Dépendances
- **Internes** : aucune
- **Externes** : `jwt` (PyJWT), `jwt.PyJWKClient`, `fastapi` (Depends, HTTPException, status), `fastapi.security.HTTPBearer`, `os`

## Fonctionnement
1. À l'import, instancie un `PyJWKClient` pointant sur `CLERK_JWKS_URL` (env) avec `cache_keys=True` — les clés publiques Clerk sont mises en cache pour éviter un appel réseau à chaque requête.
2. `get_current_user` est injecté comme dépendance globale dans `api.py`.
3. **Pas de token** : retourne `{"sub": "guest", "is_guest": True}` — les routes sans auth sont accessibles en mode lecture.
4. **Token valide** : décode le JWT avec l'algorithme RS256, `verify_aud=False` (Clerk n'impose pas d'audience fixe sur le plan gratuit), et retourne le payload complet.
5. **Token expiré** : dégrade en guest avec `reason: "token_expired"` — choix POC, à durcir en production.
6. **Toute autre erreur** (JWT malformé, JWKS indisponible) : dégrade en guest avec `reason: "token_invalid"`.

## Utilisé par
- `api.py` : injecté en `dependencies=[Depends(get_current_user)]` sur l'instance FastAPI — s'applique à tous les endpoints sans exception.

## Points d'attention
- La dégradation en guest sur token expiré est intentionnellement permissive (contexte POC). En production, retourner HTTP 401 pour les tokens expirés.
- `CLERK_JWKS_URL` doit être définie dans `.env` ; si elle manque, `PyJWKClient` lèvera une erreur à l'import (et non à la première requête).
- Le payload retourné n'est pas exploité par les routes actuelles (pas de RBAC) — le `sub` est disponible si besoin de personnalisation future.
- `auto_error=False` sur `HTTPBearer` permet de recevoir `None` quand l'en-tête `Authorization` est absent, ce qui déclenche la branche guest.
