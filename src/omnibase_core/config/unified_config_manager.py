#!/usr/bin/env python3
"""
Unified Configuration Manager

Centralizes all configuration management for external dependencies
with proper fallback strategies and environment variable support.
"""

import os
from dataclasses import dataclass
from typing import Any

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


@dataclass
class ServiceDiscoveryConfig:
    """Configuration for service discovery systems."""

    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_datacenter: str = "dc1"
    consul_timeout: int = 10
    consul_token: str | None = None
    consul_scheme: str = "http"

    # Fallback configuration
    use_in_memory_fallback: bool = True
    fallback_timeout: int = 5

    @property
    def consul_url(self) -> str:
        """Get full Consul URL."""
        return f"{self.consul_scheme}://{self.consul_host}:{self.consul_port}"


@dataclass
class DatabaseConfig:
    """Configuration for database connections."""

    # PostgreSQL configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "omnibase"
    postgres_user: str = "omnibase"
    postgres_password: str | None = None
    postgres_ssl_mode: str = "prefer"
    postgres_connection_timeout: int = 30
    postgres_command_timeout: int = 60
    postgres_max_connections: int = 10
    postgres_min_connections: int = 1

    # Fallback configuration
    use_in_memory_fallback: bool = True
    fallback_timeout: int = 5

    @property
    def postgres_dsn(self) -> str:
        """Get PostgreSQL DSN."""
        password_part = f":{self.postgres_password}" if self.postgres_password else ""
        return (
            f"postgresql://{self.postgres_user}{password_part}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            f"?sslmode={self.postgres_ssl_mode}"
        )


@dataclass
class LoggingConfig:
    """Configuration for logging systems."""

    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_console: bool = True
    enable_file: bool = False
    file_path: str | None = None
    max_file_size: int = 10_000_000  # 10MB
    backup_count: int = 5


@dataclass
class UnifiedConfig:
    """Unified configuration for all external dependencies."""

    service_discovery: ServiceDiscoveryConfig
    database: DatabaseConfig
    logging: LoggingConfig

    # Global settings
    environment: str = "development"
    debug: bool = False
    enable_metrics: bool = True
    enable_health_checks: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        # Custom configuration format with nested structure
        return {
            "service_discovery": {
                "consul_host": self.service_discovery.consul_host,
                "consul_port": self.service_discovery.consul_port,
                "consul_datacenter": self.service_discovery.consul_datacenter,
                "consul_timeout": self.service_discovery.consul_timeout,
                "consul_token": self.service_discovery.consul_token,
                "consul_scheme": self.service_discovery.consul_scheme,
                "use_in_memory_fallback": self.service_discovery.use_in_memory_fallback,
                "fallback_timeout": self.service_discovery.fallback_timeout,
            },
            "database": {
                "postgres_host": self.database.postgres_host,
                "postgres_port": self.database.postgres_port,
                "postgres_database": self.database.postgres_database,
                "postgres_user": self.database.postgres_user,
                "postgres_password": self.database.postgres_password,
                "postgres_ssl_mode": self.database.postgres_ssl_mode,
                "postgres_connection_timeout": self.database.postgres_connection_timeout,
                "postgres_command_timeout": self.database.postgres_command_timeout,
                "postgres_max_connections": self.database.postgres_max_connections,
                "postgres_min_connections": self.database.postgres_min_connections,
                "use_in_memory_fallback": self.database.use_in_memory_fallback,
                "fallback_timeout": self.database.fallback_timeout,
            },
            "logging": {
                "level": self.logging.level.name,
                "format": self.logging.format,
                "enable_console": self.logging.enable_console,
                "enable_file": self.logging.enable_file,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
            },
            "environment": self.environment,
            "debug": self.debug,
            "enable_metrics": self.enable_metrics,
            "enable_health_checks": self.enable_health_checks,
        }


