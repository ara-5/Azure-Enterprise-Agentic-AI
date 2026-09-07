"""Single source of truth for how the platform authenticates to Azure.

In Azure Container Apps this resolves to the user-assigned Managed Identity
(no secrets, no connection strings). Locally it falls back to whatever the
developer is signed in as (az CLI, VS Code, environment vars) via
DefaultAzureCredential's normal chain -- nothing here is Azure-specific
per environment, which is the point: the same code path runs in dev and
in production.
"""
from functools import lru_cache

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

from app.config import get_settings

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


@lru_cache
def get_credential():
    settings = get_settings()
    client_id = getattr(settings, "managed_identity_client_id", None)
    if not settings.is_local and client_id:
        # User-assigned identity: pin the client id explicitly so the
        # container never accidentally picks up a different identity.
        return ManagedIdentityCredential(client_id=client_id)
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)
