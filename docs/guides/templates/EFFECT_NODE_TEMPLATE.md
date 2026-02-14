> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > Templates > EFFECT Node

# EFFECT Node Template

## Overview

Template for building ONEX EFFECT nodes. EFFECT nodes handle **external I/O operations** -- any interaction with systems outside the ONEX runtime boundary (databases, APIs, file system, message queues).

**Architectural invariants**:

- Nodes are thin shells -- only `__init__` calling `super().__init__(container)`
- Handlers own ALL business logic
- YAML contracts define behavior
- Handlers are resolved via the container (DI), never directly instantiated
- EFFECT nodes emit `events[]` via `ModelHandlerOutput.for_effect(events=[...])`
- EFFECT nodes CANNOT emit `intents[]`, `projections[]`, or return `result`

## When to Use

- Database operations (PostgreSQL, Qdrant, Redis)
- HTTP/API calls to external services
- File system read/write operations
- Message queue interactions (Kafka, RabbitMQ)
- Service discovery (Consul, Kubernetes)
- Secret management (Vault)

## Directory Structure

```
nodes/node_user_storage_effect/
    contract.yaml              # ONEX contract (required)
    node.py                    # Thin node shell (required)
    handlers/
        handler_storage.py     # Business logic lives here
    models/
        __init__.py
        model_storage_request.py
        model_storage_result.py
```

## Template Files

### 1. YAML Contract (`contract.yaml`)

The contract is the **single source of truth** for node behavior.

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
node_version: "1.0.0"
name: "node_user_storage_effect"
node_type: "EFFECT_GENERIC"
description: "Storage operations for user records."

input_model:
  name: "ModelStorageRequest"
  module: "myapp.nodes.node_user_storage_effect.models.model_storage_request"

output_model:
  name: "ModelStorageResult"
  module: "myapp.nodes.node_user_storage_effect.models.model_storage_result"

# Capability-oriented naming (what it does, not what technology it uses)
capabilities:
  - name: "user.storage"
    description: "Store, query, update, and delete user records"
  - name: "user.storage.query"
  - name: "user.storage.upsert"

# External I/O operations
io_operations:
  - operation: "store_user"
    description: "Persist a user record"
    input_fields:
      - record: "ModelUserRecord"
      - correlation_id: "UUID | None"
    output_fields:
      - result: "ModelUpsertResult"
    idempotent: true

  - operation: "query_user"
    description: "Query user by user_id"
    input_fields:
      - user_id: "str"
    output_fields:
      - record: "ModelUserRecord | None"
    idempotent: true

# Error handling configuration
error_handling:
  retry_policy:
    max_retries: 3
    exponential_base: 2
    retry_on:
      - "ConnectionError"
      - "TimeoutError"
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    reset_timeout_seconds: 60

# Handler routing
handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - handler:
        name: "HandlerStorage"
        module: "myapp.nodes.node_user_storage_effect.handlers.handler_storage"
```

### 2. Node Implementation (`node.py`)

The node is a **thin coordination shell**. No business logic here. Handlers are resolved via the container, never directly instantiated.

```python
"""User storage effect node for database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeUserStorageEffect(NodeEffect):
    """Effect node for user storage operations.

    Capability: user.storage

    This node handles all external database interactions for user records.
    Behavior is driven by contract.yaml configuration.
    All business logic lives in handlers/handler_storage.py.

    Handlers are resolved via container DI -- never instantiate them directly.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the storage effect node."""
        super().__init__(container)


__all__ = ["NodeUserStorageEffect"]
```

### 3. Handler Implementation (`handlers/handler_storage.py`)

All business logic lives in the handler. Dependencies are resolved from the container, never instantiated directly.

```python
"""Storage handler for the user storage effect node."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput

if TYPE_CHECKING:
    from omnibase_core.protocols.protocol_database import ProtocolDatabase


class HandlerStorage:
    """Handler that owns the storage business logic.

    Dependencies (database client, etc.) are injected via the container --
    never instantiated directly in the handler or the node.
    """

    def __init__(self, db_client: ProtocolDatabase) -> None:
        """Initialize with injected dependencies.

        Args:
            db_client: Database client resolved from the container.
                       Never do ``DatabaseHandler()`` -- always resolve
                       via ``container.get_service(ProtocolDatabase)``.
        """
        self._db = db_client

    async def handle_store(
        self,
        record: dict[str, Any],
        correlation_id: UUID | None = None,
    ) -> ModelHandlerOutput:
        """Store a user record in the database.

        Args:
            record: User record data to persist.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            ModelHandlerOutput with events describing what happened.
        """
        result = await self._db.upsert(
            table="users",
            record=record,
            correlation_id=correlation_id,
        )

        # EFFECT nodes emit events, never return result
        return ModelHandlerOutput.for_effect(
            events=[
                {
                    "event_type": "user.stored",
                    "user_id": record.get("user_id"),
                    "correlation_id": str(correlation_id) if correlation_id else None,
                    "rows_affected": result.rows_affected,
                }
            ]
        )

    async def handle_query(
        self,
        user_id: str,
    ) -> ModelHandlerOutput:
        """Query a user record from the database.

        Args:
            user_id: The user ID to look up.

        Returns:
            ModelHandlerOutput with events describing the query result.
        """
        record = await self._db.query_one(
            table="users",
            filters={"user_id": user_id},
        )

        return ModelHandlerOutput.for_effect(
            events=[
                {
                    "event_type": "user.queried",
                    "user_id": user_id,
                    "found": record is not None,
                }
            ]
        )
