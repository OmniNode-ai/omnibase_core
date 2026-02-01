"""Effect operation data context model for effect node inputs.

This module provides ModelEffectInputData, a typed context model for
describing effect operation targets, parameters, and operational characteristics.
Used as a typed context parameter in Generic patterns for effect operations.

Thread Safety:
    ModelEffectInputData instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

Note:
    This context model describes WHAT an effect operation targets. For execution
    configuration (retries, timeouts, circuit breakers), see ModelEffectInput.
    For retry state tracking, see ModelRetryContext.

See Also:
    - ModelEffectInput: Effect input with execution configuration
    - ModelRetryContext: Retry state tracking
    - ModelOperationalContext: Operation-level metadata
    - ModelResourceContext: Resource identification
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_effect_types import EnumEffectType

__all__ = ["ModelEffectInputData"]


class ModelEffectInputData(BaseModel):
    """Typed context for effect operation data.

    This model provides structured fields for describing effect operation
    targets, parameters, and operational characteristics. Use as a typed
    context parameter in Generic patterns for effect operations.

    Use Cases:
        - Effect input operation data typing
        - API call target specification
        - Database operation parameters
        - File operation target identification
        - Event emission configuration
        - Typed operation_data for ModelEffectInput

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        effect_type: Type of side effect operation (DATABASE_OPERATION, API_CALL,
            FILE_OPERATION, etc.). Determines which handler processes the operation.
        resource_path: Target resource path or URI for the effect operation.
            Interpretation depends on effect_type (file path, URL, table name, etc.).
        target_system: Identifier for the target external system (e.g., "postgres",
            "s3", "kafka", "rest-api"). Used for routing and monitoring.
        idempotency_key: Optional key for idempotent operations. When provided,
            duplicate operations with the same key are safely deduplicated.
        operation_name: Human-readable name for the operation. Used for logging,
            tracing, and monitoring dashboards.
        resource_id: Optional UUID identifying a specific resource being operated on.
            Useful for audit trails and cross-referencing.
        content_type: MIME type or content type hint for the operation payload
            (e.g., "application/json", "text/plain").
        encoding: Character encoding for text-based operations (e.g., "utf-8").

    Example:
        API call operation data::

            from omnibase_core.models.context import ModelEffectInputData
            from omnibase_core.enums.enum_effect_types import EnumEffectType

            operation = ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path="https://api.example.com/users",
                target_system="user-service",
                operation_name="create_user",
                content_type="application/json",
            )

        Database operation data::

            operation = ModelEffectInputData(
                effect_type=EnumEffectType.DATABASE_OPERATION,
                resource_path="users",
                target_system="postgres",
                operation_name="insert_user",
            )

        File operation data::

            from uuid import uuid4

            operation = ModelEffectInputData(
                effect_type=EnumEffectType.FILE_OPERATION,
                resource_path="/data/exports/report.json",
                target_system="local-fs",
                operation_name="write_report",
                idempotency_key="report-2024-01-15",
                resource_id=uuid4(),
                content_type="application/json",
                encoding="utf-8",
            )

        Using with ModelEffectInput::

            from omnibase_core.models.effect import ModelEffectInput

            input_data = ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.API_CALL,
                    resource_path="https://api.example.com/users",
                    target_system="user-service",
                    operation_name="fetch_users",
                ),
                timeout_ms=5000,
            )

    See Also:
        - ModelEffectInput: Effect input wrapper with execution configuration
        - ModelRetryContext: For retry-specific state tracking
        - ModelOperationalContext: For operation-level metadata
        - ModelResourceContext: For general resource identification
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    effect_type: EnumEffectType = Field(
        description=(
            "Type of side effect operation (DATABASE_OPERATION, API_CALL, "
            "FILE_OPERATION, etc.) that determines handler routing"
        ),
    )
    resource_path: str | None = Field(
        default=None,
        description=(
            "Target resource path or URI for the effect operation "
            "(interpretation depends on effect_type: file path, URL, table name, etc.)"
        ),
        max_length=4096,
    )
    target_system: str | None = Field(
        default=None,
        description=(
            "Identifier for the target external system (e.g., 'postgres', 's3', "
            "'kafka', 'rest-api') used for routing and monitoring"
        ),
        max_length=256,
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Key for idempotent operations (duplicates with same key are deduplicated)",
        max_length=512,
    )
    operation_name: str | None = Field(
        default=None,
        description="Human-readable name for the operation used in logging and tracing",
        max_length=256,
    )
    resource_id: UUID | None = Field(
        default=None,
        description="UUID identifying the specific resource being operated on",
    )
    content_type: str | None = Field(
        default=None,
        description="MIME type or content type hint for the operation payload (e.g., 'application/json')",
        max_length=256,
    )
    encoding: str | None = Field(
        default=None,
        description="Character encoding for text-based operations (e.g., 'utf-8')",
        max_length=64,
    )
