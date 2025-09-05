#!/usr/bin/env python3
"""
Examples demonstrating environment-based configuration management.

Shows how to create and use environment-configurable models for various
ONEX components with validation, type conversion, and hierarchical overrides.
"""

import asyncio
import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator

from omnibase_core.core.configuration import (
    ModelEnvironmentConfig,
    config_registry,
    is_production_environment,
    register_config,
)
from omnibase_core.core.resilience import (
    CircuitBreakerFactory,
    ExternalDependencyCircuitBreaker,
    ModelCircuitBreakerConfig,
)


class ModelDatabaseConfig(ModelEnvironmentConfig):
    """Database configuration with environment variable support."""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="omnibase", description="Database name")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")

    # Connection pool settings
    min_pool_size: int = Field(default=5, description="Minimum connection pool size")
    max_pool_size: int = Field(default=20, description="Maximum connection pool size")

    # Security settings
    use_ssl: bool = Field(default=True, description="Use SSL connection")
    ssl_cert_path: Optional[str] = Field(
        default=None, description="SSL certificate path"
    )

    @field_validator("password")
    @classmethod
    def validate_password_in_production(cls, v: str) -> str:
        if is_production_environment() and not v:
            raise ValueError("Database password is required in production")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    def get_connection_string(self, mask_password: bool = True) -> str:
        """Get database connection string."""
        password = "***" if mask_password and self.password else self.password
        return f"postgresql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"


