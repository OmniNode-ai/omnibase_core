# Dependency Inversion in ONEX Architecture

> **Version**: 0.4.0
> **Last Updated**: 2025-12-10
> **Status**: Production
> **Related Ticket**: OMN-220

## Overview

The ONEX framework enforces strict **dependency inversion** to maintain clean architectural boundaries between abstraction layers and concrete implementations. This principle ensures that `omnibase_core` remains a pure abstraction layer without direct dependencies on transport or infrastructure libraries.

## Architecture Principle

### Layer Separation

```
+--------------------------------------------------+
|                  SERVICE LAYER                    |
|    (Applications, APIs, Workers)                 |
|    - Consumes protocols from omnibase_core       |
|    - Uses implementations from omnibase_spi      |
+--------------------------------------------------+
                        |
                        v
+--------------------------------------------------+
|               omnibase_spi                        |
|    (Service Provider Interface)                  |
|    - Concrete implementations of protocols       |
|    - Transport library integrations              |
|    - Infrastructure adapters                     |
+--------------------------------------------------+
                        |
                        v
+--------------------------------------------------+
|               omnibase_core                       |
|    (Core Abstractions)                           |
|    - Protocol definitions (interfaces)           |
|    - Domain models and contracts                 |
|    - Base node implementations                   |
|    - NO transport/infrastructure dependencies    |
+--------------------------------------------------+
```

### Dependency Direction

- **omnibase_core**: Provides protocol abstractions (interfaces only)
- **omnibase_spi**: Provides concrete implementations using transport libraries
- **Services**: Depend on `omnibase_core` protocols, use `omnibase_spi` implementations

This ensures that:
1. Core logic is testable without infrastructure dependencies
2. Transport libraries can be swapped without changing business logic
3. The framework remains decoupled from specific vendors or technologies

## Transport Library Restrictions

The following transport and infrastructure libraries are **FORBIDDEN** in `omnibase_core`:

### Message Queue Clients

| Library | Use Instead |
|---------|-------------|
| `kafka` | `ProtocolEventBus` |
| `aiokafka` | `ProtocolEventBus` |

### HTTP Clients

| Library | Use Instead |
|---------|-------------|
| `httpx` | `ProtocolHttpClient` |
| `aiohttp` | `ProtocolHttpClient` |
| `requests` | `ProtocolHttpClient` |

### Database Clients

| Library | Use Instead |
|---------|-------------|
| `asyncpg` | `ProtocolRepository` |
| `psycopg` | `ProtocolRepository` |
| `psycopg2` | `ProtocolRepository` |

### Secret Store Clients

| Library | Use Instead |
|---------|-------------|
| `hvac` | `ProtocolSecretStore` |

### Service Discovery Clients

| Library | Use Instead |
|---------|-------------|
| `consul` | `ProtocolServiceDiscovery` |

### Cache/Queue Clients

| Library | Use Instead |
|---------|-------------|
| `redis` | `ProtocolCache` |
| `valkey` | `ProtocolCache` |

## Why This Matters

### 1. Testability

Without direct transport dependencies, `omnibase_core` components can be tested in isolation using mock implementations:

```python
# In tests - use mock implementations
class MockEventBus:
    def __init__(self):
        self.published_events = []

    async def publish(self, event: ModelEventEnvelope) -> None:
        self.published_events.append(event)

# Test node without Kafka dependency
container = ModelONEXContainer()
container.register_service("ProtocolEventBus", MockEventBus())

node = MyComputeNode(container)
result = await node.process(input_data)
```

### 2. Flexibility

Transport libraries can be swapped without modifying business logic:

```python
# Development: Use in-memory implementation
container.register_service("ProtocolEventBus", InMemoryEventBus())

# Production: Use Kafka implementation (from omnibase_spi)
container.register_service("ProtocolEventBus", KafkaEventBus(config))

# Same node code works with both
node = MyComputeNode(container)
```

### 3. Layer Separation

Clear boundaries between abstraction and implementation:

