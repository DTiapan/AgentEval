"""Public alias for agenteval.core.telemetry (Slice 11, DR-040)."""

from agenteval.core.telemetry import (
    Span,
    StatusCode,
    configure_telemetry,
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    get_in_memory_spans,
    get_tracer,
    inject_trace_context,
    reset_telemetry,
    start_span,
    telemetry_status,
)

__all__ = [
    "StatusCode",
    "Span",
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
