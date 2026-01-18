> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Message Topic Mapping

# Message Category to Topic Mapping

## Overview

This document defines the canonical mapping between ONEX message categories and Kafka topic patterns. Proper topic segregation is critical for:

- **Routing correctness**: Messages reach the right consumers
- **Scaling independence**: Each message type can scale independently
- **Observability**: Clear debugging and monitoring by message type
- **Retention policies**: Different retention/replay policies per type
- **Security**: Fine-grained access control per topic type

---

## Message Categories

ONEX defines three primary message categories, each with distinct semantics:

| Category | Semantic | Tense | Multiplicity | Mutability |
|----------|----------|-------|--------------|------------|
| **EVENT** | Fact about what happened | Past | Multiple consumers | Immutable |
| **COMMAND** | Request for action | Imperative | Single handler | Can be rejected |
| **INTENT** | Declarative side effect | Present | Effect executor | Deferred execution |

### EVENT

Events represent **facts about what happened**. They are immutable records of state changes.

**Characteristics**:
- Past tense naming: `UserCreated`, `OrderCompleted`, `PaymentProcessed`
- Immutable once published
- Multiple consumers allowed (fan-out)
- Used for event sourcing, audit trails, notifications

**Example**:
```python
from omnibase_core.models.events import ModelEventEnvelope

# Events describe what happened
event = ModelEventEnvelope.create_broadcast(
    payload=UserCreatedEvent(user_id="123", email="user@example.com"),
    source_node_id=node_id,
)
# Publish to: dev.user-service.events.v1
```

### COMMAND

Commands represent **requests for action**. They can be accepted or rejected.

**Characteristics**:
- Imperative naming: `CreateUser`, `ProcessOrder`, `CancelPayment`
- Single handler expected (command bus pattern)
- Can be rejected with reason
- Used for triggering business operations

**Example**:
```python
from omnibase_core.models.events import ModelEventEnvelope

# Commands request action
command = ModelEventEnvelope.create_directed(
    payload=CreateUserCommand(email="new@example.com", name="New User"),
    source_node_id=orchestrator_id,
    target_node_id=user_service_id,
)
# Publish to: dev.user-service.commands.v1
```

### INTENT

Intents represent **declarative side effect descriptions** from pure Reducer FSMs.

**Characteristics**:
- Describes what should happen, not how
- Emitted by pure Reducers to maintain purity
- Executed by Effect nodes
- Used for maintaining Reducer purity (see ModelIntent architecture)

**Example**:
```python
from omnibase_core.models.reducer import ModelIntent

# Intent describes side effect declaratively
intent = ModelIntent(
    intent_type="log_metric",
    target="metrics_service",
    payload={"metric": "processing_time", "value": 123.45},
    priority=3,
)
# Publish to: dev.omninode-bridge.intents.event-publish.v1
```

---

## Topic Naming Convention

### Format

```
<environment>.<domain>.<category>s.<version>
```

| Component | Description | Examples |
|-----------|-------------|----------|
| `environment` | Deployment environment | `dev`, `staging`, `prod`, `test`, `local` |
| `domain` | Business domain/service | `user-service`, `payment`, `omninode-bridge` |
| `category` | Message category suffix | `events`, `commands`, `intents` |
| `version` | Schema version | `v1`, `v2` |

### Examples

| Message Category | Domain | Full Topic Name |
|-----------------|--------|-----------------|
| EVENT | user-service | `dev.user-service.events.v1` |
| COMMAND | order-management | `prod.order-management.commands.v1` |
| INTENT | omninode-bridge | `dev.omninode-bridge.intents.v1` |

---

## Category to Topic Mapping Rules

### Mapping Table

| Message Category | Topic Pattern | Example Topic |
|-----------------|---------------|---------------|
| **EVENT** | `<env>.<domain>.events.<version>` | `dev.user.events.v1` |
| **COMMAND** | `<env>.<domain>.commands.<version>` | `prod.order.commands.v1` |
| **INTENT** | `<env>.<domain>.intents.<version>` | `dev.payment.intents.v1` |

