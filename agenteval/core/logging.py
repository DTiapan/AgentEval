"""Central structured logging engine powered by structlog (Slice 8, DR-037)."""

import logging
import os
import sys
from typing import Any, cast

import structlog
from structlog.types import EventDict, Processor


def add_gcp_severity(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Map log level to Google Cloud Logging native severity field."""
    level = str(event_dict.get("level", method_name)).upper()
    event_dict["severity"] = "WARNING" if level == "WARN" else level
    return event_dict


def add_otel_trace_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Inject active OpenTelemetry trace_id and span_id into structlog event."""
    try:
        from agenteval.core.telemetry import get_current_span_id, get_current_trace_id

        trace_id = get_current_trace_id()
        if trace_id:
            event_dict["trace_id"] = trace_id
        span_id = get_current_span_id()
        if span_id:
            event_dict["span_id"] = span_id
    except Exception:
        pass
    return event_dict


_LOGGING_CONFIGURED = False


def configure_logging(
    *,
    log_level: str | None = None,
    log_format: str | None = None,
    force: bool = False,
) -> None:
    """
    Configure application-wide structured logging.

    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: AGENTEVAL_LOG_LEVEL or INFO)
        log_format: 'json' or 'console' (default: AGENTEVAL_LOG_FORMAT or auto-detected)
        force: If True, reconfigures logging even if already configured.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED and not force:
        return

    effective_level_str = (log_level or os.environ.get("AGENTEVAL_LOG_LEVEL") or "INFO").upper()
    level_num = getattr(logging, effective_level_str, logging.INFO)

    fmt = log_format or os.environ.get("AGENTEVAL_LOG_FORMAT")
    if fmt is None:
        is_prod = os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod")
        fmt = "json" if (is_prod or not sys.stderr.isatty()) else "console"
    fmt = fmt.lower()

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        add_gcp_severity,
        add_otel_trace_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: Processor
    if fmt == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level_num,
        force=True,
    )

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    for handler in logging.root.handlers:
        handler.setFormatter(formatter)

    _LOGGING_CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog BoundLogger."""
    if not _LOGGING_CONFIGURED:
        configure_logging()
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def bind_contextvars(**kwargs: Any) -> None:
    """Bind key-value pairs into the current async/thread context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """Clear all context variables for the current async/thread context."""
    structlog.contextvars.clear_contextvars()


def unbind_contextvars(*keys: str) -> None:
    """Unbind specific keys from the current context."""
    structlog.contextvars.unbind_contextvars(*keys)
