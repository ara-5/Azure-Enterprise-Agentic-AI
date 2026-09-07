"""Application Insights wiring via Azure Monitor OpenTelemetry.

Instruments FastAPI, outbound HTTP (incl. Azure SDK calls) and logging in
one call. Every request gets a trace; cost_tracking.py and the RAG pipeline
emit custom events/spans on top of this so token usage, latency, retrieval
hit-rate and $ cost are all queryable in the same App Insights resource.
"""
import logging

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

from app.config import get_settings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("azure_enterprise_agentic_ai")


def setup_telemetry(app) -> None:
    settings = get_settings()
    if not settings.applicationinsights_connection_string:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set; telemetry disabled (local dev).")
        return

    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
        logger_name="app",
    )

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    logger.info("Application Insights telemetry configured.")


def emit_event(name: str, properties: dict) -> None:
    """Custom event for business metrics (cost, evaluation scores, retrieval quality)."""
    with tracer.start_as_current_span(name) as span:
        for key, value in properties.items():
            span.set_attribute(key, value)
