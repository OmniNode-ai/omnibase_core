"""
Intent to upsert a node registration in PostgreSQL.

This module provides the ModelPostgresUpsertRegistrationIntent class for
declaring node registration persistence to PostgreSQL.

Thread Safety:
    ModelPostgresUpsertRegistrationIntent is immutable (frozen=True) after creation.

Example:
    >>> from omnibase_core.models.intents import ModelPostgresUpsertRegistrationIntent
    >>> from pydantic import BaseModel
    >>> from uuid import uuid4
    >>>
    >>> class NodeRecord(BaseModel):
    ...     node_id: str
    ...     node_type: str
    >>>
    >>> intent = ModelPostgresUpsertRegistrationIntent(
    ...     record=NodeRecord(node_id="123", node_type="compute"),
    ...     correlation_id=uuid4(),
    ... )

See Also:
    - model_core_intent_base: Base class for core intents
"""

from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent


class ModelPostgresUpsertRegistrationIntent(ModelCoreIntent):
    """Intent to upsert a node registration in PostgreSQL.

    Emitted by Reducers when node registration data should be persisted
    to PostgreSQL. The Effect node executes this intent by performing
    an upsert operation on the registration table.

    The record field accepts any BaseModel to allow flexibility in
    registration record schemas while maintaining type safety through
    the discriminated union pattern at the intent level.

    Attributes:
        kind: Discriminator for intent routing ("postgres.upsert_registration").
        record: Registration record to upsert (typed BaseModel).
    """

    kind: Literal["postgres.upsert_registration"] = Field(
        default="postgres.upsert_registration",
        description="Discriminator for intent routing",
    )
    record: BaseModel = Field(
        ...,
        description="Registration record to upsert",
    )
