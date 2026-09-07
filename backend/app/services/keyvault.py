"""Thin wrapper around Key Vault for the handful of secrets that genuinely
need to be secrets (rather than Bicep-provisioned config). Most values in
production actually arrive as Container Apps secrets that are themselves
Key Vault references resolved at deploy time -- this client covers the
runtime lookups (e.g. rotating keys, admin tooling) that need a live read.
"""
import logging
from functools import lru_cache

from azure.core.exceptions import ResourceNotFoundError
from azure.keyvault.secrets import SecretClient

from app.config import get_settings
from app.core.azure_credential import get_credential

logger = logging.getLogger(__name__)


@lru_cache
def _client() -> SecretClient | None:
    settings = get_settings()
    if not settings.azure_key_vault_url:
        return None
    return SecretClient(vault_url=settings.azure_key_vault_url, credential=get_credential())


def get_secret(name: str, default: str | None = None) -> str | None:
    client = _client()
    if client is None:
        return default
    try:
        return client.get_secret(name).value
    except ResourceNotFoundError:
        logger.warning("Key Vault secret '%s' not found, using default", name)
        return default
