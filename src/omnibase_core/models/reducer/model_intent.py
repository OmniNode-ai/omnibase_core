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

Intent Types (Extension Examples):
    - "plugin.execute": Execute a plugin action
    - "webhook.send": Send a webhook notification
    - "custom.transform": Apply custom data transformation
    - "experimental.feature": Test experimental feature

Example:
    >>> from omnibase_core.models.reducer import ModelIntent
    >>> from pydantic import BaseModel
    >>>
    >>> class WebhookPayload(BaseModel):
    ...     url: str
    ...     method: str
    ...     body: dict
    >>>
    >>> # Extension intent for webhook plugin
    >>> intent = ModelIntent(
    ...     intent_type="webhook.send",
    ...     target="notifications",
    ...     payload={"url": "https://...", "method": "POST", "body": {}},
    ...     priority=5,
    ... )

See Also:
    - omnibase_core.models.intents: Core infrastructure intents (discriminated union)
    - omnibase_core.nodes.node_reducer: Emits intents during reduction
    - omnibase_core.nodes.node_effect: Executes intents
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Intent payloads require flexible dict[str, Any] to carry arbitrary data "
    "for side effects (event data, log metadata, storage payloads, etc.)."
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

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Intent payload data",
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

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
