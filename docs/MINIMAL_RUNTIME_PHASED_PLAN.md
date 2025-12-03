# Phased Cut-Down Plan: Minimum Correct Runtime, Then Incremental

**Version**: 1.1.0
**Status**: Draft
**Created**: 2025-12-03
**Repository**: omnibase_core
**Related Documents**:
- [Declarative Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md)
- [Dependency Refactoring Plan](./DEPENDENCY_REFACTORING_PLAN.md)
- [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md)

---

## Overview

You do not need all the new ideas at once. You need a **smallest slice** that is:
- Architecturally correct
- Locally runnable
- Easy to extend

Below is the minimal version, then the incremental phases.

---

## Core Design Invariants

Before diving into phases, establish these invariants:

1. **All behavior is contract-driven.**
2. **NodeRuntime is the only executable event loop** - lives in `omnibase_core`.
3. **Node logic is pure**: no I/O, no mixins, no inheritance.
4. **Core never depends on SPI or infra.**
5. **SPI only defines protocols**, never implementations.
6. **Infra owns all I/O** and real system integrations.

**Critical**: No code in `omnibase_core` may initiate network I/O, database I/O, file I/O, or external process execution.

---

## Table of Contents

1. [Core Design Invariants](#core-design-invariants)
2. [Phase 0: Non-Negotiables](#phase-0-non-negotiables-you-decide-once)
3. [Phase 1: Minimal Local Runtime Host](#phase-1-minimal-local-runtime-host-single-process-single-runtime-node)
4. [Phase 2: Add One Real Integration](#phase-2-add-one-real-integration-still-local-runtime)
5. [Phase 3: Plug In Cloud Data Plane](#phase-3-plug-in-cloud-data-plane-runtime-still-local)
6. [Phase 4: Multiple Runtime Hosts And Scaling](#phase-4-multiple-runtime-hosts-and-scaling-later-not-now)
7. [Priority Checklist](#priority-checklist-do-this-in-order)

---

## Phase 0: Non-Negotiables (You Decide Once)

These are tiny but structural. Do them first.

### 1. Core Types

- Add `NodeKind.RUNTIME_HOST` to your core enums (required for Phase 1 RuntimeHostContract).
- Define or confirm:
    - `OnexEnvelope` (tenant_id, node_id, contract_id, payload, correlation_id, causality fields).
    - `NodeId`, `TenantId`, `ContractId` models.

### 2. Minimal Topic Naming

Use the simplest correct subset:

| Purpose | Topic Pattern |
|---------|--------------|
| Commands to a node | `onex.app.local.global.cmd.node.<node_slug>.v1` |
| Events from a node | `onex.app.local.global.evt.node.<node_slug>.v1` |
| Runtime logs | `onex.sys.local.global.log.runtime.<runtime_slug>.v1` |

You can expand to full plane/env/tenant later. This subset is enough to avoid painting yourself into a corner.

### 3. Contract Base Models

Confirm you have Pydantic models for:

| Contract Type | Description |
|--------------|-------------|
| `BaseNodeContract` | Base class for all node contracts |
| `ReducerContract` | State management nodes |
| `OrchestratorContract` | Workflow coordination nodes |
| `EffectContract` | External interaction nodes |
| `RuntimeHostContract` | Runtime host (introduced in Phase 1) |

Each contract has:

```python
class BaseNodeContract(BaseModel):
    node_id: NodeId
    kind: NodeKind
    version: str
    tenant_scope: str | list[str] = "global"  # "global" or list of tenants
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### 4. Mixin Classification

Before Phase 1, classify all existing mixins using the R/H/D system:

| Classification | Destination | When |
|----------------|-------------|------|
| **R** (Runtime) | `NodeRuntime` / `NodeInstance` | Phase 1 |
| **H** (Handler) | Handler implementations | Phase 1-2 |
| **D** (Domain) | Pure libraries | Phase 1 |

See [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) for complete classification.

---

## Phase 1: Minimal Local Runtime Host (Single Process, Single Runtime Node)

**Goal**: One binary, one runtime host contract, one or two nodes, end-to-end through Kafka.

### 1. RuntimeHostContract (Cut-Down Version)

Add a minimal SPI model:

```yaml
kind: runtime_host
node_id: runtime-dev
version: "0.1.0"
subscriptions:
    # for now, a fixed pattern for commands
    cmd_topics:
        - "onex.app.local.global.cmd.node.#"
handlers:
    families:
        - "local"
        - "http"
host_selector:
    # for the MVP, just explicit node_ids
    node_ids:
        - "echo-node"
        - "http-proxy-node"
```

**For MVP**:
- `host_selector.node_ids` is enough.
- No labels, no tenant filters yet.

### 2. NodeRuntime and NodeInstance

**Package Placement**:
- `NodeRuntime` -> `omnibase_core/runtime/node_runtime.py` (pure algorithm)
- `NodeInstance` -> `omnibase_core/runtime/node_instance.py` (pure algorithm)
- `RuntimeHostProcess` -> `omnibase_infra/runtime_host/entrypoint.py` (owns Kafka connections)

The split:
- **Core** defines *what* the runtime does (consume envelope -> route -> handle -> emit)
- **Infra** defines *how* it connects to Kafka (real connections, wire-up)

Implement two classes in **omnibase_core**:

#### NodeInstance

```python
class NodeInstance:
    """Single node instance hosted by a runtime."""

    node_id: NodeId
    kind: NodeKind  # REDUCER / ORCHESTRATOR / EFFECT
    contract: BaseNodeContract  # typed contract
    handlers: list[Handler]  # references to handler instances (injected from infra)

    def handle(self, envelope: OnexEnvelope) -> list[OnexEnvelope]:
        """Process envelope and return response envelopes."""
        ...
```

#### NodeRuntime

```python
class NodeRuntime:
    """Runtime host that manages multiple node instances.

    This is the PURE ALGORITHM component. It does not own Kafka connections.
    Those are injected by RuntimeHostProcess (in omnibase_infra).
    """

    runtime_node_id: NodeId
    runtime_contract: RuntimeHostContract
    node_instances: dict[NodeId, NodeInstance]
    # Note: No kafka_consumer/kafka_producer here - those live in infra

    def load_contracts(self, registry: ProtocolRegistry) -> None:
        """Load node contracts from registry based on RuntimeHostContract."""
        ...

    def init_node_instances(self, handlers: dict[str, Handler]) -> None:
        """Instantiate NodeInstance for each hosted node.

        Handlers are injected from infra layer.
        """
        ...

    def route_envelope(self, envelope: OnexEnvelope) -> list[OnexEnvelope]:
        """Route envelope to appropriate NodeInstance and return results.

        This is the pure routing logic - no I/O.
        """
        ...
```

This is the core runtime. Keep it small and boring. All I/O lives in infra.

### 2.1 Runtime Mixin Absorption

NodeRuntime and NodeInstance absorb these runtime-level mixins:

- `mixin_event_bus` -> `NodeRuntime._decode_envelope()`, `._encode_envelope()`
- `mixin_event_handler` -> `NodeInstance.handle()`
- `mixin_node_lifecycle` -> `NodeRuntime.init_node_instances()`, `.shutdown()`
- `mixin_health_check` -> `NodeRuntime.health_check()`
- `mixin_metrics` -> `NodeRuntime._emit_metrics()`
- `mixin_discovery_responder` -> `NodeRuntime._handle_discovery()`

Nodes no longer inherit these mixins; the runtime provides these capabilities.

### 3. Minimum Handlers

**Package Placement**: All handlers live in `omnibase_infra/handlers/`

Start with two handler families:

#### Local Handler (Testing Only)

**Location**: `omnibase_infra/handlers/local_handler.py`

```python
class LocalHandler(Handler):
    """Echo/trivial transformation handler for testing."""

    async def execute(self, envelope: OnexEnvelope) -> OnexEnvelope:
        # Returns echo or trivial transformation
        # Lets you verify the loop without touching external systems
        ...
```

#### HTTP Handler

**Location**: `omnibase_infra/handlers/http_handler.py`

```python
class HttpHandler(Handler):
    """HTTP REST handler using httpx."""

    url_template: str
    method: str
    headers: dict[str, str]

    async def execute(self, envelope: OnexEnvelope) -> OnexEnvelope:
        # Sends request and returns response payload
        # Used by EffectContract like http-proxy-node
        ...
```

**No DB, no LLM, no Qdrant in Phase 1.** Those come later.

### 3.1 Runtime Host Architecture

```
RuntimeHostProcess (omnibase_infra)
    |
    +-- NodeRuntime (omnibase_core)
          +-- NodeInstance(echo-node)
          +-- NodeInstance(http-proxy-node)
          +-- handlers: (injected from infra)
                 local: LocalHandler
                 http: HttpRestHandler
```

The process container (infra) owns:
- Kafka consumer/producer connections
- Handler instantiation and injection
- CLI entry point

The runtime (core) owns:
- Envelope routing logic
- Node instance lifecycle
- Handler dispatch (via injected protocols)

### 4. Registry Stub (File-Based)

For MVP runtime, use a simple file-based registry:

```
contracts/
├── runtime/
│   └── runtime-dev.yaml
└── nodes/
    ├── echo-node.yaml
    └── http-proxy-node.yaml
```

Add a tiny `FileRegistry` class:

```python
class FileRegistry:
    """File-based contract registry for MVP."""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    def get_runtime_contract(self, node_id: NodeId) -> RuntimeHostContract:
        """Returns parsed RuntimeHostContract."""
        ...

    def get_node_contract(self, node_id: NodeId) -> BaseNodeContract:
        """Returns parsed node contract."""
        ...
```

Later, replace with HTTP/DB backed registry. **Do not overbuild this now.**

### 5. CLI Entry Point

Add a command: `omninode-runtime-host`

**Behavior**:

1. Reads `--runtime-node-id` and `--config` path.
2. Loads infra config (Kafka host, registry path).
3. Loads the runtime host contract from the registry.
4. Constructs `NodeRuntime`.
5. Runs `run_loop()`.

This is what you actually "start" when you run the system locally.

```bash
# Example usage
omninode-runtime-host --runtime-node-id runtime-dev --config ./config/local.yaml
```

---

## Phase 2: Add One Real Integration (Still Local Runtime)

Once Phase 1 is working, add **one** serious effect family that hits real infra.

**Pick exactly one**:
- `db` handler (Postgres)
- `llm` handler (to your local model runner)

**Do not add both in this phase.**

### Option A: DB Handler

**Handler Mixin Absorption**: The DB handler absorbs connection pooling, retry, and health check logic that was previously in mixins. See [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) for complete handler-mixin mapping.

Define `DbEffectContract` subset:

```yaml
kind: effect
node_id: query-user
version: "0.1.0"
effect_type: "db"
db:
    connection: "default"
    sql: "select * from users where id = :user_id"
    params:
        user_id: "$.payload.user_id"
```

Implement `DbHandler`:

```python
class DbHandler(Handler):
    """PostgreSQL database handler."""

    async def execute(self, envelope: OnexEnvelope) -> OnexEnvelope:
        # Uses a pooled connection to Postgres
        # Executes query
        # Returns rows as list of dicts in payload
        ...
```

**Full path verification**:

1. CLI emits `cmd` envelope to `onex.app.local.global.cmd.node.query-user.v1`
2. Runtime host picks it up
3. `DbHandler` executes query
4. Runtime emits `evt` to `onex.app.local.global.evt.node.query-user.v1` with results

This is enough to prove "real world" correctness.

### Option B: LLM Handler

Same pattern, but replaced with:
- LLM model id
- Prompt template
- Output normalization

---

## Phase 3: Plug In Cloud Data Plane (Runtime Still Local)

Only after Phase 2 works locally do you move to hybrid.

**Changes**:

- Point the runtime's Kafka/Postgres/Qdrant config to the AWS endpoints via WireGuard.
- **Do not move the runtime itself to AWS yet.**
- Confirm:
    - Same contracts
    - Same topics
    - Same NodeRuntime and NodeInstance code

Now your laptop runtime hosts nodes that talk to cloud infra. That satisfies the "correct and hybrid" requirement without building worker pools or multi-tenant runtime hosts yet.

```yaml
# config/hybrid.yaml
kafka:
  bootstrap_servers: "kafka.aws.internal:9092"  # via WireGuard
postgres:
  host: "postgres.aws.internal"
  port: 5432
qdrant:
  host: "qdrant.aws.internal"
  port: 6333
```

---

## Phase 4: Multiple Runtime Hosts And Scaling (Later, Not Now)

Only after MVP and basic beta you can:

- Add multiple `RuntimeHostContract`s:
    - `runtime-dev-light` (echo, http handlers)
    - `runtime-dev-llm` (llm, embedding handlers)
- Deploy them as K8s Deployments in AWS.
- Switch some nodes to be hosted there instead of on the laptop.

At that point:
- The **local runtime** becomes a dev tool
- The **cloud runtimes** become the live worker pools

---

## Priority Checklist (Do This In Order)

| Step | Task | Status |
|------|------|--------|
| 1 | Add `NodeKind.RUNTIME_HOST` and confirm core ONEX envelope models | ⬜ |
| 1.5 | Classify all mixins as R/H/D and freeze mixin design | ⬜ |
| 2 | Lock a minimal topic schema for `cmd.node.*`, `evt.node.*`, `log.runtime.*` | ⬜ |
| 3 | Implement `RuntimeHostContract` with `node_ids`, `cmd_topics`, `handlers.families` | ⬜ |
| 4 | Implement `NodeInstance` and `NodeRuntime` | ⬜ |
| 5 | Wire: file-based registry, runtime host CLI, local echo and http handlers | ⬜ |
| 6 | Verify one end-to-end echo flow over Kafka | ⬜ |
| 7 | Add one real handler (DB or LLM) | ⬜ |
| 8 | Point infra config at AWS for hybrid mode | ⬜ |

**Everything else is optional and incremental.**

---

## Relationship to Other Plans

This plan **complements** the existing planning documents:

| Document | Focus | Relationship |
|----------|-------|--------------|
| [Dependency Refactoring Plan](./DEPENDENCY_REFACTORING_PLAN.md) | Fix Core/SPI inversion | **Prerequisite** - Core types must be clean |
| [Declarative Effect Nodes Implementation Plan](./DECLARATIVE_EFFECT_NODES_IMPLEMENTATION_PLAN.md) | Effect node infrastructure | **Provides handlers** - HTTP, Postgres, Kafka |
| [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) | Mixin -> R/H/D dissolution | **Integrated** - Mixins dissolve across phases |
| **This Document** | Minimal runtime host | **Orchestrates** - Uses effect handlers in runtime |

### Integration Points

1. **Phase 0** of this plan uses types from Core (after dependency refactoring)
2. **Phase 1** http handler aligns with `HttpRestHandler` from Effect Nodes plan
3. **Phase 2** db handler aligns with `PostgresHandler` from Effect Nodes plan
4. **Phase 3** uses the same Kafka infrastructure as Effect Nodes events config

---

## Summary

That is the minimum that is both correct and small enough to finish under current time pressure. Everything above that is just multiplying this same pattern.

**Key Principles**:
- Start with the smallest architecturally correct slice
- Add real integrations one at a time
- Move to hybrid only after local works
- Scale only after MVP is proven

---

**Last Updated**: 2025-12-03
**Project Version**: 0.2.0
