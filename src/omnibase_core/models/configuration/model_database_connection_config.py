import os
import re

from pydantic import BaseModel, Field, SecretStr, field_validator

from omnibase_core.constants.constants_field_limits import (
    MAX_IDENTIFIER_LENGTH,
    MAX_NAME_LENGTH,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelDatabaseConnectionConfig(BaseModel):
    """
    Enterprise-grade database connection configuration with comprehensive validation,
    business logic, and environment override capabilities.

    Features:
    - Strong typing with comprehensive validation
    - Environment variable override support
    - Connection string generation and parsing
    - SSL/TLS configuration management
    - Connection pooling recommendations
    - Health check capability assessment
    - Performance tuning recommendations
    """

    host: str = Field(
        default=...,
        description="Database host",
        pattern=r"^[a-zA-Z0-9\-\.]+$",
        max_length=MAX_NAME_LENGTH,
    )
    port: int = Field(default=..., description="Database port", ge=1, le=65535)
    database: str = Field(
        default=...,
        description="Database name",
        pattern=r"^[a-zA-Z0-9_\-]+$",
        max_length=MAX_IDENTIFIER_LENGTH,
    )
    username: str = Field(
        default=..., description="Database username", max_length=MAX_IDENTIFIER_LENGTH
    )
    password: SecretStr = Field(default=..., description="Database password (secured)")
    ssl_enabled: bool = Field(
        default=False, description="Whether to use SSL connection"
    )
    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1,
        le=300,
    )

    @field_validator("host", mode="before")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate database host format."""
        if not v or not v.strip():
            msg = "Database host cannot be empty"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Remove leading/trailing whitespace
        v = v.strip()

        # Basic hostname validation
        if not re.match(r"^[a-zA-Z0-9\-\.]+$", v):
            msg = f"Invalid host format: {v}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Check for common invalid patterns
        if v.startswith("-") or v.endswith("-"):
            msg = f"Host cannot start or end with hyphen: {v}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if ".." in v:
            msg = f"Host cannot contain consecutive dots: {v}"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    @field_validator("database", mode="before")
    @classmethod
    def validate_database_name(cls, v: str) -> str:
        """Validate database name format."""
        if not v or not v.strip():
            msg = "Database name cannot be empty"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        v = v.strip()

        # Check for SQL injection patterns
        dangerous_patterns = [
            "--",
            ";",
            "'",
            '"',
            "/*",
            "*/",
            "DROP",
            "DELETE",
            "INSERT",
        ]
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if pattern in v_upper:
                msg = f"Database name contains potentially dangerous pattern: {pattern}"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        return v

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate database username."""
        if not v or not v.strip():
            msg = "Database username cannot be empty"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        v = v.strip()

        # Check for SQL injection patterns
        if any(pattern in v.upper() for pattern in ["--", ";", "'", '"']):
            msg = "Username contains potentially dangerous characters"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        return v

    # === Connection Management ===

    def get_connection_string(self, driver: str = "postgresql") -> str:
        """Get database connection string for the specified driver."""
        protocol_map = {
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "mysql": "mysql",
            "sqlite": "sqlite",
            "oracle": "oracle",
            "mssql": "mssql+pyodbc",
        }

        protocol = protocol_map.get(driver.lower(), driver)

        # Basic connection string format
        ssl_params = "?sslmode=require" if self.ssl_enabled else ""

        return f"{protocol}://{self.username}:***@{self.host}:{self.port}/{self.database}{ssl_params}"

    def get_masked_connection_string(self, driver: str = "postgresql") -> str:
        """Get connection string with password masked for logging."""
        return self.get_connection_string(driver)

    def get_actual_connection_string(self, driver: str = "postgresql") -> str:
        """Get actual connection string with real password (use carefully)."""
        protocol_map = {
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "mysql": "mysql",
            "sqlite": "sqlite",
            "oracle": "oracle",
            "mssql": "mssql+pyodbc",
        }

        protocol = protocol_map.get(driver.lower(), driver)
        password = self.password.get_secret_value()

        ssl_params = "?sslmode=require" if self.ssl_enabled else ""

        return f"{protocol}://{self.username}:{password}@{self.host}:{self.port}/{self.database}{ssl_params}"

    def get_connection_parameters(self) -> dict[str, str]:
        """Get connection parameters as key-value pairs."""
        params = {
            "host": self.host,
            "port": str(self.port),
            "database": self.database,
            "user": self.username,
            "password": self.password.get_secret_value(),
            "connect_timeout": str(self.connection_timeout),
        }

        if self.ssl_enabled:
            params["sslmode"] = "require"
        else:
            params["sslmode"] = "prefer"

        return params

    def get_masked_connection_parameters(self) -> dict[str, str]:
        """Get connection parameters with password masked."""
        params = self.get_connection_parameters()
        params["password"] = "***MASKED***"
        return params

    # === Security Assessment ===

    def is_secure_configuration(self) -> bool:
        """Assess if this is a secure configuration for production."""
        # Check SSL requirement
        if not self.ssl_enabled:
            return False

        # Check password strength (basic)
        password = self.password.get_secret_value()
        if len(password) < 8:
            return False

        # Check for localhost (not secure for production)
        if self.host.lower() in ("localhost", "127.0.0.1"):
            return False

        # Check for default ports (security through obscurity)
        default_ports = {
            5432,
            3306,
            1433,
            1521,
        }  # PostgreSQL, MySQL, SQL Server, Oracle
        if self.port in default_ports:
            return False  # Consider non-default ports more secure

        return True

    def get_security_recommendations(self) -> list[str]:
        """Get security recommendations for this configuration."""
        recommendations = []

        if not self.ssl_enabled:
            recommendations.append("Enable SSL/TLS for production database connections")

        password = self.password.get_secret_value()
        if len(password) < 12:
            recommendations.append(
                "Use stronger passwords (12+ characters) for production",
            )

        if self.host.lower() in ("localhost", "127.0.0.1"):
            recommendations.append(
                "Use dedicated database server instead of localhost for production",
            )

        default_ports = {
            5432: "PostgreSQL",
            3306: "MySQL",
            1433: "SQL Server",
            1521: "Oracle",
        }
        if self.port in default_ports:
            recommendations.append(
                f"Consider using non-default port instead of {self.port} ({default_ports[self.port]} default)",
            )

        if self.connection_timeout > 60:
            recommendations.append(
                "Long connection timeouts may lead to resource exhaustion",
            )

        return recommendations

    def requires_ssl(self) -> bool:
        """Check if SSL is enabled for this connection."""
        return self.ssl_enabled

    def get_security_profile(self) -> dict[str, str]:
        """Get security profile assessment."""
        password = self.password.get_secret_value()

        # Password strength assessment
        if len(password) >= 16:
            password_strength = "strong"
        elif len(password) >= 12:
            password_strength = "moderate"
        elif len(password) >= 8:
            password_strength = "weak"
        else:
            password_strength = "very_weak"

        return {
            "ssl_enabled": "yes" if self.ssl_enabled else "no",
            "password_strength": password_strength,
            "host_type": (
                "localhost"
                if self.host.lower() in ("localhost", "127.0.0.1")
                else "remote"
            ),
            "port_type": (
                "default" if self.port in {5432, 3306, 1433, 1521} else "custom"
            ),
            "overall_security": (
                "high" if self.is_secure_configuration() else "needs_improvement"
            ),
        }

    # === Performance Assessment ===

    def get_performance_profile(self) -> dict[str, str]:
        """Get performance characteristics of this configuration."""
        profile = {
            "connection_latency": "low" if self.connection_timeout <= 10 else "high",
            "ssl_overhead": "present" if self.ssl_enabled else "none",
            "timeout_profile": (
                "aggressive" if self.connection_timeout <= 15 else "conservative"
            ),
        }

        # Host-based performance assessment
        if self.host.lower() in ("localhost", "127.0.0.1"):
            profile["network_latency"] = "minimal"
        else:
            profile["network_latency"] = "variable"

        return profile

    def get_performance_recommendations(self) -> list[str]:
        """Get performance tuning recommendations."""
        recommendations = []

        if self.connection_timeout < 5:
            recommendations.append(
                "Very short timeout may cause connection failures under load",
            )

        if self.connection_timeout > 60:
            recommendations.append(
                "Long timeout may cause resource exhaustion - consider reducing",
            )

        if self.ssl_enabled:
            recommendations.append("SSL adds latency - ensure adequate timeout values")

        if self.host.lower() not in ("localhost", "127.0.0.1"):
            recommendations.append(
                "Consider connection pooling for remote database connections",
            )

        return recommendations

    # === Connection Pool Recommendations ===

    def get_pool_recommendations(self) -> dict[str, int]:
        """Get connection pool size recommendations based on configuration."""
        base_pool_size = 5
        max_pool_size = 20

        # Adjust based on timeout (longer timeout = fewer connections needed)
        if self.connection_timeout > 30:
            base_pool_size = max(3, base_pool_size - 2)
            max_pool_size = max(10, max_pool_size - 5)
        elif self.connection_timeout < 10:
            base_pool_size = min(10, base_pool_size + 3)
            max_pool_size = min(30, max_pool_size + 10)

        # Adjust for SSL overhead
        if self.ssl_enabled:
            base_pool_size = min(8, base_pool_size + 2)
            max_pool_size = min(25, max_pool_size + 5)

        return {
            "min_pool_size": max(1, base_pool_size // 2),
            "initial_pool_size": base_pool_size,
            "max_pool_size": max_pool_size,
            "pool_timeout": self.connection_timeout + 5,
        }

    # === Environment Override Support ===

    def apply_environment_overrides(self) -> "ModelDatabaseConnectionConfig":
        """Apply environment variable overrides for CI/local testing."""
        overrides: dict[str, object] = {}

        # Environment variable mappings
        env_mappings = {
            "ONEX_DB_HOST": "host",
            "ONEX_DB_PORT": "port",
            "ONEX_DB_DATABASE": "database",
            "ONEX_DB_USERNAME": "username",
            "ONEX_DB_PASSWORD": "password",
            "ONEX_DB_SSL_ENABLED": "ssl_enabled",
            "ONEX_DB_CONNECTION_TIMEOUT": "connection_timeout",
        }

        for env_var, field_name in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # Type conversion for different field types
                if field_name in ["port", "connection_timeout"]:
                    try:
                        overrides[field_name] = int(env_value)
                    except ValueError:
                        continue
                elif field_name == "ssl_enabled":
                    overrides[field_name] = env_value.lower() in (
                        "true",
                        "1",
                        "yes",
                        "on",
                    )
                elif field_name == "password":
                    overrides[field_name] = SecretStr(env_value)
                else:
                    overrides[field_name] = env_value

        if overrides:
            current_data = self.model_dump()
            current_data.update(overrides)
            return ModelDatabaseConnectionConfig(**current_data)

        return self

    # === Health Check Support ===

    def can_perform_health_check(self) -> bool:
        """Check if health check can be performed with this configuration."""
        # Basic requirements: host, port, credentials
        return bool(self.host and self.port and self.username and self.password)

    def get_health_check_timeout(self) -> int:
        """Get recommended timeout for health check operations."""
        # Health checks should be faster than normal operations
        return min(self.connection_timeout, 10)

    def get_health_check_query(self, driver: str = "postgresql") -> str:
        """Get appropriate health check query for the database type."""
        health_queries = {
            "postgresql": "SELECT 1",
            "postgres": "SELECT 1",
            "mysql": "SELECT 1",
            "oracle": "SELECT 1 FROM DUAL",
            "mssql": "SELECT 1",
            "sqlite": "SELECT 1",
        }

        return health_queries.get(driver.lower(), "SELECT 1")
