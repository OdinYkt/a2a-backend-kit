"""Optional observability setup helpers."""
# pyright: reportMissingImports=false

from __future__ import annotations

import base64
import logging
import os

try:
    from opentelemetry import trace
except ModuleNotFoundError:  # pragma: no cover - exercised by env without OTEL
    trace = None  # type: ignore[assignment]

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ModuleNotFoundError:  # pragma: no cover - exercised by env without OTEL
    OTLPSpanExporter = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    BatchSpanProcessor = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
_otel_configured = False


def setup_otel(*, service_name: str, service_version: str = "dev") -> bool:
    global _otel_configured
    if _otel_configured:
        return True

    host = os.getenv("LANGFUSE_HOST")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not (host and public_key and secret_key):
        logger.info("Langfuse env absent; OTEL disabled for %s", service_name)
        return False

    if not all((trace, OTLPSpanExporter, Resource, TracerProvider, BatchSpanProcessor)):
        logger.warning("OpenTelemetry packages missing; OTEL disabled for %s", service_name)
        return False

    assert trace is not None
    assert OTLPSpanExporter is not None
    assert Resource is not None
    assert TracerProvider is not None
    assert BatchSpanProcessor is not None

    endpoint = f"{host.rstrip('/')}/api/public/otel/v1/traces"
    token = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode(
        "ascii"
    )
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={"Authorization": f"Basic {token}"},
    )
    resource = Resource.create(
        {"service.name": service_name, "service.version": service_version}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _otel_configured = True
    return True
