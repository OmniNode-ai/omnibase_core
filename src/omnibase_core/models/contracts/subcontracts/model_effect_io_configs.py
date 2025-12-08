"""
Effect IO Configuration Models - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Handler-specific IO configuration models using Pydantic discriminated unions.
Each model provides configuration for a specific type of external I/O operation:
- HTTP: REST API calls with URL templates and request configuration
- DB: Database operations with SQL templates and connection management
- Kafka: Message production with topic, payload, and delivery settings
- Filesystem: File operations with path templates and atomicity controls

DISCRIMINATED UNION:
The EffectIOConfig union type uses handler_type as the discriminator field,
enabling Pydantic to automatically select the correct model during validation.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "ModelHttpIOConfig",
    "ModelDbIOConfig",
    "ModelKafkaIOConfig",
    "ModelFilesystemIOConfig",
    "EffectIOConfig",
]


class ModelHttpIOConfig(BaseModel):
    """
    HTTP IO configuration for REST API calls.

    Provides URL templating with ${} placeholders, HTTP method configuration,
    headers, body templates, query parameters, and connection settings.

    Example:
        config = ModelHttpIOConfig(
            url_template="https://api.example.com/users/${input.user_id}",
            method="GET",
            headers={"Authorization": "Bearer ${env.API_TOKEN}"},
            timeout_ms=5000,
        )
    """

    handler_type: Literal[EnumEffectHandlerType.HTTP] = Field(
        default=EnumEffectHandlerType.HTTP,
        description="Discriminator field for HTTP handler",
    )

    url_template: str = Field(
        ...,
        description="URL with ${} placeholders for variable substitution",
        min_length=1,
    )

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP method for the request",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers with optional ${} placeholders",
    )

    body_template: str | None = Field(
        default=None,
        description="Request body template with ${} placeholders (required for POST/PUT/PATCH)",
    )

    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters with optional ${} placeholders",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=100,
        le=300000,
        description="Request timeout in milliseconds (100ms - 5min)",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP redirects",
    )

    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )

    @model_validator(mode="after")
    def validate_body_for_method(self) -> "ModelHttpIOConfig":
        """Require body_template for POST/PUT/PATCH methods."""
        methods_requiring_body = {"POST", "PUT", "PATCH"}
        if self.method in methods_requiring_body and self.body_template is None:
            raise ModelOnexError(
                message=f"body_template is required for {self.method} requests",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "method": ModelSchemaValue.from_value(self.method),
                    }
                ),
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelDbIOConfig(BaseModel):
    """
    Database IO configuration for SQL operations.

    Provides SQL query templating with positional parameters ($1, $2, ...),
    connection management, and operation-specific settings.

    Security:
        Raw queries are validated to prevent SQL injection via ${input.*} patterns.
        Use parameterized queries ($1, $2, ...) for user input instead.

    Example:
        config = ModelDbIOConfig(
            operation="select",
            connection_name="primary_db",
            query_template="SELECT * FROM users WHERE id = $1 AND status = $2",
            query_params=["${input.user_id}", "${input.status}"],
        )
    """

    handler_type: Literal[EnumEffectHandlerType.DB] = Field(
        default=EnumEffectHandlerType.DB,
        description="Discriminator field for DB handler",
    )

    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(
        ...,
        description="Database operation type",
    )

    connection_name: str = Field(
        ...,
        description="Named connection reference from connection pool",
        min_length=1,
    )

    query_template: str = Field(
        ...,
        description="SQL query with $1, $2, ... positional parameters",
        min_length=1,
    )

    query_params: list[str] = Field(
        default_factory=list,
        description="Parameter values/templates for positional placeholders",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=100,
        le=300000,
        description="Query timeout in milliseconds (100ms - 5min)",
    )

    fetch_size: int | None = Field(
        default=None,
        ge=1,
        le=100000,
        description="Fetch size for cursor-based retrieval",
    )

    read_only: bool = Field(
        default=False,
        description="Whether to execute in read-only transaction mode",
    )

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation(cls, value: object) -> object:
        """Normalize operation to lowercase."""
        if isinstance(value, str):
            return value.lower().strip()
        # Return non-string values as-is; Pydantic will validate them
        return value

    @model_validator(mode="after")
    def validate_sql_injection_prevention(self) -> "ModelDbIOConfig":
        """Prevent SQL injection via ${input.*} patterns in raw queries."""
        if self.operation == "raw":
            # Check for potentially dangerous ${input.*} patterns in query_template
            input_pattern = re.compile(r"\$\{input\.[^}]+\}")
            if input_pattern.search(self.query_template):
                raise ModelOnexError(
                    message="Raw queries must not contain ${input.*} patterns. "
                    "Use parameterized queries ($1, $2, ...) with query_params instead.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("securityerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "sql_injection_prevention"
                            ),
                        }
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_param_count(self) -> "ModelDbIOConfig":
        """Validate that query_params count matches $N placeholders in query."""
        # Find all $N placeholders (where N is a number)
        placeholder_pattern = re.compile(r"\$(\d+)")
        matches = placeholder_pattern.findall(self.query_template)

        if not matches:
            # No placeholders, params should be empty
            if self.query_params:
                raise ModelOnexError(
                    message=f"query_params has {len(self.query_params)} items "
                    "but query_template has no $N placeholders",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "param_count_validation"
                            ),
                        }
                    ),
                )
            return self

        # Get the highest placeholder number
        max_placeholder = max(int(n) for n in matches)

        # Check params count matches
        if len(self.query_params) != max_placeholder:
            raise ModelOnexError(
                message=f"query_params has {len(self.query_params)} items "
                f"but query_template requires {max_placeholder} (highest placeholder: ${max_placeholder})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "param_count_validation"
                        ),
                        "expected_params": ModelSchemaValue.from_value(max_placeholder),
                        "actual_params": ModelSchemaValue.from_value(
                            len(self.query_params)
                        ),
                    }
                ),
            )

        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelKafkaIOConfig(BaseModel):
    """
    Kafka IO configuration for message production.

    Provides topic configuration, payload templating, partition key generation,
    and delivery settings for Kafka message production.

    Example:
        config = ModelKafkaIOConfig(
            topic="user-events",
            payload_template='{"user_id": "${input.user_id}", "action": "${input.action}"}',
            partition_key_template="${input.user_id}",
            acks="all",
        )
    """

    handler_type: Literal[EnumEffectHandlerType.KAFKA] = Field(
        default=EnumEffectHandlerType.KAFKA,
        description="Discriminator field for Kafka handler",
    )

    topic: str = Field(
        ...,
        description="Kafka topic to produce messages to",
        min_length=1,
    )

    payload_template: str = Field(
        ...,
        description="Message payload template with ${} placeholders",
        min_length=1,
    )

    partition_key_template: str | None = Field(
        default=None,
        description="Template for partition key (affects message ordering)",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Kafka message headers with optional ${} placeholders",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=100,
        le=300000,
        description="Producer timeout in milliseconds (100ms - 5min)",
    )

    acks: Literal["0", "1", "all"] = Field(
        default="all",
        description="Acknowledgment level: 0=none, 1=leader, all=all replicas",
    )

    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(
        default="none",
        description="Compression codec for message payloads",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelFilesystemIOConfig(BaseModel):
    """
    Filesystem IO configuration for file operations.

    Provides file path templating, operation type specification,
    and atomicity controls for filesystem operations.

    Example:
        config = ModelFilesystemIOConfig(
            file_path_template="/data/output/${input.date}/${input.filename}.json",
            operation="write",
            atomic=True,
            create_dirs=True,
        )
    """

    handler_type: Literal[EnumEffectHandlerType.FILESYSTEM] = Field(
        default=EnumEffectHandlerType.FILESYSTEM,
        description="Discriminator field for Filesystem handler",
    )

    file_path_template: str = Field(
        ...,
        description="File path with ${} placeholders for variable substitution",
        min_length=1,
    )

    operation: Literal["read", "write", "delete", "move", "copy"] = Field(
        ...,
        description="Filesystem operation type",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=100,
        le=300000,
        description="Operation timeout in milliseconds (100ms - 5min)",
    )

    atomic: bool = Field(
        default=True,
        description="Use atomic operations (write to temp, then rename)",
    )

    create_dirs: bool = Field(
        default=True,
        description="Create parent directories if they don't exist",
    )

    encoding: str = Field(
        default="utf-8",
        description="Text encoding for file content",
    )

    mode: str | None = Field(
        default=None,
        description="File permission mode (e.g., '0644')",
    )

    @model_validator(mode="after")
    def validate_atomic_for_operation(self) -> "ModelFilesystemIOConfig":
        """
        Validate atomic setting is only applicable to write/move operations.

        Note: This validator does not raise an error for invalid combinations
        since setting atomic=True for read/delete/copy operations is harmless
        (the setting is simply ignored). The validator exists as documentation
        and for potential future enforcement.
        """
        # atomic_operations = {"write", "move"}
        # For now, we allow atomic=True on any operation but it only has effect
        # on write and move operations. This provides forward compatibility.
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


# Discriminated union type for all IO configurations
# Pydantic uses handler_type as the discriminator to select the correct model
EffectIOConfig = (
    ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig
)
