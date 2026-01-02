# Execution Shape Examples

> **Version**: 1.0.0
> **Ticket**: OMN-933
> **Status**: Reference
> **Last Updated**: 2025-12-19

## Overview

This document provides practical, real-world examples for each of the five canonical execution shapes defined in [CANONICAL_EXECUTION_SHAPES.md](CANONICAL_EXECUTION_SHAPES.md). These examples demonstrate how to correctly implement message routing patterns in the ONEX Four-Node Architecture.

Each example includes:
- **Use Case**: A concrete business scenario
- **When to Use**: Guidance on when this shape is appropriate
- **Code Example**: Complete, runnable code demonstrating the pattern
- **Why This Shape**: Explanation of architectural reasoning

---

## Table of Contents

1. [Shape 1: Event to Orchestrator](#shape-1-event-to-orchestrator)
2. [Shape 2: Event to Reducer](#shape-2-event-to-reducer)
3. [Shape 3: Intent to Effect](#shape-3-intent-to-effect)
4. [Shape 4: Command to Orchestrator](#shape-4-command-to-orchestrator)
5. [Shape 5: Command to Effect](#shape-5-command-to-effect)
6. [Summary: Choosing the Right Shape](#summary-choosing-the-right-shape)

---

## Shape 1: Event to Orchestrator

### Use Case: Order Processing Workflow Triggered by Webhook

A payment provider sends a webhook when a payment is confirmed. This external event triggers a multi-step order fulfillment workflow.

### When to Use

Use **Event to Orchestrator** when:
- An external event (webhook, Kafka message, timer) arrives
- The event requires **multi-step coordination** across multiple nodes
- You need **lease-based single-writer semantics** for workflow ownership
- Multiple downstream nodes must be orchestrated in sequence or parallel

### Code Example

```python
from uuid import uuid4
from datetime import timedelta
from typing import Any

from omnibase_core.nodes import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_action_type import EnumActionType


class NodeOrderFulfillmentOrchestrator(NodeOrchestrator):
    """Orchestrates order fulfillment workflow triggered by payment events."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")

    async def handle_payment_confirmed(
        self, event: ModelEventEnvelope
    ) -> None:
        """
        Handle payment.confirmed event and orchestrate fulfillment.

        This is Shape 1: Event -> Orchestrator
        """
        order_id = event.payload.get("order_id")
        self.logger.info(f"Payment confirmed for order {order_id}")

        # Acquire exclusive lease for this workflow
        lease = await self.acquire_lease(
            workflow_id=f"order-fulfillment-{order_id}",
            lease_duration=timedelta(minutes=30)
        )

        # Step 1: Validate inventory (Effect node)
        validate_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeInventoryValidatorEffect",
            lease_id=lease.lease_id,
            epoch=0,
            payload={"order_id": order_id, "items": event.payload.get("items")}
        )

        # Step 2: Reserve shipping slot (Effect node, depends on Step 1)
        shipping_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeShippingReservationEffect",
            dependencies=[validate_action.action_id],
            lease_id=lease.lease_id,
            epoch=1,
            payload={"order_id": order_id}
        )

        # Step 3: Notify customer (Effect node, depends on Step 2)
        notify_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeCustomerNotificationEffect",
            dependencies=[shipping_action.action_id],
            lease_id=lease.lease_id,
            epoch=2,
            payload={"order_id": order_id, "template": "order_shipped"}
        )

        # Execute workflow with dependency ordering
        await self.execute_workflow([
            validate_action,
            shipping_action,
            notify_action
        ])


# Event handler registration (e.g., Kafka consumer)
@event_handler("payment.confirmed")
async def on_payment_confirmed(event: ModelEventEnvelope) -> None:
    """Route payment events to the fulfillment orchestrator."""
    container = get_container()  # Your DI container
    orchestrator = NodeOrderFulfillmentOrchestrator(container)
    await orchestrator.handle_payment_confirmed(event)
```

### Why This Shape

**Events represent facts that happened externally.** When a payment provider confirms a payment, this is an external fact that our system must react to. The reaction involves multiple coordinated steps:

1. **Multi-step coordination**: Inventory check, shipping reservation, and notification are distinct operations
2. **Ordering dependencies**: Each step depends on the previous one
3. **Single-writer semantics**: Only one workflow should process a given order
4. **Error recovery**: If shipping fails, the orchestrator can retry or compensate

Routing directly to a Reducer or Effect would bypass this coordination layer, leading to race conditions or incomplete workflows.

---

## Shape 2: Event to Reducer

### Use Case: Order Status Update from Domain Event

When an order ships, a domain event triggers a state transition in the order FSM (Finite State Machine).

### When to Use

Use **Event to Reducer** when:
- A domain event indicates a **state change** occurred
- You need to update an **FSM (finite state machine)**
- The result should emit **Intents** for side effects (not execute them directly)
- The state transition logic must be **pure and testable**

### Code Example

```python
from typing import Any
from pydantic import BaseModel

from omnibase_core.nodes import NodeReducer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.fsm.model_intent import ModelIntent
from omnibase_core.enums.enum_intent_type import EnumIntentType


class OrderState(BaseModel):
    """Order FSM state."""
    order_id: str
    status: str  # PENDING, PAID, SHIPPED, DELIVERED, CANCELLED
    shipped_at: str | None = None
    tracking_number: str | None = None


class NodeOrderStateReducer(NodeReducer):
    """
    Manages order state transitions via pure FSM logic.

    This is Shape 2: Event -> Reducer
    """

    # Valid FSM transitions
    VALID_TRANSITIONS: dict[str, list[str]] = {
        "PENDING": ["PAID", "CANCELLED"],
        "PAID": ["SHIPPED", "CANCELLED"],
        "SHIPPED": ["DELIVERED"],
        "DELIVERED": [],  # Terminal state
        "CANCELLED": [],  # Terminal state
    }

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")

    async def handle_shipment_event(
        self, event: ModelEventEnvelope
    ) -> tuple[OrderState, list[ModelIntent]]:
        """
        Handle shipment.created event and transition order state.

        Returns:
            Tuple of (new_state, intents_to_execute)
        """
        order_id = event.payload.get("order_id")
        tracking_number = event.payload.get("tracking_number")
        shipped_at = event.payload.get("shipped_at")

        # Load current state (via intent in real implementation)
        current_state = await self._load_state(order_id)

        # Validate transition
        if "SHIPPED" not in self.VALID_TRANSITIONS.get(current_state.status, []):
            self.logger.warning(
                f"Invalid transition: {current_state.status} -> SHIPPED"
            )
            return current_state, []

        # Pure state transition
        new_state = OrderState(
            order_id=order_id,
            status="SHIPPED",
            shipped_at=shipped_at,
            tracking_number=tracking_number
        )

        # Emit intents for side effects (Reducer doesn't execute I/O)
        intents = [
            # Persist the new state
            ModelIntent(
                intent_type=EnumIntentType.DATABASE_WRITE,
                target="orders_table",
                priority=10,
                payload={
                    "order_id": order_id,
                    "status": "SHIPPED",
                    "shipped_at": shipped_at,
                    "tracking_number": tracking_number
                }
            ),
            # Send notification email
            ModelIntent(
                intent_type=EnumIntentType.NOTIFICATION,
                target="email_service",
                priority=5,
                payload={
                    "template": "order_shipped",
                    "order_id": order_id,
                    "tracking_number": tracking_number
                }
            ),
            # Update analytics
            ModelIntent(
                intent_type=EnumIntentType.EVENT_PUBLISH,
                target="analytics_topic",
                priority=1,
                payload={
                    "event_type": "order.shipped",
                    "order_id": order_id
                }
            )
        ]

        self.logger.info(f"Order {order_id} transitioned to SHIPPED")
        return new_state, intents

    async def _load_state(self, order_id: str) -> OrderState:
        """Load current state (simplified for example)."""
        # In production, this would emit an intent to load from DB
        return OrderState(order_id=order_id, status="PAID")


# Event handler registration
@event_handler("shipment.created")
async def on_shipment_created(event: ModelEventEnvelope) -> None:
    """Route shipment events to the order state reducer."""
    container = get_container()
    reducer = NodeOrderStateReducer(container)
    new_state, intents = await reducer.handle_shipment_event(event)

    # Intents are queued for Effect nodes to execute
    await publish_intents(intents)
```

### Why This Shape

**Reducers manage state transitions with pure FSM logic.** The shipment event represents a domain fact that changes the order's state:

1. **Pure logic**: The transition `PAID -> SHIPPED` is deterministic and side-effect free
2. **Testability**: You can test FSM transitions without mocking databases or email services
3. **Intent emission**: Side effects (DB write, email) are described as Intents, not executed
4. **Clear separation**: The Reducer decides WHAT should happen; Effect nodes decide HOW

If this event went directly to an Orchestrator, it would conflate state management with workflow coordination.

---

## Shape 3: Intent to Effect

### Use Case: Persisting State Changes to Database

After a Reducer emits a database write Intent, an Effect node executes the actual I/O operation.

### When to Use

Use **Intent to Effect** when:
- A Reducer has emitted an **Intent** describing a side effect
- The side effect requires **external I/O** (database, API, file system)
- You need **retry logic**, **circuit breakers**, or **transaction management**
- The I/O implementation details should be **decoupled** from state logic

### Code Example

```python
from typing import Any

from omnibase_core.nodes import NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.fsm.model_intent import ModelIntent
from omnibase_core.models.results.model_intent_result import ModelIntentResult
from omnibase_core.enums.enum_intent_type import EnumIntentType
from omnibase_core.decorators.error_handling import standard_error_handling


class NodeDatabaseWriterEffect(NodeEffect):
    """
    Executes database write intents emitted by Reducers.

    This is Shape 3: Intent -> Effect
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
        self.db_client = container.get_service("ProtocolDatabaseClient")

    @standard_error_handling
    async def execute_intent(self, intent: ModelIntent) -> ModelIntentResult:
        """
        Execute a database write intent.

        The Reducer described WHAT to write; this Effect determines HOW.
        """
        if intent.intent_type != EnumIntentType.DATABASE_WRITE:
            return ModelIntentResult(
                intent_id=intent.intent_id,
                status="skipped",
                message="Not a database write intent"
            )

        table = intent.target
        payload = intent.payload

        self.logger.info(f"Executing DB write to {table}: {payload}")

        try:
            # Execute the actual I/O with retry and circuit breaker
            async with self.db_client.transaction() as tx:
                await tx.upsert(
                    table=table,
                    data=payload,
                    conflict_keys=["order_id"]
                )
                await tx.commit()

            return ModelIntentResult(
                intent_id=intent.intent_id,
                status="completed",
                message=f"Successfully wrote to {table}"
            )

        except Exception as e:
            self.logger.error(f"DB write failed: {e}")
            return ModelIntentResult(
                intent_id=intent.intent_id,
                status="failed",
                message=str(e),
                retry_eligible=True
            )


class NodeNotificationEffect(NodeEffect):
    """Executes notification intents (email, SMS, push)."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
        self.email_client = container.get_service("ProtocolEmailClient")

    @standard_error_handling
    async def execute_intent(self, intent: ModelIntent) -> ModelIntentResult:
        """Execute notification intent."""
        if intent.intent_type != EnumIntentType.NOTIFICATION:
            return ModelIntentResult(
                intent_id=intent.intent_id,
                status="skipped"
            )

        template = intent.payload.get("template")
        order_id = intent.payload.get("order_id")
        tracking_number = intent.payload.get("tracking_number")

        self.logger.info(f"Sending {template} notification for order {order_id}")

        # Load customer email (could be another intent chain)
        customer = await self._load_customer(order_id)

        await self.email_client.send(
            to=customer.email,
            template=template,
            variables={
                "order_id": order_id,
                "tracking_number": tracking_number,
                "customer_name": customer.name
            }
        )

        return ModelIntentResult(
            intent_id=intent.intent_id,
            status="completed"
        )


# Intent consumer (e.g., Kafka consumer for intent queue)
async def process_intent_queue() -> None:
    """Consume and execute intents from the queue."""
    container = get_container()

    # Route intents to appropriate Effect nodes
    effect_registry = {
        EnumIntentType.DATABASE_WRITE: NodeDatabaseWriterEffect(container),
        EnumIntentType.NOTIFICATION: NodeNotificationEffect(container),
    }

    async for intent in consume_intent_queue():
        effect_node = effect_registry.get(intent.intent_type)
        if effect_node:
            result = await effect_node.execute_intent(intent)
            await publish_intent_result(result)
```

### Why This Shape

**Intents describe WHAT should happen; Effects decide HOW.** The Reducer's Intent says "write this data to orders_table," but the Effect handles:

1. **Implementation details**: Connection pooling, transactions, conflict resolution
2. **Error handling**: Retries, circuit breakers, dead letter queues
3. **I/O isolation**: Database failures don't contaminate FSM logic
4. **Testability**: Reducer tests don't need database mocks; Effect tests focus on I/O

If the Reducer executed I/O directly, it would violate purity and make FSM logic untestable.

---

## Shape 4: Command to Orchestrator

### Use Case: User Initiates Data Import via API

A user calls an API endpoint to start a data import workflow. The command triggers orchestrated processing.

### When to Use

Use **Command to Orchestrator** when:
- An **API endpoint** or **CLI command** triggers a workflow
- The command requires **multi-step processing** with coordination
- You need to **track workflow progress** and handle partial failures
- **Multiple nodes** must be invoked in a specific order

### Code Example

```python
from uuid import uuid4, UUID
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from omnibase_core.nodes import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_action_type import EnumActionType


router = APIRouter()


class ImportRequest(BaseModel):
    """API request for data import."""
    source_url: str
    target_table: str
    options: dict[str, Any] = {}


class ImportResponse(BaseModel):
    """API response for data import."""
    workflow_id: str
    status: str
    message: str


class NodeDataImportOrchestrator(NodeOrchestrator):
    """
    Orchestrates data import workflows triggered by API commands.

    This is Shape 4: Command -> Orchestrator
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")

    async def start_import(self, request: ImportRequest) -> str:
        """
        Start a data import workflow.

        Returns:
            workflow_id for tracking progress
        """
        workflow_id = str(uuid4())
        self.logger.info(f"Starting import workflow {workflow_id}")

        # Acquire lease for exclusive workflow ownership
        lease = await self.acquire_lease(
            workflow_id=workflow_id,
            lease_duration=timedelta(hours=1)
        )

        # Step 1: Fetch data from source (Effect)
        fetch_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeDataFetcherEffect",
            lease_id=lease.lease_id,
            epoch=0,
            payload={
                "source_url": request.source_url,
                "workflow_id": workflow_id
            }
        )

        # Step 2: Validate and transform data (Compute)
        transform_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.COMPUTE,
            target_node_type="NodeDataTransformerCompute",
            dependencies=[fetch_action.action_id],
            lease_id=lease.lease_id,
            epoch=1,
            payload={
                "workflow_id": workflow_id,
                "schema": request.target_table
            }
        )

        # Step 3: Load data into target (Effect)
        load_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EFFECT,
            target_node_type="NodeDataLoaderEffect",
            dependencies=[transform_action.action_id],
            lease_id=lease.lease_id,
            epoch=2,
            payload={
                "workflow_id": workflow_id,
                "target_table": request.target_table
            }
        )

        # Step 4: Update import status (Reducer via Event)
        status_action = ModelAction(
            action_id=uuid4(),
            action_type=EnumActionType.EVENT_PUBLISH,
            target_node_type="import_status_topic",
            dependencies=[load_action.action_id],
            lease_id=lease.lease_id,
            epoch=3,
            payload={
                "event_type": "import.completed",
                "workflow_id": workflow_id
            }
        )

        # Execute workflow asynchronously
        await self.execute_workflow_async([
            fetch_action,
            transform_action,
            load_action,
            status_action
        ])

        return workflow_id


# API endpoint
@router.post("/api/v1/imports", response_model=ImportResponse)
async def create_import(request: ImportRequest) -> ImportResponse:
    """
    Start a data import workflow.

    This is a Command -> Orchestrator pattern.
    """
    container = get_container()
    orchestrator = NodeDataImportOrchestrator(container)

    try:
        workflow_id = await orchestrator.start_import(request)
        return ImportResponse(
            workflow_id=workflow_id,
            status="started",
            message=f"Import workflow started. Track progress at /api/v1/imports/{workflow_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/imports/{workflow_id}")
async def get_import_status(workflow_id: str) -> dict[str, Any]:
    """Get import workflow status."""
    container = get_container()
    # Query workflow status from storage
    return await container.get_service("ProtocolWorkflowStore").get_status(workflow_id)
```

### Why This Shape

**Commands express user intent to perform an action.** When a user clicks "Import Data," they're issuing a command that requires:

1. **Multi-step processing**: Fetch, transform, load, notify
2. **Workflow tracking**: User can check progress via `/imports/{id}`
3. **Error recovery**: If transform fails, orchestrator can retry or rollback
4. **Resource management**: Lease prevents duplicate workflows for same import

Routing directly to an Effect would skip coordination; routing to a Reducer would conflate state management with workflow initiation.

---

## Shape 5: Command to Effect

### Use Case: Simple Health Check Endpoint

An API endpoint checks database connectivity. No workflow coordination needed.

### When to Use

Use **Command to Effect** when:
- The command requires a **single I/O operation**
- No **multi-step coordination** is needed
- The operation is **stateless** (no FSM transitions)
- You need **immediate response** without workflow tracking

### Code Example

```python
from typing import Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from omnibase_core.nodes import NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.decorators.error_handling import standard_error_handling


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    cache: str
    timestamp: str


class NodeHealthCheckEffect(NodeEffect):
    """
    Performs health checks against external systems.

    This is Shape 5: Command -> Effect
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
        self.db_client = container.get_service("ProtocolDatabaseClient")
        self.cache_client = container.get_service("ProtocolCacheClient")

    @standard_error_handling
    async def check_health(self) -> dict[str, str]:
        """
        Check health of all external dependencies.

        Direct I/O without orchestration - appropriate for simple operations.
        """
        results = {
            "database": "unknown",
            "cache": "unknown"
        }

        # Check database
        try:
            await self.db_client.execute("SELECT 1")
            results["database"] = "healthy"
        except Exception as e:
            self.logger.warning(f"Database health check failed: {e}")
            results["database"] = "unhealthy"

        # Check cache
        try:
            await self.cache_client.ping()
            results["cache"] = "healthy"
        except Exception as e:
            self.logger.warning(f"Cache health check failed: {e}")
            results["cache"] = "unhealthy"

        return results


class NodeUserFetcherEffect(NodeEffect):
    """Fetches user data from database."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.db_client = container.get_service("ProtocolDatabaseClient")

    @standard_error_handling
    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """
        Fetch a single user by ID.

        Simple CRUD operation - no orchestration needed.
        """
        result = await self.db_client.query(
            "SELECT * FROM users WHERE id = $1",
            [user_id]
        )
        return result[0] if result else None


# API endpoints
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    This is a Command -> Effect pattern for simple I/O.
    """
    container = get_container()
    effect = NodeHealthCheckEffect(container)
    results = await effect.check_health()

    status = "healthy" if all(v == "healthy" for v in results.values()) else "degraded"

    return HealthResponse(
        status=status,
        database=results["database"],
        cache=results["cache"],
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/api/v1/users/{user_id}")
async def get_user(user_id: str) -> dict[str, Any]:
    """
    Get user by ID.

    Simple read operation - Command -> Effect is appropriate.
    """
    container = get_container()
    effect = NodeUserFetcherEffect(container)

    user = await effect.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### Why This Shape

**Simple operations don't need orchestration.** A health check or user lookup is:

1. **Single operation**: One database query, no dependencies
2. **Stateless**: No FSM transitions to manage
3. **Immediate**: Response returns directly, no workflow tracking
4. **Simple**: Adding orchestration would be unnecessary complexity

Using an Orchestrator for a health check would be over-engineering. Using a Reducer would be incorrect since there's no state to reduce.

---

## Summary: Choosing the Right Shape

Use this decision tree to select the correct execution shape:

```text
Is this triggered by an external event or a command?
|
+-- External Event (Kafka, webhook, timer)
|   |
|   +-- Needs multi-step coordination? --> Shape 1: Event -> Orchestrator
|   |
|   +-- Needs state transition (FSM)?  --> Shape 2: Event -> Reducer
|
+-- Command (API, CLI)
    |
    +-- Needs multi-step coordination? --> Shape 4: Command -> Orchestrator
    |
    +-- Single I/O operation?          --> Shape 5: Command -> Effect


Is this an Intent from a Reducer?
|
+-- Yes --> Shape 3: Intent -> Effect
```

### Quick Reference Table

| Trigger | Need | Shape | Example |
|---------|------|-------|---------|
| Event | Multi-step workflow | Event -> Orchestrator | Payment triggers order fulfillment |
| Event | State transition | Event -> Reducer | Shipment updates order status |
| Intent | Execute side effect | Intent -> Effect | Persist state to database |
| Command | Multi-step workflow | Command -> Orchestrator | API starts data import |
| Command | Single I/O | Command -> Effect | Health check, user lookup |

### Anti-Pattern Reminder

**Never**:
- Command -> Reducer (bypasses orchestration)
- Reducer -> I/O (violates purity)
- Effect -> Reducer (wrong data flow direction)
- Compute -> I/O (violates purity)

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Canonical Execution Shapes](CANONICAL_EXECUTION_SHAPES.md) | Shape definitions and constraints |
| [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md) | Complete architecture overview |
| [Node Types Guide](../guides/node-building/02_NODE_TYPES.md) | When to use each node type |
| [Message Topic Mapping](MESSAGE_TOPIC_MAPPING.md) | Topic routing rules |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-19
**Primary Maintainer**: ONEX Framework Team
