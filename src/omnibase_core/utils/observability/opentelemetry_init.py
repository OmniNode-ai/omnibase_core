#!/usr/bin/env python3
"""
ONEX OpenTelemetry Initialization Module

Provides standardized OpenTelemetry setup for all ONEX services with:
- W3C trace context propagation
- Intelligent sampling for <5% overhead
- Security-aware instrumentation
- Integration with existing Prometheus monitoring
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import Resource, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pydantic import BaseModel, Field

# Exporters (with optional imports)
try:
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
except ImportError:
    OTLPSpanExporter = None
    OTLPMetricExporter = None

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
except ImportError:
    JaegerExporter = None

try:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
except ImportError:
    PrometheusMetricReader = None

# Instrumentation (with graceful import handling)
instrumentor_imports = {}

# Define instrumentors to try importing
instrumentor_modules = {
    "fastapi": "opentelemetry.instrumentation.fastapi.FastAPIInstrumentor",
    "asyncpg": "opentelemetry.instrumentation.asyncpg.AsyncPGInstrumentor",
    "psycopg2": "opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor",
    "sqlalchemy": "opentelemetry.instrumentation.sqlalchemy.SQLAlchemyInstrumentor",
    "aiohttp_client": "opentelemetry.instrumentation.aiohttp_client.AioHttpClientInstrumentor",
    "httpx": "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor",
    "requests": "opentelemetry.instrumentation.requests.RequestsInstrumentor",
    "asyncio": "opentelemetry.instrumentation.asyncio.AsyncioInstrumentor",
    "logging": "opentelemetry.instrumentation.logging.LoggingInstrumentor",
}

# Initialize logger first
logger = logging.getLogger(__name__)

# Import available instrumentors
for name, module_path in instrumentor_modules.items():
    try:
        module_name, class_name = module_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        instrumentor_imports[name] = getattr(module, class_name)
    except ImportError:
        logger.debug(f"Instrumentor {name} not available: {module_path}")
        instrumentor_imports[name] = None

# Resource detection (optional)
try:
    from opentelemetry.resourcedetector.docker import DockerResourceDetector
except ImportError:
    DockerResourceDetector = None

try:
    from opentelemetry.resourcedetector.container import ContainerResourceDetector
except ImportError:
    ContainerResourceDetector = None

# Sampling
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
from opentelemetry.semconv.resource import ResourceAttributes


class ModelOpenTelemetryInitInfo(BaseModel):
    """Information about OpenTelemetry initialization."""

    service_name: str = Field(..., description="Name of the initialized service")
    service_version: str = Field(..., description="Version of the initialized service")
    service_namespace: str = Field(
        ...,
        description="Namespace of the initialized service",
    )
    deployment_environment: str = Field(..., description="Deployment environment")
    sampling_rate: float = Field(..., description="Configured sampling rate")
    collector_endpoint: str = Field(..., description="Collector endpoint URL")
    tracer_provider: TracerProvider = Field(
        ...,
        description="Initialized tracer provider",
    )
    meter_provider: MeterProvider = Field(..., description="Initialized meter provider")
    instrumentors_enabled: list[str] = Field(
        default_factory=list,
        description="List of enabled instrumentors",
    )
    resource_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Resource attributes",
    )

    class Config:
        arbitrary_types_allowed = True  # Allow OpenTelemetry types


class ONEXOpenTelemetryConfig:
    """Configuration class for ONEX OpenTelemetry setup."""

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        service_namespace: str = "onex",
        deployment_environment: str | None = None,
        collector_endpoint: str | None = None,
        sampling_rate: float | None = None,
        enable_console_export: bool = False,
        enable_prometheus_export: bool = True,
        enable_jaeger_export: bool = True,
        custom_resource_attributes: dict[str, str] | None = None,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.service_namespace = service_namespace
        self.deployment_environment = deployment_environment or os.getenv(
            "ONEX_ENVIRONMENT",
            "development",
        )

        # Collector configuration
        self.collector_endpoint = collector_endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://onex-otel-collector:4317",
        )

        # Performance configuration
        self.sampling_rate = (
            sampling_rate
            if sampling_rate is not None
            else self._get_default_sampling_rate()
        )

        # Export configuration
        self.enable_console_export = enable_console_export or (
            self.deployment_environment == "development"
            and os.getenv("OTEL_ENABLE_CONSOLE_EXPORT", "false").lower() == "true"
        )
        self.enable_prometheus_export = enable_prometheus_export
        self.enable_jaeger_export = enable_jaeger_export

        # Custom attributes
        self.custom_resource_attributes = custom_resource_attributes or {}

    def _get_default_sampling_rate(self) -> float:
        """Get default sampling rate based on service priority and environment."""
        env = self.deployment_environment.lower()

        # Higher sampling for development, lower for production
        if env in ["development", "dev", "local"]:
            base_rate = 0.1  # 10% for development
        elif env in ["staging", "test"]:
            base_rate = 0.05  # 5% for staging
        else:  # production
            base_rate = 0.02  # 2% for production

        # Adjust based on service priority
        high_priority_services = [
            "onex-event-bus",
            "onex-generation-hub",
            "onex-task-queue",
        ]
        if self.service_name in high_priority_services:
            base_rate *= 2  # Double sampling for critical services

        return min(base_rate, 0.1)  # Cap at 10% to ensure <5% overhead


def create_resource(config: ONEXOpenTelemetryConfig) -> Resource:
    """Create OpenTelemetry resource with comprehensive service identification."""

    # Base resource attributes
    resource_attributes = {
        ResourceAttributes.SERVICE_NAME: config.service_name,
        ResourceAttributes.SERVICE_VERSION: config.service_version,
        ResourceAttributes.SERVICE_NAMESPACE: config.service_namespace,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: config.deployment_environment,
        "onex.instrumented": "true",
        "onex.instrumentation_version": "1.0.0",
    }

    # Add container/Docker attributes
    if DockerResourceDetector:
        try:
            docker_detector = DockerResourceDetector()
            docker_resource = docker_detector.detect()
            resource_attributes.update(docker_resource.attributes)
        except Exception as e:
            logger.debug(f"Docker resource detection failed: {e}")

    if ContainerResourceDetector:
        try:
            container_detector = ContainerResourceDetector()
            container_resource = container_detector.detect()
            resource_attributes.update(container_resource.attributes)
        except Exception as e:
            logger.debug(f"Container resource detection failed: {e}")

    # Add custom attributes
    resource_attributes.update(config.custom_resource_attributes)

    return Resource.create(resource_attributes)


def setup_tracing(
    config: ONEXOpenTelemetryConfig,
    resource: Resource,
) -> TracerProvider:
    """Setup distributed tracing with intelligent sampling."""

    # Create tracer provider
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(root=TraceIdRatioBased(config.sampling_rate)),
    )

    # OTLP exporter to collector
    if config.collector_endpoint and OTLPSpanExporter:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=config.collector_endpoint,
                insecure=True,
                timeout=10,
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    otlp_exporter,
                    max_queue_size=2048,
                    max_export_batch_size=512,
                    export_timeout_millis=5000,
                    schedule_delay_millis=1000,
                ),
            )
            logger.info(
                f"✅ OTLP trace exporter configured: {config.collector_endpoint}",
            )
        except Exception as e:
            logger.warning(f"⚠️ OTLP trace exporter setup failed: {e}")
    elif config.collector_endpoint and not OTLPSpanExporter:
        logger.warning(
            "⚠️ OTLP trace exporter not available - install opentelemetry-exporter-otlp",
        )

    # Jaeger exporter (fallback)
    if config.enable_jaeger_export and JaegerExporter:
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name="onex-jaeger",
                agent_port=6831,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info("✅ Jaeger trace exporter configured")
        except Exception as e:
            logger.warning(f"⚠️ Jaeger trace exporter setup failed: {e}")
    elif config.enable_jaeger_export and not JaegerExporter:
        logger.warning(
            "⚠️ Jaeger trace exporter not available - install opentelemetry-exporter-jaeger",
        )

    # Console exporter for development
    if config.enable_console_export:
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("✅ Console trace exporter enabled")

    return tracer_provider


def setup_metrics(config: ONEXOpenTelemetryConfig, resource: Resource) -> MeterProvider:
    """Setup metrics collection and export."""

    readers = []

    # OTLP metrics exporter
    if config.collector_endpoint and OTLPMetricExporter:
        try:
            otlp_metric_exporter = OTLPMetricExporter(
                endpoint=config.collector_endpoint,
                insecure=True,
                timeout=10,
            )
            readers.append(
                PeriodicExportingMetricReader(
                    exporter=otlp_metric_exporter,
                    export_interval_millis=10000,  # 10 seconds
                ),
            )
            logger.info("✅ OTLP metric exporter configured")
        except Exception as e:
            logger.warning(f"⚠️ OTLP metric exporter setup failed: {e}")
    elif config.collector_endpoint and not OTLPMetricExporter:
        logger.warning(
            "⚠️ OTLP metric exporter not available - install opentelemetry-exporter-otlp",
        )

    # Prometheus metrics reader
    if config.enable_prometheus_export and PrometheusMetricReader:
        try:
            prometheus_reader = PrometheusMetricReader()
            readers.append(prometheus_reader)
            logger.info("✅ Prometheus metric reader configured")
        except Exception as e:
            logger.warning(f"⚠️ Prometheus metric reader setup failed: {e}")
    elif config.enable_prometheus_export and not PrometheusMetricReader:
        logger.warning(
            "⚠️ Prometheus metric reader not available - install opentelemetry-exporter-prometheus",
        )

    # Console metrics for development
    if config.enable_console_export:
        console_metric_exporter = ConsoleMetricExporter()
        readers.append(
            PeriodicExportingMetricReader(
                exporter=console_metric_exporter,
                export_interval_millis=30000,  # 30 seconds
            ),
        )
        logger.info("✅ Console metric exporter enabled")

    # Create meter provider
    return MeterProvider(resource=resource, metric_readers=readers)


def setup_auto_instrumentation(config: ONEXOpenTelemetryConfig):
    """Setup automatic instrumentation for common libraries."""

    instrumentors = []

    # Database instrumentation
    if instrumentor_imports.get("asyncpg"):
        try:
            instrumentor_imports["asyncpg"]().instrument()
            instrumentors.append("asyncpg")
        except Exception as e:
            logger.debug(f"AsyncPG instrumentation failed: {e}")

    if instrumentor_imports.get("psycopg2"):
        try:
            instrumentor_imports["psycopg2"]().instrument()
            instrumentors.append("psycopg2")
        except Exception as e:
            logger.debug(f"Psycopg2 instrumentation failed: {e}")

    if instrumentor_imports.get("sqlalchemy"):
        try:
            instrumentor_imports["sqlalchemy"]().instrument()
            instrumentors.append("sqlalchemy")
        except Exception as e:
            logger.debug(f"SQLAlchemy instrumentation failed: {e}")

    # HTTP instrumentation
    if instrumentor_imports.get("aiohttp_client"):
        try:
            instrumentor_imports["aiohttp_client"]().instrument()
            instrumentors.append("aiohttp-client")
        except Exception as e:
            logger.debug(f"AioHTTP client instrumentation failed: {e}")

    if instrumentor_imports.get("httpx"):
        try:
            instrumentor_imports["httpx"]().instrument()
            instrumentors.append("httpx")
        except Exception as e:
            logger.debug(f"HTTPX instrumentation failed: {e}")

    if instrumentor_imports.get("requests"):
        try:
            instrumentor_imports["requests"]().instrument()
            instrumentors.append("requests")
        except Exception as e:
            logger.debug(f"Requests instrumentation failed: {e}")

    # Messaging instrumentation
    # Kafka instrumentation removed - belongs in infrastructure

    # Async instrumentation
    if instrumentor_imports.get("asyncio"):
        try:
            instrumentor_imports["asyncio"]().instrument()
            instrumentors.append("asyncio")
        except Exception as e:
            logger.debug(f"Asyncio instrumentation failed: {e}")

    # Logging instrumentation
    if instrumentor_imports.get("logging"):
        try:
            instrumentor_imports["logging"]().instrument(set_logging_format=True)
            instrumentors.append("logging")
        except Exception as e:
            logger.debug(f"Logging instrumentation failed: {e}")

    if instrumentors:
        logger.info(f"✅ Auto-instrumentation enabled: {', '.join(instrumentors)}")
    else:
        logger.warning(
            "⚠️ No instrumentors available - install OpenTelemetry instrumentation packages",
        )

    return instrumentors


def initialize_opentelemetry(
    service_name: str,
    service_version: str = "1.0.0",
    **kwargs,
) -> ModelOpenTelemetryInitInfo:
    """
    Initialize OpenTelemetry for an ONEX service.

    Args:
        service_name: Name of the service (e.g., "onex-event-bus")
        service_version: Version of the service
        **kwargs: Additional configuration options

    Returns:
        Dictionary with initialized providers and configuration info
    """

    logger.info(f"🚀 Initializing OpenTelemetry for {service_name}")

    # Create configuration
    config = ONEXOpenTelemetryConfig(
        service_name=service_name,
        service_version=service_version,
        **kwargs,
    )

    # Create resource
    resource = create_resource(config)

    # Setup tracing
    tracer_provider = setup_tracing(config, resource)
    trace.set_tracer_provider(tracer_provider)

    # Setup metrics
    meter_provider = setup_metrics(config, resource)
    metrics.set_meter_provider(meter_provider)

    # Setup auto-instrumentation
    instrumentors = setup_auto_instrumentation(config)

    # Return initialization info
    resource_attrs_dict = {k: str(v) for k, v in resource.attributes.items()}

    initialization_info = ModelOpenTelemetryInitInfo(
        service_name=config.service_name,
        service_version=config.service_version,
        service_namespace=config.service_namespace,
        deployment_environment=config.deployment_environment,
        sampling_rate=config.sampling_rate,
        collector_endpoint=config.collector_endpoint,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        instrumentors_enabled=instrumentors,
        resource_attributes=resource_attrs_dict,
    )

    logger.info(f"✅ OpenTelemetry initialized for {service_name}")
    logger.info(f"   📊 Sampling rate: {config.sampling_rate:.1%}")
    logger.info(f"   🔗 Collector: {config.collector_endpoint}")
    logger.info(f"   🛠️ Instrumentors: {len(instrumentors)} enabled")

    return initialization_info


def get_tracer(name: str, version: str = "1.0.0"):
    """Get a tracer instance for the given name and version."""
    return trace.get_tracer(name, version)


def get_meter(name: str, version: str = "1.0.0"):
    """Get a meter instance for the given name and version."""
    return metrics.get_meter(name, version)


# Environment-based initialization for containerized services
if __name__ == "__main__":
    # Initialize from environment variables (useful for auto-instrumentation)
    service_name = os.getenv("OTEL_SERVICE_NAME", "onex-service")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")

    init_info = initialize_opentelemetry(
        service_name=service_name,
        service_version=service_version,
    )
