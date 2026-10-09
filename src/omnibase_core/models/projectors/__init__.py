# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Projector Models - Contract definitions for declarative projectors.

Provides models for defining projection schemas, indexes, and materialization
configurations in a declarative manner.

Key Models
----------
ModelIdempotencyConfig
    Configuration for idempotent event processing. Specifies the
    idempotency key and whether checking is enabled.

ModelProjectionIntent
    Intent to project an event envelope via a named projector key.
    Produced by reducers and consumed by NodeProjectionEffect.

ModelProjectionResult
    Result of a projection operation, including success status,
    rows affected, and any error information.

ModelProjectorColumn
    Column definition with event field mapping for projector tables.

ModelProjectorIndex
    Index configuration for projector tables.

ModelProjectorSchema
    Database schema for projection including table, columns, indexes, and version.

ModelProjectorBehavior
    Behavior configuration for projector event handling.

ModelProjectorContract
    Complete declarative projector definition including identity, event
    subscriptions, schema, and behavior. Core principle: "Projectors are
    consumers of ModelEventEnvelope streams, not participants in handler
    dispatch. They never emit events, intents, or projections."

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access.

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.projectors.model_dashboard_hint import ModelDashboardHint
    from omnibase_core.models.projectors.model_idempotency_config import (
        ModelIdempotencyConfig,
    )
    from omnibase_core.models.projectors.model_partial_update_operation import (
        ModelPartialUpdateOperation,
    )
    from omnibase_core.models.projectors.model_projection_intent import (
        ModelProjectionIntent,
    )
    from omnibase_core.models.projectors.model_projection_result import (
        ModelProjectionResult,
    )
    from omnibase_core.models.projectors.model_projector_behavior import (
        ModelProjectorBehavior,
    )
    from omnibase_core.models.projectors.model_projector_column import (
        ModelProjectorColumn,
    )
    from omnibase_core.models.projectors.model_projector_contract import (
        EVENT_NAME_PATTERN,
        ModelProjectorContract,
    )
    from omnibase_core.models.projectors.model_projector_index import (
        ModelProjectorIndex,
    )
    from omnibase_core.models.projectors.model_projector_schema import (
        ModelProjectorSchema,
    )

__all__ = [
    "EVENT_NAME_PATTERN",
    "ModelDashboardHint",
    "ModelIdempotencyConfig",
    "ModelPartialUpdateOperation",
    "ModelProjectionIntent",
    "ModelProjectionResult",
    "ModelProjectorBehavior",
    "ModelProjectorColumn",
    "ModelProjectorContract",
    "ModelProjectorIndex",
    "ModelProjectorSchema",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDashboardHint": (
        "omnibase_core.models.projectors.model_dashboard_hint",
        "ModelDashboardHint",
    ),
    "ModelIdempotencyConfig": (
        "omnibase_core.models.projectors.model_idempotency_config",
        "ModelIdempotencyConfig",
    ),
    "ModelPartialUpdateOperation": (
        "omnibase_core.models.projectors.model_partial_update_operation",
        "ModelPartialUpdateOperation",
    ),
    "ModelProjectionIntent": (
        "omnibase_core.models.projectors.model_projection_intent",
        "ModelProjectionIntent",
    ),
    "ModelProjectionResult": (
        "omnibase_core.models.projectors.model_projection_result",
        "ModelProjectionResult",
    ),
    "ModelProjectorBehavior": (
        "omnibase_core.models.projectors.model_projector_behavior",
        "ModelProjectorBehavior",
    ),
    "ModelProjectorColumn": (
        "omnibase_core.models.projectors.model_projector_column",
        "ModelProjectorColumn",
    ),
    "EVENT_NAME_PATTERN": (
        "omnibase_core.models.projectors.model_projector_contract",
        "EVENT_NAME_PATTERN",
    ),
    "ModelProjectorContract": (
        "omnibase_core.models.projectors.model_projector_contract",
        "ModelProjectorContract",
    ),
    "ModelProjectorIndex": (
        "omnibase_core.models.projectors.model_projector_index",
        "ModelProjectorIndex",
    ),
    "ModelProjectorSchema": (
        "omnibase_core.models.projectors.model_projector_schema",
        "ModelProjectorSchema",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
