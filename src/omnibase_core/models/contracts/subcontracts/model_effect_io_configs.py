"""
Effect IO Configuration Models.



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

Thread Safety:
    All IO configuration models are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

See Also:
    - :class:`ModelEffectSubcontract`: Parent contract using these IO configs
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_resolved_context`:
        Resolved context models after template substitution
    - :class:`NodeEffect`: The primary node using these configurations
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - examples/contracts/effect/: Example YAML contracts

Author: ONEX Framework Team
"""

import re
import warnings
from typing import Annotated, ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
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

    Attributes:
        handler_type: Discriminator field identifying this as an HTTP handler.
        url_template: URL with ${} placeholders for variable substitution.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        headers: HTTP headers with optional ${} placeholders.
        body_template: Request body template with ${} placeholders.
        query_params: Query parameters with optional ${} placeholders.
        timeout_ms: Request timeout in milliseconds (1s - 10min).
        follow_redirects: Whether to follow HTTP redirects.
        verify_ssl: Whether to verify SSL certificates.

    Example:
        >>> config = ModelHttpIOConfig(
        ...     url_template="https://api.example.com/users/${input.user_id}",
        ...     method="GET",
        ...     headers={"Authorization": "Bearer ${env.API_TOKEN}"},
        ...     timeout_ms=5000,
        ... )
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
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Request timeout in milliseconds (1s - 10min)",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP redirects",
    )

    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )

    @field_validator("verify_ssl", mode="after")
    @classmethod
    def warn_on_disabled_ssl_verification(cls, value: bool) -> bool:
        """
        Emit a security warning when SSL verification is disabled.

        Args:
            value: The verify_ssl field value.

        Returns:
            The unchanged value after emitting warning if False.
        """
        if not value:
            warnings.warn(
                "verify_ssl=False disables SSL certificate validation. "
                "This is insecure for production use.",
                UserWarning,
                stacklevel=2,
            )
        return value

    @model_validator(mode="after")
    def validate_body_for_method(self) -> "ModelHttpIOConfig":
        """
        Require body_template for POST/PUT/PATCH methods.

        These HTTP methods typically carry a request body, so a body_template
        is required to ensure the request is properly configured.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If body_template is None for POST/PUT/PATCH.
        """
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

    Attributes:
        handler_type: Discriminator field identifying this as a DB handler.
        operation: Database operation type (select, insert, update, delete, upsert, raw).
        connection_name: Named connection reference from connection pool.
        query_template: SQL query with $1, $2, ... positional parameters.
        query_params: Parameter values/templates for positional placeholders.
        timeout_ms: Query timeout in milliseconds (1s - 10min).
        fetch_size: Fetch size for cursor-based retrieval.
        read_only: Whether to execute in read-only transaction mode.

    Example:
        >>> config = ModelDbIOConfig(
        ...     operation="select",
        ...     connection_name="primary_db",
        ...     query_template="SELECT * FROM users WHERE id = $1 AND status = $2",
        ...     query_params=["${input.user_id}", "${input.status}"],
        ... )
    """

    # Pre-compiled regex patterns for better performance in validators
    _INPUT_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$\{input\.[^}]+\}")
    _PLACEHOLDER_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\$(\d+)")

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
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Query timeout in milliseconds (1s - 10min)",
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
        """
        Normalize operation to lowercase.

        Ensures consistent operation type comparison by converting string
        values to lowercase and stripping whitespace.

        Args:
            value: The operation field value to normalize.

        Returns:
            Normalized lowercase string if input is string, otherwise unchanged.
        """
        if isinstance(value, str):
            return value.lower().strip()
        # Return non-string values as-is; Pydantic will validate them
        return value

    @model_validator(mode="after")
    def validate_sql_injection_prevention(self) -> "ModelDbIOConfig":
        """
        Prevent SQL injection via ${input.*} patterns in raw queries.

        Raw queries must use parameterized placeholders ($1, $2, ...) instead
        of direct template substitution to prevent SQL injection attacks.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If raw query contains ${input.*} patterns.
        """
        if self.operation == "raw":
            # Check for potentially dangerous ${input.*} patterns in query_template
            if self._INPUT_PATTERN.search(self.query_template):
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
    def validate_param_count_and_sequence(self) -> "ModelDbIOConfig":
        """
        Validate query_params count and placeholder sequence.

        Ensures:
            1. query_params count matches the highest $N placeholder
            2. Placeholders are sequential starting from $1 (no gaps like $1, $3 missing $2)

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If param count mismatches or placeholders have gaps.
        """
        # Find all $N placeholders (where N is a number)
        matches = self._PLACEHOLDER_PATTERN.findall(self.query_template)

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

        # Get unique placeholder numbers as integers, sorted
        placeholder_nums = sorted({int(n) for n in matches})
        max_placeholder = placeholder_nums[-1]

        # Check params count matches highest placeholder
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

        # Check placeholders are sequential starting from $1 (no gaps)
        expected_sequence = list(range(1, max_placeholder + 1))
        if placeholder_nums != expected_sequence:
            missing = sorted(set(expected_sequence) - set(placeholder_nums))
            raise ModelOnexError(
                message=f"Placeholders must be sequential starting from $1. "
                f"Missing placeholders: ${', $'.join(str(n) for n in missing)}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "placeholder_sequence_validation"
                        ),
                        "found_placeholders": ModelSchemaValue.from_value(
                            placeholder_nums
                        ),
                        "missing_placeholders": ModelSchemaValue.from_value(missing),
                    }
                ),
            )

        return self

    @model_validator(mode="after")
    def validate_read_only_semantics(self) -> "ModelDbIOConfig":
        """
        Enforce read_only semantics: only select operations allowed when read_only=True.

        Read-only mode enables database optimizations but restricts operations
        to SELECT queries only.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If read_only=True with non-select operation.
        """
        if self.read_only and self.operation != "select":
            raise ModelOnexError(
                message=f"read_only=True only allows 'select' operation, "
                f"but got '{self.operation}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "read_only_semantics"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                        "read_only": ModelSchemaValue.from_value(self.read_only),
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

    WARNING: Using acks="0" (fire-and-forget) provides no delivery guarantees
    and messages may be lost silently. This configuration requires explicit
    opt-in via the acks_zero_acknowledged field.

    Attributes:
        handler_type: Discriminator field identifying this as a Kafka handler.
        topic: Kafka topic to produce messages to.
        payload_template: Message payload template with ${} placeholders.
        partition_key_template: Template for partition key (affects message ordering).
        headers: Kafka message headers with optional ${} placeholders.
        timeout_ms: Producer timeout in milliseconds (1s - 10min).
        acks: Acknowledgment level (0=none, 1=leader, all=all replicas).
        acks_zero_acknowledged: Explicit opt-in for acks=0 mode.
        compression: Compression codec for message payloads.

    Example:
        >>> config = ModelKafkaIOConfig(
        ...     topic="user-events",
        ...     payload_template='{"user_id": "${input.user_id}", "action": "${input.action}"}',
        ...     partition_key_template="${input.user_id}",
        ...     acks="all",
        ... )

    Example with acks=0 (fire-and-forget, use with caution):
        >>> config = ModelKafkaIOConfig(
        ...     topic="metrics",
        ...     payload_template='{"metric": "${input.name}", "value": ${input.value}}',
        ...     acks="0",
        ...     acks_zero_acknowledged=True,  # Required explicit opt-in
        ... )
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
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Producer timeout in milliseconds (1s - 10min)",
    )

    acks: Literal["0", "1", "all"] = Field(
        default="all",
        description="Acknowledgment level: 0=none (fire-and-forget, may lose messages), "
        "1=leader only, all=all replicas (strongest guarantee)",
    )

    acks_zero_acknowledged: bool = Field(
        default=False,
        description="Explicit opt-in for acks=0 (fire-and-forget mode). "
        "Must be True when using acks='0' to acknowledge the risk of message loss.",
    )

    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(
        default="none",
        description="Compression codec for message payloads",
    )

    @model_validator(mode="after")
    def validate_acks_zero_opt_in(self) -> "ModelKafkaIOConfig":
        """
        Require explicit opt-in for acks=0 configuration.

        Kafka acks=0 (fire-and-forget) provides no delivery guarantees and messages
        may be lost silently. This validator ensures users explicitly acknowledge
        this risk by setting acks_zero_acknowledged=True.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If acks=0 without acks_zero_acknowledged=True.
        """
        if self.acks == "0":
            # Always emit a warning when acks=0 is used
            warnings.warn(
                "Kafka acks=0 provides no delivery guarantees. Messages may be lost. "
                "Use acks=1 or acks='all' for better reliability.",
                UserWarning,
                stacklevel=2,
            )
            # Require explicit opt-in
            if not self.acks_zero_acknowledged:
                raise ModelOnexError(
                    message="Kafka acks=0 requires explicit opt-in. "
                    "Set acks_zero_acknowledged=True to acknowledge the risk of message loss.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "acks_zero_opt_in"
                            ),
                            "acks": ModelSchemaValue.from_value(self.acks),
                            "acks_zero_acknowledged": ModelSchemaValue.from_value(
                                self.acks_zero_acknowledged
                            ),
                        }
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_acks_zero_acknowledged_only_for_acks_zero(
        self,
    ) -> "ModelKafkaIOConfig":
        """
        Prevent acks_zero_acknowledged=True when acks is not "0".

        The acks_zero_acknowledged field is only meaningful when acks="0".
        Setting it to True with acks="1" or acks="all" is a configuration error
        that creates confusing state. This validator ensures consistent configuration.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If acks_zero_acknowledged=True with acks != "0".
        """
        if self.acks != "0" and self.acks_zero_acknowledged:
            raise ModelOnexError(
                message=f"acks_zero_acknowledged=True is only valid when acks='0', "
                f"but acks='{self.acks}'. Set acks_zero_acknowledged=False or "
                f"change acks to '0'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "acks_zero_acknowledged_semantics"
                        ),
                        "acks": ModelSchemaValue.from_value(self.acks),
                        "acks_zero_acknowledged": ModelSchemaValue.from_value(
                            self.acks_zero_acknowledged
                        ),
                    }
                ),
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelFilesystemIOConfig(BaseModel):
    """
    Filesystem IO configuration for file operations.

    Provides file path templating, operation type specification,
    and atomicity controls for filesystem operations.

    For move/copy operations, both file_path_template (source) and
    destination_path_template (target) are required.

    Attributes:
        handler_type: Discriminator field identifying this as a Filesystem handler.
        file_path_template: File path with ${} placeholders (source for move/copy).
        destination_path_template: Destination path for move/copy operations.
        operation: Filesystem operation type (read, write, delete, move, copy).
        timeout_ms: Operation timeout in milliseconds (1s - 10min).
        atomic: Use atomic operations (write to temp, then rename).
        create_dirs: Create parent directories if they don't exist.
        encoding: Text encoding for file content.
        mode: File permission mode (e.g., '0644').

    Example (write):
        >>> config = ModelFilesystemIOConfig(
        ...     file_path_template="/data/output/${input.date}/${input.filename}.json",
        ...     operation="write",
        ...     atomic=True,
        ...     create_dirs=True,
        ... )

    Example (move):
        >>> config = ModelFilesystemIOConfig(
        ...     file_path_template="/data/inbox/${input.filename}",
        ...     destination_path_template="/data/archive/${input.date}/${input.filename}",
        ...     operation="move",
        ...     create_dirs=True,
        ... )
    """

    handler_type: Literal[EnumEffectHandlerType.FILESYSTEM] = Field(
        default=EnumEffectHandlerType.FILESYSTEM,
        description="Discriminator field for Filesystem handler",
    )

    file_path_template: str = Field(
        ...,
        description="File path with ${} placeholders for variable substitution. "
        "For move/copy operations, this is the source path.",
        min_length=1,
    )

    destination_path_template: str | None = Field(
        default=None,
        description="Destination path with ${} placeholders for move/copy operations. "
        "Required for 'move' and 'copy' operations, ignored for other operations.",
    )

    operation: Literal["read", "write", "delete", "move", "copy"] = Field(
        ...,
        description="Filesystem operation type",
    )

    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Operation timeout in milliseconds (1s - 10min)",
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
        Validate atomic setting is only applicable to write operations.

        Atomic operations (write to temp file, then rename) only make sense for
        write operations. Enabling atomic=True for read/delete/move/copy operations
        is a configuration error and will raise a validation error.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If atomic=True for non-write operations.
        """
        if self.atomic and self.operation != "write":
            raise ModelOnexError(
                message=f"atomic=True is only valid for 'write' operations, "
                f"not '{self.operation}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "atomic_operation_validation"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                    }
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_destination_for_move_copy(self) -> "ModelFilesystemIOConfig":
        """
        Validate destination_path_template is required for move/copy operations.

        Move and copy operations require both a source path (file_path_template)
        and a destination path (destination_path_template). Without the destination,
        the operation would fail at runtime.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If move/copy operation without destination_path_template.
        """
        operations_requiring_destination = {"move", "copy"}
        if (
            self.operation in operations_requiring_destination
            and self.destination_path_template is None
        ):
            raise ModelOnexError(
                message=f"destination_path_template is required for '{self.operation}' operations",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "destination_path_validation"
                        ),
                        "operation": ModelSchemaValue.from_value(self.operation),
                    }
                ),
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid")


# Discriminated union type for all IO configurations
# Pydantic uses handler_type as the discriminator to select the correct model
EffectIOConfig = Annotated[
    ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig,
    Discriminator("handler_type"),
]
