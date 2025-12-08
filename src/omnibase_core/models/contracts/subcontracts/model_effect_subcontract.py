"""
Effect Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

This module defines the ModelEffectSubcontract model which represents the complete
contract for NodeEffect operations. It specifies declarative effect operations with
retry policies, circuit breakers, transaction boundaries, and observability.

The effect subcontract is part of the ONEX contract system and defines:
    - Operation identity (name, version, description)
    - Effect operation specifications with IO configurations
    - Default policies for retry, circuit breaker, and transactions
    - Execution mode (sequential, parallel, failfast)

Thread Safety:
    ModelEffectSubcontract and all submodels are immutable (frozen=True) after
    creation, making them thread-safe for concurrent read access.

Execution Model:
    Operations can execute in different orders:
    - FORWARD: Operations run one after another in definition order
    - REVERSE: Operations run in reverse order (for rollback scenarios)
    - PARALLEL: Operations run concurrently (where possible)

Idempotency:
    Effect operations have built-in idempotency awareness based on handler type:
    - HTTP: POST=non-idempotent, GET/PUT/DELETE/PATCH=idempotent
    - DB: SELECT=idempotent, INSERT/UPDATE/DELETE/UPSERT/RAW=non-idempotent
    - KAFKA: Always non-idempotent (at-least-once semantics)
    - FILESYSTEM: READ=idempotent, WRITE/DELETE/MOVE/COPY=non-idempotent

Example YAML Contract:
    .. code-block:: yaml

        effect_operations:
          version: "1.0.0"
          operation_name: "user_creation_effect"
          operation_version: "1.0.0"
          description: "Create user via API and publish event"
          execution_order: "forward"
          default_retry_policy:
            max_attempts: 3
            backoff_strategy: "exponential"
            base_delay_ms: 100
          default_circuit_breaker:
            enabled: true
            failure_threshold: 5
            success_threshold: 2
          operations:
            - operation_id: "create_user_api"
              operation_name: "CreateUserAPI"
              description: "Call user creation API"
              io_config:
                handler_type: "http"
                url_template: "https://api.example.com/users"
                method: "POST"
                body_template: '{"name": "${input.name}"}'
                timeout_ms: 5000
              retry_policy:
                max_attempts: 5
              operation_timeout_ms: 10000

Example Python Usage:
    >>> from omnibase_core.models.contracts.subcontracts import ModelEffectSubcontract
    >>> from omnibase_core.models.contracts.subcontracts import ModelEffectOperation
    >>> from omnibase_core.models.contracts.subcontracts import ModelHttpIOConfig
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> contract = ModelEffectSubcontract(
    ...     version=ModelSemVer(major=1, minor=0, patch=0),
    ...     operation_name="user_creation_effect",
    ...     operation_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     description="Create user via API",
    ...     operations=[...],  # List of ModelEffectOperation
    ... )

See Also:
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_io_configs`: IO configurations
    - :mod:`omnibase_core.models.contracts.model_effect_retry_config`: Retry policies
    - :class:`NodeEffect`: The primary node using this subcontract
    - :class:`MixinEffectExecution`: Mixin providing effect execution logic
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - examples/contracts/effect/: Example YAML contracts

Author: ONEX Framework Team
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_effect import (
    MIN_EFFECT_SUBCONTRACT_MINOR_VERSION,
    SUPPORTED_EFFECT_SUBCONTRACT_MAJOR_VERSIONS,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.enums.enum_execution_order import EnumExecutionOrder
from omnibase_core.enums.enum_state_management import EnumIsolationLevel
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.model_effect_retry_config import (
    ModelEffectRetryConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "ModelEffectCircuitBreaker",
    "ModelEffectTransactionConfig",
    "ModelEffectResponseHandling",
    "ModelEffectObservability",
    "ModelEffectOperation",
    "ModelEffectSubcontract",
]


# Idempotency defaults by handler type and operation.
#
# Type Safety Note:
# Keys correspond to EnumEffectHandlerType values (http, db, kafka, filesystem)
# and inner keys match the Literal types in IO configs:
#   - HTTP: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] (ModelHttpIOConfig.method)
#   - DB: Literal["select", "insert", "update", "delete", "upsert", "raw"] (ModelDbIOConfig.operation)
#   - Filesystem: Literal["read", "write", "delete", "move", "copy"] (ModelFilesystemIOConfig.operation)
#
# Using string keys here rather than enum values for dict access simplicity.
# The get_effective_idempotency() method handles type-safe access via isinstance checks.
IDEMPOTENCY_DEFAULTS: dict[str, dict[str, bool]] = {
    "http": {
        "GET": True,
        "POST": False,
        "PUT": True,
        "PATCH": True,
        "DELETE": True,
    },
    "db": {
        "select": True,
        "insert": False,
        "update": False,
        "delete": False,
        "upsert": False,
        "raw": False,
    },
    "kafka": {
        # Kafka is always non-idempotent due to at-least-once semantics
        "all": False,
    },
    "filesystem": {
        "read": True,
        "write": False,
        "delete": False,
        "move": False,
        "copy": False,
    },
}


class ModelEffectCircuitBreaker(BaseModel):
    """
    Circuit breaker configuration for effect operations.

    Simplified circuit breaker config that prevents cascading failures by
    "opening" the circuit after a threshold of consecutive failures.

    State Transitions:
        CLOSED (normal) -> OPEN (failures exceed threshold)
        OPEN (failing) -> HALF_OPEN (timeout expires, testing recovery)
        HALF_OPEN (testing) -> CLOSED (success_threshold met) or OPEN (failure)

    Attributes:
        enabled: Whether circuit breaker is active for this operation.
        failure_threshold: Number of consecutive failures before opening circuit.
        success_threshold: Number of consecutive successes in HALF_OPEN to close.
        timeout_ms: Milliseconds to wait in OPEN state before entering HALF_OPEN.
        half_open_requests: Max requests to allow in HALF_OPEN state for testing.

    Example:
        >>> config = ModelEffectCircuitBreaker(
        ...     enabled=True,
        ...     failure_threshold=5,
        ...     success_threshold=2,
        ...     timeout_ms=60000,
        ... )
    """

    enabled: bool = Field(
        default=False,
        description="Whether circuit breaker is active",
    )

    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Consecutive failures before opening circuit (1-100)",
    )

    success_threshold: int = Field(
        default=2,
        ge=1,
        le=50,
        description="Consecutive successes in HALF_OPEN to close (1-50)",
    )

    timeout_ms: int = Field(
        default=60000,
        ge=1000,
        le=3600000,
        description="Milliseconds in OPEN state before HALF_OPEN (1s - 1h)",
    )

    half_open_requests: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Max requests in HALF_OPEN state (1-10)",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelEffectTransactionConfig(BaseModel):
    """
    Transaction boundary configuration for database operations.

    WARNING: Only applicable to DB handler type. Using transaction config
    with non-DB handlers will be ignored.

    Provides ACID transaction semantics for database operations with
    configurable isolation levels and rollback behavior.

    Attributes:
        enabled: Whether to wrap operation in a transaction.
        isolation_level: SQL transaction isolation level (READ_COMMITTED, etc.).
        rollback_on_error: Automatically rollback transaction on errors.
        timeout_ms: Transaction timeout in milliseconds.

    Example:
        >>> config = ModelEffectTransactionConfig(
        ...     enabled=True,
        ...     isolation_level=EnumIsolationLevel.REPEATABLE_READ,
        ...     rollback_on_error=True,
        ...     timeout_ms=30000,
        ... )
    """

    enabled: bool = Field(
        default=False,
        description="Whether to use transaction boundaries (DB only)",
    )

    isolation_level: EnumIsolationLevel = Field(
        default=EnumIsolationLevel.READ_COMMITTED,
        description="Transaction isolation level",
    )

    rollback_on_error: bool = Field(
        default=True,
        description="Automatically rollback on errors",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=600000,
        description="Transaction timeout in milliseconds (1s - 10min)",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelEffectResponseHandling(BaseModel):
    """
    Response extraction and validation configuration.

    Defines how to extract data from effect responses, which status codes
    indicate success, and whether to fail on empty responses.

    Attributes:
        success_codes: HTTP status codes or DB row counts considered successful.
        extract_fields: Dict mapping output field names to extraction paths.
        fail_on_empty: Whether to fail if response is empty/null.
        extraction_engine: Engine for path-based extraction (jsonpath, jq, xpath).

    Example:
        >>> config = ModelEffectResponseHandling(
        ...     success_codes=[200, 201, 204],
        ...     extract_fields={"user_id": "$.data.id", "email": "$.data.email"},
        ...     fail_on_empty=True,
        ...     extraction_engine="jsonpath",
        ... )
    """

    success_codes: list[int] = Field(
        default_factory=lambda: [200, 201, 204],
        description="Status codes or row counts indicating success",
    )

    extract_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of output field names to extraction paths",
    )

    fail_on_empty: bool = Field(
        default=False,
        description="Whether to fail if response is empty/null",
    )

    extraction_engine: str = Field(
        default="jsonpath",
        description="Engine for path-based extraction (jsonpath, jq, xpath)",
    )

    @field_validator("extraction_engine")
    @classmethod
    def validate_extraction_engine(cls, value: str) -> str:
        """Validate extraction engine is supported."""
        allowed = {"jsonpath", "jq", "xpath"}
        if value not in allowed:
            raise ModelOnexError(
                message=f"extraction_engine must be one of {allowed}, got '{value}'",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "extraction_engine_validation"
                        ),
                        "allowed_engines": ModelSchemaValue.from_value(list(allowed)),
                        "provided_engine": ModelSchemaValue.from_value(value),
                    }
                ),
            )
        return value

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelEffectObservability(BaseModel):
    """
    Logging, metrics, and tracing configuration for effect operations.

    Defines what telemetry to emit during effect execution for debugging,
    monitoring, and distributed tracing.

    Attributes:
        log_request: Whether to log outgoing requests (WARNING: may log sensitive data).
        log_response: Whether to log responses (WARNING: may log sensitive data).
        emit_metrics: Whether to emit performance/success metrics.
        trace_propagation: Whether to propagate distributed trace context.

    Example:
        >>> config = ModelEffectObservability(
        ...     log_request=False,  # Contains sensitive data
        ...     log_response=False,
        ...     emit_metrics=True,
        ...     trace_propagation=True,
        ... )
    """

    log_request: bool = Field(
        default=False,
        description="Log outgoing requests (may contain sensitive data)",
    )

    log_response: bool = Field(
        default=False,
        description="Log responses (may contain sensitive data)",
    )

    emit_metrics: bool = Field(
        default=True,
        description="Emit performance and success metrics",
    )

    trace_propagation: bool = Field(
        default=True,
        description="Propagate distributed trace context",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelEffectOperation(BaseModel):
    """
    Single effect operation specification.

    Defines a single external side effect with its IO configuration, retry policy,
    circuit breaker, transaction settings, and observability configuration.

    Operations use discriminated union IO configs to support multiple handler types
    (HTTP, DB, Kafka, Filesystem) in a type-safe manner.

    Attributes:
        operation_id: Unique identifier for this operation (correlation tracking).
        operation_name: Human-readable name for the operation.
        description: Detailed description of what this operation does.
        io_config: Handler-specific IO configuration (discriminated union).
        retry_policy: Operation-specific retry policy (overrides default).
        circuit_breaker: Operation-specific circuit breaker (overrides default).
        transaction_config: Transaction configuration (DB operations only).
        response_handling: Response extraction and validation configuration.
        observability: Logging, metrics, and tracing configuration.
        operation_timeout_ms: Maximum execution time for this operation.
        idempotent: Whether operation is idempotent (defaults based on handler type).

    Example:
        >>> from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import ModelHttpIOConfig
        >>> operation = ModelEffectOperation(
        ...     operation_name="CreateUser",
        ...     description="Create user via REST API",
        ...     io_config=ModelHttpIOConfig(
        ...         url_template="https://api.example.com/users",
        ...         method="POST",
        ...         body_template='{"name": "${input.name}"}',
        ...     ),
        ... )
    """

    # Identity
    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique operation identifier for correlation tracking",
    )

    operation_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable operation name",
    )

    description: str = Field(
        default="",
        max_length=1000,
        description="Detailed operation description",
    )

    # IO Configuration (discriminated union)
    io_config: EffectIOConfig = Field(
        ...,
        description="Handler-specific IO configuration",
    )

    # Resilience configurations (operation-level overrides)
    retry_policy: ModelEffectRetryConfig | None = Field(
        default=None,
        description="Operation-specific retry policy (overrides default)",
    )

    circuit_breaker: ModelEffectCircuitBreaker | None = Field(
        default=None,
        description="Operation-specific circuit breaker (overrides default)",
    )

    transaction_config: ModelEffectTransactionConfig | None = Field(
        default=None,
        description="Transaction configuration (DB operations only)",
    )

    # Response and observability
    response_handling: ModelEffectResponseHandling = Field(
        default_factory=ModelEffectResponseHandling,
        description="Response extraction and validation",
    )

    observability: ModelEffectObservability = Field(
        default_factory=ModelEffectObservability,
        description="Logging, metrics, and tracing configuration",
    )

    # Execution constraints
    operation_timeout_ms: int | None = Field(
        default=None,
        ge=1000,
        le=3600000,
        description="Maximum execution time (1s - 1h)",
    )

    idempotent: bool | None = Field(
        default=None,
        description="Whether operation is idempotent (auto-detected if None)",
    )

    @model_validator(mode="after")
    def validate_transaction_config_for_db_only(self) -> "ModelEffectOperation":
        """
        Warn if transaction_config is used with non-DB handler types.

        Transaction semantics only apply to database operations. Using
        transaction_config with HTTP/Kafka/Filesystem handlers is a
        configuration mistake that should be caught early.
        """
        if self.transaction_config is not None and self.transaction_config.enabled:
            handler_type = self.io_config.handler_type
            if handler_type != EnumEffectHandlerType.DB:
                raise ModelOnexError(
                    message=f"transaction_config is only applicable to DB handlers, "
                    f"but handler_type is '{handler_type.value}'",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "transaction_config_handler_validation"
                            ),
                            "handler_type": ModelSchemaValue.from_value(
                                handler_type.value
                            ),
                        }
                    ),
                )
        return self

    def get_effective_idempotency(self) -> bool:
        """
        Get effective idempotency status for this operation.

        Returns explicitly set idempotent value, or computes default based
        on handler type and operation method/type.

        Returns:
            True if operation is idempotent, False otherwise.

        Example:
            >>> # HTTP POST - defaults to non-idempotent
            >>> http_op = ModelEffectOperation(
            ...     operation_name="CreateUser",
            ...     io_config=ModelHttpIOConfig(
            ...         url_template="https://api.example.com/users",
            ...         method="POST",
            ...         body_template="{}",
            ...     ),
            ... )
            >>> assert http_op.get_effective_idempotency() is False
            >>>
            >>> # HTTP GET - defaults to idempotent
            >>> get_op = ModelEffectOperation(
            ...     operation_name="GetUser",
            ...     io_config=ModelHttpIOConfig(
            ...         url_template="https://api.example.com/users/123",
            ...         method="GET",
            ...     ),
            ... )
            >>> assert get_op.get_effective_idempotency() is True
            >>>
            >>> # Explicit override
            >>> explicit_op = ModelEffectOperation(
            ...     operation_name="IdempotentPost",
            ...     io_config=ModelHttpIOConfig(
            ...         url_template="https://api.example.com/idempotent",
            ...         method="POST",
            ...         body_template="{}",
            ...     ),
            ...     idempotent=True,  # Explicit override
            ... )
            >>> assert explicit_op.get_effective_idempotency() is True
        """
        # Return explicit value if set
        if self.idempotent is not None:
            return self.idempotent

        # Compute default based on handler type
        handler_type = self.io_config.handler_type

        # Import concrete types for type narrowing.
        # NOTE: isinstance checks are required here for type narrowing because:
        # 1. io_config is typed as a Union (EffectIOConfig), not a specific type
        # 2. The discriminated union pattern requires runtime type checking to access
        #    type-specific fields like 'method' (HTTP) or 'operation' (DB/Filesystem)
        # 3. Duck-typing via hasattr() wouldn't provide mypy type narrowing
        # 4. This is a standard Pydantic discriminated union access pattern
        from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
            ModelDbIOConfig,
            ModelFilesystemIOConfig,
            ModelHttpIOConfig,
            ModelKafkaIOConfig,
        )

        if handler_type == EnumEffectHandlerType.HTTP:
            # HTTP idempotency based on method
            if isinstance(self.io_config, ModelHttpIOConfig):
                return IDEMPOTENCY_DEFAULTS["http"].get(self.io_config.method, False)

        elif handler_type == EnumEffectHandlerType.DB:
            # DB idempotency based on operation type
            if isinstance(self.io_config, ModelDbIOConfig):
                return IDEMPOTENCY_DEFAULTS["db"].get(self.io_config.operation, False)

        elif handler_type == EnumEffectHandlerType.KAFKA:
            # Kafka is always non-idempotent (at-least-once)
            return IDEMPOTENCY_DEFAULTS["kafka"]["all"]

        elif handler_type == EnumEffectHandlerType.FILESYSTEM:
            # Filesystem idempotency based on operation type
            if isinstance(self.io_config, ModelFilesystemIOConfig):
                return IDEMPOTENCY_DEFAULTS["filesystem"].get(
                    self.io_config.operation, False
                )

        # Default to non-idempotent for unknown handlers
        return False

    model_config = ConfigDict(frozen=True, extra="forbid")


class ModelEffectSubcontract(BaseModel):
    """
    v1.0 Effect subcontract for declarative side effect operations.

    Defines effect operations with retry policies, circuit breakers, transaction
    boundaries, and observability. Operations can execute sequentially, in parallel,
    or with fail-fast semantics.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it safe
        for concurrent read access from multiple threads or async tasks.

    Contract Versioning:
        The version field tracks the subcontract schema version. This allows
        schema evolution while preserving existing contracts for backward
        compatibility.

    Default Policies:
        Default retry, circuit breaker, and transaction configs apply to ALL
        operations unless explicitly overridden at the operation level.

    Execution Orders:
        - FORWARD: Operations run one after another in definition order (preserves ordering)
        - REVERSE: Operations run in reverse order (useful for rollback/cleanup)
        - PARALLEL: Operations run concurrently (best performance)

    Attributes:
        version: Semantic version of the subcontract schema format.
        operation_name: Unique name identifying this effect operation set.
        operation_version: Semantic version of this operation implementation.
        description: Human-readable description of the operation set.
        operations: List of effect operations to execute.
        default_retry_policy: Default retry policy for all operations.
        default_circuit_breaker: Default circuit breaker for all operations.
        default_transaction_config: Default transaction config (DB operations only).
        execution_order: Order in which to execute operations (forward, reverse, parallel).
        correlation_id: Unique identifier for tracking related operations.

    Example:
        >>> from omnibase_core.models.contracts.subcontracts import ModelEffectSubcontract
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> contract = ModelEffectSubcontract(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     operation_name="user_creation_flow",
        ...     operation_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     description="Create user and publish events",
        ...     execution_order=EnumExecutionOrder.FORWARD,
        ...     operations=[...],
        ... )
    """

    # Identity
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Subcontract schema version",
    )

    operation_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Unique operation set name",
    )

    operation_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Operation implementation version",
    )

    description: str = Field(
        default="",
        max_length=2000,
        description="Human-readable description",
    )

    # Operations list
    operations: list[ModelEffectOperation] = Field(
        ...,
        min_length=1,
        description="List of effect operations to execute",
    )

    # Default policies (apply to all operations unless overridden)
    default_retry_policy: ModelEffectRetryConfig = Field(
        default_factory=ModelEffectRetryConfig,
        description="Default retry policy for all operations",
    )

    default_circuit_breaker: ModelEffectCircuitBreaker = Field(
        default_factory=ModelEffectCircuitBreaker,
        description="Default circuit breaker for all operations",
    )

    default_transaction_config: ModelEffectTransactionConfig = Field(
        default_factory=ModelEffectTransactionConfig,
        description="Default transaction config (DB operations only)",
    )

    # Execution configuration
    execution_order: EnumExecutionOrder = Field(
        default=EnumExecutionOrder.FORWARD,
        description="Execution order: forward, reverse, or parallel",
    )

    # Tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID for tracking related operations",
    )

    @field_validator("version")
    @classmethod
    def validate_contract_version(cls, v: ModelSemVer) -> ModelSemVer:
        """
        Validate that the contract version is supported by this runtime.

        Contract version validation ensures:
        1. The major version is in the supported set (breaking changes)
        2. The minor version meets the minimum requirements (feature availability)

        This prevents runtime errors when loading contracts with incompatible
        schema versions. Major version bumps indicate breaking changes that
        require code updates. Minor version requirements ensure expected
        features are available.

        Args:
            v: Semantic version of the subcontract.

        Returns:
            The validated version.

        Raises:
            ModelOnexError: If the version is not supported.

        Example:
            >>> # Valid version
            >>> subcontract = ModelEffectSubcontract(
            ...     version=ModelSemVer(major=1, minor=0, patch=0),
            ...     operation_name="test",
            ...     operation_version=ModelSemVer(major=1, minor=0, patch=0),
            ...     operations=[...],
            ... )
            >>>
            >>> # Invalid major version - raises ModelOnexError
            >>> subcontract = ModelEffectSubcontract(
            ...     version=ModelSemVer(major=99, minor=0, patch=0),  # Not supported
            ...     ...
            ... )
        """
        if v.major not in SUPPORTED_EFFECT_SUBCONTRACT_MAJOR_VERSIONS:
            supported_versions = sorted(SUPPORTED_EFFECT_SUBCONTRACT_MAJOR_VERSIONS)
            raise ModelOnexError(
                message=f"Unsupported effect subcontract major version: {v.major}. "
                f"Supported major versions: {supported_versions}. "
                f"Please upgrade the contract or use a compatible runtime version.",
                error_code=EnumCoreErrorCode.VERSION_INCOMPATIBLE,
                context={
                    "provided_version": str(v),
                    "provided_major": v.major,
                    "supported_major_versions": supported_versions,
                },
            )

        # Check minimum minor version for the major version
        if v.minor < MIN_EFFECT_SUBCONTRACT_MINOR_VERSION:
            raise ModelOnexError(
                message=f"Effect subcontract minor version {v.minor} is below minimum "
                f"required version {MIN_EFFECT_SUBCONTRACT_MINOR_VERSION} for major "
                f"version {v.major}. Some required features may be missing.",
                error_code=EnumCoreErrorCode.VERSION_INCOMPATIBLE,
                context={
                    "provided_version": str(v),
                    "provided_minor": v.minor,
                    "minimum_minor": MIN_EFFECT_SUBCONTRACT_MINOR_VERSION,
                    "major_version": v.major,
                },
            )

        return v

    @field_validator("operations")
    @classmethod
    def validate_unique_operation_names(
        cls, v: list[ModelEffectOperation]
    ) -> list[ModelEffectOperation]:
        """
        Validate that all operation names are unique within the subcontract.

        Each operation must have a unique operation_name to enable unambiguous
        references in logs, metrics, and error handling.

        Args:
            v: List of operations to validate.

        Returns:
            The validated list of operations.

        Raises:
            ModelOnexError: If duplicate operation names are found.
        """
        if v:
            operation_names = [op.operation_name for op in v]
            if len(operation_names) != len(set(operation_names)):
                # Find duplicates for better error message
                seen: set[str] = set()
                duplicates: list[str] = []
                for name in operation_names:
                    if name in seen and name not in duplicates:
                        duplicates.append(name)
                    seen.add(name)
                raise ModelOnexError(
                    message=f"Operation names must be unique. Duplicates found: {duplicates}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "operation_name_uniqueness"
                            ),
                            "duplicates": ModelSchemaValue.from_value(duplicates),
                        }
                    ),
                )
        return v

    # NOTE: Single-operation subcontracts with PARALLEL or REVERSE execution_order
    # are technically valid (PARALLEL has no effect, REVERSE just executes the
    # single operation). No validation is performed since these configurations
    # don't cause errors - they're just potentially confusing. Consider adding
    # a diagnostic warning in a future version if this causes user confusion.

    model_config = ConfigDict(frozen=True, extra="forbid")
