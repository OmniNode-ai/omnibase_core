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

import warnings
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.reducer.payloads import ModelIntentPayloadUnion
from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)
from omnibase_core.utils.util_decorators import allow_dict_str_any


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

        Args:
            data: Raw input data for model construction. Can be any type
                for mode="before" validators.

        Returns:
            The input data unchanged.
        """
        if not isinstance(data, dict):
            return data

        payload = data.get("payload")

        # No payload or empty dict - no warning needed (common default case)
        if payload is None or payload == {}:
            return data

        # Already a typed payload instance - no warning needed
        if isinstance(payload, ModelIntentPayloadBase):
            return data

        # Dict payload that's not empty - check if it's a serialized typed payload
        if isinstance(payload, dict):
            # If it has an intent_type field, it might be a serialized typed payload
            # In that case, Pydantic will handle deserialization via the discriminator
            if "intent_type" in payload:
                return data

            # Legacy untyped dict payload - issue deprecation warning
            warnings.warn(
                "Using untyped dict payload in ModelIntent is deprecated. "
                "Use typed payloads from omnibase_core.models.reducer.payloads instead. "
                "For plugins/extensions, use PayloadExtension. "
                "See: docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md",
                DeprecationWarning,
                stacklevel=4,  # Point to caller's caller (through Pydantic internals)
            )

        return data

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
