"""
Extension intent model for plugin and experimental workflows.

This module provides ModelIntent, a flexible intent class for extension workflows
where the intent schema is not known at compile time. For core infrastructure
intents (registration, persistence, lifecycle), use the discriminated union
in omnibase_core.models.intents instead.

Intent System Architecture:
    The ONEX intent system has two tiers:

    1. Core Intents (omnibase_core.models.intents):
       - Discriminated union pattern
       - Closed set of known intents
       - Exhaustive pattern matching required
       - Compile-time type safety
       - Use for: registration, persistence, lifecycle, core workflows

    2. Extension Intents (this module):
       - Generic ModelIntent with typed payload
       - Open set for plugins and extensions
       - String-based intent_type routing
       - Runtime validation
       - Use for: plugins, experimental features, third-party integrations

Design Pattern:
    ModelIntent maintains Reducer purity by separating the decision of "what side
    effect should occur" from the execution of that side effect. The Reducer emits
    intents describing what should happen, and the Effect node consumes and executes
    them.

    Reducer function: delta(state, action) -> (new_state, intents[])

Thread Safety:
    ModelIntent is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access. Note that this provides shallow immutability.

When to Use ModelIntent vs Core Intents:
    Use ModelIntent when:
    - Building a plugin or extension
    - Experimenting with new intent types
    - Intent schema is dynamic or user-defined
    - Third-party integration with unknown schemas

    Use Core Intents (models.intents) when:
    - Working with registration, persistence, or lifecycle
    - Need exhaustive handling guarantees
    - Want compile-time type safety
    - Building core infrastructure

Typed Payloads (v0.4.0+):
    ModelIntent now supports typed payloads via ModelIntentPayloadUnion for
    compile-time type safety. Legacy dict[str, Any] payloads are still supported
    during the migration period but will issue a deprecation warning.

    Typed Payload Categories:
        - Logging: PayloadLogEvent, PayloadMetric
        - Persistence: PayloadPersistState, PayloadPersistResult
        - FSM: PayloadFSMStateAction, PayloadFSMTransitionAction, PayloadFSMCompleted
        - Events: PayloadEmitEvent
        - I/O: PayloadWrite, PayloadHTTP
        - Notifications: PayloadNotify
        - Extensions: PayloadExtension (catch-all for plugins)

Intent Types (Extension Examples):
    - "plugin.execute": Execute a plugin action
    - "webhook.send": Send a webhook notification
    - "custom.transform": Apply custom data transformation
    - "experimental.feature": Test experimental feature

Example (Typed Payload - Recommended):
    >>> from omnibase_core.models.reducer import ModelIntent
    >>> from omnibase_core.models.reducer.payloads import PayloadLogEvent
    >>>
    >>> # Create intent with typed payload
    >>> intent = ModelIntent(
    ...     intent_type="log_event",
    ...     target="logging",
    ...     payload=PayloadLogEvent(
    ...         level="INFO",
    ...         message="Processing completed",
    ...         context={"duration_ms": 125},
    ...     ),
    ... )

Example (Legacy Dict - Deprecated):
    >>> from omnibase_core.models.reducer import ModelIntent
    >>>
    >>> # Legacy dict payload (deprecated, issues warning)
    >>> intent = ModelIntent(
    ...     intent_type="webhook.send",
    ...     target="notifications",
    ...     payload={"url": "https://...", "method": "POST", "body": {}},
    ...     priority=5,
    ... )

See Also:
    - omnibase_core.models.reducer.payloads: Typed payload models
    - omnibase_core.models.intents: Core infrastructure intents (discriminated union)
    - omnibase_core.nodes.node_reducer: Emits intents during reduction
    - omnibase_core.nodes.node_effect: Executes intents
"""

import logging
import warnings
from typing import Any, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.reducer.payloads import ModelIntentPayloadUnion
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)
from omnibase_core.utils.util_decorators import allow_dict_str_any

# Module-level logger for validation diagnostics
_logger = logging.getLogger(__name__)