```python
# omnibase_core - Pure protocol definition
class ProtocolEventBus(Protocol):
    async def publish(self, event: ModelEventEnvelope) -> None: ...
    async def subscribe(self, topic: str, handler: Callable) -> None: ...

# omnibase_spi - Concrete implementation
class KafkaEventBus:
    """Kafka implementation of ProtocolEventBus."""

    def __init__(self, bootstrap_servers: list[str]):
        self._producer = AIOKafkaProducer(...)  # Kafka dependency here

    async def publish(self, event: ModelEventEnvelope) -> None:
        await self._producer.send(...)
```

### 4. Vendor Independence

The framework is not locked to specific vendors:

- Kafka can be replaced with RabbitMQ, AWS SQS, or GCP Pub/Sub
- PostgreSQL can be replaced with MySQL, MongoDB, or DynamoDB
- HashiCorp Vault can be replaced with AWS Secrets Manager
- Redis can be replaced with Memcached or DynamoDB

## Allowed Patterns

While transport libraries are forbidden in runtime code, the following patterns are acceptable:

### Type Checking Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type-only imports are allowed for documentation purposes
    from aiokafka import AIOKafkaProducer
```

### Protocol Definitions

```python
# Protocols that abstract transports are encouraged
class ProtocolMessageBroker(Protocol):
    """Abstract interface for message brokers."""

    async def send(self, topic: str, message: bytes) -> None: ...
    async def receive(self, topic: str) -> bytes: ...
```

### Test Mocks and Fixtures

```python
# In tests/ directory - transport mocks are allowed
class FakeKafkaProducer:
    """Test double for Kafka producer."""

    async def send(self, topic: str, value: bytes) -> None:
        pass
```

## Enforcement

### Automated Validation

The `scripts/check_transport_imports.py` script validates these constraints:

```bash
# Check all files
poetry run python scripts/check_transport_imports.py

# Check with verbose output
poetry run python scripts/check_transport_imports.py --verbose

# Check specific file
poetry run python scripts/check_transport_imports.py --file src/omnibase_core/some_file.py

# Output as JSON (for CI integration)
poetry run python scripts/check_transport_imports.py --json

# Check only changed files (faster CI)
poetry run python scripts/check_transport_imports.py --changed-files
```

### CI Integration

Transport import validation runs automatically in CI:

1. **PR Checks**: All changed files are scanned for violations
2. **Full Validation**: Periodic full codebase scans
3. **Blocking**: PRs with violations cannot be merged

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations found |
| 1 | Transport import violations detected (blocks PR) |
| 2 | Script error (invalid arguments, file not found) |

## Migration Guide

### Moving Transport Code to omnibase_spi

If you have code that directly imports transport libraries:

1. **Identify the protocol** that abstracts the transport
2. **Move the implementation** to `omnibase_spi`
3. **Update the consumer** to depend on the protocol
4. **Register the implementation** in the service container

**Before** (in omnibase_core):

```python
# BAD: Direct transport import in omnibase_core
from aiokafka import AIOKafkaProducer

class MyService:
    def __init__(self):
        self.producer = AIOKafkaProducer(...)
```

**After** (protocol in omnibase_core, implementation in omnibase_spi):

```python
# GOOD: Protocol-based dependency
# In omnibase_core/my_service.py
class MyService:
    def __init__(self, container: ModelONEXContainer):
        self.event_bus = container.get_service("ProtocolEventBus")

# Implementation lives in omnibase_spi
```

### Temporary Allowlist

Pre-existing violations may be temporarily allowlisted while being addressed:

```python
# In scripts/check_transport_imports.py
TEMPORARY_ALLOWLIST: frozenset[str] = frozenset({
    "mixins/mixin_health_check.py",  # TODO: Refactor to use ProtocolHttpClient
})
```

Allowlisted files:
- Are tracked for future remediation
- Have expiration dates for review
- Should be addressed systematically

## Related Documentation

- [Protocol Architecture](./PROTOCOL_ARCHITECTURE.md) - Complete protocol inventory and patterns
- [Dependency Injection](./DEPENDENCY_INJECTION.md) - Container-based DI patterns
- [ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md) - Node type responsibilities
- [Container Types](./CONTAINER_TYPES.md) - ModelONEXContainer vs ModelContainer

## References

- [SOLID Principles - Dependency Inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Clean Architecture - Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [PEP 544 - Structural Subtyping (Protocols)](https://peps.python.org/pep-0544/)

---

**Document Version**: 1.0
**Created**: 2025-12-10
**Maintainer**: ONEX Core Team