class ModelAPIServiceConfig(ModelEnvironmentConfig):
    """API service configuration."""

    service_name: str = Field(..., description="Service name")
    base_url: str = Field(..., description="Base API URL")

    # Authentication
    api_key: Optional[str] = Field(default=None, description="API key")
    auth_header: str = Field(default="Authorization", description="Auth header name")

    # Request settings
    timeout_seconds: float = Field(default=30.0, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(default=1.0, description="Delay between retries")

    # Rate limiting
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window: int = Field(
        default=60, description="Rate limit window in seconds"
    )

    # Feature flags
    enable_caching: bool = Field(default=True, description="Enable response caching")
    enable_circuit_breaker: bool = Field(
        default=True, description="Enable circuit breaker"
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")


class ModelMonitoringConfig(ModelEnvironmentConfig):
    """Monitoring and observability configuration."""

    # Metrics
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics endpoint port")
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json|text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Health checks
    health_check_interval: int = Field(default=30, description="Health check interval")
    health_check_timeout: int = Field(default=5, description="Health check timeout")

    # Tracing
    enable_tracing: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    tracing_service_name: Optional[str] = Field(
        default=None, description="Tracing service name"
    )
    jaeger_endpoint: Optional[str] = Field(
        default=None, description="Jaeger endpoint URL"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class ModelApplicationConfig(ModelEnvironmentConfig):
    """Complete application configuration."""

    # Core settings
    app_name: str = Field(..., description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Database
    database: ModelDatabaseConfig = Field(default_factory=ModelDatabaseConfig)

    # Monitoring
    monitoring: ModelMonitoringConfig = Field(default_factory=ModelMonitoringConfig)

    # External services
    external_services: List[str] = Field(
        default_factory=list, description="List of external service names"
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1024 <= v <= 65535:
            raise ValueError("Port must be between 1024 and 65535")
        return v


# Example usage functions


def example_basic_configuration():
    """Example: Basic configuration from environment."""
    print("\n=== Basic Configuration Example ===")

    # Set some environment variables for demonstration
    os.environ["DB_HOST"] = "localhost"
    os.environ["DB_PORT"] = "5432"
    os.environ["DB_DATABASE"] = "myapp"
    os.environ["DB_USERNAME"] = "user"
    os.environ["DB_PASSWORD"] = "secret123"

    # Create configuration from environment
    db_config = ModelDatabaseConfig.from_environment(prefix="DB")

    print(f"Database Config: {db_config.get_connection_string()}")
    print(f"Pool size: {db_config.min_pool_size} - {db_config.max_pool_size}")
    print(f"SSL enabled: {db_config.use_ssl}")


def example_api_service_configuration():
    """Example: API service configuration."""
    print("\n=== API Service Configuration Example ===")

    # Set environment variables
    os.environ["API_SERVICE_NAME"] = "payment-service"
    os.environ["API_BASE_URL"] = "https://api.payment-provider.com"
    os.environ["API_API_KEY"] = "sk_live_abc123"
    os.environ["API_TIMEOUT_SECONDS"] = "10.0"
    os.environ["API_MAX_RETRIES"] = "5"
    os.environ["API_ENABLE_CIRCUIT_BREAKER"] = "true"

    # Create configuration
    api_config = ModelAPIServiceConfig.from_environment(
        prefix="API",
        service_name="payment-service",  # Override via parameter
        base_url="https://api.payment-provider.com",
    )

    print(f"Service: {api_config.service_name}")
    print(f"URL: {api_config.base_url}")
    print(f"Timeout: {api_config.timeout_seconds}s")
    print(f"Retries: {api_config.max_retries}")
    print(f"Circuit breaker: {api_config.enable_circuit_breaker}")


def example_nested_configuration():
    """Example: Nested configuration with sub-models."""
    print("\n=== Nested Configuration Example ===")

    # Set environment variables for different components
    os.environ["APP_NAME"] = "omnibase-service"
    os.environ["APP_ENVIRONMENT"] = "production"
    os.environ["APP_HOST"] = "0.0.0.0"
    os.environ["APP_PORT"] = "8080"

    # Database settings
    os.environ["APP_DATABASE_HOST"] = "db.production.com"
    os.environ["APP_DATABASE_PORT"] = "5432"
    os.environ["APP_DATABASE_PASSWORD"] = "prod_secret"

    # Monitoring settings
    os.environ["APP_MONITORING_ENABLE_METRICS"] = "true"
    os.environ["APP_MONITORING_LOG_LEVEL"] = "WARNING"
    os.environ["APP_MONITORING_ENABLE_TRACING"] = "true"

    # Create nested configuration
    app_config = ModelApplicationConfig.from_environment(prefix="APP")

    print(f"App: {app_config.app_name} v{app_config.app_version}")
    print(f"Environment: {app_config.environment}")
    print(f"Server: {app_config.host}:{app_config.port}")
    print(f"Database: {app_config.database.get_connection_string()}")
    print(f"Metrics: {app_config.monitoring.enable_metrics}")
    print(f"Log level: {app_config.monitoring.log_level}")


def example_configuration_registry():
    """Example: Using configuration registry."""
    print("\n=== Configuration Registry Example ===")

    # Register configurations in registry
    db_config = register_config("database", ModelDatabaseConfig, prefix="DB")

    monitoring_config = register_config(
        "monitoring", ModelMonitoringConfig, prefix="MONITORING"
    )

    # Retrieve from registry
    retrieved_db = config_registry.get("database")
    retrieved_monitoring = config_registry.get("monitoring")

    print(f"Registered configs: {config_registry.list_configs()}")
    print(f"Database from registry: {retrieved_db.host if retrieved_db else 'None'}")
    print(
        f"Monitoring from registry: {retrieved_monitoring.log_level if retrieved_monitoring else 'None'}"
    )

    # Reload all configurations
    print("Reloading all configurations...")
    config_registry.reload_all()


def example_configuration_documentation():
    """Example: Generate configuration documentation."""
    print("\n=== Configuration Documentation Example ===")

    # Get documentation for all environment variables
    docs = ModelApplicationConfig.get_env_documentation()

    print("Environment Variables Documentation:")
    print("-" * 50)

    for doc in docs[:5]:  # Show first 5 for brevity
        print(f"Field: {doc['field']}")
        print(f"Environment Keys: {doc['env_keys']}")
        print(f"Description: {doc['description']}")
        print(f"Type: {doc['type']}")
        print(f"Required: {doc['required']}")
        print(f"Default: {doc['default']}")
        print()


async def example_with_circuit_breaker():
    """Example: Configuration with circuit breaker integration."""
    print("\n=== Configuration + Circuit Breaker Example ===")

    # Configure API service
    os.environ["PAYMENT_API_BASE_URL"] = "https://api.stripe.com"
    os.environ["PAYMENT_API_TIMEOUT_SECONDS"] = "5.0"
    os.environ["PAYMENT_API_ENABLE_CIRCUIT_BREAKER"] = "true"

    api_config = ModelAPIServiceConfig.from_environment(
        prefix="PAYMENT_API", service_name="stripe-api"
    )

    # Create circuit breaker if enabled
    circuit_breaker = None
    if api_config.enable_circuit_breaker:
        # Create circuit breaker with service-specific environment config
        circuit_breaker = CircuitBreakerFactory.create_from_environment(
            api_config.service_name,
            prefix=f"CIRCUIT_BREAKER_{api_config.service_name.upper()}",
        )

    print(f"API Config: {api_config.service_name} -> {api_config.base_url}")
    print(f"Circuit breaker enabled: {api_config.enable_circuit_breaker}")

    if circuit_breaker:
        print(f"Circuit breaker state: {circuit_breaker.get_state()}")

        # Example API call through circuit breaker
        async def mock_api_call():
            """Mock API call that might fail."""
            import random

            if random.random() < 0.3:  # 30% failure rate
                raise Exception("API temporarily unavailable")
            return {"status": "success", "data": "payment processed"}

        try:
            result = await circuit_breaker.call(mock_api_call)
            print(f"API call result: {result}")
        except Exception as e:
            print(f"API call failed: {e}")

        # Show metrics
        metrics = circuit_breaker.get_metrics()
        print(
            f"Circuit breaker metrics: {metrics.total_requests} requests, {metrics.failed_requests} failures"
        )


def example_environment_detection():
    """Example: Environment detection and conditional configuration."""
    print("\n=== Environment Detection Example ===")

    from omnibase_core.core.configuration import (
        is_development_environment,
        is_production_environment,
    )

    # Test different environment settings
    test_envs = [
        {"ENVIRONMENT": "production"},
        {"ENVIRONMENT": "development", "DEBUG": "true"},
        {"NODE_ENV": "production"},
        {},  # Default
    ]

    for env_vars in test_envs:
        # Set test environment
        for key, value in env_vars.items():
            os.environ[key] = value

        is_prod = is_production_environment()
        is_dev = is_development_environment()

        print(f"Environment vars: {env_vars}")
        print(f"  Production: {is_prod}")
        print(f"  Development: {is_dev}")

        # Clean up
        for key in env_vars:
            os.environ.pop(key, None)


def main():
    """Run all configuration examples."""
    print("ONEX Environment-Based Configuration Examples")
    print("=" * 60)

    # Run examples
    example_basic_configuration()
    example_api_service_configuration()
    example_nested_configuration()
    example_configuration_registry()
    example_configuration_documentation()
    example_environment_detection()

    # Run async example
    asyncio.run(example_with_circuit_breaker())

    print("\n" + "=" * 60)
    print("All examples completed!")


if __name__ == "__main__":
    main()
