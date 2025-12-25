"""
Action Model.

Orchestrator-issued Action with lease semantics for single-writer guarantees.
Converted from NamedTuple to Pydantic BaseModel for better validation.

Thread Safety:
    ModelAction is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. This follows
    ONEX thread safety guidelines where action models are frozen to ensure lease
    semantics and epoch tracking remain consistent during distributed coordination.
    Note that this provides shallow immutability - while the model's fields cannot
    be reassigned, mutable field values (like dict/list contents) can still be
    modified. For full thread safety with mutable nested data, use
    model_copy(deep=True) to create independent copies.

    To create a modified copy (e.g., for retry with incremented retry_count):
        new_action = action.model_copy(update={"retry_count": action.retry_count + 1})

Extracted from node_orchestrator.py to eliminate embedded class anti-pattern.

Migration Status (OMN-1008):
    The payload field now accepts typed payloads (ActionPayloadType) in addition
    to the legacy dict[str, Any]. New code should use typed payloads for better
    type safety. Legacy dict usage triggers a deprecation warning.
"""

import logging
import warnings
from datetime import datetime
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.payloads import ActionPayloadType
from omnibase_core.utils.util_decorators import allow_dict_str_any

# Module-level logger for validation diagnostics
_logger = logging.getLogger(__name__)


