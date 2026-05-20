import datetime
import logging
import os
import time
import uuid
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from pythonjsonlogger import jsonlogger

from .handler import OpenSearchHandler
from .middleware import get_span_id, get_trace_id


class _JsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, service_name: str, environment: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service_name = service_name
        self._environment = environment

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)

        log_record["@timestamp"] = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3] + "Z"
        log_record["service"] = self._service_name
        log_record["env"] = self._environment
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["tie_breaker_id"] = str(uuid.uuid4())
        log_record["log_sequence"] = time.monotonic_ns()

        trace_id = get_trace_id()
        span_id = get_span_id()
        if trace_id:
            log_record["trace_id"] = trace_id
        if span_id:
            log_record["span_id"] = span_id

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            log_record["exception"] = record.exc_text

        for field in ("color_message", "taskName", "exc_info", "exc_text"):
            log_record.pop(field, None)


def setup_logging() -> None:
    """
    Initialise OpenTelemetry and the Python logging system.

      OPENSEARCH_HOST         Full URL of the OpenSearch node
      OPENSEARCH_USER         Basic auth username  (default: admin)
      OPENSEARCH_PASSWORD     Basic auth password
      OPENSEARCH_INDEX        Target index name    (default: wisepay-banking)
      SERVICE_NAME            Emitted in every log record (default: wisepay-banking)
      APP_ENV                 Environment name     (default: production)
      LOG_LEVEL               Root log level       (default: DEBUG)
      LOG_BATCH_SIZE          Records per bulk flush (default: 50)
      LOG_FLUSH_INTERVAL      Seconds between flushes (default: 1.0)
      LOG_MAX_QUEUE_SIZE      In-memory queue cap  (default: 10000)
    """
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    opensearch_host: Optional[str] = os.getenv("OPENSEARCH_HOST")
    opensearch_user: str = os.getenv("OPENSEARCH_USER", "admin")
    opensearch_password: Optional[str] = os.getenv("OPENSEARCH_PASSWORD")
    opensearch_index: str = os.getenv("OPENSEARCH_INDEX", "wisepay-banking")
    service_name: str = os.getenv("SERVICE_NAME", "wisepay-banking")
    environment: str = os.getenv("APP_ENV", "production")
    log_level_str: str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    batch_size: int = int(os.getenv("LOG_BATCH_SIZE", "50"))
    flush_interval: float = float(os.getenv("LOG_FLUSH_INTERVAL", "1.0"))
    max_queue_size: int = int(os.getenv("LOG_MAX_QUEUE_SIZE", "10000"))

    log_level = getattr(logging, log_level_str, logging.DEBUG)
    formatter = _JsonFormatter(service_name, environment)

    if opensearch_host and opensearch_password:
        handler: logging.Handler = OpenSearchHandler(
            host=opensearch_host,
            index=opensearch_index,
            user=opensearch_user,
            password=opensearch_password,
            batch_size=batch_size,
            flush_interval=flush_interval,
            max_queue_size=max_queue_size,
        )
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    for noisy in ("httpcore", "httpx", "urllib3", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
