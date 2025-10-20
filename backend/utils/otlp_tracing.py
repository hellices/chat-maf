"""
OpenTelemetry configuration for FastAPI backend.
Exports traces, metrics, and logs to Aspire Dashboard via OTLP gRPC.
"""

import logging
import os
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes


def configure_otlp_grpc_tracing(
    endpoint: str = None,
    service_name: str = "backend-fastapi",
    service_version: str = "1.0.0",
) -> trace.Tracer:
    """
    Configure OpenTelemetry for traces, metrics, and logs.

    Args:
        endpoint: OTLP gRPC endpoint (e.g., "http://localhost:4317")
        service_name: Name of the service
        service_version: Version of the service

    Returns:
        Tracer instance
    """
    # Use environment variable if endpoint not provided
    if endpoint is None:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # Check if telemetry is enabled
    otlp_enabled = os.getenv("OTLP_ENABLED", "true").lower() == "true"
    if not otlp_enabled:
        print("OpenTelemetry is disabled (OTLP_ENABLED is not true)")
        return trace.get_tracer(__name__)

    # Create resource with service information
    resource = Resource(
        attributes={
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_VERSION: service_version,
        }
    )

    # Configure Tracing
    trace_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    trace_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(trace_provider)

    # Configure Metrics
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint))
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Configure Logging
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    log_exporter = OTLPLogExporter(endpoint=endpoint)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    handler.setFormatter(logging.Formatter("Python: %(message)s"))

    # Attach OTLP handler to root logger
    logging.getLogger().addHandler(handler)

    print(f"OpenTelemetry initialized successfully. Endpoint: {endpoint}")

    tracer = trace.get_tracer(__name__)
    return tracer
