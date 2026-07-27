<!-- onex-allow-file-todo-marker reason="repository policy guide intentionally documents TODO marker examples" -->

# CLAUDE.md - Omnibase Core

> **Python**: 3.12+ | **Framework**: ONEX Core | **Package Manager**: uv | **Shared Standards**: See **`~/.claude/CLAUDE.md`** for shared development standards (Python, Git, testing, architecture principles) and infrastructure configuration (PostgreSQL, Kafka/Redpanda, Docker networking, environment variables).

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

## Agent Behavioral Rules

- Never disable pre-commit hooks, CI checks, or type checkers to make code pass. Fix the code instead.
- Never write state files to `~/.claude/` — use the workspace-local `.onex_state/` directory.

### Contract-first topic definitions

This repo defines the contract framework that all ONEX nodes use. Kafka topic
declarations belong in contract YAML files (`event_bus.publish_topics` /
`subscribe_topics`), not hardcoded in application code. Enforced by
`validation/validator_hardcoded_topics.py` plus the `demo-path-topic-coherence`
CI gate (`onex-demo-path-topic-gate`), and by
`validators/contract_config_compliance.py` (bare env reads, bus-bypass imports,
missing contract config; CI job `contract-config-compliance`).

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
`omnibase-compat` is the single exemption: compat is the shared substrate every
OmniNode repo is allowed to hard-depend on.

---

## Quick Reference

```bash
# Setup
uv sync --all-extras && pre-commit install

# Testing — PARALLEL BY DEFAULT: addopts pins -n4, --timeout=60, --reruns=2
uv run pytest tests/                    # All tests (4 xdist workers via addopts)
uv run pytest tests/ -n 0 -xvs          # Debug mode (disable parallelism)
uv run pytest tests/ --cov              # With coverage (fail_under=60 in pyproject)

# Code Quality
uv run mypy src/omnibase_core/          # Type checking (strict=true, 0 errors required)
uv run ruff check src/ tests/           # Linting
pre-commit run --all-files              # All hooks
```

**Test markers**: `--strict-markers` is on. Markers are registered in
`pyproject.toml` `[tool.pytest.ini_options] markers` plus `tests/conftest.py`
(`memory_intensive`, `isolated`) — read those two sources, not a hand-copied list.

**uv, not Poetry**: `uv sync --all-extras` / `uv run <command>` / `uv lock`. All
Python commands — including any spawned agent's — run via `uv run`, never bare
`python`/`pip`. Shared git/hook rules (`--no-verify` / `--no-gpg-sign`
prohibitions, no background commits) live in `~/.claude/CLAUDE.md`.

---

## Handler Output Constraints

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |

**Enforcement**: Pydantic validator at `ModelHandlerOutput` constructor + runtime validation + CI `node-purity-check` job.

### Runtime-synthesized terminal events

Synchronous-return handlers invoked via `RuntimeLocal._run_single_handler` receive
a **runtime-synthesized terminal event** after successful result classification.
The runtime publishes to the contract's declared `terminal_event` topic with
payload::

    {"status": "success" | "failure",
     "correlation_id": "<uuid>",
     "source": "runtime_local"}

The `source: "runtime_local"` field lets consumers distinguish runtime-synthesized
terminals from handler-published ones. FAILED results publish `status: "failure"`.
This applies **only** to the single-handler path; the event-driven path
(`_run_event_driven`) relies on handler-published terminals and must not
double-emit. Full rationale: `_publish_synthesized_terminal` docstring in
`src/omnibase_core/runtime/runtime_local.py`.

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
| ArtifactStore | `src/omnibase_core/artifacts/artifact_store.py` — content-addressed artifact storage |
| Dispatch Bus Client | `src/omnibase_core/dispatch/dispatch_bus_client.py` — typed dispatch surface over the event bus |
| Doctor Health Checks | `src/omnibase_core/doctor/` — extensible health-check registry; checks registered in `onex.doctor` entry-point group |
| In-Memory Event Bus | `src/omnibase_core/event_bus/event_bus_inmemory.py` — registered in `onex.backends` entry-point group |
| OmniGate | `src/omnibase_core/gate/` — config loader, diff hash, receipt canonical |

