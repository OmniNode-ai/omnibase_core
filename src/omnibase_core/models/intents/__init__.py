"""
Core infrastructure intents module.

This module provides typed intent variants for core infrastructure workflows
using the discriminated union pattern. For extension/plugin intents, use
omnibase_core.models.reducer.model_intent.ModelIntent instead.

Intent System Architecture:
    The ONEX intent system has two tiers:

    1. Core Intents (this module):
       - Discriminated union pattern
       - Closed set of known intents
       - Exhaustive pattern matching required
       - Compile-time type safety
       - Use for: registration, persistence, lifecycle, core workflows

    2. Extension Intents (omnibase_core.models.reducer.model_intent):
       - Generic ModelIntent with typed payload
       - Open set for plugins and extensions
       - String-based intent_type routing
       - Runtime validation
       - Use for: plugins, experimental features, third-party integrations

Effect Pattern - Reducer to Effect Flow:
    Core intents implement the ONEX "Intent -> Effect" pattern, which separates
    pure state transitions (Reducer) from side effect execution (Effect).

    **The Flow**:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                         ONEX Intent Flow                         │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Action          Reducer                    Effect              │
    │     │               │                          │                 │
    │     │   dispatch    │                          │                 │
    │     │──────────────>│                          │                 │
    │     │               │   (state, intents[])     │                 │
    │     │               │─────────────────────────>│                 │
    │     │               │                          │   execute       │
    │     │               │                          │   side effect   │
    │     │               │                          │       │         │
    │     │               │                          │<──────┘         │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘
    ```

    1. **Action dispatched** to Reducer (e.g., StartupAction, ShutdownAction)
    2. **Reducer is PURE** - computes new state AND emits typed intents
       - NO side effects in Reducer
       - Intents are data structures describing desired outcomes
    3. **Effect receives intents** via discriminated union type
       - Pattern matches on intent.kind discriminator
       - Executes actual side effect (API calls, DB writes, etc.)
    4. **Correlation ID** links the entire flow for distributed tracing

    **Why This Pattern?**
    - **Testability**: Reducers are pure functions, easy to unit test
    - **Predictability**: Side effects isolated to Effect nodes
    - **Type Safety**: Discriminated unions catch unhandled intents at compile time
    - **Traceability**: correlation_id enables end-to-end request tracking

Usage:
    >>> from omnibase_core.models.intents import (
    ...     ModelCoreIntent,
    ...     ModelConsulRegisterIntent,
    ...     ModelConsulDeregisterIntent,
    ...     ModelPostgresUpsertRegistrationIntent,
    ...     ModelCoreRegistrationIntent,
    ... )

Example - Reducer emitting intents:
    >>> from uuid import uuid4
    >>>
    >>> def reduce(state: NodeState, action: StartupAction) -> tuple[NodeState, list]:
    ...     '''Pure reducer - returns new state and intents, NO side effects.'''
    ...     new_state = state.with_status("registering")
    ...     intents = [
    ...         ModelConsulRegisterIntent(
    ...             kind="consul.register",
    ...             service_id=f"node-{state.node_id}",
    ...             service_name="onex-compute",
    ...             tags=["node_type:compute"],
    ...             correlation_id=action.correlation_id,
    ...         ),
    ...         ModelPostgresUpsertRegistrationIntent(
    ...             kind="postgres.upsert_registration",
    ...             record=NodeRecord(node_id=state.node_id, status="active"),
    ...             correlation_id=action.correlation_id,
    ...         ),
    ...     ]
    ...     return (new_state, intents)

Example - Effect pattern matching:
    >>> async def execute(intent: ModelCoreRegistrationIntent) -> None:
    ...     '''Effect node - performs actual side effects based on intent type.'''
    ...     match intent:
    ...         case ModelConsulRegisterIntent():
    ...             await consul_client.register(
    ...                 service_id=intent.service_id,
    ...                 service_name=intent.service_name,
    ...                 tags=intent.tags,
    ...             )
    ...         case ModelConsulDeregisterIntent():
    ...             await consul_client.deregister(intent.service_id)
    ...         case ModelPostgresUpsertRegistrationIntent():
    ...             await db.upsert_registration(intent.record)

Performance Note:
    The discriminator field (`kind`) is placed FIRST in all intent models for
    optimal union type resolution. Pydantic checks fields in order when resolving
    discriminated unions, so having the discriminator first speeds up type matching.

See Also:
    - omnibase_core.models.reducer.model_intent: Extension intent system
    - omnibase_core.nodes.NodeReducer: Reducer node implementation
    - omnibase_core.nodes.NodeEffect: Effect node implementation
"""

from typing import Annotated

from pydantic import Field

from omnibase_core.models.intents.model_consul_deregister_intent import (
    ModelConsulDeregisterIntent,
)
from omnibase_core.models.intents.model_consul_register_intent import (
    ModelConsulRegisterIntent,
)
from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent
from omnibase_core.models.intents.model_postgres_upsert_registration_intent import (
    ModelPostgresUpsertRegistrationIntent,
)
from omnibase_core.models.intents.model_registration_record_base import (
    ModelRegistrationRecordBase,
)

# ---- Discriminated Union ----

ModelCoreRegistrationIntent = Annotated[
    ModelConsulRegisterIntent
    | ModelConsulDeregisterIntent
    | ModelPostgresUpsertRegistrationIntent,
    Field(discriminator="kind"),
]
"""Discriminated union of all core registration intents.

Use this type for:
- Reducer return types: `list[ModelCoreRegistrationIntent]`
- Effect dispatch signatures: `def execute(intent: ModelCoreRegistrationIntent)`
- Pattern matching in Effects

Adding a new intent requires:
1. Create new model file: model_<intent_name>_intent.py
2. Add to this union
3. Update all Effect dispatch handlers (exhaustive matching)
"""

__all__ = [
    # Base classes
    "ModelCoreIntent",
    "ModelRegistrationRecordBase",
    # Concrete intents
    "ModelConsulRegisterIntent",
    "ModelConsulDeregisterIntent",
    "ModelPostgresUpsertRegistrationIntent",
    # Discriminated union
    "ModelCoreRegistrationIntent",
]
