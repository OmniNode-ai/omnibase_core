"""
Projector Models - Contract definitions for declarative projectors.

Provides models for defining projection schemas, indexes, and materialization
configurations in a declarative manner.

Key Models
----------
ModelIdempotencyConfig
    Configuration for idempotent event processing. Specifies the
    idempotency key and whether checking is enabled.

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

from omnibase_core.models.projectors.model_idempotency_config import (
    ModelIdempotencyConfig,
)
from omnibase_core.models.projectors.model_partial_update_operation import (
    ModelPartialUpdateOperation,
)
from omnibase_core.models.projectors.model_projection_result import (
    ModelProjectionResult,
)
from omnibase_core.models.projectors.model_projector_behavior import (
    ModelProjectorBehavior,
)
from omnibase_core.models.projectors.model_projector_column import ModelProjectorColumn
from omnibase_core.models.projectors.model_projector_contract import (
    EVENT_NAME_PATTERN,
    ModelProjectorContract,
)
from omnibase_core.models.projectors.model_projector_index import ModelProjectorIndex
from omnibase_core.models.projectors.model_projector_schema import ModelProjectorSchema

__all__ = [
    "EVENT_NAME_PATTERN",
    "ModelIdempotencyConfig",
    "ModelPartialUpdateOperation",
    "ModelProjectionResult",
    "ModelProjectorBehavior",
    "ModelProjectorColumn",
    "ModelProjectorContract",
    "ModelProjectorIndex",
    "ModelProjectorSchema",
]
