import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, cost, documents, evaluation, health
from app.config import get_settings
from app.core.telemetry import setup_telemetry

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting Azure Enterprise Agentic AI Platform (env=%s)", settings.app_env)
    if settings.disable_auth:
        logger.warning("DISABLE_AUTH=true -- authentication is bypassed. Never set this outside local dev.")
    yield


app = FastAPI(
    title="Azure Enterprise Agentic AI Platform",
    description="Enterprise Agentic RAG platform on Azure OpenAI, Azure AI Search and Semantic Kernel.",
    version="1.0.0",
    lifespan=lifespan,
)

# Frontend origin is configured per-environment; wide open only in local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_local else [],
    allow_origin_regex=None if settings.is_local else r"https://.*\.azurecontainerapps\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_telemetry(app)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(cost.router)
app.include_router(evaluation.router)
