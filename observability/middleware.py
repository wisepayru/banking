import contextvars
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Per-request context vars — readable from any logger on the same async task
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
_span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)


def get_trace_id() -> Optional[str]:
    return _trace_id_var.get()


def get_span_id() -> Optional[str]:
    return _span_id_var.get()


class TraceMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that:
      - Extracts an existing W3C traceparent from the incoming request, or
        starts a fresh OTEL span if none is present.
      - Stores trace_id and span_id in contextvars so they are automatically
        included in every log record for the duration of the request.
      - Injects a traceparent response header so callers can correlate.
    """

    _propagator = TraceContextTextMapPropagator()

    async def dispatch(self, request: Request, call_next) -> Response:
        tracer = trace.get_tracer(__name__)
        ctx = self._propagator.extract(dict(request.headers))

        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}", context=ctx
        ) as span:
            span_ctx = span.get_span_context()
            trace_id = format(span_ctx.trace_id, "032x")
            span_id = format(span_ctx.span_id, "016x")

            _trace_id_var.set(trace_id)
            _span_id_var.set(span_id)

            response = await call_next(request)
            response.headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
            return response


def build_outgoing_headers() -> dict:
    """
    Return headers to inject on every outgoing HTTP call so downstream
    services can correlate their logs with ours via X-Request-Id and
    the W3C traceparent.
    """
    trace_id = get_trace_id()
    span_id = get_span_id()
    headers = {}
    if trace_id:
        headers["X-Request-Id"] = trace_id
    if trace_id and span_id:
        headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
    return headers
