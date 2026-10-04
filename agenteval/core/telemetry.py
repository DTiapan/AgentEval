"""Central OpenTelemetry distributed tracing engine (Slice 11, DR-040)."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import context, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Span, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from agenteval import __version__

_TRACER_PROVIDER: TracerProvider | None = None
_IN_MEMORY_EXPORTER: InMemorySpanExporter | None = None
_ACTIVE_EXPORTER_NAME: str = "none"
_TELEMETRY_CONFIGURED: bool = False


def _clean_attributes(attributes: dict[str, Any] | None) -> dict[str, Any]:
    """Ensure span attribute values conform to valid OpenTelemetry primitive types."""
    if not attributes:
        return {}
    cleaned: dict[str, Any] = {}
    for k, v in attributes.items():
        if v is None:
            continue
        if isinstance(v, (bool, str, int, float, bytes)):
            cleaned[k] = v
        elif isinstance(v, (list, tuple)):
            cleaned[k] = [str(item) if not isinstance(item, (bool, str, int, float)) else item for item in v]
        else:
            cleaned[k] = str(v)
    return cleaned


def configure_telemetry(
    *,
    service_name: str | None = None,
    exporter_type: str | None = None,
    otlp_endpoint: str | None = None,
    force: bool = False,
) -> TracerProvider:
    """
    Configure application-wide OpenTelemetry tracing.

    Args:
        service_name: Name of the service (default: OTEL_SERVICE_NAME or 'agenteval').
        exporter_type: 'otlp', 'console', 'memory', or 'none'.
        otlp_endpoint: URL endpoint for OTLP HTTP trace receiver.
        force: If True, reconfigures provider even if already configured.
    """
    global _TRACER_PROVIDER, _IN_MEMORY_EXPORTER, _ACTIVE_EXPORTER_NAME, _TELEMETRY_CONFIGURED
    if _TELEMETRY_CONFIGURED and not force and _TRACER_PROVIDER is not None:
        return _TRACER_PROVIDER

    effective_service = service_name or os.environ.get("OTEL_SERVICE_NAME", "agenteval")
    resource = Resource.create(
        {
            "service.name": effective_service,
            "service.version": __version__,
        }
    )

    provider = TracerProvider(resource=resource)

    # Determine exporter
    exp_choice = (
        exporter_type
        or os.environ.get("AGENTEVAL_OTEL_EXPORTER")
        or ("otlp" if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") else None)
    )
    if exp_choice is None:
        is_dev = os.environ.get("ENVIRONMENT", "development").lower() in ("development", "dev")
        otel_flag = os.environ.get("AGENTEVAL_OTEL_ENABLED", "").lower() in ("1", "true", "yes", "on")
        if otel_flag and is_dev:
            exp_choice = "console"
        else:
            exp_choice = "none"

    exp_choice = exp_choice.lower()
    _ACTIVE_EXPORTER_NAME = exp_choice
    _IN_MEMORY_EXPORTER = None

    exporter: SpanExporter | None = None
    if exp_choice == "memory":
        _IN_MEMORY_EXPORTER = InMemorySpanExporter()
        exporter = _IN_MEMORY_EXPORTER
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    elif exp_choice == "console":
        exporter = ConsoleSpanExporter()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    elif exp_choice == "otlp":
        endpoint = otlp_endpoint or os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
        )
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    try:
        trace.set_tracer_provider(provider)
    except Exception:
        pass
    trace._TRACER_PROVIDER = provider
    _TRACER_PROVIDER = provider
    _TELEMETRY_CONFIGURED = True
    return provider


def get_tracer(name: str = "agenteval") -> trace.Tracer:
    """Return an OpenTelemetry Tracer instance."""
    if _TRACER_PROVIDER is None:
        configure_telemetry()
    assert _TRACER_PROVIDER is not None
    return _TRACER_PROVIDER.get_tracer(name)


@contextmanager
def start_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "agenteval",
) -> Iterator[Span]:
    """Context manager to start and end an OpenTelemetry span."""
    tracer = get_tracer(tracer_name)
    attrs = _clean_attributes(attributes)
    with tracer.start_as_current_span(name, attributes=attrs) as span:
        try:
            yield span
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            raise


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """Inject W3C traceparent and tracestate into outbound HTTP headers."""
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier=headers)
    return headers


def extract_trace_context(headers: dict[str, str]) -> context.Context:
    """Extract OpenTelemetry context from inbound HTTP carrier headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(carrier=headers)


def get_current_trace_id() -> str | None:
    """Get active span's 32-character hex trace ID, or None if inactive."""
    current_span = trace.get_current_span()
    ctx = current_span.get_span_context()
    if ctx and ctx.is_valid and ctx.trace_id != 0:
        return f"{ctx.trace_id:032x}"
    return None


def get_current_span_id() -> str | None:
    """Get active span's 16-character hex span ID, or None if inactive."""
    current_span = trace.get_current_span()
    ctx = current_span.get_span_context()
    if ctx and ctx.is_valid and ctx.span_id != 0:
        return f"{ctx.span_id:016x}"
    return None


def get_in_memory_spans() -> list[ReadableSpan]:
    """Retrieve captured spans if configured with InMemorySpanExporter."""
    if _IN_MEMORY_EXPORTER is not None:
        return list(_IN_MEMORY_EXPORTER.get_finished_spans())
    return []


def reset_telemetry() -> None:
    """Reset global telemetry state (useful for isolated unit testing)."""
    global _TRACER_PROVIDER, _IN_MEMORY_EXPORTER, _ACTIVE_EXPORTER_NAME, _TELEMETRY_CONFIGURED
    if _TRACER_PROVIDER is not None:
        try:
            _TRACER_PROVIDER.shutdown()
        except Exception:
            pass
    _TRACER_PROVIDER = None
    _IN_MEMORY_EXPORTER = None
    _ACTIVE_EXPORTER_NAME = "none"
    _TELEMETRY_CONFIGURED = False
    trace._TRACER_PROVIDER = None
    if hasattr(trace, "_TRACER_PROVIDER_SET_ONCE"):
        trace._TRACER_PROVIDER_SET_ONCE._done = False


def telemetry_status() -> dict[str, Any]:
    """Return dictionary of current telemetry configuration."""
    return {
        "enabled": _ACTIVE_EXPORTER_NAME != "none",
        "exporter": _ACTIVE_EXPORTER_NAME,
        "service_name": os.environ.get("OTEL_SERVICE_NAME", "agenteval"),
    }


__all__ = [
    "Span",
    "StatusCode",
    "configure_telemetry",
    "extract_trace_context",
    "get_current_span_id",
    "get_current_trace_id",
    "get_in_memory_spans",
    "get_tracer",
    "inject_trace_context",
    "reset_telemetry",
    "start_span",
    "telemetry_status",
]