@allow_dict_str_any(
    "MIGRATION IN PROGRESS (OMN-1008): Action model now supports typed payloads "
    "(ActionPayloadType) and supports legacy dict[str, Any] during migration. "
    "Legacy dict usage is deprecated. Use typed payloads for new code."
)
class ModelAction(BaseModel):
    """
    Orchestrator-issued Action with lease management for single-writer semantics.

    Represents an Action emitted by the Orchestrator to Compute/Reducer nodes
    with single-writer semantics enforced via lease_id and epoch. The lease_id
    proves Orchestrator ownership, while epoch provides optimistic concurrency
    control through monotonically increasing version numbers.

    This model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access from multiple threads or async tasks. Unknown
    fields are rejected (extra='forbid') to ensure strict schema compliance.

    To modify a frozen instance, use model_copy():
        >>> modified = action.model_copy(update={"priority": 5, "retry_count": 1})

    Attributes:
        action_id: Unique identifier for this action (auto-generated UUID).
        action_type: Type of action for execution routing (required).
        target_node_type: Target node type for action execution (1-100 chars, required).
        payload: Action payload data (default empty dict).
        dependencies: List of action IDs this action depends on (default empty list).
        priority: Execution priority (1-10, higher = more urgent, default 1).
        timeout_ms: Execution timeout in ms (100-300000, default 30000). Raises TimeoutError on expiry.
        lease_id: Lease ID proving Orchestrator ownership (required).
        epoch: Monotonically increasing version number (>= 0, required).
        retry_count: Number of retry attempts on failure (0-10, default 0).
        metadata: Action execution metadata with full type safety (default ModelActionMetadata()).
        created_at: Timestamp when action was created (auto-generated).

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_workflow_execution import EnumActionType
        >>> action = ModelAction(
        ...     action_type=EnumActionType.INVOKE,
        ...     target_node_type="compute",
        ...     lease_id=uuid4(),
        ...     epoch=1,
        ...     priority=5,
        ... )

    Converted from NamedTuple to Pydantic BaseModel for:
    - Runtime validation with constraint checking
    - Better type safety via Pydantic's type coercion
    - Serialization support (JSON, dict)
    - Default value handling with factories
    - Lease validation for single-writer semantics
    - Thread safety via immutability (frozen=True)
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action",
    )

    action_type: EnumActionType = Field(
        default=...,
        description="Type of action for execution routing",
    )

    target_node_type: str = Field(
        default=...,
        description="Target node type for action execution",
        min_length=1,
        max_length=100,
    )

    # union-ok: migration_support - Accepts typed payloads (preferred) or legacy dict
    payload: ActionPayloadType | dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Action payload data. Preferred: Use typed payloads from "
            "ActionPayloadType (e.g., ModelDataActionPayload, "
            "ModelTransformationActionPayload). Legacy dict[str, Any] is "
            "supported during migration but deprecated."
        ),
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of action IDs this action depends on",
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    timeout_ms: int = Field(
        default=30000,
        description=(
            "Execution timeout in milliseconds. When exceeded, the action execution "
            "is cancelled and a TimeoutError is raised. The Orchestrator may retry "
            "the action based on retry_count and backoff policy. For long-running "
            "operations (e.g., large file transfers, complex computations), increase "
            "this value up to the maximum of 300000ms (5 minutes). Consider breaking "
            "very long operations into smaller actions with progress checkpoints."
        ),
        ge=100,
        le=300000,  # Max 5 minutes
    )

    # Lease management fields for single-writer semantics
    lease_id: UUID = Field(
        default=...,
        description="Lease ID proving Orchestrator ownership",
    )

    epoch: int = Field(
        default=...,
        description="Monotonically increasing version number",
        ge=0,
    )

    retry_count: int = Field(
        default=0,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    metadata: ModelActionMetadata = Field(
        default_factory=ModelActionMetadata,
        description="Action execution metadata with full type safety",
    )

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when action was created",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _validate_payload_format(cls, data: Any) -> Any:
        """
        Validate payload and emit deprecation warning for legacy dict usage.

        This validator supports legacy dict format during migration while
        encouraging adoption of typed payloads (ActionPayloadType).

        Error Handling:
            This validator explicitly catches and logs any unexpected errors
            during payload inspection to prevent silent failures. If an error
            occurs, it logs the exception and re-raises it wrapped in
            ModelOnexError for consistent error reporting.

        Args:
            data: Raw input data before model construction

        Returns:
            The input data (unchanged) after validation and warning emission

        Raises:
            ModelOnexError: If payload inspection fails unexpectedly.
        """
        if not isinstance(data, dict):
            return data

        try:
            payload = data.get("payload")

            # Skip if payload is None (default factory will create empty dict)
            if payload is None:
                return data

            # Already a typed payload instance - validate and pass through
            if isinstance(payload, ModelActionPayloadBase):
                _logger.debug(
                    "ModelAction received typed payload: %s",
                    type(payload).__name__,
                )
                return data

            if isinstance(payload, dict):
                # Empty dict is the default, don't warn
                if not payload:
                    return data

                # Heuristic: Typed action payloads have an 'action_type' discriminator field.
                # This field is defined in ModelActionPayloadBase and serves as the
                # discriminator for the SpecificActionPayload union type.
                #
                # If 'action_type' is present, this is likely a serialized typed payload
                # that Pydantic will deserialize via the discriminated union pattern.
                #
                # Heuristic accuracy:
                #   - False positives: A legacy dict with an 'action_type' key will be treated
                #     as a typed payload. This is acceptable since it follows the typed contract.
                #   - False negatives: None - all typed payloads MUST have 'action_type'.
                if "action_type" in payload:
                    # Log for debugging - helps trace payload deserialization issues
                    _logger.debug(
                        "ModelAction payload has action_type='%s', "
                        "will attempt typed deserialization",
                        payload.get("action_type"),
                    )
                    return data

                # Legacy untyped dict payload - issue deprecation warning
                # stacklevel=4 points through: warn() -> validator -> Pydantic -> caller
                warnings.warn(
                    "ModelAction: Using untyped dict[str, Any] payload is deprecated. "
                    "Use typed payloads from ActionPayloadType (e.g., "
                    "ModelDataActionPayload, ModelTransformationActionPayload) for "
                    "better type safety. See omnibase_core.models.orchestrator.payloads "
                    "for available payload types.",
                    DeprecationWarning,
                    stacklevel=4,
                )

            # Handle unexpected payload types (not dict, not ModelActionPayloadBase)
            elif payload is not None:
                # Log unexpected type for debugging
                _logger.warning(
                    "ModelAction received unexpected payload type: %s. "
                    "Expected dict or ActionPayloadType (ModelActionPayloadBase subclass).",
                    type(payload).__name__,
                )

        except Exception as e:
            # Log and re-raise with context - never silently swallow exceptions
            _logger.exception(
                "ModelAction payload validation failed unexpectedly: %s",
                str(e),
            )
            raise ModelOnexError(
                message=(
                    f"ModelAction payload validation failed: {e}. "
                    "Check that the payload is a valid dict or typed ActionPayloadType model."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                payload_type=type(data.get("payload", None)).__name__
                if isinstance(data, dict)
                else "unknown",
                original_error=str(e),
            ) from e

        return data

    @model_validator(mode="after")
    def _validate_action_consistency(self) -> Self:
        """
        Validate cross-field consistency for action semantics.

        Validates:
        1. Self-dependency check: An action cannot depend on itself
        2. Retry/timeout coherence: Warns if retry_count * timeout_ms exceeds reasonable limits
        3. ActionPayloadType integration: Validates typed payload compatibility with action_type

        Returns:
            Self: The validated model instance

        Raises:
            ModelOnexError: If action has circular self-dependency
        """
        # Check for circular self-dependency
        if self.action_id in self.dependencies:
            raise ModelOnexError(
                message=(
                    f"ModelAction validation failed: action_id ({self.action_id}) "
                    "cannot be in its own dependencies list. This would create a "
                    "circular dependency that can never be resolved."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                action_id=str(self.action_id),
                dependencies=[str(d) for d in self.dependencies],
                action_type=self.action_type.value
                if hasattr(self.action_type, "value")
                else str(self.action_type),
            )

        # Warn if total potential execution time is very high
        # (retry_count + 1) * timeout_ms = total potential time
        total_potential_ms = (self.retry_count + 1) * self.timeout_ms
        max_reasonable_ms = 600000  # 10 minutes
        if total_potential_ms > max_reasonable_ms:
            warnings.warn(
                f"ModelAction: Total potential execution time "
                f"({total_potential_ms}ms = ({self.retry_count}+1) retries * "
                f"{self.timeout_ms}ms timeout) exceeds {max_reasonable_ms}ms. "
                "Consider reducing retry_count or timeout_ms to prevent "
                "excessive blocking in orchestration workflows.",
                UserWarning,
                stacklevel=2,
            )

        # Validate ActionPayloadType integration when using typed payloads
        self._validate_payload_type_integration()

        return self

    def _validate_payload_type_integration(self) -> None:
        """
        Validate that typed payload is compatible with the action_type.

        This method performs integration validation between the typed payload
        (if present) and the ModelAction's action_type field. It checks if the
        payload type is among the recommended types for the given action_type.

        This is a soft validation (warning) rather than an error because:
        - The recommendations are guidelines, not strict requirements
        - Edge cases may require non-standard payload/action combinations
        - Extensibility is important for the orchestrator pattern

        Note:
            This validation only applies to typed payloads (instances of
            ModelActionPayloadBase). Legacy dict payloads skip this check.
        """
        # Skip validation for legacy dict payloads - they don't have type info
        if not isinstance(self.payload, ModelActionPayloadBase):
            return

        # Import here to avoid circular import at module level
        from omnibase_core.models.orchestrator.payloads import (
            get_recommended_payloads_for_action_type,
        )

        # Get recommended payload types for this action_type
        recommended_types = get_recommended_payloads_for_action_type(self.action_type)

        # If no recommendations exist for this action_type, skip validation
        if not recommended_types:
            _logger.debug(
                "No recommended payload types for action_type=%s, skipping validation",
                self.action_type,
            )
            return

        # Check if the payload type is among the recommended types
        payload_type = type(self.payload)
        is_recommended = any(
            isinstance(self.payload, recommended_type)
            for recommended_type in recommended_types
        )

        if not is_recommended:
            # Log for debugging - this isn't an error but may indicate misuse
            recommended_names = [t.__name__ for t in recommended_types]
            _logger.info(
                "ModelAction: Payload type '%s' is not among recommended types %s "
                "for action_type=%s. This may be intentional for custom workflows.",
                payload_type.__name__,
                recommended_names,
                self.action_type,
            )
            # Issue informational warning for potential misuse
            warnings.warn(
                f"ModelAction: Payload type '{payload_type.__name__}' is not among "
                f"the recommended types {recommended_names} for action_type="
                f"{self.action_type.value if hasattr(self.action_type, 'value') else self.action_type}. "
                "This may be intentional for custom workflows, but consider using "
                "a recommended payload type for better semantic alignment. "
                "See get_recommended_payloads_for_action_type() for guidance.",
                UserWarning,
                stacklevel=3,  # Point through _validate_action_consistency to caller
            )
