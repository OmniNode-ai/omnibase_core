# OMN-11546 Core Node Migration Audit

Date: 2026-05-22

## Scope

This audit classifies the six files named by OMN-11546 before any core to infra
migration work starts:

- `src/omnibase_core/nodes/node_reducer.py`
- `src/omnibase_core/nodes/node_compute.py`
- `src/omnibase_core/nodes/node_effect.py`
- `src/omnibase_core/nodes/node_orchestrator.py`
- `src/omnibase_core/infrastructure/node_core_base.py`
- `src/omnibase_core/runtime/runtime_local.py`

The classification uses the ADR-005 core/infra boundary:
`omnibase_core` owns protocols, domain models, pure computation logic, and base
node implementations that use injected services. Concrete transport, broker,
database, and runtime backend implementations belong outside core.

## Classification

| File | Classification | Decision | Rationale |
| --- | --- | --- | --- |
| `src/omnibase_core/infrastructure/node_core_base.py` | Abstract base | Keep in core | Defines the common `NodeCoreBase` lifecycle, container integration, protocol dependency resolution, metadata, and abstract `process()` contract. It resolves contracts and protocol dependencies through core models and DI. It does not own a concrete external backend. |
| `src/omnibase_core/nodes/node_compute.py` | Base declarative node implementation | Keep in core | Implements the canonical pure compute node surface. Optional cache, timing, and parallel execution are protocol-injected and the file documents pure-mode operation when those services are absent. This is an allowed base node implementation under ADR-005, not an infra adapter. |
| `src/omnibase_core/nodes/node_reducer.py` | Base declarative node implementation | Keep in core | Implements the FSM-driven reducer surface and emits typed reducer outputs and projection intents. It does not import transport or persistence libraries. Stateful execution is local to the node instance and documented as a current base-node limitation. |
| `src/omnibase_core/nodes/node_effect.py` | Base declarative node implementation | Keep in core | Defines the contract-driven effect shell, retry/circuit-breaker metadata handling, and handler routing. The file describes external I/O operations, but does not implement concrete HTTP, database, filesystem, or broker clients. Those remain delegated to handlers/adapters. |
| `src/omnibase_core/nodes/node_orchestrator.py` | Base declarative node implementation | Keep in core | Implements the workflow coordination node and explicitly forbids direct external writes. It emits actions and tracks workflow state; concrete side effects remain delegated to target nodes. |
| `src/omnibase_core/runtime/runtime_local.py` | Concrete runtime implementation / mixed | Split then migrate | This file loads workflow contracts from disk, imports handler/input classes dynamically, creates event buses, starts/closes the bus, writes `.onex_state` results, and discovers Kafka via `onex.backends` entry points. It avoids direct `omnibase_infra` imports, but it is still a concrete local runtime runner rather than a core abstraction. |

## Migration Recommendation

Do not move the four `Node*` classes or `NodeCoreBase` as part of the Phase 4
core-to-infra migration. They are core framework surfaces and are heavily
documented, imported, and tested as public API.

Create the next implementation ticket for `RuntimeLocal` only:

1. Extract stable core-owned contract/input parsing types if needed.
2. Move the concrete local runtime runner to an infra/runtime package that can
   own backend construction, event-bus lifecycle, dynamic handler loading, and
   state writes.
3. Preserve existing CLI/import compatibility through an approved, time-bounded
   facade only if downstream compatibility requires it.
4. Run the existing runtime test suite before and after the move:
   `tests/unit/runtime/test_runtime_local_execution.py`,
   `tests/unit/runtime/test_runtime_local_event_bus_override.py`,
   `tests/unit/runtime/test_runtime_local_reducer_state_sink.py`,
   and `tests/test_runtime_local_input_flag.py`.

## Evidence Commands

Commands run from the OMN-11546 worktree:

```bash
wc -l src/omnibase_core/nodes/node_reducer.py \
  src/omnibase_core/nodes/node_compute.py \
  src/omnibase_core/nodes/node_effect.py \
  src/omnibase_core/nodes/node_orchestrator.py \
  src/omnibase_core/infrastructure/node_core_base.py \
  src/omnibase_core/runtime/runtime_local.py

rg -n "^(from|import|class|def|async def)|Protocol|ABC|abstractmethod|Kafka|Redis|httpx|asyncio|subprocess|Path|open\\(|requests|socket|producer|consumer|event_bus|runtime" \
  src/omnibase_core/nodes/node_reducer.py \
  src/omnibase_core/nodes/node_compute.py \
  src/omnibase_core/nodes/node_effect.py \
  src/omnibase_core/nodes/node_orchestrator.py \
  src/omnibase_core/infrastructure/node_core_base.py \
  src/omnibase_core/runtime/runtime_local.py

rg -n "runtime_local|RuntimeLocal|node_reducer|node_compute|node_effect|node_orchestrator|node_core_base" \
  tests src/omnibase_core -g '*.py'
```

Key observations:

- ADR-005 allows base node implementations in core and forbids concrete I/O
  dependencies in core.
- `NodeCompute`, `NodeReducer`, `NodeEffect`, and `NodeOrchestrator` are
  documented public API and are imported by integration, concurrency, protocol,
  model-service, and API snapshot tests.
- `RuntimeLocal` is imported by the CLI and runtime test suite and performs
  concrete runtime orchestration, backend selection, disk input/output, and
  dynamic module loading.