### File Naming Conventions

Every directory under `src/omnibase_core/` requires a file-name prefix
(`models/` → `model_*`, `enums/` → `enum_*`, `nodes/` → `node_*`, ...). The
enforced map is `DIRECTORY_PREFIX_RULES` in
`src/omnibase_core/validation/checker_naming_convention.py` (CI job
`naming-conventions`) — read it there; a hand-copied table here drifted.
Traps: the rule keys on the FIRST directory after `omnibase_core/`
(`models/cli/model_cli.py` follows the `models` rule, not `cli`), and several
directories accept multiple prefixes (e.g. `pipeline/`, `types/`, `errors/`,
`validation/`, `runtime/`). Always allowed: `__init__.py`, `conftest.py`,
`py.typed`, and `_`-prefixed private modules.

---

## Pydantic Model Standards

| Model Type | Required ConfigDict |
|------------|---------------------|
| **Immutable value** | `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` |
| **Mutable internal** | `ConfigDict(extra="forbid", from_attributes=True)` |
| **Contract/external** | `ConfigDict(extra="forbid", ...)` |

**`extra="forbid"` is mandatory on EVERY model** — `extra="ignore"` and `extra="allow"` are
default-deny. Declaring nothing is not neutral: Pydantic's default for an undeclared `extra`
is `"ignore"`, so a model with no `model_config` is *already* silently dropping unknown
fields. Multiple live silent-data-loss incidents came from exactly that. Inheriting `forbid`
from a base counts — do not redundantly redeclare it. If a model must tolerate unknown input,
add an explicit typed passthrough field; do not loosen `extra`. Enforced by
`omnibase_core.validators.pydantic_extra_forbid` as a CI gate (inside the required Quality
Gate) and a pre-commit hook; the only suppression is an expiring, ticket-and-PR-keyed waiver
in `extra_forbid_waivers.yaml`.

**`from_attributes=True`**: Required on frozen models for pytest-xdist compatibility.

**Mutable defaults**: ALWAYS use `default_factory` — e.g. `items: list[str] = Field(default_factory=list)`

### Plan Contract Enforcement Fields

`ModelPlanContract` carries plan-level enforcement metadata for the plan → epic → tickets → PR → dogfood chain. When adding a new plan, set `epic_id` (Linear epic identifier), `plan_phases`, `success_criteria` (via `ModelDoDItem`), and `halt_conditions` at the top level — not in `context`. The existing `phase: EnumPlanPhase` lifecycle field is distinct from `plan_phases: list[str]` and must not be confused.

**See**: [Pydantic Best Practices](docs/conventions/PYDANTIC_BEST_PRACTICES.md)

---

## Code Quality

- **TODO policy**: `# TODO(TICKET-ID): ...` — a TODO without a Linear ticket is blocked by the agent-left-marker pre-commit hook.
- **Type ignores**: specific code + reason — `# type: ignore[arg-type]` with a `NOTE(TICKET-ID):` explanation; never bare `# type: ignore`.
- **Enum vs Literal**: Enums on external contract surfaces and cross-process boundaries; Literals allowed only in internal parsing glue.
- **Thread safety**: Do NOT share node instances across threads — nodes are single-request scoped; use thread-local instances. See [Threading Guide](docs/guides/THREADING.md).

---

## Common Pitfalls

- Always call `super().__init__(container)` in node constructors — skipping base-class init breaks DI.
- Node `__init__` takes `ModelONEXContainer`, never `ModelContainer` (value wrapper).
- `ModelHandlerOutput.for_orchestrator(result=...)` raises — ORCHESTRATOR cannot return `result` (see Handler Output Constraints).
- Prefer type-based DI resolution (`container.get_service(ProtocolEventBus)`); string-based is the late-binding-plugin exception, not the default.
- Use `uv run` for all Python commands.

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

**Ready?** → [Node Building Guide](docs/guides/node-building/README.md)
