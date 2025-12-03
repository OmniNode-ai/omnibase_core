# ONEX Architecture Evolution Overview

**Version**: 1.1.0
**Status**: Master Planning Document
**Created**: 2025-12-03
**Updated**: 2025-12-03
**Repository**: omnibase_core

> **Note (v1.1.0)**: This version includes architectural corrections to ensure handlers reside in `omnibase_infra`, NodeRuntime remains in `omnibase_core`, and the dependency flow is accurately represented.

---

## Executive Summary

This document provides a comprehensive overview of the ONEX architecture evolution from **mixin-based inheritance** to a **declarative runtime-host model**. It synthesizes four detailed planning documents into a single roadmap.

### The Vision

Transform ONEX nodes from "service objects composed from mixins" into:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BEFORE (Current)                            │
├─────────────────────────────────────────────────────────────────────┤
│  NodeVaultAdapterEffect(                                            │
│      NodeEffectService,                                             │
│      VaultClientMixin,                                              │
│      LoggingMixin,                                                  │
│      HealthMixin,                                                   │
│      MetricsMixin,                                                  │
│      RetryMixin,                                                    │
│      ...                                                            │
│  )                                                                  │
│  - Owns Vault client lifecycle                                      │
│  - Owns event loop                                                  │
│  - Owns health check endpoint                                       │
│  - 500+ lines of inherited code                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          AFTER (Target)                             │
├─────────────────────────────────────────────────────────────────────┤
│  vault_adapter/                                                     │
│  ├── contract.yaml          # Declarative contract                  │
│  ├── models.py              # Input/output models                   │
│  └── logic.py               # Pure domain logic (30-150 lines)      │
│                                                                     │
│  + NodeRuntime (core)        # Manages lifecycle, events, metrics   │
│  + VaultHandler (infra)      # Owns Vault client, retries, health   │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Lines per node | 500+ | 30-150 (80-95% reduction) |
| Inheritance depth | 5-8 levels | 0-1 levels |
| Test isolation | Hard | Easy |
| Runtime coupling | Tight | Loose |
| Deployment unit | Per-node process | Runtime host |

---

## Core Design Invariants

These invariants are non-negotiable and guide all architectural decisions:

1. **All behavior is contract-driven.**
2. **NodeRuntime is the only executable event loop.**
3. **Node logic is pure: no I/O, no mixins, no inheritance.**
4. **Core never depends on SPI or infra.**
5. **SPI only defines protocols, never implementations.**
6. **Infra owns all I/O and real system integrations.**

**Critical Invariant**: No code in `omnibase_core` may initiate network I/O, database I/O, file I/O, or external process execution.

---

## Table of Contents

