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
    >>> intents: list[ModelCoreRegistrationIntent] = [
    ...     ModelConsulRegisterIntent(
    ...         service_id="node-123",
    ...         service_name="onex-compute",
    ...         tags=["node_type:compute"],
    ...         correlation_id=uuid4(),
    ...     ),
    ... ]

Example - Effect pattern matching:
    >>> def execute(intent: ModelCoreRegistrationIntent) -> None:
    ...     match intent:
    ...         case ModelConsulRegisterIntent():
    ...             register_with_consul(intent)
    ...         case ModelConsulDeregisterIntent():
    ...             deregister_from_consul(intent)
    ...         case ModelPostgresUpsertRegistrationIntent():
    ...             upsert_to_postgres(intent)

See Also:
    - omnibase_core.models.reducer.model_intent: Extension intent system
"""

from typing import Annotated, Union

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

# ---- Discriminated Union ----

ModelCoreRegistrationIntent = Annotated[
    Union[
        ModelConsulRegisterIntent,
        ModelConsulDeregisterIntent,
        ModelPostgresUpsertRegistrationIntent,
    ],
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
    # Base class
    "ModelCoreIntent",
    # Concrete intents
    "ModelConsulRegisterIntent",
    "ModelConsulDeregisterIntent",
    "ModelPostgresUpsertRegistrationIntent",
    # Discriminated union
    "ModelCoreRegistrationIntent",
]