### Programmatic Usage

```python
from omnibase_core.enums import EnumMessageCategory
from omnibase_core.models.events import ModelTopicNaming

# Create topic naming for events
events_topic = ModelTopicNaming(
    environment="dev",
    domain="user-service",
    category=EnumMessageCategory.EVENT,
)
print(events_topic.topic_name)  # dev.user-service.events.v1

# Convenience factory methods
commands_topic = ModelTopicNaming.for_commands("order-service", environment="prod")
print(commands_topic.topic_name)  # prod.order-service.commands.v1

intents_topic = ModelTopicNaming.for_intents("payment")
print(intents_topic.topic_name)  # dev.payment.intents.v1
```

---

## Enforcement Rules

### Rule 1: Category-Topic Alignment

**Events MUST only be published to `.events` topics**:
```python
# CORRECT
await publish(topic="dev.user.events.v1", message=user_created_event)

# WRONG - Event to commands topic
await publish(topic="dev.user.commands.v1", message=user_created_event)  # VIOLATION
```

**Commands MUST only be published to `.commands` topics**:
```python
# CORRECT
await publish(topic="dev.order.commands.v1", message=create_order_command)

# WRONG - Command to events topic
await publish(topic="dev.order.events.v1", message=create_order_command)  # VIOLATION
```

**Intents MUST only be published to `.intents` topics**:
```python
# CORRECT
await publish(topic="dev.metrics.intents.v1", message=log_metric_intent)

# WRONG - Intent to events topic
await publish(topic="dev.metrics.events.v1", message=log_metric_intent)  # VIOLATION
```

### Rule 2: Consumer Type Alignment

**Event consumers can be multiple (fan-out)**:
```python
# Multiple services can consume the same event
user_created_topic = "dev.user.events.v1"
await notification_service.subscribe(user_created_topic)
await audit_service.subscribe(user_created_topic)
await analytics_service.subscribe(user_created_topic)
```

**Command consumers should be single (command bus)**:
```python
# Only one handler should process each command
create_user_topic = "dev.user.commands.v1"
await user_service.subscribe(create_user_topic)  # Single handler
```

**Intent consumers are Effect nodes**:
```python
# Effect nodes execute intents
intent_topic = "dev.omninode-bridge.intents.v1"
await effect_node.subscribe(intent_topic)  # Effect executor
```

### Rule 3: Validation at Publish Time

Use the validation helper to enforce category-topic alignment:

```python
from omnibase_core.models.events import validate_topic_matches_category
from omnibase_core.enums import EnumMessageCategory

# Validate before publishing
topic = "dev.user.events.v1"
if not validate_topic_matches_category(topic, EnumMessageCategory.EVENT):
    raise ValueError(f"Topic {topic} does not match expected category EVENT")
```

---

## Why This Matters

### 1. Prevents Cross-Contamination

Without topic segregation, a consumer expecting events might receive commands, leading to:
- Processing failures
- Data corruption
- Silent errors

### 2. Enables Independent Scaling

Each topic type can have different:
- Partition counts
- Consumer groups
- Processing throughput

```
Events topic: 32 partitions (high fan-out)
Commands topic: 8 partitions (single handler per partition)
Intents topic: 16 partitions (Effect node parallelism)
```

### 3. Simplifies Debugging

When issues occur, topic segregation enables:
- Quick identification of message type
- Targeted consumer group debugging
- Clear message flow tracing

### 4. Enables Different Policies

| Policy | Events | Commands | Intents |
|--------|--------|----------|---------|
| **Retention** | 7 days (audit) | 24 hours | 1 hour |
| **Compaction** | Disabled | Disabled | Enabled |
| **Replication** | 3 (durability) | 2 | 2 |

---

## Topic Category Detection

Use `EnumMessageCategory.from_topic()` to detect category from topic name:

