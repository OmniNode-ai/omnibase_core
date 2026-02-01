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

Typed Payloads (v0.4.0+):
    The payload field requires typed payloads implementing ProtocolActionPayload.
    All payload classes must have a `kind` attribute for routing.

    Available Payload Types:
        - ModelLifecycleActionPayload: Start, stop, restart operations
        - ModelOperationalActionPayload: Operational status changes
        - ModelDataActionPayload: Data processing operations
        - ModelValidationActionPayload: Validation operations
        - ModelManagementActionPayload: Resource management
        - ModelTransformationActionPayload: Data transformations
        - ModelMonitoringActionPayload: Monitoring and metrics
        - ModelRegistryActionPayload: Registry operations
        - ModelFilesystemActionPayload: File system operations
        - ModelCustomActionPayload: Custom extension payloads

See Also:
    - docs/architecture/MODELACTION_TYPED_PAYLOADS.md: ModelAction typed payload architecture
    - docs/architecture/PAYLOAD_TYPE_ARCHITECTURE.md: General payload type architecture
"""

import warnings
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants import (
    MAX_IDENTIFIER_LENGTH,
    TIMEOUT_DEFAULT_MS,
    TIMEOUT_LONG_MS,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator.payloads.model_protocol_action_payload import (
    ProtocolActionPayload,
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
        payload: Action payload implementing ProtocolActionPayload (required).
        dependencies: List of action IDs this action depends on (default empty list).
        priority: Execution priority (1-10, higher = more urgent, default 1).
        timeout_ms: Execution timeout in ms (100-TIMEOUT_LONG_MS, default TIMEOUT_DEFAULT_MS).
            Raises TimeoutError on expiry. See omnibase_core.constants for values.
        lease_id: Lease ID proving Orchestrator ownership (required).
        epoch: Monotonically increasing version number (>= 0, required).
        retry_count: Number of retry attempts on failure (0-10, default 0).
        metadata: Action execution metadata with full type safety (default ModelActionMetadata()).
        created_at: Timestamp when action was created (auto-generated).

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_workflow_execution import EnumActionType
        >>> from omnibase_core.models.orchestrator.payloads import ModelDataActionPayload
        >>> from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
        >>> from omnibase_core.models.core.model_predefined_categories import OPERATION
        >>>
        >>> action = ModelAction(
        ...     action_type=EnumActionType.EFFECT,
        ...     target_node_type="NodeEffect",
        ...     payload=ModelDataActionPayload(
        ...         action_type=ModelNodeActionType(
        ...             name="read",
        ...             category=OPERATION,
        ...             display_name="Read Data",
        ...             description="Read data from storage",
        ...         ),
        ...     ),
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
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    payload: ProtocolActionPayload = Field(
        ...,
        description=(
            "Action payload implementing ProtocolActionPayload. "
            "Use typed payloads from omnibase_core.models.orchestrator.payloads "
            "(e.g., ModelDataActionPayload, ModelTransformationActionPayload)."
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
        default=TIMEOUT_DEFAULT_MS,
        description=(
            "Execution timeout in milliseconds. When exceeded, the action execution "
            "is cancelled and a TimeoutError is raised. The Orchestrator may retry "
            "the action based on retry_count and backoff policy. For long-running "
            "operations (e.g., large file transfers, complex computations), increase "
            "this value up to the maximum of 300000ms (5 minutes). Consider breaking "
            "very long operations into smaller actions with progress checkpoints. "
            "\n\n"
            "Note: Timeout enforcement is pending implementation in the action "
            "execution layer. Currently, the timeout_ms value is propagated from "
            "workflow steps (via utils/util_workflow_executor.py) and FSM transitions "
            "(via utils/util_fsm_executor.py) but is not yet enforced at action execution "
            "time. For compute pipeline timeouts, see ModelComputeSubcontract.pipeline_timeout_ms "
            "which IS enforced in utils/util_compute_executor.py using ThreadPoolExecutor."
        ),
        ge=100,
        le=TIMEOUT_LONG_MS,  # Max 5 minutes
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
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when action was created (UTC)",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
        arbitrary_types_allowed=True,  # Required for Protocol types
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def _ensure_utc_aware(cls, v: datetime) -> datetime:
        """
        Ensure created_at is always UTC-aware.

        This validator standardizes datetime handling:
        - Naive datetime (no tzinfo): Assumes UTC, adds UTC tzinfo
        - Non-UTC aware datetime: Converts to UTC equivalent

        This ensures consistent UTC timestamps for distributed coordination
        and action tracking across time zones.

        Args:
            v: The datetime value to validate

        Returns:
            UTC-aware datetime
        """
        if v.tzinfo is None:
            # Naive datetime: assume UTC and add tzinfo
            return v.replace(tzinfo=UTC)
        elif v.tzinfo != UTC:
            # Non-UTC timezone: convert to UTC
            return v.astimezone(UTC)
        return v

    @model_validator(mode="after")
    def _validate_action_consistency(self) -> Self:
        """
        Validate cross-field consistency for action semantics.

        Validates:
        1. Self-dependency check: An action cannot depend on itself
        2. Retry/timeout coherence: Warns if retry_count * timeout_ms exceeds reasonable limits
        3. Payload type integration: Validates typed payload compatibility with action_type

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
                error_code=EnumCoreErrorCode.ORCHESTRATOR_SEMANTIC_CYCLE_DETECTED,
                action_id=str(self.action_id),
                dependencies=[str(d) for d in self.dependencies],
                action_type=self.action_type.value,
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
                stacklevel=3,
            )

        # Validate payload type integration when using typed payloads
        self._validate_payload_type_integration()

        return self

    def _validate_payload_type_integration(self) -> None:
        """
        Validate that typed payload is compatible with the action_type.

        This method performs integration validation between the typed payload
        and the ModelAction's action_type field. It checks if the payload type
        is among the recommended types for the given action_type.

        This is a soft validation (warning) rather than an error because:
        - The recommendations are guidelines, not strict requirements
        - Edge cases may require non-standard payload/action combinations
        - Extensibility is important for the orchestrator pattern
        """
        # Only validate if payload is a ModelActionPayloadBase subclass
        # (Protocols don't provide enough info for recommendation checks)
        if not isinstance(self.payload, ModelActionPayloadBase):
            return

        # Import here to avoid circular import at module level
        from omnibase_core.models.orchestrator.payloads import (
            get_recommended_payloads_for_action_type,
        )

        # Get recommended payload types for this action_type
        # Note: All EnumActionType values have recommendations defined in
        # _ACTION_TYPE_TO_PAYLOAD_RECOMMENDATIONS, so this always returns a non-empty list
        recommended_types = get_recommended_payloads_for_action_type(self.action_type)

        # Check if the payload type is among the recommended types
        is_recommended = any(
            isinstance(self.payload, recommended_type)
            for recommended_type in recommended_types
        )

        if not is_recommended:
            # Get payload_type only when needed (inside this branch)
            payload_type = type(self.payload)
            recommended_names = [t.__name__ for t in recommended_types]
            # Issue informational warning for potential misuse
            warnings.warn(
                f"ModelAction: Payload type '{payload_type.__name__}' is not among "
                f"the recommended types {recommended_names} for action_type="
                f"{self.action_type.value}. "
                "This may be intentional for custom workflows, but consider using "
                "a recommended payload type for better semantic alignment. "
                "See get_recommended_payloads_for_action_type() for guidance.",
                UserWarning,
                stacklevel=3,
            )


__all__ = ["ModelAction"]
