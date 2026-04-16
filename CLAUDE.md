# CLAUDE.md - Omnibase Core

> **Python**: 3.12+ | **Framework**: ONEX Core | **Package Manager**: uv | **Shared Standards**: See **`~/.claude/CLAUDE.md`** for shared development standards (Python, Git, testing, architecture principles) and infrastructure configuration (PostgreSQL, Kafka/Redpanda, Docker networking, environment variables).

---

## Table of Contents

1. [Repo Invariants](#repo-invariants)
2. [Non-Goals](#non-goals)
3. [External SDK Surface](#external-sdk-surface)
4. [Quick Reference](#quick-reference)
5. [Python Development - uv](#python-development---uv)
6. [Handler Output Constraints](#handler-output-constraints)
7. [Forbidden Data Flow Patterns](#forbidden-data-flow-patterns)
8. [Dependency Injection](#dependency-injection)
9. [Error Handling](#error-handling)
10. [Project Structure](#project-structure)
11. [Pydantic Model Standards](#pydantic-model-standards)
12. [Code Quality](#code-quality)
13. [Common Pitfalls](#common-pitfalls)
14. [Documentation](#documentation)

---

## Repo Invariants

These are non-negotiable architectural truths:

- **Nodes are thin** - Nodes are coordination shells, not business logic containers
- **Handlers own logic** - Business logic lives in handlers, not nodes
- **Reducers are pure** - `delta(state, event) -> (new_state, intents[])` with no I/O
- **Orchestrators emit, never return** - ORCHESTRATOR nodes cannot return `result`
- **Contracts are source of truth** - YAML contracts define behavior, not code
- **Unidirectional flow** - EFFECT → COMPUTE → REDUCER → ORCHESTRATOR, never backwards

---

## Agent Behavioral Rules (OMN-6888)

### Autonomous mode safety rails

When operating autonomously in this repo:
- Never disable pre-commit hooks, CI checks, or type checkers to make code pass.
  Fix the code instead.
- Never write state files to `~/.claude/` -- use `omni_home/.onex_state/`.

### Contract-first topic definitions

This repo defines the contract framework that all ONEX nodes use. Kafka topic
declarations belong in contract YAML files (`event_bus.publish_topics` /
`subscribe_topics`), not hardcoded in application code. The `ContractConfigExtractor`
and validation pipeline enforce this.

---

## Non-Goals

We explicitly do **NOT** optimize for:

- **Backwards compatibility for internal APIs** - Internal Python module paths may change without notice. The stable external surface is defined in the External SDK Surface section below.
- **Convenience over correctness** - Contract violations fail loudly
- **Business logic in nodes** - Nodes coordinate; handlers compute
- **Dynamic runtime behavior** - All behavior must be contract-declared
- **Implicit state** - All state transitions are explicit and auditable
- **Tight coupling** - Protocol-based DI enforces loose coupling

---

## External SDK Surface

This package is consumed by external developers. The following surfaces are **stable**
and must not change without a deprecation path:

| Surface | Contract | Example |
|---------|----------|---------|
| `onex` CLI commands | Command names and flags are stable | `onex init`, `onex new node`, `onex validate`, `onex discover` |
| `onex.nodes` entry-point group | Group name is stable; external packages register nodes here | `[project.entry-points."onex.nodes"]` |
| Generated scaffold layout | Directory structure from `onex init` / `onex new node` is stable | `src/<pkg>/nodes/<name>/contract.yaml` |
| Contract validation | `onex validate` accepts any directory with valid contract.yaml files | No monorepo assumptions |

The following are **unstable** (may change without notice):
- Internal Python module paths (`omnibase_core.infrastructure.*`, `omnibase_core.services.*`, etc.)
- Node base class internal APIs
- Validation rule implementations (new rules may be added)

**CI enforcement**: `test_no_internal_deps.py` prevents internal OmniNode packages
from appearing in hard dependencies (`sdk-boundary-check` CI job).

---

## Quick Reference

```bash
# Setup
uv sync --all-extras && pre-commit install

# Testing
uv run pytest tests/                    # All tests (sequential by default)
uv run pytest tests/ -n 4               # With 4 parallel workers
uv run pytest tests/ -n 0 -xvs          # Debug mode (no parallelism)
uv run pytest tests/ --cov              # With coverage (60% minimum required)

# Code Quality
uv run mypy src/omnibase_core/          # Type checking (strict, 0 errors required)
uv run ruff check src/ tests/           # Linting
pre-commit run --all-files              # All hooks
```

**Test markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.performance`, `@pytest.mark.memory_intensive`, `@pytest.mark.isolated`

---

## Python Development - uv

> **Shared rules** (`--no-verify` prohibition, pre-commit hook policy) are in `~/.claude/CLAUDE.md`. Below are repo-specific additions only.

### Package Manager

This repository uses **uv** (not Poetry) for dependency management. All Python commands must be run via `uv run`.

```bash
uv sync --all-extras    # Install all dependencies (replaces: poetry install)
uv run <command>        # Run command in venv (replaces: poetry run <command>)
uv lock                 # Regenerate lockfile (replaces: poetry lock)
```

### Additional Git Commit Rules

- **NEVER use `--no-gpg-sign`** unless explicitly requested by the user.
- **NEVER run git commits in background mode** - always foreground.

### Agent Instructions

When spawning polymorphic agents or AI assistants:
- **ALWAYS** instruct them to use `uv run` for Python commands
- **NEVER** allow direct pip or python execution
- **NEVER** run agents in background mode

---

## Handler Output Constraints

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |

**Enforcement**: Pydantic validator at `ModelHandlerOutput` constructor + runtime validation + CI `node-purity-check` job.

### Runtime-synthesized terminal events (OMN-8940)

Synchronous-return handlers invoked via `RuntimeLocal._run_single_handler` receive
a **runtime-synthesized terminal event** after successful result classification.
The runtime publishes to the contract's declared `terminal_event` topic with
payload::

    {"status": "success" | "failure",
     "correlation_id": "<uuid>",
     "source": "runtime_local"}

The `source: "runtime_local"` field lets consumers distinguish runtime-synthesized
terminals from handler-published ones. This semantics applies **only** to the
single-handler execution path; the event-driven path (`_run_event_driven`) still
relies on handler-published terminals and must not double-emit.

**Rationale**: before this change, sync-return handlers like `NodeMergeSweep`
bypassed the bus entirely — the runtime classified the return value and wrote
state without the terminal topic ever receiving a message. That made bus-transit
claims unprovable for the single-handler path. Runtime-synthesized terminals
make the bus participate in every completed workflow regardless of handler
return style. FAILED results publish with `status: "failure"` — silence on
failure would be worse than a documented failure event.

**See**: [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md), [Canonical Execution Shapes](docs/architecture/CANONICAL_EXECUTION_SHAPES.md)

---

## Forbidden Data Flow Patterns

- Command → Reducer (bypasses orchestration)
- Reducer → I/O (violates purity)
- Orchestrator → Typed Result (only COMPUTE returns results)

**Canonical shapes**: `EVENT_TO_REDUCER`, `EVENT_TO_ORCHESTRATOR`, `INTENT_TO_EFFECT`, `COMMAND_TO_ORCHESTRATOR`, `COMMAND_TO_EFFECT`

**See**: [Canonical Execution Shapes](docs/architecture/CANONICAL_EXECUTION_SHAPES.md), [Execution Shape Examples](docs/architecture/EXECUTION_SHAPE_EXAMPLES.md)

---

## Dependency Injection

### Container Types (CRITICAL)

| Type | Purpose | In Node `__init__` |
|------|---------|-------------------|
| `ModelContainer[T]` | Value wrapper | **NEVER** |
| `ModelONEXContainer` | Dependency injection | **ALWAYS** |

**Resolution style**: Prefer type-based (`container.get_service(ProtocolLogger)`). String-based allowed for late-binding plugins. Never mix styles within the same module.

**See**: [Container Types](docs/architecture/CONTAINER_TYPES.md), [Dependency Injection](docs/architecture/DEPENDENCY_INJECTION.md)

---

## Error Handling

### ValueError vs ModelOnexError

| Use Case | Exception Type |
|----------|---------------|
| Standard Python validation at function boundaries | `ValueError` |
| Pydantic model validators | `ValueError` |
| ONEX-specific errors needing error codes | `ModelOnexError` |
| Errors that will be serialized/logged | `ModelOnexError` |
| Errors in node/workflow execution | `ModelOnexError` |

### Decorator Contract

- Cancellation signals (`SystemExit`, `KeyboardInterrupt`, `asyncio.CancelledError`) always propagate
- `ModelOnexError` re-raised as-is
- Other exceptions wrapped in `ModelOnexError`

### Comment Markers

- `# fallback-ok:` - Graceful degradation
- `# boundary-ok:` - API boundaries
- `# cleanup-resilience-ok:` - Cleanup must complete

**See**: [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

## Project Structure

**See**: [Architecture Overview](docs/architecture/overview.md) for full directory tree.

### Architecture Extensions

| Subsystem | Location |
|-----------|----------|
| Cross-Repo Validation | `src/omnibase_core/validation/cross_repo/` |
| Cryptographic Envelope | `src/omnibase_core/crypto/` |
| Architecture Handshakes | `architecture-handshakes/` |
| Contract Merge Engine | `src/omnibase_core/merge/` |
| Replay/Corpus System | `src/omnibase_core/models/replay/`, `services/replay/`, `protocols/replay/` |
| DB Validation | `src/omnibase_core/validation/db/` |
| Claude Code Hooks | `src/omnibase_core/models/hooks/`, `enums/hooks/` |

### File Naming Conventions

| Directory | Required Prefix | Example |
|-----------|----------------|---------|
| `cli/` | `cli_*` | `cli_commands.py` |
| `constants/` | `constants_*` | `constants_event_types.py` |
| `container/` | `container_*` | `container_service_registry.py` |
| `context/` | `context_*` | `context_application.py` |
| `contracts/` | `contract_*` | `contract_hash_registry.py` |
| `decorators/` | `decorator_*` | `decorator_error_handling.py` |
| `enums/` | `enum_*` | `enum_node_kind.py` |
| `errors/` | `error_*` or `exception_*` | `exception_groups.py` |
| `factories/` | `factory_*` | `factory_contract_profile.py` |
| `infrastructure/` | `node_*` or `infra_*` | `node_base.py` |
| `logging/` | `logging_*` | `logging_structured.py` |
| `mixins/` | `mixin_*` | `mixin_handler_routing.py` |
| `models/` | `model_*` | `model_event_envelope.py` |
| `nodes/` | `node_*` | `node_compute.py` |
| `pipeline/` | `builder_*`, `runner_*`, `manifest_*`, `handler_*` | `builder_execution_plan.py` |
| `protocols/` | `protocol_*` | `protocol_event_bus.py` |
| `runtime/` | `runtime_*`, `handler_*` | `runtime_file_registry.py` |
| `services/` | `service_*` | `service_handler_registry.py` |
| `types/` | `typed_dict_*`, `type_*`, `converter_*` | `type_compute_pipeline.py` |
| `utils/` | `util_*` | `util_datetime_parser.py` |
| `validation/` | `validator_*` or `checker_*` | `validator_contracts.py` |

**Exceptions**: `__init__.py`, `conftest.py`, `py.typed` are always allowed.

---

## Pydantic Model Standards

| Model Type | Required ConfigDict |
|------------|---------------------|
| **Immutable value** | `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` |
| **Mutable internal** | `ConfigDict(extra="forbid", from_attributes=True)` |
| **Contract/external** | `ConfigDict(extra="ignore", ...)` |

**`from_attributes=True`**: Required on frozen models for pytest-xdist compatibility.

**Mutable defaults**: ALWAYS use `default_factory` — e.g. `items: list[str] = Field(default_factory=list)`

### Plan Contract Enforcement Fields (OMN-8421)

`ModelPlanContract` carries plan-level enforcement metadata for the OMN-8416 plan → epic → tickets → PR → dogfood chain. When adding a new plan, set `epic_id` (Linear epic in `^OMN-\d+$` format), `plan_phases`, `success_criteria` (via `ModelDoDItem`), and `halt_conditions` at the top level — not in `context`. The existing `phase: EnumPlanPhase` lifecycle field is distinct from `plan_phases: list[str]` and must not be confused.

**See**: [Pydantic Best Practices](docs/conventions/PYDANTIC_BEST_PRACTICES.md)

---

## Code Quality

### TODO Policy

```python
# Correct - with Linear ticket
# TODO(OMN-1234): Add validation for edge case

# Wrong - missing ticket
# TODO: Fix this later
```

### Type Ignore Policy

```python
# Correct - specific code + explanation
# NOTE(OMN-1234): mypy false-positive due to Protocol-based DI.
value = container.get_service("ProtocolLogger")  # type: ignore[arg-type]

# Wrong - generic ignore
value = some_call()  # type: ignore
```

### Docstring Guidelines

- **Write** for: complex logic, non-obvious behavior, public APIs, edge cases
- **Skip** for: simple getters, obvious signatures, private helpers
- **Never tautological**: `def get_name: """Get the name."""` adds no value

### Enum vs Literal Policy

| Context | Use |
|---------|-----|
| **External contract surface** | Enums |
| **Internal parsing glue** | Literals allowed |
| **Cross-process boundaries** | Enums only |

### Thread Safety

Do NOT share node instances across threads without synchronization. Nodes are single-request scoped.

**See**: [Threading Guide](docs/guides/THREADING.md)

---

## Common Pitfalls

### Don't

1. **Skip base class initialization**
   ```python
   def __init__(self, container):
       pass  # WRONG - missing super().__init__(container)
   ```

2. **Confuse container types**
   ```python
   def __init__(self, container: ModelContainer):  # WRONG - use ModelONEXContainer
   ```

3. **Return result from ORCHESTRATOR**
   ```python
   return ModelHandlerOutput.for_orchestrator(result={"status": "done"})  # ValueError!
   ```

4. **Share nodes across threads**
   ```python
   threading.Thread(target=node.process).start()  # UNSAFE
   ```

### Do

1. Always call `super().__init__(container)` in node constructors
2. Use `ModelONEXContainer` for dependency injection
3. Use protocol names for DI: `container.get_service("ProtocolEventBus")`
4. Use `uv run` for all Python commands
5. Use thread-local instances for multi-threaded access

---

## Documentation

| Topic | Document |
|-------|----------|
| Documentation Index | `docs/INDEX.md` |
| Four-Node Architecture | `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md` |
| Execution Shapes | `docs/architecture/CANONICAL_EXECUTION_SHAPES.md` |
| Container Types | `docs/architecture/CONTAINER_TYPES.md` |
| Node Building Guide | `docs/guides/node-building/README.md` |
| Declarative Contracts | `docs/architecture/CONTRACT_SYSTEM.md` |
| Handler System | `docs/contracts/HANDLER_CONTRACT_GUIDE.md` |
| Claude Code Hooks | `docs/architecture/CLAUDE_CODE_HOOKS.md` |
| Mixins | `docs/architecture/MIXIN_ARCHITECTURE.md` |
| Migration Guide | `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` |
| Threading | `docs/guides/THREADING.md` |
| Error Handling | `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md` |
| ONEX Terminology | `docs/standards/onex_terminology.md` |

---

**Python**: 3.12+ | **Ready?** → [Node Building Guide](docs/guides/node-building/README.md)
