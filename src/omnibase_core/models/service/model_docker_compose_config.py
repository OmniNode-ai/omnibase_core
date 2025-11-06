"""Docker Compose Config Model.

Configuration constants for Docker Compose generation.
"""

# env-var-ok: constant definitions for Docker config, not environment variables


class ModelDockerComposeConfig:
    """Configuration constants for Docker Compose generation."""

    # Docker Compose version
    COMPOSE_VERSION = "3.8"

    # Infrastructure service images
    ZOOKEEPER_IMAGE = "confluentinc/cp-zookeeper:7.4.0"
    KAFKA_IMAGE = "confluentinc/cp-kafka:7.4.0"
    PROMETHEUS_IMAGE = "prom/prometheus:v2.45.0"
    GRAFANA_IMAGE = "grafana/grafana:10.0.0"
    REDIS_IMAGE = "redis:7.2-alpine"

    # Health check defaults
    DEFAULT_HEALTH_CHECK_INTERVAL = "10s"
    DEFAULT_HEALTH_CHECK_TIMEOUT = "5s"
    DEFAULT_HEALTH_CHECK_RETRIES = 3
    DEFAULT_HEALTH_CHECK_START_PERIOD = "30s"

    # Resource limits
    DEFAULT_MEMORY_LIMIT = "256M"
    DEFAULT_CPU_LIMIT = "0.5"

    # Network configuration
    DEFAULT_NETWORK_NAME = "onex-network"
    DEFAULT_BRIDGE_NAME = "onex-bridge"

    # Port assignments
    ZOOKEEPER_PORT = 2181
    KAFKA_PORT = 9092
    PROMETHEUS_PORT = 9090
    GRAFANA_PORT = 3000
    REDIS_PORT = 6379
