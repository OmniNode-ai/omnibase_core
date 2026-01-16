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
       - Generic ModelIntent with Protocol-typed payload
       - Open set for plugins and extensions
       - String-based intent_type routing
       - Runtime validation via Protocol
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
    ModelIntent requires typed payloads implementing ProtocolIntentPayload.
    All payload classes must have an `intent_type` attribute for routing.

    Typed Payload Categories:
        - Logging: ModelPayloadLogEvent, ModelPayloadMetric
        - Persistence: ModelPayloadPersistState, ModelPayloadPersistResult
        - FSM: ModelPayloadFSMStateAction, ModelPayloadFSMTransitionAction, ModelPayloadFSMCompleted
        - Events: ModelPayloadEmitEvent
        - I/O: ModelPayloadWrite, ModelPayloadHTTP
        - Notifications: ModelPayloadNotify
        - Extensions: ModelPayloadExtension (catch-all for plugins)

Intent Types (Extension Examples):
    - "plugin.execute": Execute a plugin action
    - "webhook.send": Send a webhook notification
    - "custom.transform": Apply custom data transformation
    - "experimental.feature": Test experimental feature

Example (Typed Payload):
    >>> from omnibase_core.models.reducer import ModelIntent
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent
    >>>
    >>> # Create intent with typed payload
    >>> intent = ModelIntent(
    ...     intent_type="log_event",
    ...     target="logging",
    ...     payload=ModelPayloadLogEvent(
    ...         level="INFO",
    ...         message="Processing completed",
    ...         context={"duration_ms": 125},
    ...     ),
    ... )

See Also:
    - docs/architecture/PAYLOAD_TYPE_ARCHITECTURE.md: Typed payload architecture guide
    - omnibase_core.models.reducer.payloads: Typed payload models
    - omnibase_core.models.reducer.payloads.ProtocolIntentPayload: Payload protocol
    - omnibase_core.models.intents: Core infrastructure intents (discriminated union)
    - omnibase_core.nodes.node_reducer: Emits intents during reduction
    - omnibase_core.nodes.node_effect: Executes intents
"""

import logging
import warnings
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants import MAX_KEY_LENGTH
from omnibase_core.models.reducer.payloads.model_protocol_intent_payload import (
    ProtocolIntentPayload,
)

# Module-level logger for validation diagnostics
_logger = logging.getLogger(__name__)


class ModelIntent(BaseModel):
    """
    Extension intent declaration for plugin and experimental workflows.

    For core infrastructure intents (registration, persistence, lifecycle),
    use the discriminated union in omnibase_core.models.intents instead.

    The Reducer is a pure function: delta(state, action) -> (new_state, intents[])
    Instead of performing side effects directly, it emits Intents describing
    what side effects should occur. The Effect node consumes these Intents
    and executes them.

    Extension Intent Examples:
        - Intent to execute plugin action
        - Intent to send webhook
        - Intent to apply custom transformation
        - Intent for experimental features

    Attributes:
        intent_id: Unique identifier for this intent (auto-generated UUID).
        intent_type: Type of intent for routing (e.g., "log_event", "notify").
        target: Target for the intent execution (service, channel, topic).
        payload: Typed payload implementing ProtocolIntentPayload.
        priority: Execution priority (1-10, higher = more urgent).
        lease_id: Optional lease ID for leased workflow tracking.
        epoch: Optional epoch for versioned state tracking.

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
        description="Type of intent (log_event, emit_event, write, notify, etc.)",
        min_length=1,
        max_length=MAX_KEY_LENGTH,
    )

    target: str = Field(
        ...,
        description="Target for the intent execution (service, channel, topic)",
        min_length=1,
        max_length=200,
    )

    payload: ProtocolIntentPayload = Field(
        ...,
        description=(
            "Intent payload implementing ProtocolIntentPayload. "
            "Use typed payloads from omnibase_core.models.reducer.payloads "
            "(e.g., ModelPayloadLogEvent, ModelPayloadNotify, ModelPayloadExtension)."
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

    @model_validator(mode="after")
    def _validate_intent_type_consistency(self) -> Self:
        """
        Validate that intent_type matches the payload's intent_type.

        This ensures consistency between the intent's routing type and the
        payload's discriminator field. If they don't match, a warning is logged
        but the model is still valid (to support extension use cases).

        Returns:
            Self: The validated model instance

        Note:
            This validator logs a warning if intent_type differs from
            payload.intent_type but does not raise an error.
        """
        payload_intent_type = self.payload.intent_type
        if self.intent_type != payload_intent_type:
            _logger.warning(
                "ModelIntent intent_type='%s' differs from payload.intent_type='%s'. "
                "This may cause routing issues. Consider using the same value.",
                self.intent_type,
                payload_intent_type,
            )
        return self

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
                stacklevel=3,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
        arbitrary_types_allowed=True,  # Required for Protocol types
    )
