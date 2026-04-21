import os
from typing import Optional
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_jwks_client = PyJWKClient(os.getenv("CLERK_JWKS_URL"), cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    # Pas de token → session guest autorisée
    if credentials is None:
        return {"sub": "guest", "is_guest": True}

    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Token expiré → on dégrade en guest plutôt que de bloquer (POC)
        return {"sub": "guest", "is_guest": True, "reason": "token_expired"}
    except Exception:
        # Token malformé ou JWKS indisponible → guest
        return {"sub": "guest", "is_guest": True, "reason": "token_invalid"}
