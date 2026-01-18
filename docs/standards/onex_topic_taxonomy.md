> **Navigation**: [Home](../index.md) > Standards > Topic Taxonomy

# ONEX Kafka Topic Naming Standard

**Purpose**: Define the canonical Kafka topic naming convention for all ONEX domains
**Audience**: Developers, architects, infrastructure engineers
**Status**: Normative (ONEX v0.4.0+)
**Last Updated**: 2025-12-19

---

## Table of Contents

1. [Overview](#overview)
2. [Topic Structure](#topic-structure)
3. [Topic Types](#topic-types)
4. [Domain Registry](#domain-registry)
5. [Default Configurations](#default-configurations)
6. [Partition Key Requirements](#partition-key-requirements)
7. [Examples](#examples)
8. [Migration Guide](#migration-guide)
9. [Validation Rules](#validation-rules)

---

## Overview

ONEX uses a structured Kafka topic naming convention to ensure consistency, discoverability, and proper configuration across all domains. This standard replaces ad-hoc topic naming patterns and provides a unified taxonomy.

### Design Principles

1. **Domain Isolation**: Each domain has dedicated topics for separation of concerns
2. **Type Semantics**: Topic types (`commands`, `events`, `intents`, `snapshots`) convey message semantics
3. **Consistent Configuration**: Default retention and compaction policies per topic type
4. **Partition Alignment**: Entity-based partitioning for ordering guarantees

### Topic Format

```text
onex.<domain>.<type>
```

**Components:**

| Component | Description | Example |
|-----------|-------------|---------|
| `onex.` | Required prefix (lowercase) | Always `onex.` |
| `<domain>` | Business/functional domain | `registration`, `discovery`, `runtime` |
| `<type>` | Topic type (semantics) | `commands`, `events`, `intents`, `snapshots` |

---

## Topic Structure

### Canonical Format

```text
onex.<domain>.<type>
```

All ONEX Kafka topics **MUST** follow this three-part structure:

```python
# Pattern definition
TOPIC_PATTERN = r"^onex\.[a-z][a-z0-9-]*[a-z0-9]\.(commands|events|intents|snapshots)$|^onex\.[a-z]\.(commands|events|intents|snapshots)$"

# Valid examples
"onex.registration.commands"
"onex.registration.events"
"onex.discovery.intents"
"onex.runtime.snapshots"

# Invalid examples
"registration.events"           # Missing onex. prefix
"onex.registration"             # Missing type suffix
"onex.Registration.events"      # Uppercase not allowed
"onex.registration.logs"        # Invalid type
```

### Naming Rules

1. **Prefix**: Always `onex.` (lowercase)
2. **Domain**: Lowercase alphanumeric with optional hyphens (no underscores, cannot end with hyphen)
3. **Type**: One of: `commands`, `events`, `intents`, `snapshots`
4. **Separator**: Single dot (`.`) between components
5. **Case**: All lowercase

---

## Topic Types

### commands

**Purpose**: Write requests and command messages

**Semantics**:
- Commands represent requests to perform actions
- Commands are imperative ("RegisterNode", "ShutdownNode")
- Commands may be rejected or fail
- Consumers process commands and emit events

**Configuration Defaults**:
```yaml
cleanup.policy: delete
retention.ms: 604800000       # 7 days
retention.bytes: -1           # Unlimited
```

**Example Messages**:
```json
{
  "command_type": "REGISTER_NODE",
  "entity_id": "node-123",
  "payload": {
    "node_type": "COMPUTE",
    "capabilities": ["transform", "aggregate"]
  }
}
```

### events

**Purpose**: Immutable event logs (domain events, facts)

**Semantics**:
- Events represent things that happened (past tense)
- Events are immutable and append-only
- Events are the source of truth for domain state
- Multiple consumers can replay events independently

**Configuration Defaults**:
```yaml
cleanup.policy: delete
retention.ms: 2592000000      # 30 days
retention.bytes: -1           # Unlimited
```

**Example Messages**:
```json
{
  "event_type": "NODE_REGISTERED",
  "entity_id": "node-123",
  "occurred_at": "2025-12-19T10:30:00Z",
  "payload": {
    "node_id": "node-123",
    "node_type": "COMPUTE",
    "registration_timestamp": "2025-12-19T10:30:00Z"
  }
}
```

### intents

**Purpose**: Coordination messages between nodes (side-effect declarations)

**Semantics**:
- Intents declare what should happen (not imperative commands)
- Used by REDUCER nodes to emit side effects without executing them
- Intent executors (EFFECT nodes) consume and execute intents
- Supports the Pure FSM pattern (ONEX v2.0+)

**Configuration Defaults**:
```yaml
cleanup.policy: delete
retention.ms: 86400000        # 1 day (short-lived coordination)
retention.bytes: -1           # Unlimited
```

**Example Messages**:
```json
{
  "intent_type": "PUBLISH_EVENT",
  "entity_id": "node-123",
  "target_topic": "onex.registration.events",
  "payload": {
    "event_type": "NODE_HEALTH_UPDATED",
    "data": {"status": "healthy"}
  }
}
```

### snapshots

**Purpose**: State snapshots for recovery and caching (optional)

**Semantics**:
- Snapshots represent point-in-time state captures
- Used for faster recovery (avoid full event replay)
- Compacted by entity_id (latest snapshot wins)
- Optional per domain (not all domains need snapshots)

**Configuration Defaults**:
```yaml
cleanup.policy: compact,delete
retention.ms: 604800000       # 7 days
retention.bytes: -1           # Unlimited
min.compaction.lag.ms: 3600000  # 1 hour before compaction eligible
```

**Example Messages**:
```json
{
  "snapshot_type": "NODE_STATE",
  "entity_id": "node-123",
  "version": 42,
  "captured_at": "2025-12-19T10:30:00Z",
  "state": {
    "node_id": "node-123",
    "status": "ACTIVE",
    "last_heartbeat": "2025-12-19T10:29:55Z"
  }
}
```

---

## Domain Registry

### Core Domains

| Domain | Purpose | Topics |
|--------|---------|--------|
| `registration` | Node registration and lifecycle | All 4 types |
| `discovery` | Node discovery protocol | `commands`, `events`, `intents` |
| `runtime` | Runtime orchestration | All 4 types |
| `metrics` | Metrics collection | `events`, `snapshots` |
| `audit` | Audit logging | `events` only |
| `health` | Health monitoring | `events`, `intents` |
| `workflow` | Workflow execution | All 4 types |

### Registering New Domains

New domains **MUST**:

1. Be registered in the domain registry (this document or a machine-readable registry)
2. Use lowercase alphanumeric names with optional hyphens
3. Document which topic types are used
4. Follow the standard topic naming pattern

**Naming Guidelines for New Domains**:
- Use singular nouns when possible (`registration`, not `registrations`)
- Prefer short, descriptive names
- Avoid abbreviations unless widely understood (`dlq` is acceptable)

### Reserved Domains

These domain prefixes are reserved for ONEX infrastructure:

| Domain | Purpose |
|--------|---------|
| `dlq` | Dead letter queues |
| `internal` | Internal system topics |
| `test` | Test/development topics |
| `debug` | Debug/diagnostic topics |

---

## Default Configurations

### Configuration Matrix

| Topic Type | cleanup.policy | retention.ms | Compaction | Use Case |
|------------|----------------|--------------|------------|----------|
| `commands` | `delete` | 7 days (604800000) | No | Write requests |
| `events` | `delete` | 30 days (2592000000) | No | Immutable logs |
| `intents` | `delete` | 1 day (86400000) | No | Coordination |
| `snapshots` | `compact,delete` | 7 days (604800000) | Yes | State recovery |

### Environment Overrides

Retention and configuration can be overridden per environment:

```yaml
# Production (longer retention)
events:
  retention.ms: 7776000000    # 90 days

# Development (shorter retention)
events:
  retention.ms: 86400000      # 1 day
```

### Topic Creation Template

```bash
# Commands topic
kafka-topics.sh --create \
  --topic onex.registration.commands \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=delete \
  --config retention.ms=604800000

# Events topic
kafka-topics.sh --create \
  --topic onex.registration.events \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=delete \
  --config retention.ms=2592000000

# Intents topic
kafka-topics.sh --create \
  --topic onex.registration.intents \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=delete \
  --config retention.ms=86400000

# Snapshots topic (with compaction)
kafka-topics.sh --create \
  --topic onex.registration.snapshots \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=compact,delete \
  --config retention.ms=604800000 \
  --config min.compaction.lag.ms=3600000
```

---

## Partition Key Requirements

### Mandatory: entity_id as Partition Key

All messages **MUST** use `envelope.entity_id` as the partition key to ensure:

1. **Ordering Guarantees**: All messages for an entity go to the same partition
2. **Consumer Locality**: Entity state can be processed by a single consumer
3. **Compaction Correctness**: Snapshots compact correctly by entity

### Implementation

```python
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

# When publishing to Kafka
envelope = ModelEventEnvelope(
    event_type="NODE_REGISTERED",
    entity_id=node_id,  # This becomes the partition key
    payload={"node_type": "COMPUTE"},
    correlation_id=correlation_id,
)

# Kafka producer configuration
producer.send(
    topic="onex.registration.events",
    key=str(envelope.entity_id).encode("utf-8"),  # Partition key
    value=envelope.model_dump_json().encode("utf-8"),
)
```

### Key Format

- **Format**: UUID as string (lowercase, hyphenated)
- **Example**: `"550e8400-e29b-41d4-a716-446655440000"`
- **Encoding**: UTF-8

### Null Keys

Messages without an `entity_id` (e.g., broadcast messages) use round-robin partitioning. This is acceptable only for:

- System-wide announcements
- Discovery broadcasts
- Health check pings

---

## Examples

### Registration Domain

Complete topic set for the registration domain:

```text
onex.registration.commands   # Node registration commands
onex.registration.events     # Node lifecycle events
onex.registration.intents    # Side-effect coordination
onex.registration.snapshots  # Node state snapshots
```

**Message Flow Example**:

```text
1. Client sends REGISTER_NODE command
   → onex.registration.commands

2. RegistrationReducer processes command, emits intent
   → onex.registration.intents (PUBLISH_EVENT intent)

3. IntentExecutor publishes event
   → onex.registration.events (NODE_REGISTERED event)

4. SnapshotReducer captures state
   → onex.registration.snapshots (NODE_STATE snapshot)
```

### Discovery Domain

```text
onex.discovery.commands      # Discovery requests
onex.discovery.events        # Discovery responses and announcements
onex.discovery.intents       # Discovery coordination
```

### Runtime Domain

```text
onex.runtime.commands        # Runtime control commands
onex.runtime.events          # Runtime lifecycle events
onex.runtime.intents         # Runtime coordination
onex.runtime.snapshots       # Runtime state snapshots
```

### Metrics Domain

```text
onex.metrics.events          # Metrics collection events
onex.metrics.snapshots       # Aggregated metrics snapshots
```

---

## Migration Guide

### Existing Ad-Hoc Topics

The following legacy topic patterns require migration to the new taxonomy:

| Legacy Topic | New Topic | Notes |
|--------------|-----------|-------|
| `onex.discovery.broadcast` | `onex.discovery.commands` | Discovery requests |
| `onex.discovery.response` | `onex.discovery.events` | Discovery responses |
| `onex.runtime.ready` | `onex.runtime.events` | Runtime lifecycle event |
| `onex.runtime.node.registered` | `onex.registration.events` | Move to registration domain |
| `dev.omninode.metrics.v1` | `onex.metrics.events` | Standardize prefix |
| `dev.omninode.tasks.v1` | `onex.workflow.commands` | Standardize prefix |

### Migration Strategy

1. **Phase 1: Dual-Write**
   - Publish to both legacy and new topics
   - Consumers continue reading from legacy topics

2. **Phase 2: Consumer Migration**
   - Migrate consumers to new topics
   - Verify message delivery and ordering

3. **Phase 3: Producer Migration**
   - Stop publishing to legacy topics
   - Monitor for any remaining consumers

4. **Phase 4: Cleanup**
   - Delete legacy topics after retention period
   - Update documentation and configuration

### Code Migration Example

```python
# Before (legacy)
DISCOVERY_BROADCAST_TOPIC = "onex.discovery.broadcast"
DISCOVERY_RESPONSE_TOPIC = "onex.discovery.response"

# After (standardized)
DISCOVERY_COMMANDS_TOPIC = "onex.discovery.commands"
DISCOVERY_EVENTS_TOPIC = "onex.discovery.events"
DISCOVERY_INTENTS_TOPIC = "onex.discovery.intents"
```

### Compatibility Layer

For gradual migration, use a topic resolver:

```python
from typing import Literal

TopicType = Literal["commands", "events", "intents", "snapshots"]

def get_topic(domain: str, topic_type: TopicType) -> str:
    """Get standardized topic name for domain and type."""
    return f"onex.{domain}.{topic_type}"

# Usage
topic = get_topic("registration", "events")  # "onex.registration.events"
```

---

## Validation Rules

### Topic Name Validation

```python
import re

VALID_TOPIC_PATTERN = re.compile(
    r"^onex\.[a-z][a-z0-9-]*[a-z0-9]\.(commands|events|intents|snapshots)$"
    r"|^onex\.[a-z]\.(commands|events|intents|snapshots)$"
)

def validate_topic_name(topic: str) -> bool:
    """Validate topic name against ONEX standard."""
    return bool(VALID_TOPIC_PATTERN.match(topic))

# Valid
assert validate_topic_name("onex.registration.events")
assert validate_topic_name("onex.my-domain.commands")
assert validate_topic_name("onex.my-service.intents")

# Invalid
assert not validate_topic_name("registration.events")      # Missing prefix
assert not validate_topic_name("onex.Registration.events") # Uppercase
assert not validate_topic_name("onex.registration.logs")   # Invalid type
```

### Pre-Commit Validation

Add topic validation to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-kafka-topics
      name: Validate Kafka topic names
      entry: python scripts/validation/validate_kafka_topics.py
      language: python
      files: \.(py|yaml|yml)$
```

### CI Validation

Topic names should be validated in CI:

```bash
# Check for non-standard topic patterns
grep -rn "topic.*=" src/ | grep -v "onex\.[a-z]" | grep -v "test"
```

---

## Related Documentation

- **Naming Conventions**: `docs/conventions/NAMING_CONVENTIONS.md`
- **Event-Driven Architecture**: `docs/patterns/EVENT_DRIVEN_ARCHITECTURE.md`
- **ModelEventEnvelope**: `src/omnibase_core/models/events/model_event_envelope.py`
- **Intent Publisher**: `docs/guides/INTENT_PUBLISHER_TESTING_DOCUMENTATION.md`

---

## Summary

| Aspect | Standard |
|--------|----------|
| **Format** | `onex.<domain>.<type>` |
| **Types** | `commands`, `events`, `intents`, `snapshots` |
| **Partition Key** | `envelope.entity_id` (UUID string) |
| **Events Retention** | 30 days (delete policy) |
| **Snapshots Policy** | compact,delete (7 days) |
| **Case** | All lowercase |

---

**Version**: 1.0.0
**Last Updated**: 2025-12-19
**Maintained By**: ONEX Architecture Team
