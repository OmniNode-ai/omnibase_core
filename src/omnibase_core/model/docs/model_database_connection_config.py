"""
Database Connection Configuration Model

Configuration for PostgreSQL database connections with production-ready settings.
"""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.core.errors.document_freshness_errors import \
    DocumentFreshnessValidationError
from omnibase_core.enums.enum_document_freshness_errors import \
    EnumDocumentFreshnessErrorCodes


class ModelDatabaseConnectionConfig(BaseModel):
    """Configuration for PostgreSQL database connections."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    # Connection settings
    host: str = Field(description="PostgreSQL database host")
    port: int = Field(ge=1, le=65535, description="PostgreSQL database port")
    database: str = Field(min_length=1, description="PostgreSQL database name")
    user: str = Field(min_length=1, description="PostgreSQL database user")
    password: str = Field(description="PostgreSQL database password")

    # Connection pool settings
    min_connections: int = Field(
        default=1, ge=1, description="Minimum pool connections"
    )
    max_connections: int = Field(
        default=10, ge=1, description="Maximum pool connections"
    )
    connection_timeout: int = Field(
        default=10, ge=1, description="Connection timeout in seconds"
    )
    idle_timeout: int = Field(
        default=300, ge=1, description="Idle connection timeout in seconds"
    )

    # SSL/TLS settings
    ssl_mode: Optional[str] = Field(
        default=None, description="SSL mode (disable, require, prefer)"
    )
    ssl_cert_path: Optional[str] = Field(
        default=None, description="Path to SSL certificate"
    )
    ssl_key_path: Optional[str] = Field(
        default=None, description="Path to SSL private key"
    )
    ssl_ca_path: Optional[str] = Field(
        default=None, description="Path to SSL CA certificate"
    )

    # Environment-specific settings
    environment: str = Field(
        default="development",
        description="Environment name (development, staging, production)",
    )

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int, info) -> int:
        """Validate max_connections is greater than min_connections."""
        if "min_connections" in info.data and v <= info.data["min_connections"]:
            raise DocumentFreshnessValidationError(
                EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID,
                "max_connections must be greater than min_connections",
            )
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of allowed values."""
        allowed_environments = {"development", "staging", "production"}
        if v not in allowed_environments:
            raise DocumentFreshnessValidationError(
                EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID,
                f"Environment must be one of: {', '.join(allowed_environments)}",
            )
        return v

    @classmethod
    def from_environment(
        cls, environment: Optional[str] = None
    ) -> "ModelDatabaseConnectionConfig":
        """Create configuration from environment variables with environment-specific defaults."""
        env = environment or os.getenv("ENVIRONMENT", "development")

        # Environment-specific connection pool defaults
        pool_configs = {
            "development": {
                "min_connections": 2,
                "max_connections": 10,
                "connection_timeout": 5,
            },
            "staging": {
                "min_connections": 5,
                "max_connections": 25,
                "connection_timeout": 10,
            },
            "production": {
                "min_connections": 10,
                "max_connections": 50,
                "connection_timeout": 15,
            },
        }

        pool_config = pool_configs.get(env, pool_configs["development"])

        # Validate required environment variables
        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise DocumentFreshnessValidationError(
                EnumDocumentFreshnessErrorCodes.FRESHNESS_CONFIG_INVALID,
                f"Missing required environment variables: {', '.join(missing_vars)}",
            )

        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "onex_dev"),
            user=os.getenv("POSTGRES_USER", "onex_user"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_connections=int(
                os.getenv(
                    "DB_POOL_MIN_CONNECTIONS", str(pool_config["min_connections"])
                )
            ),
            max_connections=int(
                os.getenv(
                    "DB_POOL_MAX_CONNECTIONS", str(pool_config["max_connections"])
                )
            ),
            connection_timeout=int(
                os.getenv("DB_POOL_TIMEOUT", str(pool_config["connection_timeout"]))
            ),
            idle_timeout=int(os.getenv("DB_POOL_IDLE_TIMEOUT", "300")),
            ssl_mode=os.getenv("POSTGRES_SSL_MODE"),
            ssl_cert_path=os.getenv("POSTGRES_SSL_CERT"),
            ssl_key_path=os.getenv("POSTGRES_SSL_KEY"),
            ssl_ca_path=os.getenv("POSTGRES_SSL_CA"),
            environment=env,
        )
