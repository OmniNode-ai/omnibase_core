> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Node Building](./README.md) > Patterns Catalog

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../../CLAUDE.md).

# Patterns Catalog -- Common ONEX Node Patterns

**Status**: Complete

## Overview

This catalog provides correct, handler-based patterns for building ONEX nodes. Every pattern follows the same structure:

1. **YAML contract** -- declares behavior, capabilities, and constraints
2. **Thin node shell** -- `__init__` calls `super().__init__(container)` and nothing else
3. **Handler class** -- owns all business logic

All examples use real classes from the omnibase_core codebase and follow the four-node architecture invariants.

## Table of Contents

1. [COMPUTE Node Patterns](#compute-node-patterns)
2. [EFFECT Node Patterns](#effect-node-patterns)
3. [REDUCER Node Patterns](#reducer-node-patterns)
4. [ORCHESTRATOR Node Patterns](#orchestrator-node-patterns)
5. [Testing Patterns](#testing-patterns)

---

## COMPUTE Node Patterns

COMPUTE nodes perform pure transformations. They return a typed `result` via `ModelHandlerOutput.for_compute()`. They cannot emit events, intents, or projections.

### Pattern 1: Data Validation

Validate input data against schema rules and return a typed result.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_schema_validator_compute"
node_type: "COMPUTE_GENERIC"
description: "Validates data structures against contract-defined schema rules."

input_model:
  name: "ModelValidationRequest"
  module: "myapp.nodes.schema_validator.models"

output_model:
  name: "ModelValidationResult"
  module: "myapp.nodes.schema_validator.models"

capabilities:
  - name: "data_validation"
  - name: "schema_enforcement"

validation_rules:
  - rule_id: "VAL-001"
    name: "Required Fields"
    severity: "ERROR"
    detection_strategy:
      type: "field_presence"
      required_fields: ["user_id", "email"]

  - rule_id: "VAL-002"
    name: "Email Format"
    severity: "ERROR"
    detection_strategy:
      type: "regex_pattern"
      field: "email"
      pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
```

**node.py** -- thin shell:

```python
"""Schema validator compute node."""

from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeSchemaValidatorCompute(NodeCompute):
    """Validates data against contract-defined rules. Logic in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py** -- all logic here:

```python
"""Handler for schema validation logic."""

from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


class ModelValidationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: dict[str, object] = Field(...)
    rules: list[dict[str, object]] = Field(default_factory=list)


class ModelValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    fields_checked: int = 0


class HandlerSchemaValidator:
    """Pure validation logic. No I/O, no side effects."""

    def validate(
        self,
        request: ModelValidationRequest,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[ModelValidationResult]:
        errors: list[str] = []
        data = request.data

        for rule in request.rules:
            rule_type = rule.get("type")
            field = str(rule.get("field", ""))

            if rule_type == "field_presence":
                if field not in data or data[field] is None:
                    errors.append(f"Missing required field: {field}")

            elif rule_type == "regex_pattern":
                pattern = str(rule.get("pattern", ""))
                value = data.get(field)
                if isinstance(value, str) and not re.match(pattern, value):
                    errors.append(f"Field '{field}' does not match pattern")

        result = ModelValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            fields_checked=len(request.rules),
        )

        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="compute.schema.validator",
            result=result,
        )
```

### Pattern 2: Data Transformation

Transform data between formats. Pure computation, deterministic output.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_data_transformer_compute"
node_type: "COMPUTE_GENERIC"
description: "Transforms data between formats."

input_model:
  name: "ModelTransformRequest"
  module: "myapp.nodes.data_transformer.models"

output_model:
  name: "ModelTransformResult"
  module: "myapp.nodes.data_transformer.models"

capabilities:
  - name: "data.transform"
  - name: "data.normalize"
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeDataTransformerCompute(NodeCompute):
    """Data transformation. Logic in handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput


class ModelTransformRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    records: list[dict[str, object]] = Field(...)
    normalize_keys: bool = False


class ModelTransformResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    transformed: list[dict[str, object]] = Field(default_factory=list)
    record_count: int = 0


class HandlerDataTransformer:
    """Pure data transformation. Same input always produces same output."""

    def transform(
        self,
        request: ModelTransformRequest,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[ModelTransformResult]:
        transformed = []

        for record in request.records:
            if request.normalize_keys:
                record = {
                    k.lower().replace(" ", "_"): v for k, v in record.items()
                }
            transformed.append(record)

        result = ModelTransformResult(
            transformed=transformed,
            record_count=len(transformed),
        )

        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="compute.data.transformer",
            result=result,
        )
```

---

## EFFECT Node Patterns

EFFECT nodes perform external I/O. They can emit events but cannot return results, emit intents, or emit projections. All I/O logic lives in handlers.

### Pattern 3: Database Storage

Persist records to a database via a capability-based handler.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_user_storage_effect"
node_type: "EFFECT_GENERIC"
description: "Persists user records to database."

input_model:
  name: "ModelStorageRequest"
  module: "myapp.nodes.user_storage.models"

output_model:
  name: "ModelStorageResult"
  module: "myapp.nodes.user_storage.models"

capabilities:
  - name: "user.storage"
  - name: "user.storage.upsert"

io_operations:
  - operation: "store_user"
    description: "Persist a user record"
    idempotent: true

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
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeUserStorageEffect(NodeEffect):
    """User storage effect. Handler performs all database I/O."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class ModelStorageRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    user_id: str
    email: str
    name: str


class HandlerUserStorage:
    """Handler that performs database I/O via injected service."""

    def __init__(self, db_service: object) -> None:
        self._db = db_service

    async def store_user(
        self,
        request: ModelStorageRequest,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        # Perform the actual I/O
        await self._db.upsert(  # type: ignore[attr-defined]
            table="users",
            data={"user_id": request.user_id, "email": request.email, "name": request.name},
        )

        # EFFECT nodes emit events, not results
        stored_event = ModelEventEnvelope(
            event_type="user.stored",
            payload={"user_id": request.user_id},
            correlation_id=correlation_id,
        )

        return ModelHandlerOutput.for_effect(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="effect.user.storage",
            events=(stored_event,),
        )
```

### Pattern 4: API Integration with Circuit Breaker

Call an external API with retry and circuit breaker, declared in the contract.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_payment_gateway_effect"
node_type: "EFFECT_GENERIC"
description: "Processes payments via external gateway."

capabilities:
  - name: "payment.process"

io_operations:
  - operation: "charge_card"
    idempotent: true

error_handling:
  retry_policy:
    max_retries: 3
    exponential_base: 2
    retry_on: ["ConnectionError", "TimeoutError"]
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    reset_timeout_seconds: 60
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodePaymentGatewayEffect(NodeEffect):
    """Payment gateway effect. Retry/circuit breaker configured in contract."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class HandlerPaymentGateway:
    """Handler that calls external payment API.

    Circuit breaker and retry logic are driven by the contract
    and applied by the runtime, not by the handler.
    """

    def __init__(self, gateway_client: object) -> None:
        self._client = gateway_client

    async def charge(
        self,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        response = await self._client.charge(  # type: ignore[attr-defined]
            amount=amount_cents,
            currency=currency,
            idempotency_key=idempotency_key,
        )

        payment_event = ModelEventEnvelope(
            event_type="payment.charged",
            payload={"charge_id": response.id, "amount": amount_cents},  # type: ignore[attr-defined]
            correlation_id=correlation_id,
        )

        return ModelHandlerOutput.for_effect(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="effect.payment.gateway",
            events=(payment_event,),
        )
```

---

## REDUCER Node Patterns

REDUCER nodes are pure functions: `delta(state, event) -> (new_state, intents[])`. They maintain no mutable instance state. State is immutable (frozen Pydantic models with `with_*` transition methods). FSM transitions are declared in the contract YAML.

### Pattern 5: Order State Machine (FSM)

Track order lifecycle through contract-driven FSM transitions.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_order_processing_reducer"
node_type: "REDUCER_GENERIC"
description: "FSM-driven reducer for order processing."

state_machine:
  state_machine_name: "order_processing_fsm"
  initial_state: "idle"

  states:
    - state_name: "idle"
      description: "Waiting for order"
    - state_name: "pending"
      description: "Order placed, awaiting payment"
      entry_actions: ["emit_payment_intent"]
    - state_name: "confirmed"
      description: "Payment confirmed"
      entry_actions: ["emit_fulfillment_intent"]
    - state_name: "completed"
      is_terminal: true
    - state_name: "failed"
      is_terminal: true

  transitions:
    - from_state: "idle"
      to_state: "pending"
      trigger: "order_placed"
    - from_state: "pending"
      to_state: "confirmed"
      trigger: "payment_confirmed"
    - from_state: "confirmed"
      to_state: "completed"
      trigger: "order_fulfilled"
    - from_state: "*"
      to_state: "failed"
      trigger: "error_received"

intent_emission:
  enabled: true
  intents:
    - intent_type: "payment.process"
      target_pattern: "payment://orders/{order_id}"
    - intent_type: "fulfillment.start"
      target_pattern: "fulfillment://orders/{order_id}"

idempotency:
  enabled: true
  strategy: "event_id_tracking"
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeReducer

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrderProcessingReducer(NodeReducer):
    """Order processing reducer. FSM transitions driven by contract.yaml."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**state model** -- immutable with `with_*` methods:

```python
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModelOrderState(BaseModel):
    """Immutable state for order processing FSM."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: str = "idle"
    order_id: str | None = None
    payment_confirmed: bool = False
    fulfillment_confirmed: bool = False
    last_processed_event_id: UUID | None = None

    def with_order_placed(self, order_id: str, event_id: UUID) -> ModelOrderState:
        """Return new state with order placed."""
        return ModelOrderState(
            status="pending",
            order_id=order_id,
            payment_confirmed=self.payment_confirmed,
            fulfillment_confirmed=self.fulfillment_confirmed,
            last_processed_event_id=event_id,
        )

    def with_payment_confirmed(self, event_id: UUID) -> ModelOrderState:
        """Return new state with payment confirmed."""
        return ModelOrderState(
            status="confirmed",
            order_id=self.order_id,
            payment_confirmed=True,
            fulfillment_confirmed=self.fulfillment_confirmed,
            last_processed_event_id=event_id,
        )

    def with_completed(self, event_id: UUID) -> ModelOrderState:
        """Return new state marking fulfillment complete."""
        return ModelOrderState(
            status="completed",
            order_id=self.order_id,
            payment_confirmed=True,
            fulfillment_confirmed=True,
            last_processed_event_id=event_id,
        )

    def is_duplicate_event(self, event_id: UUID) -> bool:
        """Check if event was already processed (idempotency)."""
        return self.last_processed_event_id == event_id
```

**handler.py** -- pure reduction logic:

```python
from __future__ import annotations

from omnibase_core.models.reducer.model_intent import ModelIntent


class HandlerOrderReducer:
    """Pure reduction: delta(state, event) -> (new_state, intents[]).

    No mutable instance state. No I/O. No logging.
    Side effects are described as intents for the effect layer.
    """

    def reduce(
        self,
        state: ModelOrderState,
        trigger: str,
        event_id: UUID,
        payload: dict[str, object],
    ) -> tuple[ModelOrderState, tuple[ModelIntent, ...]]:
        # Idempotency check
        if state.is_duplicate_event(event_id):
            return state, ()

        if trigger == "order_placed":
            order_id = str(payload.get("order_id", ""))
            new_state = state.with_order_placed(order_id, event_id)
            intents = (
                ModelIntent(
                    intent_type="payment.process",
                    target="payment_service",
                    payload={"order_id": order_id},
                    priority=1,
                ),
            )
            return new_state, intents

        if trigger == "payment_confirmed":
            new_state = state.with_payment_confirmed(event_id)
            intents = (
                ModelIntent(
                    intent_type="fulfillment.start",
                    target="fulfillment_service",
                    payload={"order_id": state.order_id},
                    priority=1,
                ),
            )
            return new_state, intents

        if trigger == "order_fulfilled":
            new_state = state.with_completed(event_id)
            return new_state, ()

        if trigger == "error_received":
            new_state = ModelOrderState(
                status="failed",
                order_id=state.order_id,
                payment_confirmed=state.payment_confirmed,
                fulfillment_confirmed=state.fulfillment_confirmed,
                last_processed_event_id=event_id,
            )
            return new_state, ()

        # Unknown trigger -- no transition
        return state, ()
```

### Pattern 6: Metrics Aggregation

Aggregate metrics from multiple sources using pure reduction.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_metrics_aggregation_reducer"
node_type: "REDUCER_GENERIC"
description: "Aggregates metrics via pure reduction."

state_machine:
  state_machine_name: "metrics_aggregation_fsm"
  initial_state: "idle"

  states:
    - state_name: "idle"
    - state_name: "collecting"
      entry_actions: ["start_collection"]
    - state_name: "completed"
      is_terminal: true

  transitions:
    - from_state: "idle"
      to_state: "collecting"
      trigger: "data_received"
    - from_state: "collecting"
      to_state: "completed"
      trigger: "aggregation_complete"
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeReducer

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeMetricsAggregationReducer(NodeReducer):
    """Metrics aggregation. Pure FSM, no mutable state."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.reducer.model_intent import ModelIntent


class ModelAggregationState(BaseModel):
    """Immutable aggregation state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    sums: dict[str, float] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    status: str = "idle"

    def with_data_folded(
        self, key: str, value: float
    ) -> ModelAggregationState:
        new_sums = {**self.sums, key: self.sums.get(key, 0.0) + value}
        new_counts = {**self.counts, key: self.counts.get(key, 0) + 1}
        return ModelAggregationState(
            sums=new_sums,
            counts=new_counts,
            status="collecting",
        )

    def averages(self) -> dict[str, float]:
        return {
            k: self.sums[k] / self.counts[k]
            for k in self.sums
            if self.counts.get(k, 0) > 0
        }


class HandlerMetricsAggregation:
    """Pure aggregation: fold data points into immutable state."""

    def reduce(
        self,
        state: ModelAggregationState,
        data_points: list[dict[str, float]],
    ) -> tuple[ModelAggregationState, tuple[ModelIntent, ...]]:
        current = state

        for point in data_points:
            for key, value in point.items():
                current = current.with_data_folded(key, value)

        intents = (
            ModelIntent(
                intent_type="record_metric",
                target="metrics_service",
                payload={
                    "averages": current.averages(),
                    "sample_count": sum(current.counts.values()),
                },
                priority=2,
            ),
        )

        return current, intents
```

---

## ORCHESTRATOR Node Patterns

ORCHESTRATOR nodes coordinate workflows. They emit events and intents but never return results. Workflow definitions, handler routing, and intent routing tables are declared in the contract YAML.

### Pattern 7: Order Processing Workflow

Coordinate an end-to-end order workflow across multiple node types.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_order_workflow_orchestrator"
node_type: "ORCHESTRATOR_GENERIC"
description: "Coordinates order processing workflow."

workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: "order_processing"
      description: "End-to-end order processing"
    execution_graph:
      nodes:
        - node_id: "validate_order"
          node_type: COMPUTE_GENERIC
          description: "Validate order data"
        - node_id: "compute_state"
          node_type: REDUCER_GENERIC
          depends_on: ["validate_order"]
          description: "FSM state transition"
        - node_id: "process_payment"
          node_type: EFFECT_GENERIC
          depends_on: ["compute_state"]
          description: "Process payment"
        - node_id: "start_fulfillment"
          node_type: EFFECT_GENERIC
          depends_on: ["process_payment"]
          description: "Start fulfillment"
    coordination_rules:
      execution_mode: sequential
      failure_recovery_strategy: retry
      max_retries: 3

handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - event_model:
        name: "ModelOrderPlacedEvent"
        module: "myapp.models.events"
      handler:
        name: "HandlerOrderPlaced"
        module: "myapp.handlers"

published_events:
  - topic: "{env}.{namespace}.orders.evt.order-validated.v1"
    event_type: "OrderValidated"
  - topic: "{env}.{namespace}.orders.evt.order-completed.v1"
    event_type: "OrderCompleted"

intent_consumption:
  intent_routing_table:
    "payment.process": "node_payment_gateway_effect"
    "fulfillment.start": "node_fulfillment_effect"
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeOrderWorkflowOrchestrator(NodeOrchestrator):
    """Order workflow orchestrator. All routing defined in contract.yaml."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.reducer.model_intent import ModelIntent


class HandlerOrderPlaced:
    """Handle incoming order-placed event.

    Orchestrator handlers emit events and intents.
    They never return results.
    """

    async def handle(
        self,
        event: ModelEventEnvelope[object],
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        order_id = event.payload.get("order_id")  # type: ignore[union-attr]

        validated_event = ModelEventEnvelope(
            event_type="order.validated",
            payload={"order_id": order_id, "status": "validated"},
            correlation_id=correlation_id,
        )

        payment_intent = ModelIntent(
            intent_type="payment.process",
            target="node_payment_gateway_effect",
            payload={"order_id": order_id},
            priority=1,
        )

        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="orchestrator.order.workflow",
            events=(validated_event,),
            intents=(payment_intent,),
        )
```

### Pattern 8: Event Fan-Out

Orchestrate parallel processing by routing a single event to multiple handlers.

**contract.yaml**:

```yaml
contract_version:
  major: 1
  minor: 0
  patch: 0
name: "node_event_fanout_orchestrator"
node_type: "ORCHESTRATOR_GENERIC"
description: "Routes events to multiple downstream handlers in parallel."

handler_routing:
  routing_strategy: "payload_type_match"
  handlers:
    - event_model:
        name: "ModelUserCreatedEvent"
        module: "myapp.models.events"
      handler:
        name: "HandlerUserCreatedFanout"
        module: "myapp.handlers"

published_events:
  - topic: "{env}.notifications.user-welcome.v1"
    event_type: "UserWelcome"
  - topic: "{env}.analytics.user-registered.v1"
    event_type: "UserRegistered"
  - topic: "{env}.provisioning.user-setup.v1"
    event_type: "UserSetup"
```

**node.py**:

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from omnibase_core.nodes import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeEventFanoutOrchestrator(NodeOrchestrator):
    """Fan-out orchestrator. Routing declared in contract."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
```

**handler.py**:

```python
from __future__ import annotations

from uuid import UUID

from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.reducer.model_intent import ModelIntent


class HandlerUserCreatedFanout:
    """Fan out user-created event to notification, analytics, and provisioning."""

    async def handle(
        self,
        event: ModelEventEnvelope[object],
        input_envelope_id: UUID,
        correlation_id: UUID,
    ) -> ModelHandlerOutput[None]:
        user_id = event.payload.get("user_id")  # type: ignore[union-attr]

        welcome_intent = ModelIntent(
            intent_type="notification.send_welcome",
            target="node_notification_effect",
            payload={"user_id": user_id, "channel": "email"},
            priority=2,
        )

        analytics_intent = ModelIntent(
            intent_type="analytics.track_registration",
            target="node_analytics_effect",
            payload={"user_id": user_id},
            priority=3,
        )

        provisioning_intent = ModelIntent(
            intent_type="provisioning.setup_defaults",
            target="node_provisioning_effect",
            payload={"user_id": user_id},
            priority=2,
        )

        return ModelHandlerOutput.for_orchestrator(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id="orchestrator.user.fanout",
            intents=(welcome_intent, analytics_intent, provisioning_intent),
        )
```

---

## Testing Patterns

### Pattern 9: Testing a COMPUTE Handler

Test the handler directly. No container, no node, no I/O.

```python
import pytest
from uuid import uuid4


@pytest.mark.unit
class TestHandlerSchemaValidator:
    def test_valid_data_passes(self) -> None:
        handler = HandlerSchemaValidator()
        request = ModelValidationRequest(
            data={"user_id": "u123", "email": "test@example.com"},
            rules=[
                {"type": "field_presence", "field": "user_id"},
                {"type": "field_presence", "field": "email"},
            ],
        )

        output = handler.validate(
            request,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
        )

        assert output.result is not None
        assert output.result.is_valid is True
        assert output.result.errors == []

    def test_missing_field_fails(self) -> None:
        handler = HandlerSchemaValidator()
        request = ModelValidationRequest(
            data={"user_id": "u123"},
            rules=[{"type": "field_presence", "field": "email"}],
        )

        output = handler.validate(
            request,
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
        )

        assert output.result is not None
        assert output.result.is_valid is False
        assert len(output.result.errors) == 1
```

### Pattern 10: Testing a REDUCER Handler

Test the pure reduction function. Verify state transitions and intent emission.

```python
import pytest
from uuid import uuid4


@pytest.mark.unit
class TestHandlerOrderReducer:
    def test_order_placed_transitions_to_pending(self) -> None:
        handler = HandlerOrderReducer()
        state = ModelOrderState()
        event_id = uuid4()

        new_state, intents = handler.reduce(
            state=state,
            trigger="order_placed",
            event_id=event_id,
            payload={"order_id": "ORD-001"},
        )

        assert new_state.status == "pending"
        assert new_state.order_id == "ORD-001"
        assert new_state.last_processed_event_id == event_id
        assert len(intents) == 1
        assert intents[0].intent_type == "payment.process"

    def test_duplicate_event_is_idempotent(self) -> None:
        handler = HandlerOrderReducer()
        event_id = uuid4()
        state = ModelOrderState(
            status="pending",
            order_id="ORD-001",
            last_processed_event_id=event_id,
        )

        new_state, intents = handler.reduce(
            state=state,
            trigger="payment_confirmed",
            event_id=event_id,  # Same event ID
            payload={},
        )

        # No transition, no intents -- idempotent
        assert new_state.status == "pending"
        assert intents == ()

    def test_error_from_any_state(self) -> None:
        handler = HandlerOrderReducer()
        state = ModelOrderState(status="confirmed", order_id="ORD-001")

        new_state, intents = handler.reduce(
            state=state,
            trigger="error_received",
            event_id=uuid4(),
            payload={"reason": "payment_declined"},
        )

        assert new_state.status == "failed"
        assert intents == ()
```

---

## Summary

| Pattern | Node Kind | Key Principle |
|---------|-----------|---------------|
| Data Validation | COMPUTE | Pure function, returns result |
| Data Transformation | COMPUTE | Deterministic, no I/O |
| Database Storage | EFFECT | I/O in handler, emits events |
| API with Circuit Breaker | EFFECT | Contract-driven error handling |
| Order State Machine | REDUCER | Immutable state, intent emission |
| Metrics Aggregation | REDUCER | Pure fold, `with_*` methods |
| Order Workflow | ORCHESTRATOR | Events + intents, no result |
| Event Fan-Out | ORCHESTRATOR | Routes to multiple effects |
| COMPUTE Test | Testing | Test handler directly, no container |
| REDUCER Test | Testing | Verify state + intents |

---

## Related Documentation

- [Node Archetypes Reference](../../reference/node-archetypes.md)
- [Handler Contract Guide](../../contracts/HANDLER_CONTRACT_GUIDE.md)
- [REDUCER Node Tutorial](05_REDUCER_NODE_TUTORIAL.md)
- [Anti-Patterns](../../patterns/ANTI_PATTERNS.md)
- [Error Handling Best Practices](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md)

---

## Document Metadata

- **Version**: 2.0.0
- **Last Updated**: 2026-02-14
- **Maintainer**: ONEX Core Team
- **Status**: Complete