@allow_dict_str_any(
    "Intent payloads support both typed payloads (ModelIntentPayloadUnion) and "
    "legacy dict[str, Any] for migration support. "
    "New code should use typed payloads."
)
class ModelIntent(BaseModel):
    """
    Extension intent declaration for plugin and experimental workflows.

    For core infrastructure intents (registration, persistence, lifecycle),
    use the discriminated union in omnibase_core.models.intents instead.

    The Reducer is a pure function: δ(state, action) → (new_state, intents[])
    Instead of performing side effects directly, it emits Intents describing
    what side effects should occur. The Effect node consumes these Intents
    and executes them.

    Extension Intent Examples:
        - Intent to execute plugin action
        - Intent to send webhook
        - Intent to apply custom transformation
        - Intent for experimental features

    See Also:
        omnibase_core.models.intents.ModelCoreIntent: Base class for core intents
        omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union type alias
            for core infrastructure intents (registration, persistence, lifecycle)
    """

    intent_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this intent",
    )

    intent_type: str = Field(
        ...,
        description="Type of intent (log, emit_event, write, notify)",
        min_length=1,
        max_length=100,
    )

    target: str = Field(
        ...,
        description="Target for the intent execution (service, channel, topic)",
        min_length=1,
        max_length=200,
    )

    payload: ModelIntentPayloadUnion | dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Intent payload data. Supports typed payloads (ModelIntentPayloadUnion) "
            "for type safety or legacy dict[str, Any] for migration support. "
            "New code should use typed payloads from omnibase_core.models.reducer.payloads."
        ),
    )

    priority: int = Field(
        default=1,
        description="Execution priority (higher = more urgent)",
        ge=1,
        le=10,
    )

    # Lease fields for single-writer semantics
    lease_id: UUID | None = Field(
        default=None,
        description="Optional lease ID if this intent relates to a leased workflow",
    )

    epoch: int | None = Field(
        default=None,
        description="Optional epoch if this intent relates to versioned state",
        ge=0,
    )

    @model_validator(mode="before")
    @classmethod
    def _check_legacy_payload(cls, data: Any) -> Any:
        """Check for legacy dict payload and issue deprecation warning.

        This validator detects when an untyped dict is passed as the payload
        and issues a deprecation warning encouraging migration to typed payloads.

        Empty dicts are allowed without warning (common default case).
        Typed payload instances (ModelIntentPayloadBase subclasses) pass through
        without warning.

        Error Handling:
            This validator explicitly catches and logs any unexpected errors
            during payload inspection to prevent silent failures. If an error
            occurs, it logs the exception and re-raises it wrapped in
            ModelOnexError for consistent error reporting.

        Args:
            data: Raw input data for model construction. Can be any type
                for mode="before" validators.

        Returns:
            The input data unchanged.

        Raises:
            ModelOnexError: If payload inspection fails unexpectedly.
        """
        if not isinstance(data, dict):
            return data

        try:
            payload = data.get("payload")

            # No payload or empty dict - no warning needed (common default case)
            if payload is None or payload == {}:
                return data

            # Already a typed payload instance - no warning needed
            if isinstance(payload, ModelIntentPayloadBase):
                return data

            # Dict payload that's not empty - check if it's a serialized typed payload
            if isinstance(payload, dict):
                # Heuristic: Typed intent payloads have an 'intent_type' discriminator field.
                # This field is defined as a Literal in each payload class (e.g., Literal["log_event"])
                # and serves as the discriminator for ModelIntentPayloadUnion.
                #
                # If 'intent_type' is present, this is likely a serialized typed payload
                # that Pydantic will deserialize via the discriminated union pattern.
                #
                # Heuristic accuracy:
                #   - False positives: A legacy dict with an 'intent_type' key will be treated
                #     as a typed payload. This is acceptable since it follows the typed contract.
                #   - False negatives: None - all typed payloads MUST have 'intent_type'.
                if "intent_type" in payload:
                    # Log for debugging - helps trace payload deserialization issues
                    _logger.debug(
                        "ModelIntent payload has intent_type='%s', "
                        "will attempt typed deserialization",
                        payload.get("intent_type"),
                    )
                    return data

                # Legacy untyped dict payload - issue deprecation warning
                # stacklevel=4 points through: warn() -> validator -> Pydantic -> caller
                warnings.warn(
                    "Using untyped dict payload in ModelIntent is deprecated. "
                    "Use typed payloads from omnibase_core.models.reducer.payloads instead. "
                    "For plugins/extensions, use PayloadExtension. "
                    "See: docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md",
                    DeprecationWarning,
                    stacklevel=4,
                )

            # Handle unexpected payload types (not dict, not ModelIntentPayloadBase)
            elif payload is not None:
                # Log unexpected type for debugging
                _logger.warning(
                    "ModelIntent received unexpected payload type: %s. "
                    "Expected dict or ModelIntentPayloadBase subclass.",
                    type(payload).__name__,
                )

        except Exception as e:
            # Log and re-raise with context - never silently swallow exceptions
            _logger.exception(
                "ModelIntent payload validation failed unexpectedly: %s",
                str(e),
            )
            raise ModelOnexError(
                message=(
                    f"ModelIntent payload validation failed: {e}. "
                    "Check that the payload is a valid dict or typed payload model."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                payload_type=type(data.get("payload", None)).__name__
                if isinstance(data, dict)
                else "unknown",
                original_error=str(e),
            ) from e

        return data

    @model_validator(mode="after")
    def _validate_lease_epoch_consistency(self) -> Self:
        """
        Validate cross-field consistency for lease semantics.

        If epoch is set (versioned state tracking), lease_id should ideally also
        be set to ensure proper single-writer semantics. This validation emits
        a warning for potentially misconfigured intents that have versioning
        without ownership proof.

        Note:
            This is a warning rather than an error because ModelIntent supports
            extension and experimental workflows where epoch may be used for
            simple versioning without the full lease semantics. For core
            infrastructure intents requiring strict single-writer guarantees,
            use the discriminated union in omnibase_core.models.intents.

        Returns:
            Self: The validated model instance
        """
        if self.epoch is not None and self.lease_id is None:
            warnings.warn(
                f"ModelIntent has epoch ({self.epoch}) set without lease_id. "
                "For proper single-writer semantics in distributed workflows, "
                "consider providing a lease_id to prove ownership. "
                "For extension intents without coordination requirements, "
                "this warning can be safely ignored.",
                UserWarning,
                stacklevel=2,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