```

### 4. Input Model (`models/model_storage_request.py`)

```python
"""Input model for user storage effect operations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelStorageRequest(BaseModel):
    """Input model for user storage operations."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    operation: str = Field(
        description="Storage operation: 'store' or 'query'",
    )
    record: dict[str, Any] | None = Field(
        default=None,
        description="User record data (required for store operations)",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID to query (required for query operations)",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for request tracing",
    )
```

### 5. Output Model (`models/model_storage_result.py`)

```python
"""Output model for user storage effect operations."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelStorageResult(BaseModel):
    """Output model for user storage operations."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(
        description="Whether the storage operation succeeded",
    )
    events_emitted: int = Field(
        default=0,
        description="Number of events emitted by this operation",
    )
```

## Output Constraints

EFFECT nodes emit **events** describing what external I/O occurred.

| Field | EFFECT |
|-------|--------|
| `events[]` | Allowed |
| `result` | Forbidden |
| `intents[]` | Forbidden |
| `projections[]` | Forbidden |

```python
# CORRECT -- EFFECT emits events
output = ModelHandlerOutput.for_effect(
    events=[{"event_type": "user.stored", "user_id": "u123"}]
)

# WRONG -- EFFECT cannot return result
output = ModelHandlerOutput.for_effect(
    result={"user_id": "u123"},  # ValueError!
)

# WRONG -- EFFECT cannot emit intents
output = ModelHandlerOutput.for_effect(
    intents=[some_intent],  # ValueError!
)
```

## Dependency Injection Pattern

Handlers receive dependencies via the container. Never instantiate service classes directly.

```python
# WRONG -- direct instantiation (anti-pattern)
class NodeMyEffect(NodeEffect):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self._http = HttpHandler()           # DO NOT DO THIS
        self._db = DatabaseHandler()         # DO NOT DO THIS
        self._file = FileHandler()           # DO NOT DO THIS

# CORRECT -- resolve from container
class NodeMyEffect(NodeEffect):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # Handler resolution happens through the container/registry,
        # driven by the contract's handler_routing configuration.
        # The node itself does NOT resolve or hold handler references.
```

The container resolves handlers based on the contract's `handler_routing` section. The node never needs to know which handler implementation it is using.

## Key Principles

1. **Node is a thin shell**: Only `__init__` calling `super().__init__(container)`. No methods, no state, no logic.
2. **Handler owns logic**: All I/O operations happen in handler classes.
3. **DI via container**: Handlers and their dependencies are resolved from `ModelONEXContainer`, never instantiated with `SomeHandler()`.
4. **Contract drives behavior**: I/O operations, retry policies, circuit breakers, and routing are defined in YAML.
5. **Capability-oriented naming**: Name by what it does ("user.storage"), not by technology ("postgres").
6. **Idempotent operations**: Mark operations as idempotent in the contract for safe retries.
7. **PEP 604 types**: Use `X | None` not `Optional[X]`, `list[str]` not `List[str]`.
8. **Pydantic v2**: Use `model_config = ConfigDict(...)` not `class Config:`. Use `pattern=` not `regex=`.
9. **`ModelONEXContainer`**: Always use `ModelONEXContainer` for DI, never `ModelContainer`.
10. **No backwards compatibility**: This repo has no external consumers.

## Testing

```python
"""Tests for the user storage effect handler."""

from unittest.mock import AsyncMock

import pytest

from myapp.nodes.node_user_storage_effect.handlers.handler_storage import (
    HandlerStorage,
)


@pytest.mark.unit
class TestHandlerStorage:
    """Test the storage handler directly -- not the node."""

    async def test_store_emits_event(self) -> None:
        mock_db = AsyncMock()
        mock_db.upsert.return_value = AsyncMock(rows_affected=1)

        handler = HandlerStorage(db_client=mock_db)
        result = await handler.handle_store(
            record={"user_id": "u1", "email": "a@b.com"},
        )

        assert len(result.events) == 1
        assert result.events[0]["event_type"] == "user.stored"
        assert result.result is None  # EFFECT cannot return result

    async def test_query_emits_found_event(self) -> None:
        mock_db = AsyncMock()
        mock_db.query_one.return_value = {"user_id": "u1"}

        handler = HandlerStorage(db_client=mock_db)
        result = await handler.handle_query(user_id="u1")

        assert result.events[0]["found"] is True
```

## Related Documentation

| Topic | Document |
|-------|----------|
| Node archetypes reference | [Node Archetypes](../../reference/node-archetypes.md) |
| Handler contract guide | [Handler Contract Guide](../../contracts/HANDLER_CONTRACT_GUIDE.md) |
| Four-node architecture | [ONEX Four-Node Architecture](../../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| Execution shapes | [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) |
| Container types | [Container Types](../../architecture/CONTAINER_TYPES.md) |
| Dependency injection | [Dependency Injection](../../architecture/DEPENDENCY_INJECTION.md) |
| Coding standards | [CLAUDE.md](../../../CLAUDE.md) |