class UnifiedConfigManager:
    """
    Centralized configuration manager for all external dependencies.

    Loads configuration from environment variables with sensible defaults
    and provides unified access to all configuration sections.
    """

    def __init__(self):
        self._config: UnifiedConfig | None = None

    def load_config(self) -> UnifiedConfig:
        """
        Load configuration from environment variables.

        Returns:
            UnifiedConfig: Loaded configuration
        """
        if self._config is not None:
            return self._config

        # Service Discovery Configuration
        service_discovery = ServiceDiscoveryConfig(
            consul_host=os.getenv("CONSUL_HOST", "localhost"),
            consul_port=int(os.getenv("CONSUL_PORT", "8500")),
            consul_datacenter=os.getenv("CONSUL_DATACENTER", "dc1"),
            consul_timeout=int(os.getenv("CONSUL_TIMEOUT", "10")),
            consul_token=os.getenv("CONSUL_TOKEN"),
            consul_scheme=os.getenv("CONSUL_SCHEME", "http"),
            use_in_memory_fallback=os.getenv("CONSUL_USE_FALLBACK", "true").lower()
            == "true",
            fallback_timeout=int(os.getenv("CONSUL_FALLBACK_TIMEOUT", "5")),
        )

        # Database Configuration
        database = DatabaseConfig(
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
            postgres_database=os.getenv("POSTGRES_DATABASE", "omnibase"),
            postgres_user=os.getenv("POSTGRES_USER", "omnibase"),
            postgres_password=os.getenv("POSTGRES_PASSWORD"),
            postgres_ssl_mode=os.getenv("POSTGRES_SSL_MODE", "prefer"),
            postgres_connection_timeout=int(
                os.getenv("POSTGRES_CONNECTION_TIMEOUT", "30"),
            ),
            postgres_command_timeout=int(os.getenv("POSTGRES_COMMAND_TIMEOUT", "60")),
            postgres_max_connections=int(os.getenv("POSTGRES_MAX_CONNECTIONS", "10")),
            postgres_min_connections=int(os.getenv("POSTGRES_MIN_CONNECTIONS", "1")),
            use_in_memory_fallback=os.getenv("POSTGRES_USE_FALLBACK", "true").lower()
            == "true",
            fallback_timeout=int(os.getenv("POSTGRES_FALLBACK_TIMEOUT", "5")),
        )

        # Logging Configuration
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_level = getattr(LogLevel, log_level_str, LogLevel.INFO)

        logging = LoggingConfig(
            level=log_level,
            format=os.getenv(
                "LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            enable_console=os.getenv("LOG_ENABLE_CONSOLE", "true").lower() == "true",
            enable_file=os.getenv("LOG_ENABLE_FILE", "false").lower() == "true",
            file_path=os.getenv("LOG_FILE_PATH"),
            max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", "10000000")),
            backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        )

        # Global Configuration
        self._config = UnifiedConfig(
            service_discovery=service_discovery,
            database=database,
            logging=logging,
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            enable_health_checks=os.getenv("ENABLE_HEALTH_CHECKS", "true").lower()
            == "true",
        )

        return self._config

    def get_service_discovery_config(self) -> ServiceDiscoveryConfig:
        """Get service discovery configuration."""
        return self.load_config().service_discovery

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.load_config().database

    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.load_config().logging

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.load_config().environment.lower() == "development"

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.load_config().environment.lower() == "production"

    def reload_config(self) -> UnifiedConfig:
        """Force reload configuration from environment."""
        self._config = None
        return self.load_config()

    def validate_config(self) -> dict[str, Any]:
        """
        Validate current configuration.

        Returns:
            Dict with validation results and any issues found
        """
        config = self.load_config()
        issues = []
        warnings = []

        # Validate service discovery
        if not config.service_discovery.consul_host:
            issues.append("consul_host cannot be empty")

        if (
            config.service_discovery.consul_port <= 0
            or config.service_discovery.consul_port > 65535
        ):
            issues.append("consul_port must be between 1 and 65535")

        if config.service_discovery.consul_timeout <= 0:
            issues.append("consul_timeout must be positive")

        # Validate database
        if not config.database.postgres_host:
            issues.append("postgres_host cannot be empty")

        if config.database.postgres_port <= 0 or config.database.postgres_port > 65535:
            issues.append("postgres_port must be between 1 and 65535")

        if not config.database.postgres_database:
            issues.append("postgres_database cannot be empty")

        if not config.database.postgres_user:
            issues.append("postgres_user cannot be empty")

        if not config.database.postgres_password and config.is_production():
            warnings.append("postgres_password not set in production environment")

        # Validate logging
        if config.logging.enable_file and not config.logging.file_path:
            issues.append("file_path required when file logging is enabled")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "config_summary": {
                "consul_url": config.service_discovery.consul_url,
                "postgres_dsn": config.database.postgres_dsn,
                "log_level": config.logging.level.name,
                "environment": config.environment,
            },
        }


# Global configuration manager instance
_config_manager: UnifiedConfigManager | None = None


def get_config_manager() -> UnifiedConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
    return _config_manager


def get_config() -> UnifiedConfig:
    """Get unified configuration."""
    return get_config_manager().load_config()


# Convenience functions
def get_service_discovery_config() -> ServiceDiscoveryConfig:
    """Get service discovery configuration."""
    return get_config().service_discovery


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return get_config().database


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return get_config().logging
