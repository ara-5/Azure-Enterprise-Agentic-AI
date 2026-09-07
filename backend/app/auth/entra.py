"""Entra ID (Azure AD) bearer-token validation for the API.

The frontend acquires an access token via MSAL (see frontend/src/auth) for
this API's App Registration, and sends it as `Authorization: Bearer <token>`.
Here we validate the signature against Entra's published JWKS, and check
issuer/audience/expiry -- standard OAuth2/OIDC validation, no custom secret.

Set DISABLE_AUTH=true only for local dev; every deployed environment must
have it unset so this actually runs.
"""
import logging
import time
from dataclasses import dataclass, field

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

_jwks_cache: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


@dataclass
class CurrentUser:
    object_id: str
    display_name: str | None
    email: str | None
    roles: list[str] = field(default_factory=list)


async def _get_jwks(tenant_id: str) -> dict:
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS:
        return _jwks_cache

    url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache["keys"] = resp.json()["keys"]
        _jwks_cache["fetched_at"] = now
    return _jwks_cache


async def _validate_token(token: str) -> dict:
    settings = get_settings()
    jwks = await _get_jwks(settings.entra_tenant_id)

    unverified_header = jwt.get_unverified_header(token)
    key_data = next((k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")), None)
    if key_data is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unable to find matching signing key.")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    try:
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=settings.entra_api_audience,
            issuer=f"https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0",
        )
    except jwt.PyJWTError as exc:
        logger.warning("Token validation failed: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token.") from exc

    return claims


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    settings = get_settings()

    if settings.disable_auth:
        return CurrentUser(object_id="local-dev-user", display_name="Local Dev", email=None, roles=["admin"])

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token.")

    claims = await _validate_token(credentials.credentials)

    allowed_groups = {g for g in settings.entra_allowed_groups.split(",") if g}
    user_groups = set(claims.get("groups", []))
    if allowed_groups and not (allowed_groups & user_groups):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not a member of an authorized group.")

    return CurrentUser(
        object_id=claims["oid"],
        display_name=claims.get("name"),
        email=claims.get("preferred_username"),
        roles=claims.get("roles", []),
    )


def require_role(role: str):
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if role not in user.roles and "admin" not in user.roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role '{role}'.")
        return user

    return _check