1. [Document Map](#1-document-map)
2. [Architecture Overview](#2-architecture-overview)
3. [The Four Transformations](#3-the-four-transformations)
4. [Execution Order](#4-execution-order)
5. [Timeline Summary](#5-timeline-summary)
6. [Quick Reference](#6-quick-reference)

---

## 1. Document Map

### Planning Documents

| Document | Focus | Size | Read Time |
|----------|-------|------|-----------|
| [Dependency Refactoring Plan](./DEPENDENCY_REFACTORING_PLAN.md) | Fix Core/SPI inversion | 25 KB | 20 min |
| [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) | R/H/D mixin classification | 27 KB | 25 min |
| [Declarative Effect Nodes Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md) | Handler infrastructure | 110 KB | 45 min |
| [Minimal Runtime Phased Plan](./MINIMAL_RUNTIME_PHASED_PLAN.md) | Runtime host MVP | 13 KB | 15 min |

### Document Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY REFACTORING PLAN                      │
│                    (Fix Core/SPI Inversion)                         │
│                                                                     │
│  Problem: Core depends on SPI (27 files with SPI imports)           │
│  Solution: Core has ZERO dependencies; SPI depends on Core          │
│  Timeline: 4 weeks                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Prerequisite
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MIXIN MIGRATION PLAN                           │
│                    (R/H/D Classification)                           │
│                                                                     │
│  40 Mixins → 3 Destinations:                                        │
│  • Runtime (R): 22 mixins → NodeRuntime/NodeInstance                │
│  • Handler (H): 4 mixins → Handler implementations                  │
│  • Domain (D): 14 mixins → Pure libraries                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
┌───────────────────────────────┐ ┌───────────────────────────────────┐
│  DECLARATIVE EFFECT NODES     │ │    MINIMAL RUNTIME PHASED PLAN    │
│  IMPLEMENTATION PLAN          │ │                                   │
│                               │ │  Phase 0: Core types, topics      │
│  • Pydantic models (10)       │ │  Phase 1: NodeRuntime MVP         │
│  • Protocol handlers (4)      │ │  Phase 2: One real handler        │
│  • Resilience components (3)  │ │  Phase 3: Cloud data plane        │
│  • NodeEffect runtime         │ │  Phase 4: Multi-runtime scaling   │
│                               │ │                                   │
│  Timeline: 7 days             │ │  Timeline: 4-8 weeks              │
└───────────────────────────────┘ └───────────────────────────────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │     PRODUCTION SYSTEM       │
                    │                             │
                    │  • Declarative contracts    │
                    │  • Runtime-hosted nodes     │
                    │  • Handler-based I/O        │
                    │  • Zero mixin inheritance   │
                    └─────────────────────────────┘
```

---

## 2. Architecture Overview

### Current Architecture (Mixin-Based)

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Node Process                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    NodeVaultAdapterEffect                    │   │
│  │  ┌─────────────────────────────────────────────────────────┐│   │
│  │  │                   NodeEffectService                     ││   │
│  │  │  ┌─────────────────────────────────────────────────────┐││   │
│  │  │  │                 VaultClientMixin                    │││   │
│  │  │  │  ┌─────────────────────────────────────────────────┐│││   │
│  │  │  │  │               LoggingMixin                      ││││   │
│  │  │  │  │  ┌─────────────────────────────────────────────┐││││   │
│  │  │  │  │  │             HealthMixin                     │││││   │
│  │  │  │  │  │  ┌─────────────────────────────────────────┐│││││   │
│  │  │  │  │  │  │           MetricsMixin                  ││││││   │
│  │  │  │  │  │  │  ┌─────────────────────────────────────┐││││││   │
│  │  │  │  │  │  │  │         EventBusMixin               │││││││   │
│  │  │  │  │  │  │  └─────────────────────────────────────┘││││││   │
│  │  │  │  │  │  └─────────────────────────────────────────┘│││││   │
│  │  │  │  │  └─────────────────────────────────────────────┘││││   │
│  │  │  │  └─────────────────────────────────────────────────┘│││   │
│  │  │  └─────────────────────────────────────────────────────┘││   │
│  │  └─────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Problems:                                                          │
│  • Deep inheritance (6-8 levels)                                    │
│  • Each node is its own process                                     │
│  • Tight coupling between concerns                                  │
│  • Hard to test in isolation                                        │
│  • Duplicated boilerplate across nodes                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Target Architecture (Runtime-Host)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   RuntimeHostProcess (omnibase_infra)               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              NodeRuntime (omnibase_core)                     │   │
│  │                                                              │   │
│  │  • Event loop coordination                                   │   │
│  │  • Envelope encoding/decoding                                │   │
│  │  • Correlation ID propagation                                │   │
│  │  • Metrics emission                                          │   │
│  │  • Health checks                                             │   │
│  │  • Discovery responses                                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              │               │               │                      │
│              ▼               ▼               ▼                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐             │
│  │ NodeInstance  │ │ NodeInstance  │ │ NodeInstance  │             │
│  │ (vault-adapter)│ │ (query-user) │ │ (echo-node)  │             │
│  │  (core)       │ │  (core)       │ │  (core)       │             │
│  │ • contract    │ │ • contract    │ │ • contract    │             │
│  │ • models      │ │ • models      │ │ • models      │             │
│  │ • logic.py    │ │ • logic.py    │ │ • logic.py    │             │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘             │
│          │                 │                 │                      │
│          │    Handlers injected from infra   │                      │
│          ▼                 ▼                 ▼                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐             │
│  │ VaultHandler  │ │  DbHandler    │ │ LocalHandler  │             │
│  │  (infra)      │ │  (infra)      │ │  (infra)      │             │
│  │ • Client pool │ │ • Conn pool   │ │ • Echo logic  │             │
│  │ • Retries     │ │ • Retries     │ │               │             │
│  │ • Health      │ │ • Health      │ │               │             │
│  └───────────────┘ └───────────────┘ └───────────────┘             │
│                                                                     │
│  Benefits:                                                          │
│  • Zero inheritance in nodes                                        │
│  • Multiple nodes per runtime                                       │
│  • Clean separation of concerns                                     │
│  • Easy to test each layer                                          │
│  • Shared infrastructure                                            │
│  • Handlers in infra, not core (no I/O in core)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Runtime Host Wiring

The runtime host process (in infra) wraps NodeRuntime (in core) and injects handlers:

```
RuntimeHostProcess (omnibase_infra/runtime_host/)
    └── NodeRuntime (omnibase_core)
          ├── NodeInstance(vault_adapter)
          ├── NodeInstance(user_query)
          └── NodeInstance(echo)
          └── handlers: (injected from infra)
                 vault_handler: VaultHandler
                 db_handler: PostgresHandler
                 kafka_handler: KafkaHandler
```

**Key Architectural Points**:
- `RuntimeHostProcess` in infra owns the Kafka consumer/producer (I/O)
- `NodeRuntime` in core orchestrates node instances (pure coordination)
- Handlers are implemented in infra but injected into runtime via protocols

### Package Responsibilities

| Package | Contains | Depends On |
|---------|----------|------------|
| `omnibase_core` | Core models, ONEX contract models, **NodeRuntime**, **NodeInstance**, enums, primitives, domain libraries | pydantic, stdlib |
| `omnibase_spi` | Pure Protocol interfaces for handlers, event bus, and system services | `omnibase_core` |
| `omnibase_infra` | Concrete handler implementations (Vault, DB, HTTP), **runtime-host entrypoints**, wire-up code | `omnibase_core`, `omnibase_spi` |
| `omniintelligence` | Node contracts, Pydantic IO models, domain logic | `omnibase_core`, `omnibase_spi` |

### Dependency Flow (Correct Direction)

```
omnibase_core (NodeRuntime, models, primitives)
    ^
    |
omnibase_spi (Protocol interfaces)
    ^
    |
omnibase_infra (Handler implementations, runtime host process)
```

**Key Points**:
- Core is the foundation - it depends on NOTHING except pydantic and stdlib
- SPI depends on Core (uses Core types in protocol signatures)
- Infra depends on both (implements SPI protocols, uses Core models)

---

## 3. The Four Transformations

### Transformation 1: Fix Dependency Direction

**Document**: [Dependency Refactoring Plan](./DEPENDENCY_REFACTORING_PLAN.md)

```
BEFORE                              AFTER
======                              =====
omnibase_core                       omnibase_core
  └── depends on → omnibase_spi       └── depends on → nothing

omnibase_spi                        omnibase_spi
  └── depends on → nothing            └── depends on → omnibase_core
```

**Key Actions**:
1. Move types from SPI to Core (`ContextValue`, `LiteralOperationStatus`, etc.)
2. Update SPI protocols to use Core types in signatures
3. Remove all SPI imports from Core (27 files)
4. Create handler protocols in SPI

**Why First**: Everything else depends on clean Core types.

---

### Transformation 2: Classify and Dissolve Mixins

**Document**: [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md)

Every mixin gets one of three classifications:

| Classification | Count | Destination | Example |
|----------------|-------|-------------|---------|
| **R** (Runtime) | 22 | `NodeRuntime` / `NodeInstance` | `mixin_event_bus` → `NodeRuntime._decode_envelope()` |
| **H** (Handler) | 4 | Handler implementations | `mixin_service_registry` → `RegistryHandler` |
| **D** (Domain) | 14 | Pure libraries | `mixin_hash_computation` → `omnibase_core.lib.hashing` |

**Key Principle**:
- If a mixin is about **how** the node runs → **Runtime**
- If it is about **how** to talk to an external system → **Handler**
- If it is about **what** the domain computation is → **Library**

---

### Transformation 3: Build Handler Infrastructure

**Document**: [Declarative Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md)

**Models in Core** (no I/O, pure data structures):
```
src/omnibase_core/models/effect/
├── model_effect_contract.py
├── model_protocol_config.py
├── model_connection_config.py
├── model_auth_config.py
├── model_operation_config.py
├── model_request_config.py
├── model_response_config.py
├── model_resilience_config.py
├── model_events_config.py
└── model_observability_config.py
```

**Handlers in Infra** (all I/O lives here):
```
omnibase_infra/
├── handlers/
│   ├── http/
│   │   └── http_rest_handler.py
│   ├── db/
│   │   └── postgres_handler.py
│   ├── graph/
│   │   └── bolt_handler.py
│   └── event/
│       └── kafka_handler.py
├── resilience/
│   ├── retry_policy.py
│   ├── circuit_breaker.py
│   └── rate_limiter.py
└── runtime_host/
    ├── entrypoint.py
    └── wiring.py
```

**What Handlers Absorb** (all moved from mixins to infra):
- Connection pooling (from mixins)
- Retry/backoff logic (from mixins)
- Health checks (from mixins)
- Metrics (from mixins)
- Client lifecycle (from mixins)

**Critical**: Handlers implement `ProtocolHandler` from SPI but live in infra, never in core.

---

### Transformation 4: Build Minimal Runtime Host

**Document**: [Minimal Runtime Phased Plan](./MINIMAL_RUNTIME_PHASED_PLAN.md)

**Phase 0**: Core types and topic naming
```
onex.app.local.global.cmd.node.<node_slug>.v1  # Commands
onex.app.local.global.evt.node.<node_slug>.v1  # Events
onex.sys.local.global.log.runtime.<slug>.v1    # Logs
```

**Phase 1**: Minimal local runtime
```python
class NodeRuntime:
    runtime_node_id: NodeId
    runtime_contract: RuntimeHostContract
    node_instances: dict[NodeId, NodeInstance]
    kafka_consumer: Consumer
    kafka_producer: Producer

    async def run_loop(self):
        while True:
            envelope = await self.consume()
            node = self.node_instances[envelope.node_id]
            results = await node.handle(envelope)
            for result in results:
                await self.produce(result)
```

**Phase 2**: Add one real handler (DB or LLM)

**Phase 3**: Point to cloud infrastructure (hybrid mode)

**Phase 4**: Multiple runtime hosts in K8s

---

## 4. Execution Order

### Critical Path

```
Week 1-4: Dependency Refactoring
    │
    ├── Week 1: Prepare Core (new types, models)
    ├── Week 2: Update SPI to use Core types
    ├── Week 3: Migrate Core imports (remove SPI dependency)
    └── Week 4: Update consuming repos
          │
          ▼
Week 5: Mixin Classification
    │
    └── Classify all 40 mixins as R/H/D
    └── Freeze mixin design (no new mixins)
          │
          ▼
Week 6-7: Handler Infrastructure
    │
    ├── Day 1: Pydantic models
    ├── Day 2-3: Protocol handlers
    ├── Day 4: Resilience components
    └── Day 5-7: Runtime and testing
          │
          ▼
Week 8-11: Runtime Host MVP
    │
    ├── Week 8: Phase 0-1 (core types, NodeRuntime)
    ├── Week 9: Phase 1 cont. (handlers, registry, CLI)
    ├── Week 10: Phase 2 (one real handler)
    └── Week 11: Phase 3 (hybrid mode)
          │
          ▼
Week 12+: Mixin Dissolution
    │
    ├── Move R mixins into NodeRuntime
    ├── Move H mixins into handlers
    ├── Move D mixins into libraries
    └── Delete obsolete mixins
```

### Parallel Workstreams

Some work can happen in parallel:

```
┌─────────────────────┐     ┌─────────────────────┐
│ Dependency          │     │ Handler             │
│ Refactoring         │────▶│ Infrastructure      │
│ (Weeks 1-4)         │     │ (Weeks 6-7)         │
└─────────────────────┘     └─────────────────────┘
                                    │
                                    ▼
┌─────────────────────┐     ┌─────────────────────┐
│ Mixin               │────▶│ Runtime Host        │
│ Classification      │     │ MVP                 │
│ (Week 5)            │     │ (Weeks 8-11)        │
└─────────────────────┘     └─────────────────────┘
```

---

## 5. Timeline Summary

### Overall Duration: 12-16 Weeks

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| Dependency Refactoring | 4 weeks | Core has zero SPI imports |
| Mixin Classification | 1 week | All 40 mixins labeled R/H/D |
| Handler Infrastructure | 1 week | 4 handlers + resilience components |
| Runtime Host MVP | 4 weeks | End-to-end Kafka flow working |
| Mixin Dissolution | 2-4 weeks | Zero mixins attached to nodes |
| **Total** | **12-16 weeks** | Production-ready system |

### Milestones

| Milestone | Week | Success Criteria |
|-----------|------|------------------|
| M1: Clean Core | 4 | `omnibase_core` has 0 SPI imports |
| M2: Mixins Classified | 5 | All 40 mixins have R/H/D label |
| M3: Handlers Ready | 7 | HTTP, Bolt, Postgres, Kafka handlers pass tests |
| M4: Echo Flow | 9 | End-to-end echo through Kafka works |
| M5: Real Handler | 10 | DB or LLM handler works with real infra |
| M6: Hybrid Mode | 11 | Local runtime talks to cloud infra |
| M7: Mixins Gone | 14 | No mixin inheritance in node classes |

---

## 6. Quick Reference

### What Goes Where

| If the code... | Package | Example |
|----------------|---------|---------|
| Coordinates node execution (no I/O) | `omnibase_core` (NodeRuntime) | `NodeRuntime._dispatch_to_node()` |
| Decodes envelopes (pure transform) | `omnibase_core` (NodeRuntime) | `_decode_envelope()` |
| Manages Kafka consumer/producer | `omnibase_infra` (RuntimeHostProcess) | `RuntimeHostProcess._consume()` |
| Manages connection pools | `omnibase_infra` (Handler) | `VaultHandler._pool` |
| Computes a hash | `omnibase_core` (domain library) | `omnibase_core.lib.hashing.compute_hash()` |
| Defines a data structure | `omnibase_core` (model) | `ModelEffectContract` |
| Defines an interface | `omnibase_spi` (protocol) | `ProtocolVaultHandler` |
| Implements an interface | `omnibase_infra` (handler) | `VaultHandler(ProtocolVaultHandler)` |
| Any network, database, or file I/O | `omnibase_infra` | Never in core or spi |

### Node Structure After Migration

```
nodes/vault_adapter/
├── contract.yaml           # Declarative contract
├── models.py               # Input/output Pydantic models
└── logic.py                # Pure domain logic (30-150 lines, 80-95% reduction)
```

```python
# logic.py (30-150 lines depending on complexity)
from omnibase_core.models.effect import ModelEffectInput, ModelEffectOutput

async def handle_vault_request(
    input_data: ModelVaultInput,
    vault_handler: ProtocolVaultHandler  # Injected from infra
) -> ModelVaultOutput:
    """Pure domain logic - no inheritance, no mixins, no I/O.

    The handler (from omnibase_infra) is injected and handles all
    actual Vault communication. This logic only orchestrates the flow.
    """
    match input_data.action:
        case "get_secret":
            secret = await vault_handler.get_secret(input_data.path)
            return ModelVaultOutput(success=True, data=secret)
        case "put_secret":
            await vault_handler.put_secret(input_data.path, input_data.data)
            return ModelVaultOutput(success=True)
```

### Files to Read (In Order)

1. **Start here**: This document (overview)
2. **Then**: [Minimal Runtime Phased Plan](./MINIMAL_RUNTIME_PHASED_PLAN.md) (15 min)
3. **Then**: [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) (25 min)
4. **Deep dive**: [Declarative Effect Nodes Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md) (45 min)
5. **Reference**: [Dependency Refactoring Plan](./DEPENDENCY_REFACTORING_PLAN.md) (20 min)

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **NodeRuntime** | Core component (in `omnibase_core`) that hosts multiple NodeInstances and manages their lifecycle via pure coordination (no I/O) |
| **NodeInstance** | Single node hosted by a runtime, contains contract + models + logic (in `omnibase_core`) |
| **RuntimeHostProcess** | Infra component (in `omnibase_infra`) that wraps NodeRuntime and owns all I/O (Kafka, etc.) |
| **Handler** | Component (in `omnibase_infra`) that owns external system connections (Vault, DB, etc.) |
| **Contract** | YAML file declaring node behavior without code |
| **R/H/D** | Classification system: Runtime / Handler / Domain |
| **SPI** | Service Provider Interface - pure protocol definitions (in `omnibase_spi`) |
| **Core** | Foundation package with models, enums, primitives, NodeRuntime, NodeInstance (no I/O) |
| **Infra** | Implementation package with handlers, RuntimeHostProcess, all I/O operations |
| **RUNTIME_HOST** | Node kind for runtime host processes that coordinate other nodes |

## Appendix B: Document Versions

| Document | Version | Last Updated |
|----------|---------|--------------|
| This Overview | 1.1.0 | 2025-12-03 |
| Dependency Refactoring Plan | 1.1.0 | 2025-12-03 |
| Mixin Migration Plan | 1.0.0 | 2025-12-03 |
| Declarative Effect Nodes Plan | 1.2.0 | 2025-12-03 |
| Minimal Runtime Phased Plan | 1.0.0 | 2025-12-03 |

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-03 | Initial release |
| 1.1.0 | 2025-12-03 | Architectural corrections: handlers moved to infra, NodeRuntime clarified as core component, dependency flow corrected, Core Design Invariants added, Lines per Node metric updated to 30-150, Runtime Host Wiring section added |

---

**Last Updated**: 2025-12-03
**Project Version**: 0.2.0
