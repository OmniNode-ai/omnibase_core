from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.configuration.model_database_connection_config import (
    ModelDatabaseConnectionConfig,
)
from omnibase_core.models.configuration.model_generic_connection_config import (
    ModelGenericConnectionConfig,
)

# Import our newly extracted models
from omnibase_core.models.configuration.model_rest_api_connection_config import (
    ModelRestApiConnectionConfig,
)
from omnibase_core.models.core.model_retry_config import ModelRetryConfig
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.security.model_security_utils import ModelSecurityUtils
from omnibase_core.models.services.model_masked_config import ModelMaskedConfig


class ModelExternalServiceConfig(BaseModel):
    """
    Enterprise-grade external service configuration with comprehensive validation,
    business logic, and service-specific configuration management.

    Features:
    - Strong typing with service-specific configuration models
    - Automatic configuration type detection and validation
    - Health check and retry configuration management
    - Security assessment and masking capabilities
    - Service discovery and connection management
    - Environment override support
    - Performance monitoring integration
    """

    service_name: str = Field(
        default="unnamed_service",
        description="Name of the external service (e.g., 'database', 'api', 'cache')",
        pattern=r"^[a-zA-Z0-9_\-]+$",
        max_length=100,
    )
    service_type: str = Field(
        default=...,
        description="Type of service (e.g., 'event_bus', 'database', 'rest_api')",
        pattern=r"^[a-zA-Z0-9_\-]+$",
        max_length=50,
    )
    connection_config: (
        ModelDatabaseConnectionConfig
        | ModelRestApiConnectionConfig
        | ModelGenericConnectionConfig
    ) = Field(
        default_factory=ModelGenericConnectionConfig,
        description="Service-specific connection configuration with validation",
    )
    health_check_enabled: bool = Field(
        default=True,
        description="Whether to perform health checks before using this service",
    )
    health_check_timeout: int = Field(
        default=5,
        description="Timeout in seconds for health check operations",
        ge=1,
        le=300,
    )
    required: bool = Field(
        default=True,
        description="Whether this service is required for the scenario. If False, gracefully degrade if unavailable.",
    )
    retry_config: ModelRetryConfig | None = Field(
        default=None,
        description="Retry configuration for service operations",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Service tags for categorization and metadata",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_service_config(cls, values: Any) -> Any:
        """Validate that connection_config matches service_type and convert to typed models."""
        if hasattr(values, "get") and callable(values.get):
            service_type = values.get("service_type", "").lower()
            connection_config = values.get("connection_config", {})

            # If connection_config is already a typed model, keep it - use duck typing
            if hasattr(connection_config, "model_dump") and callable(
                connection_config.model_dump,
            ):
                return values

            # Convert dict[str, Any]to appropriate typed model based on service_type - use duck typing
            # Only convert if connection_config has data (not empty dict)
            if (
                hasattr(connection_config, "get")
                and callable(connection_config.get)
                and connection_config  # Check if not empty
            ):
                if service_type in ["database", "db", "postgresql", "mysql"]:
                    try:
                        values["connection_config"] = ModelDatabaseConnectionConfig(
                            **connection_config,
                        )
                    except (ValueError, ValidationError) as e:
                        msg = f"Invalid database connection config: {e!s}"
                        raise ModelOnexError(
                            msg,
                            error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                        ) from e
                    except Exception as e:
                        msg = f"Failed to create database connection config: {e!s}"
                        raise ModelOnexError(
                            msg,
                            error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        ) from e
                elif service_type in ["rest_api", "api", "http", "https"]:
                    try:
                        values["connection_config"] = ModelRestApiConnectionConfig(
                            **connection_config,
                        )
                    except (ValueError, ValidationError) as e:
                        msg = f"Invalid REST API connection config: {e!s}"
                        raise ModelOnexError(
                            msg,
                            error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                        ) from e
                    except Exception as e:
                        msg = f"Failed to create REST API connection config: {e!s}"
                        raise ModelOnexError(
                            msg,
                            error_code=EnumCoreErrorCode.OPERATION_FAILED,
                        ) from e

        return values

    def get_masked_config(self) -> ModelMaskedConfig:
        """Get configuration with sensitive fields masked for logging."""
        # Get connection dict
        if hasattr(self.connection_config, "model_dump"):
            connection_dict = self.connection_config.model_dump()
        else:
            connection_dict = {}

        masked_connection = ModelSecurityUtils.mask_dict_credentials(connection_dict)

        # Build masked config
        # Type note: masked_connection contains only simple types (str, int, bool) after masking
        # Complex types are recursively masked to simple representations
        return ModelMaskedConfig(
            service_name=self.service_name,
            service_type=self.service_type,
            connection_config=masked_connection,  # type: ignore[arg-type]
            health_check_enabled=self.health_check_enabled,
            health_check_timeout=self.health_check_timeout,
            required=self.required,
            retry_config=self.retry_config.model_dump() if self.retry_config else None,
            tags=self.tags,
        )

    def get_connection_string_safe(self) -> str:
        """Get a safe connection string for logging (no credentials)."""
        # Use duck typing to determine connection config type
        if (
            hasattr(self.connection_config, "host")
            and hasattr(self.connection_config, "port")
            and hasattr(self.connection_config, "database")
        ):
            # Database connection config
            return f"db://{self.connection_config.host}:{self.connection_config.port}/{self.connection_config.database}"
        if hasattr(self.connection_config, "get_base_domain"):
            # REST API connection config
            return f"api://{self.connection_config.get_base_domain()}"
        return f"{self.service_type}://[configured]"

    def apply_environment_overrides(self) -> "ModelExternalServiceConfig":
        """Apply environment variable overrides for CI/local testing."""
        # Apply overrides to connection_config if it supports them
        if hasattr(self.connection_config, "apply_environment_overrides"):
            updated_connection_config = (
                self.connection_config.apply_environment_overrides()
            )

            # Create new instance with updated connection config
            current_data = self.model_dump()
            current_data["connection_config"] = updated_connection_config.model_dump()
            return ModelExternalServiceConfig(**current_data)

        return self

    @classmethod
    def create_database_service(
        cls,
        service_name: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        required: bool = True,
    ) -> "ModelExternalServiceConfig":
        """Create database service configuration."""
        from pydantic import SecretStr

        db_config = ModelDatabaseConnectionConfig(
            host=host,
            port=port,
            database=database,
            username=username,
            password=SecretStr(password),
            ssl_enabled=False,
            connection_timeout=30,
        )

        return cls(
            service_name=service_name,
            service_type="database",
            connection_config=db_config,
            health_check_enabled=True,
            health_check_timeout=5,
            required=required,
            retry_config=ModelRetryConfig.create_standard(),
        )
