# ADR-005: Core-Infra Dependency Boundary

## Document Metadata

| Field | Value |
|-------|-------|
| **Document Type** | Architecture Decision Record (ADR) |
| **Document Number** | ADR-005 |
| **Status** | 🟢 **IMPLEMENTED** |
| **Created** | 2025-12-26 |
| **Last Updated** | 2025-12-26 |
| **Author** | ONEX Framework Team |
| **Related Issue** | [OMN-1015](https://linear.app/omninode/issue/OMN-1015) |
| **Implementation Commit** | `f3c370b6` - Remove aiohttp direct dependency from omnibase_core |
| **Related ADR** | [ADR-001](./ADR-001-protocol-based-di-architecture.md) - Protocol-Based DI Architecture |

---

## Document Purpose

This Architecture Decision Record documents the architectural boundary between `omnibase_core` (abstractions) and `omnibase_infra` (implementations), specifically regarding external I/O dependencies such as HTTP clients, message brokers, and database drivers.

**Why this document exists**:
- To establish the invariant that `omnibase_core` must be free of direct I/O library dependencies
- To document the rationale for removing `aiohttp` from omnibase_core dependencies
- To provide guidance on preventing similar architectural violations
- To define the layering principle: Core -> SPI -> Infra

**When to reference this document**:
- When adding new dependencies to omnibase_core
- When implementing protocol-based services
- When reviewing PRs that modify core dependencies
- When designing new node implementations that require I/O

---

## Document Status and Maintenance

**Current Status**: IMPLEMENTED - aiohttp removed, validation scripts in place

**Maintenance Model**: This is a **policy document** establishing an architectural invariant. Updates should occur when:
- New categories of forbidden dependencies are identified
- Enforcement mechanisms are enhanced
- The layering model evolves

**Supersession**: This document is NOT superseded. The core purity principle is foundational to ONEX architecture.

---

## Target Audience

| Audience | Use Case |
|----------|----------|
| **Core Developers** | Understanding what dependencies are allowed in omnibase_core |
| **Node Developers** | Knowing where to place I/O implementations |
| **CI/CD Engineers** | Configuring enforcement in pipelines |
| **Code Reviewers** | Evaluating PRs that add or modify dependencies |
| **Architects** | Understanding the layering model |

---

## Executive Summary

`omnibase_core` is the foundational abstraction layer of the ONEX framework. It MUST contain only:
- Protocol definitions (interfaces)
- Domain models (Pydantic BaseModel subclasses)
- Pure computation logic (no side effects)
- Base node implementations (using injected services)

Direct dependencies on transport/I/O libraries (aiohttp, httpx, kafka, redis, asyncpg, etc.) are **FORBIDDEN** in omnibase_core. These libraries belong in `omnibase_infra`, which provides concrete implementations of core protocols.

**Decision**: Remove aiohttp and all similar transport libraries from omnibase_core, enforce via CI validation.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Background](#background)
3. [Decision](#decision)
4. [Implementation](#implementation)
5. [Enforcement](#enforcement)
6. [Trade-offs](#trade-offs)
7. [References](#references)

---

## Problem Statement

Prior to commit `f3c370b6`, `omnibase_core` included `aiohttp` as a direct dependency. This violated the architectural principle that:

> **Core provides abstractions; Infra provides implementations.**

Having aiohttp in core created several problems:

1. **Tight Coupling**: Core was coupled to a specific HTTP library
2. **Testability Reduction**: Tests required mocking aiohttp instead of using simple protocol mocks
3. **Dependency Bloat**: Core carried unnecessary transitive dependencies
4. **Architecture Violation**: Core should define `ProtocolHttpClient`, not depend on its implementation

**Question resolved**: Should omnibase_core contain any direct I/O library dependencies?

**Answer**: **No.** All I/O libraries belong in omnibase_infra.

---

## Background

### ONEX Layering Model

The ONEX framework uses a strict layered architecture:

```text
+--------------------------------------------------+
|                  SERVICE LAYER                    |
|    (Applications, APIs, Workers)                 |
|    - Consumes protocols from omnibase_core       |
|    - Uses implementations from omnibase_infra    |
+--------------------------------------------------+
                        |
                        v
+--------------------------------------------------+
|               omnibase_infra                      |
|    (Infrastructure Layer)                        |
|    - Concrete implementations of protocols       |
|    - Transport library integrations              |
|    - Infrastructure adapters (Kafka, Postgres)   |
+--------------------------------------------------+
                        |
                        v
+--------------------------------------------------+
|               omnibase_spi                        |
|    (Service Provider Interface)                  |
|    - May extend Core protocols                   |
|    - Cross-service contract definitions          |
|    - Depends on omnibase_core (NOT reverse)      |
+--------------------------------------------------+
                        |
                        v
+--------------------------------------------------+
|               omnibase_core                       |
|    (Core Abstractions - Source of Truth)         |
|    - Protocol definitions (interfaces)           |
|    - Domain models and contracts                 |
|    - Base node implementations                   |
|    - NO transport/infrastructure dependencies    |
+--------------------------------------------------+
```

### Dependency Direction

Dependencies flow **downward only**:
- Services -> Infra -> SPI -> Core
- Core has NO upward dependencies
- Core has NO sibling dependencies on transport libraries

### The aiohttp Violation

`aiohttp` was listed in `pyproject.toml` as a direct dependency of omnibase_core. While the library was not imported at module level in most files, its presence in dependencies violated the architectural boundary.

**Commit f3c370b6** removed this dependency and updated protocol documentation to clarify where implementations belong.

---

## Decision

### Core Principle

**omnibase_core MUST NOT have direct dependencies on transport/I/O libraries.**

### Forbidden Dependencies in Core

The following libraries are **FORBIDDEN** as direct dependencies in omnibase_core:

| Category | Forbidden Libraries | Protocol Alternative |
|----------|--------------------|--------------------|
| **HTTP Clients** | `aiohttp`, `httpx`, `requests` | `ProtocolHttpClient` |
| **Message Queues** | `kafka`, `aiokafka` | `ProtocolEventBus` |
| **Databases** | `asyncpg`, `psycopg`, `psycopg2` | `ProtocolRepository` |
| **Caches** | `redis`, `valkey` | `ProtocolCache` |
| **Secret Stores** | `hvac` | `ProtocolSecretStore` |
| **Service Discovery** | `consul` | `ProtocolServiceDiscovery` |

### Allowed Patterns

While runtime imports are forbidden, these patterns ARE allowed:

**1. TYPE_CHECKING imports (type hints only)**:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type-only imports are allowed for documentation purposes
    from aiohttp import ClientSession
```

**2. Protocol Definitions**:
```python
# Protocols that abstract transports are encouraged
from typing import Protocol, runtime_checkable

@runtime_checkable
class ProtocolHttpClient(Protocol):
    """Abstract interface for HTTP clients."""

    async def get(
        self,
        url: str,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> ProtocolHttpResponse:
        ...
```

**3. Documentation Examples (in docstrings)**:
```python
class ProtocolHttpClient(Protocol):
    """
    Example adapter implementation (in omnibase_infra):

        # NOTE: This belongs in omnibase_infra, NOT omnibase_core
        import aiohttp

        class AioHttpClientAdapter:
            def __init__(self, session: aiohttp.ClientSession):
                self._session = session
    """
```

### Correct vs Incorrect Patterns

**INCORRECT (in omnibase_core)**:
```python
# BAD: Direct transport import in omnibase_core
import aiohttp

class HealthCheckMixin:
    async def check_health(self, url: str) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status == 200
```

**CORRECT (in omnibase_core)**:
```python
# GOOD: Protocol-based dependency injection
from omnibase_core.protocols.http import ProtocolHttpClient

class HealthCheckMixin:
    def __init__(self, http_client: ProtocolHttpClient):
        self._http_client = http_client

    async def check_health(self, url: str) -> bool:
        response = await self._http_client.get(url, timeout=5.0)
        return response.status == 200
```

**CORRECT (in omnibase_infra)**:
```python
# GOOD: Concrete implementation in infra layer
import aiohttp
from omnibase_core.protocols.http import ProtocolHttpClient, ProtocolHttpResponse

class AioHttpClientAdapter:
    """Implements ProtocolHttpClient using aiohttp."""

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    async def get(
        self,
        url: str,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> ProtocolHttpResponse:
        client_timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None
        async with self._session.get(url, timeout=client_timeout, headers=headers) as resp:
            body = await resp.text()
            return AioHttpResponseAdapter(resp.status, body)
```

---

## Implementation

### Changes Made (Commit f3c370b6)

1. **Removed aiohttp from dependencies**:
   - Updated `pyproject.toml` to remove aiohttp
   - Updated `poetry.lock` to remove transitive dependencies

2. **Updated protocol documentation**:
   - Added architecture boundary notes to `ProtocolHttpClient`
   - Clarified that adapters belong in omnibase_infra
   - Added migration guide in docstrings

3. **Preserved documentation examples**:
   - aiohttp usage examples in docstrings are retained
   - These serve as implementation guidance for omnibase_infra

### Files Modified

- `pyproject.toml` - Removed aiohttp dependency
- `poetry.lock` - Regenerated without aiohttp
- `src/omnibase_core/protocols/http/__init__.py` - Updated exports
- `src/omnibase_core/protocols/http/protocol_http_client.py` - Added boundary documentation

---

## Enforcement

### Automated Validation Script

The `scripts/validate-no-transport-imports.sh` script enforces this policy:

```bash
# Run validation
./scripts/validate-no-transport-imports.sh

# Or via make/pre-commit hooks
make validate-transport-imports
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No violations found |
| 1 | Transport import violations detected (blocks PR) |

### CI Integration

The transport import check runs in CI as part of the test workflow:

```yaml
# .github/workflows/test.yml
- name: Check Transport Imports
  run: ./scripts/validate-no-transport-imports.sh
```

### Pre-commit Integration (Optional)

For local enforcement, add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-transport-imports
      name: Check Transport Imports
      entry: ./scripts/validate-no-transport-imports.sh
      language: system
      pass_filenames: false
      types: [python]
```

### Forbidden Imports Configuration

The script checks for these forbidden transport/I/O libraries:

```bash
# HTTP clients
aiohttp, httpx, requests, urllib3

# Kafka clients
kafka, aiokafka, confluent_kafka

# Redis clients
redis, aioredis

# Database clients
asyncpg, psycopg2, psycopg, aiomysql

# Message queues
pika, aio_pika, kombu, celery

# gRPC
grpc, grpcio

# WebSocket
websockets, wsproto
```

### Exclusions

The script excludes:
- Protocol definition files with documentation examples (e.g., `protocols/http/protocol_http_client.py`)
- Comments and TYPE_CHECKING blocks
- `__pycache__` and compiled files

---

## Trade-offs

### Accepted Trade-offs

1. **Indirection Overhead**
   - **Impact**: Code must go through protocols rather than direct library calls
   - **Rationale**: Indirection enables testing, swappability, and clean architecture
   - **Mitigation**: Container-based DI minimizes boilerplate

2. **Developer Learning Curve**
   - **Impact**: Developers must understand the protocol pattern
   - **Rationale**: This is standard clean architecture; investment pays off in maintainability
   - **Mitigation**: Comprehensive documentation and examples

3. **Split Implementation Locations**
   - **Impact**: Protocol in core, implementation in infra (two places to look)
   - **Rationale**: Clear separation of concerns
   - **Mitigation**: Consistent naming conventions and documentation

### Benefits Realized

1. **Testability**: Core components can be tested without I/O mocks
2. **Swappability**: HTTP library can change without core changes
3. **Reduced Dependencies**: Core has minimal dependency footprint
4. **Clear Architecture**: Unambiguous layer responsibilities
5. **Vendor Independence**: Not locked to specific transport libraries

---

## References

### Related Documentation

- **[ADR-001](./ADR-001-protocol-based-di-architecture.md)**: Protocol-Based DI Architecture
- **[DEPENDENCY_INVERSION.md](../DEPENDENCY_INVERSION.md)**: Detailed dependency inversion guide
- **[NODE_PURITY_GUARANTEES.md](../NODE_PURITY_GUARANTEES.md)**: Node purity constraints
- **[PROTOCOL_ARCHITECTURE.md](../PROTOCOL_ARCHITECTURE.md)**: Complete protocol inventory

### Related Code

- **Implementation Commit**: `f3c370b6` - Remove aiohttp direct dependency
- **Validation Script**: `scripts/validate-no-transport-imports.sh`
- **HTTP Protocol**: `src/omnibase_core/protocols/http/protocol_http_client.py`

### Related Issues

- **OMN-1015**: Fix aiohttp architecture violation in omnibase_core
- **OMN-220**: Transport import validation (original tracking issue)

### External References

- [SOLID Principles - Dependency Inversion](https://en.wikipedia.org/wiki/Dependency_inversion_principle)
- [Clean Architecture - Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [PEP 544 - Structural Subtyping (Protocols)](https://peps.python.org/pep-0544/)

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-26 | 1.0 | ONEX Framework Team | Initial ADR documenting core-infra boundary and aiohttp removal |

---

**Document Status**: IMPLEMENTED - All enforcement mechanisms in place
**Verification**: Validated against commit f3c370b6 and scripts/check_transport_imports.py
