"""Centralized application settings.

Values are loaded from environment variables (populated locally via .env,
and in Azure via Container Apps secrets that reference Key Vault, injected
through the platform's user-assigned Managed Identity -- see
infra/modules/containerapps.bicep). No secret ever needs to be typed into
the container image or the app's source.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved relative to this file (backend/app/config.py -> repo root), not
# the process's working directory -- otherwise `uvicorn app.main:app` run
# from inside backend/ silently misses the .env sitting at the repo root
# (the convention docker-compose.yml and the README both use), and every
# setting quietly falls back to its default.
_REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(_REPO_ROOT_ENV, ".env"), extra="ignore")

    app_env: str = Field(default="local")
    log_level: str = Field(default="INFO")
    disable_auth: bool = Field(default=False)
    managed_identity_client_id: str | None = None
    # When true, chat/agent routes are served by app/rag/demo.py and
    # app/agents/demo_orchestrator.py -- a zero-Azure-cost, keyword-retrieval
    # stand-in over the bundled sample docs, so the project runs end-to-end
    # with no Azure subscription at all. Defaults on so a fresh clone works
    # immediately; set to false (and configure the AZURE_* values below) to
    # run against real Azure OpenAI / AI Search.
    demo_mode: bool = Field(default=True)

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_api_key: str | None = None

    # Azure AI Search
    azure_search_endpoint: str = ""
    azure_search_index_name: str = "enterprise-rag-index"
    azure_search_api_key: str | None = None

    # Azure Blob Storage
    azure_storage_account_url: str = ""
    azure_storage_container_documents: str = "documents"
    azure_storage_container_cost: str = "cost-exports"
    azure_storage_connection_string: str | None = None

    # Entra ID
    entra_tenant_id: str = ""
    entra_api_client_id: str = ""
    entra_api_audience: str = ""
    entra_allowed_groups: str = ""

    # Key Vault
    azure_key_vault_url: str = ""

    # Application Insights
    applicationinsights_connection_string: str | None = None

    # Cost tracking
    cost_input_per_1k_tokens: float = 0.0025
    cost_output_per_1k_tokens: float = 0.01
    cost_embedding_per_1k_tokens: float = 0.00013
    cost_budget_monthly_usd: float = 200.0
    cost_alert_webhook_url: str | None = None

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
