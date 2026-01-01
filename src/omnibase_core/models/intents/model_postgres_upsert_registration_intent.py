"""
Intent to upsert a node registration in PostgreSQL.

This module provides the ModelPostgresUpsertRegistrationIntent class for
declaring node registration persistence to PostgreSQL. This is a core intent
that participates in the discriminated union pattern for type-safe handling.

Design Pattern:
    Reducers emit this intent when node registration data should be persisted.
    The Effect node receives the intent via the ModelCoreRegistrationIntent union,
    pattern-matches on the `kind` discriminator, and executes the PostgreSQL upsert.

    This separation ensures Reducer purity - the Reducer declares the desired
    outcome without performing the actual database operation.

Database Semantics:
    - Upsert (INSERT ... ON CONFLICT UPDATE) semantics
    - Record schema is flexible (any BaseModel subclass)
    - Effect is responsible for schema-to-table mapping
    - correlation_id enables distributed tracing across services

Record Type Options:
    The record field accepts any BaseModel. For improved type safety and
    consistency, consider using one of these approaches:

    1. **ModelRegistrationRecordBase** (recommended for new code):
       Inherit from this base class to get ONEX-compliant settings and
       a standard to_persistence_dict() method:
       ```python
       from omnibase_core.models.intents import ModelRegistrationRecordBase

       class NodeRecord(ModelRegistrationRecordBase):
           node_id: str
           node_type: str
           status: str
       ```

    2. **ProtocolRegistrationRecord** (for protocol-based type checking):
       Implement this protocol for maximum flexibility with type safety:
       ```python
       from omnibase_core.protocols.intents import ProtocolRegistrationRecord

       class CustomRecord(BaseModel):
           # ... fields ...

           def to_persistence_dict(self) -> dict[str, object]:
               return self.model_dump(mode="json")
       ```

    3. **Plain BaseModel** (backward compatible):
       Any BaseModel works, though you lose the to_persistence_dict() contract.

Thread Safety:
    ModelPostgresUpsertRegistrationIntent is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.intents import (
    ...     ModelPostgresUpsertRegistrationIntent,
    ...     ModelRegistrationRecordBase,
    ... )
    >>> from uuid import uuid4
    >>>
    >>> class NodeRecord(ModelRegistrationRecordBase):
    ...     node_id: str
    ...     node_type: str
    ...     status: str
    >>>
    >>> # Persist a node registration
    >>> intent = ModelPostgresUpsertRegistrationIntent(
    ...     record=NodeRecord(
    ...         node_id="compute-abc123",
    ...         node_type="compute",
    ...         status="active",
    ...     ),
    ...     correlation_id=uuid4(),
    ... )

See Also:
    omnibase_core.models.intents.ModelCoreIntent: Base class for core intents
    omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union type
    omnibase_core.models.intents.ModelConsulRegisterIntent: Consul registration intent
    omnibase_core.models.intents.ModelRegistrationRecordBase: Base class for records
    omnibase_core.protocols.intents.ProtocolRegistrationRecord: Record protocol
"""

from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.models.intents.model_core_intent_base import ModelCoreIntent


class ModelPostgresUpsertRegistrationIntent(ModelCoreIntent):
    """Intent to upsert a node registration in PostgreSQL.

    Emitted by Reducers when node registration data should be persisted
    to PostgreSQL. The Effect node executes this intent by performing
    an upsert (INSERT ... ON CONFLICT UPDATE) operation on the registration table.

    This intent participates in the ModelCoreRegistrationIntent discriminated
    union, enabling exhaustive pattern matching in Effect nodes.

    The record field accepts any BaseModel to allow flexibility in registration
    record schemas while maintaining type safety through the discriminated union
    pattern at the intent level. The Effect node is responsible for mapping
    the record to the appropriate database schema.

    Effect Pattern - Intent to Execution Flow:
        This intent is part of the ONEX Reducer -> Effect architecture:

        1. **Reducer emits intent** (pure, no side effects):
           ```python
           def reduce(state: NodeState, action: RegisterAction) -> tuple[NodeState, list[Intent]]:
               record = NodeRegistrationRecord(
                   node_id=state.node_id,
                   node_type=state.node_type,
                   status="active",
                   registered_at=datetime.now(timezone.utc),
               )
               return (
                   state.with_status("registered"),
                   [ModelPostgresUpsertRegistrationIntent(
                       kind="postgres.upsert_registration",
                       record=record,
                       correlation_id=action.correlation_id,
                   )]
               )
           ```

        2. **Effect receives and executes** (performs side effect):
           ```python
           class NodePostgresEffect(NodeEffect):
               async def execute(self, intent: ModelCoreRegistrationIntent) -> None:
                   match intent:
                       case ModelPostgresUpsertRegistrationIntent():
                           await self.db.execute(
                               \"\"\"
                               INSERT INTO node_registrations (node_id, node_type, status)
                               VALUES ($1, $2, $3)
                               ON CONFLICT (node_id) DO UPDATE SET status = $3
                               \"\"\",
                               intent.record.node_id,
                               intent.record.node_type,
                               intent.record.status,
                           )
           ```

        3. **Correlation ID enables tracing** across the entire flow.

    Attributes:
        kind: Discriminator literal for intent routing. Always
            "postgres.upsert_registration". Used by Pydantic's discriminated
            union to route to correct handler. Placed first for optimal
            union type resolution performance.
        record: Registration record to upsert. Any BaseModel subclass is accepted,
            enabling flexible schemas. The Effect node maps this to database columns.

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
        ...     kind="postgres.upsert_registration",
        ...     record=NodeRecord(node_id="123", node_type="compute"),
        ...     correlation_id=uuid4(),
        ... )

    See Also:
        omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union
        omnibase_core.models.intents.ModelConsulRegisterIntent: Consul registration
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    # Pydantic checks fields in order when resolving discriminated unions,
    # so having the discriminator first speeds up type matching.
    kind: Literal["postgres.upsert_registration"] = Field(
        default="postgres.upsert_registration",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )
    record: BaseModel = Field(
        ...,
        description=(
            "Registration record to upsert. Accepts any BaseModel subclass, "
            "enabling flexible schemas. Effect maps this to database columns."
        ),
    )
