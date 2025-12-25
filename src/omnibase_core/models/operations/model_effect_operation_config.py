# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

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
from typing_extensions import TypeIs

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH,
    EFFECT_OPERATION_NAME_MAX_LENGTH,
)
from omnibase_core.models.contracts.subcontracts.model_effect_circuit_breaker import (
    ModelEffectCircuitBreaker,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    EffectIOConfig,
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_response_handling import (
    ModelEffectResponseHandling,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)

__all__ = ["ModelEffectOperationConfig"]


# Type alias for the union of all typed IO config models
_TypedIOConfigUnion = (
    ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig
)


def _is_typed_io_config(
    config: _TypedIOConfigUnion
    | dict[str, Any],  # ONEX_EXCLUDE: dict_str_any - TypeIs narrowing
) -> TypeIs[_TypedIOConfigUnion]:
    """TypeIs predicate to check if io_config is already a typed EffectIOConfig model.

    Uses TypeIs (PEP 742) for bidirectional type narrowing. Unlike TypeGuard,
    TypeIs narrows the type in both branches:
    - Positive branch: config is _TypedIOConfigUnion
    - Negative branch: config is dict[str, Any]

    This enables mypy to understand type narrowing when checking if io_config
    is already parsed into a typed model vs. a raw dictionary.

    Args:
        config: The io_config value, either typed or dict.

    Returns:
        True if config is one of the typed IO config models, False if dict.

    """
    return isinstance(
        config,
        (
            ModelHttpIOConfig,
            ModelDbIOConfig,
            ModelKafkaIOConfig,
            ModelFilesystemIOConfig,
        ),
    )


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
    # dict-any-ok: accepts both typed models and dicts for parsing flexibility
    io_config: Annotated[
        ModelHttpIOConfig
        | ModelDbIOConfig
        | ModelKafkaIOConfig
        | ModelFilesystemIOConfig
        | dict[str, Any],  # ONEX_EXCLUDE: dict_str_any - typed model union
        Field(
            description="Handler-specific IO configuration. Can be a typed model "
            "or a dict that will be parsed based on handler_type."
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
        "Defaults to 30000ms via DEFAULT_OPERATION_TIMEOUT_MS.",
    )

    # Response handling configuration
    # ONEX_EXCLUDE: dict_str_any - typed model union for flexibility
    response_handling: ModelEffectResponseHandling | dict[str, Any] | None = Field(
        default=None,
        description="Configuration for response interpretation and field extraction",
    )

    # Resilience configurations (per-operation overrides)
    # ONEX_EXCLUDE: dict_str_any - typed model union for flexibility
    retry_policy: ModelEffectRetryPolicy | dict[str, Any] | None = Field(
        default=None,
        description="Per-operation retry policy configuration",
    )
    # ONEX_EXCLUDE: dict_str_any - typed model union for flexibility
    circuit_breaker: ModelEffectCircuitBreaker | dict[str, Any] | None = Field(
        default=None,
        description="Per-operation circuit breaker configuration",
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
                raise ValueError("io_config is required")
        return data

    # ONEX_EXCLUDE: dict_str_any - serialization output
    def get_io_config_as_dict(self) -> dict[str, Any]:
        """Get io_config as a dictionary.

        Useful when the mixin needs to pass io_config to _parse_io_config
        which expects a dict structure.

        Performance Note:
            This method uses an early-return pattern to avoid unnecessary
            serialization. If io_config is already a dict, it returns directly.
            The model_dump() path is only hit when io_config is a typed model.

            In practice, callers (like MixinEffectExecution._parse_io_config)
            check isinstance() before calling this method, so the model_dump()
            path is rarely executed. When it is, Pydantic v2's Rust-based
            model_dump() is highly optimized.

            Caching via @cached_property is not used because frozen=True
            prevents attribute assignment on the instance.

        Returns:
            Dict representation of io_config.

        """
        if isinstance(self.io_config, dict):
            return self.io_config
        return self.io_config.model_dump()

    # ONEX_EXCLUDE: dict_str_any - serialization output
    def get_response_handling_as_dict(self) -> dict[str, Any]:
        """Get response_handling as a dictionary.

        Performance Note:
            Similar to get_io_config_as_dict(), this method uses early returns
            to avoid unnecessary serialization:
            - Returns {} immediately if response_handling is None
            - Returns the dict directly if already a dict
            - Only calls model_dump() when response_handling is a typed model

            This method returns dict format for callers that require it.
            Production code typically uses the typed ModelEffectResponseHandling
            directly via the response_handling attribute.

            Caching is not implemented because:
            1. The model is frozen (prevents @cached_property)
            2. The method is not called repeatedly on the same instance
            3. Pydantic v2's model_dump() is Rust-optimized

        Returns:
            Dict representation of response_handling, or empty dict if None.

        """
        if self.response_handling is None:
            return {}
        if isinstance(self.response_handling, dict):
            return self.response_handling
        return self.response_handling.model_dump()

    def get_typed_io_config(self) -> _TypedIOConfigUnion:
        """Get io_config as a typed EffectIOConfig.

        Uses TypeIs-based type narrowing (PEP 742) to properly narrow the return
        type. Unlike TypeGuard, TypeIs provides bidirectional narrowing:
        - Positive branch: config is _TypedIOConfigUnion
        - Negative branch: config is dict[str, Any]

        Parses dict io_config into the appropriate typed model based on
        handler_type discriminator.

        Returns:
            Typed IO config (ModelHttpIOConfig, ModelDbIOConfig,
            ModelKafkaIOConfig, or ModelFilesystemIOConfig). The return type
            is properly narrowed by the TypeIs predicate, enabling mypy to
            understand that the result is always a typed model, never a dict.

        Raises:
            ValueError: If handler_type is unknown or io_config is invalid.

        Example:
            >>> config = ModelEffectOperationConfig(
            ...     io_config={"handler_type": "http", "url_template": "...", "method": "GET"}
            ... )
            >>> typed = config.get_typed_io_config()
            >>> # mypy knows typed is _TypedIOConfigUnion, not dict
            >>> assert hasattr(typed, "handler_type")

        """
        # TypeIs narrows self.io_config to _TypedIOConfigUnion in positive branch
        # and to dict[str, Any] in negative branch
        if _is_typed_io_config(self.io_config):
            return self.io_config

        # At this point, mypy knows self.io_config is dict[str, Any]
        # Parse dict to typed model using match statement for cleaner type handling
        handler_type = self.io_config.get("handler_type")
        match handler_type:
            case "http":
                return ModelHttpIOConfig.model_validate(self.io_config)
            case "db":
                return ModelDbIOConfig.model_validate(self.io_config)
            case "kafka":
                return ModelKafkaIOConfig.model_validate(self.io_config)
            case "filesystem":
                return ModelFilesystemIOConfig.model_validate(self.io_config)
            case _:
                from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
                from omnibase_core.models.errors.model_onex_error import ModelOnexError

                raise ModelOnexError(
                    f"Unknown handler_type: {handler_type}",
                    error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
                )

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
