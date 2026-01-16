"""Effect Operation Configuration Model.

Provides a typed model to replace dict[str, Any] usage for operation_config
parameters in MixinEffectExecution. This model supports both direct attribute
access and factory methods for creating from dictionaries.

This model is distinct from ModelEffectOperation:
- ModelEffectOperation: Full effect operation definition with strict validation
- ModelEffectOperationConfig: Runtime configuration during mixin execution,
  supporting both typed and serialized (dict) data patterns

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

See Also:
    - MixinEffectExecution: Primary consumer of this model
    - ModelEffectOperation: Full operation definition model
    - ModelEffectResponseHandling: Response handling configuration
    - ModelEffectRetryPolicy: Retry policy configuration
    - ModelEffectCircuitBreaker: Circuit breaker configuration

"""

from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH,
    EFFECT_OPERATION_NAME_MAX_LENGTH,
)
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
    ModelEffectCircuitBreaker,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
    ModelEffectResponseHandling,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_transaction_config import (
    ModelEffectTransactionConfig,
)

__all__ = ["ModelEffectOperationConfig"]


class ModelEffectOperationConfig(BaseModel):
    """Runtime configuration for a single effect operation.

    This model provides type safety for operation_config parameters in
    MixinEffectExecution methods. It replaces dict[str, Any] usage while
    maintaining flexibility to accept both typed Pydantic models and
    serialized dictionaries for nested configurations.

    The io_config field uses a discriminated union based on handler_type,
    ensuring type-safe validation. When provided as a dict, it will be
    automatically parsed into the appropriate typed model.

    Attributes:
        io_config: Handler-specific IO configuration. This is the core
            configuration that defines the operation type and parameters.
            Uses discriminated union based on handler_type field.
        operation_name: Human-readable name for the operation. Used for
            logging and error context. Defaults to "unknown".
        description: Optional description of what the operation does.
        operation_timeout_ms: Overall timeout for the operation including
            all retries. If None, uses DEFAULT_OPERATION_TIMEOUT_MS (30s).
        response_handling: Configuration for interpreting operation responses,
            including success codes and field extraction.
        retry_policy: Per-operation retry policy configuration.
        circuit_breaker: Per-operation circuit breaker configuration.
        transaction_config: Transaction configuration for DB operations.
            Only applicable when the operation uses a database handler.
        correlation_id: Optional correlation ID for tracing.
        idempotent: Whether the operation is idempotent (safe to retry).

    Example:
        >>> from omnibase_core.models.operations import ModelEffectOperationConfig
        >>> from omnibase_core.models.contracts.subcontracts import ModelHttpIOConfig
        >>>
        >>> config = ModelEffectOperationConfig(
        ...     io_config=ModelHttpIOConfig(
        ...         handler_type="http",
        ...         url_template="https://api.example.com/users/${input.user_id}",
        ...         method="GET",
        ...     ),
        ...     operation_name="fetch_user",
        ...     operation_timeout_ms=5000,
        ... )

        >>> # Creating from a dictionary
        >>> config = ModelEffectOperationConfig.model_validate({
        ...     "io_config": {
        ...         "handler_type": "http",
        ...         "url_template": "https://api.example.com/users/123",
        ...         "method": "GET",
        ...     },
        ...     "operation_name": "fetch_user",
        ... })

    See Also:
        - MixinEffectExecution._parse_io_config: Parses io_config to typed model
        - MixinEffectExecution._execute_with_retry: Uses this config for retries
        - ModelEffectOperation: Full operation definition model

    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # Core configuration - io_config is required
    # Uses discriminated union based on handler_type field
    io_config: Annotated[
        EffectIOConfig,
        Field(
            description="Handler-specific IO configuration. Uses discriminated union "
            "based on handler_type field (http, db, kafka, filesystem)."
        ),
    ]

    # Operation metadata
    operation_name: str = Field(
        default="unknown",
        min_length=1,
        max_length=EFFECT_OPERATION_NAME_MAX_LENGTH,
        description="Human-readable operation name for logging and error context",
    )
    description: str | None = Field(
        default=None,
        max_length=EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH,
        description="Optional description of the operation",
    )

    # Timeout configuration
    # NOTE: Unlike ModelEffectOperation (contract definition), this runtime config
    # does not enforce strict timeout bounds. This allows flexibility for testing
    # and dynamic configuration. The contract model (ModelEffectOperation) enforces
    # EFFECT_TIMEOUT_MIN_MS and EFFECT_TIMEOUT_MAX_MS for production contracts.
    operation_timeout_ms: int | None = Field(
        default=None,
        ge=1,  # At least 1ms to be valid
        description="Overall operation timeout including retries. "
        "Defaults to TIMEOUT_DEFAULT_MS (30 seconds). "
        "See omnibase_core.constants for timeout constant values.",
    )

    # Response handling configuration
    response_handling: ModelEffectResponseHandling | None = Field(
        default=None,
        description="Configuration for response interpretation and field extraction",
    )

    # Resilience configurations (per-operation overrides)
    retry_policy: ModelEffectRetryPolicy | None = Field(
        default=None,
        description="Per-operation retry policy configuration",
    )
    circuit_breaker: ModelEffectCircuitBreaker | None = Field(
        default=None,
        description="Per-operation circuit breaker configuration",
    )
    transaction_config: ModelEffectTransactionConfig | None = Field(
        default=None,
        description="Transaction configuration for DB operations",
    )

    # Correlation and idempotency
    correlation_id: UUID | str | None = Field(
        default=None,
        description="Optional correlation ID for distributed tracing",
    )
    idempotent: bool | None = Field(
        default=None,
        description="Whether operation is idempotent (safe to retry)",
    )

    @model_validator(mode="before")
    @classmethod
    def _validate_io_config_type(cls, data: Any) -> Any:
        """Validate that io_config is present and properly structured.

        This pre-validation hook runs before Pydantic's field validation.
        It ensures the required io_config field exists when input is a dict.
        If io_config is a dict without handler_type, the discriminated union
        validation will fail later with a more specific error.

        Args:
            data: Raw input data, typically a dict from JSON/YAML or
                another Pydantic model's model_dump() output.

        Returns:
            The validated data unchanged if validation passes.

        Raises:
            ValueError: If data is a dict and io_config key is missing.

        Note:
            This validator does not check handler_type validity; that is
            handled by the discriminated union validation on the io_config
            field itself.

        """
        if isinstance(data, dict):
            io_config = data.get("io_config")
            if io_config is None:
                # io_config is required
                # error-ok: Pydantic validator requires ValueError
                raise ValueError("io_config is required")
        return data

    @allow_dict_any(reason="Serialization method for io_config")
    def get_io_config_as_dict(self) -> dict[str, Any]:
        """Get io_config as a dictionary.

        Useful for serialization or when dict representation is needed.

        Returns:
            Dict representation of io_config.
        """
        return self.io_config.model_dump()

    @allow_dict_any(reason="Serialization method for response_handling")
    def get_response_handling_as_dict(self) -> dict[str, Any]:
        """Get response_handling as a dictionary.

        Returns:
            Dict representation of response_handling, or empty dict if None.
        """
        if self.response_handling is None:
            return {}
        return self.response_handling.model_dump()

    def get_typed_io_config(self) -> EffectIOConfig:
        """Get io_config as a typed EffectIOConfig.

        Returns:
            Typed IO config (ModelHttpIOConfig, ModelDbIOConfig,
            ModelKafkaIOConfig, or ModelFilesystemIOConfig).
        """
        return self.io_config

    # ONEX_EXCLUDE: dict_str_any - factory input
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelEffectOperationConfig":
        """Create a ModelEffectOperationConfig from a dictionary.

        This factory method provides explicit conversion from dict,
        which is useful when migrating from dict[str, Any] patterns.

        Args:
            data: Dictionary containing operation configuration.

        Returns:
            Validated ModelEffectOperationConfig instance.

        Note:
            This method does NOT mutate the input dictionary. Pydantic's
            model_validate handles conversion without modifying the source.

        Example:
            >>> config = ModelEffectOperationConfig.from_dict({
            ...     "io_config": {"handler_type": "http", "url_template": "...", "method": "GET"},
            ...     "operation_name": "my_op",
            ... })

        """
        return cls.model_validate(data)

    @classmethod
    def from_effect_operation(
        cls,
        operation: Any,  # ModelEffectOperation, avoiding circular import
    ) -> "ModelEffectOperationConfig":
        """Create a ModelEffectOperationConfig from a ModelEffectOperation.

        This factory method converts the full operation definition (used in
        YAML contracts) into the runtime configuration format consumed by
        MixinEffectExecution methods. It preserves all configuration fields
        while adapting to the runtime context.

        Args:
            operation: A ModelEffectOperation instance containing the full
                operation definition. Type hint is Any to avoid circular
                imports (ModelEffectOperation imports from this module).

        Returns:
            ModelEffectOperationConfig with all applicable values copied
            from the operation. Fields not present in ModelEffectOperation
            (like extra fields from extra="allow") are not copied.

        Example:
            Converting a contract operation to runtime config::

                from omnibase_core.models.contracts import ModelEffectOperation

                # Full operation definition from YAML contract
                operation = ModelEffectOperation(
                    operation_name="fetch_user",
                    io_config=ModelHttpIOConfig(
                        handler_type="http",
                        url_template="https://api.example.com/users/${input.id}",
                        method="GET",
                    ),
                    operation_timeout_ms=5000,
                    retry_policy=ModelEffectRetryPolicy(max_retries=3),
                )

                # Convert to runtime config for mixin execution
                config = ModelEffectOperationConfig.from_effect_operation(operation)
                assert config.operation_name == "fetch_user"
                assert config.operation_timeout_ms == 5000

        See Also:
            - ModelEffectOperation: Full operation definition model
            - MixinEffectExecution: Consumes this runtime config

        """
        return cls(
            io_config=operation.io_config,
            operation_name=operation.operation_name,
            description=operation.description,
            operation_timeout_ms=operation.operation_timeout_ms,
            response_handling=operation.response_handling,
            retry_policy=operation.retry_policy,
            circuit_breaker=operation.circuit_breaker,
            correlation_id=operation.correlation_id,
            idempotent=operation.idempotent,
        )