```python
from omnibase_core.enums import EnumMessageCategory

# Detect category from topic
category = EnumMessageCategory.from_topic("dev.user.events.v1")
print(category)  # EnumMessageCategory.EVENT

category = EnumMessageCategory.from_topic("prod.order.commands.v1")
print(category)  # EnumMessageCategory.COMMAND

category = EnumMessageCategory.from_topic("dev.payment.intents.v1")
print(category)  # EnumMessageCategory.INTENT

# Invalid topic returns None
category = EnumMessageCategory.from_topic("invalid-topic")
print(category)  # None
```

---

## Integration with ONEX Architecture

### Effect Nodes and Intents

Effect nodes subscribe to intent topics and execute the described side effects:

```python
class NodeEffect(NodeCoreBase):
    async def start(self):
        intent_topic = ModelTopicNaming.for_intents(
            domain="omninode-bridge",
            environment=self.environment,
        )
        await self.subscribe(intent_topic.topic_name, self.handle_intent)

    async def handle_intent(self, message: ProtocolEventMessage):
        intent = ModelEventPublishIntent.model_validate_json(message.value)
        await self.execute_intent(intent)
```

### Reducer Purity and Intent Emission

Reducers emit intents to maintain purity (no direct I/O):

```python
class NodeReducer(NodeCoreBase):
    async def process(self, input_data) -> ModelReducerOutput:
        result = self._reduce(input_data)

        # Emit intent instead of direct logging
        intent = ModelIntent(
            intent_type="log_metric",
            target="metrics_service",
            payload={"metric": "items_processed", "value": len(input_data)},
        )

        return ModelReducerOutput(result=result, intents=[intent])
```

### Orchestrator and Command Dispatch

Orchestrators dispatch commands to coordinate workflows:

```python
class NodeOrchestrator(NodeCoreBase):
    async def start_workflow(self, workflow_id: UUID):
        command_topic = ModelTopicNaming.for_commands(
            domain="payment-service",
            environment=self.environment,
        )

        command = ProcessPaymentCommand(order_id=order_id, amount=amount)
        await self.publish(command_topic.topic_name, command)
```

---

## API Reference

### EnumMessageCategory

```python
from omnibase_core.enums import EnumMessageCategory

# Values
EnumMessageCategory.EVENT    # "event" - facts about what happened
EnumMessageCategory.COMMAND  # "command" - requests for action
EnumMessageCategory.INTENT   # "intent" - declarative side effects

# Properties
category.topic_suffix   # "events", "commands", or "intents"
category.description    # Human-readable description

# Class methods
EnumMessageCategory.from_topic(topic)  # Parse category from topic name
```

### ModelTopicNaming

```python
from omnibase_core.models.events import ModelTopicNaming
from omnibase_core.enums import EnumMessageCategory

# Full constructor
naming = ModelTopicNaming(
    environment="dev",
    domain="user-service",
    category=EnumMessageCategory.EVENT,
    version="v1",
)

# Factory methods
events = ModelTopicNaming.for_events("user-service", environment="prod")
commands = ModelTopicNaming.for_commands("order-service")
intents = ModelTopicNaming.for_intents("payment")

# Properties
naming.topic_name    # "dev.user-service.events.v1"
naming.topic_suffix  # "events"

# Parsing
parsed = ModelTopicNaming.parse_topic("dev.user.events.v1")
```

### Validation Helpers

```python
from omnibase_core.models.events import (
    validate_topic_matches_category,
    get_topic_category,
)
from omnibase_core.enums import EnumMessageCategory

# Validate topic matches expected category
is_valid = validate_topic_matches_category(
    topic="dev.user.events.v1",
    expected_category=EnumMessageCategory.EVENT,
)  # True

# Extract category from topic
category = get_topic_category("dev.order.commands.v1")
# EnumMessageCategory.COMMAND
```

---

## Related Documentation

- [ONEX Four-Node Architecture](ONEX_FOUR_NODE_ARCHITECTURE.md)
- [ModelIntent Architecture](MODEL_INTENT_ARCHITECTURE.md)
- [Event Envelope Model](../../src/omnibase_core/models/events/model_event_envelope.py)

---

**Last Updated**: 2025-12-19
**Ticket**: OMN-933
**Status**: Implemented
