# CLAUDE.md - Omnibase Core

> **Python**: 3.12+ | **Framework**: ONEX Core | **Shared Standards**: See **`~/.claude/CLAUDE.md`** for shared development standards (Python, Poetry, Git, testing, architecture principles) and infrastructure configuration (PostgreSQL, Kafka/Redpanda, Docker networking, environment variables).

---

## Table of Contents

1. [Repo Invariants](#repo-invariants)
2. [Non-Goals](#non-goals)
3. [Quick Reference](#quick-reference)
4. [Python Development - Poetry](#python-development---poetry)
5. [Project Overview](#project-overview)
6. [Architecture: Four-Node Pattern](#architecture-four-node-pattern)
7. [Declarative Contracts](#declarative-contracts)
8. [Handler System](#handler-system)
9. [Data Flow Patterns](#data-flow-patterns)
10. [Claude Code Hooks](#claude-code-hooks)
11. [Dependency Injection](#dependency-injection)
12. [Error Handling](#error-handling)
13. [Mixins](#mixins)
14. [Project Structure](#project-structure)
15. [Pydantic Model Standards](#pydantic-model-standards)
16. [Thread Safety](#thread-safety)
17. [Testing & CI](#testing--ci)
18. [Code Quality](#code-quality)
19. [Common Pitfalls](#common-pitfalls)

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

## Non-Goals

We explicitly do **NOT** optimize for:

- **Backwards compatibility** - This repo has no external consumers. Schemas, APIs, and interfaces may change without deprecation periods. If something needs to change, change it. No `_deprecated` suffixes, no shims, no compatibility layers.
- **Convenience over correctness** - Contract violations fail loudly
- **Business logic in nodes** - Nodes coordinate; handlers compute
- **Dynamic runtime behavior** - All behavior must be contract-declared
- **Implicit state** - All state transitions are explicit and auditable
- **Tight coupling** - Protocol-based DI enforces loose coupling

---

## Quick Reference

```bash
# Setup
poetry install && pre-commit install

# Testing
poetry run pytest tests/                    # All tests (sequential by default)
poetry run pytest tests/ -n 4               # With 4 parallel workers
poetry run pytest tests/ -n 0 -xvs          # Debug mode (no parallelism)
poetry run pytest tests/ --cov              # With coverage (60% minimum required)

# Code Quality
poetry run mypy src/omnibase_core/          # Type checking (strict, 0 errors required)
poetry run ruff check src/ tests/           # Linting
pre-commit run --all-files                  # All hooks
```

---

## Python Development - Poetry

> **Shared rules** (Poetry usage, `--no-verify` prohibition, pre-commit hook policy) are in `~/.claude/CLAUDE.md`. Below are repo-specific additions only.

### Additional Git Commit Rules

- **NEVER use `--no-gpg-sign`** unless explicitly requested by the user.
- **NEVER run git commits in background mode** - always foreground.

### Agent Instructions

When spawning polymorphic agents or AI assistants:
- **ALWAYS** instruct them to use `poetry run` for Python commands
- **NEVER** allow direct pip or python execution
- **NEVER** run agents in background mode

---

## Project Overview

**omnibase_core** provides foundational building blocks for the ONEX framework:

- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR data flow
- **Protocol-Driven DI**: `container.get_service("ProtocolName")` resolution
- **Zero Boilerplate**: Base classes eliminate 80+ lines per node
- **Declarative Contracts**: YAML-driven FSM and workflow definitions
- **Structured Errors**: ModelOnexError with error codes and context

### Dependencies

- **Framework**: Pydantic 2.11+, FastAPI 0.120+
- **Testing**: pytest 8.4+, pytest-asyncio, pytest-xdist
- **Coverage**: 60% minimum (`fail_under = 60` in pyproject.toml)

---

## Architecture: Four-Node Pattern

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│ External I/O│    │  Transform  │    │  FSM State  │    │  Workflow   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Data Flow**: Unidirectional left-to-right. No backwards dependencies.

### Node Types

| Node | Purpose | Primary Output | Key Mixin |
|------|---------|----------------|-----------|
| **EFFECT** | External I/O (APIs, DB, files) | `events[]` | `MixinEffectExecution` |
| **COMPUTE** | Pure data transformation | `result` (required) | `MixinHandlerRouting` |
| **REDUCER** | FSM state management | `projections[]` | `MixinFSMExecution` |
| **ORCHESTRATOR** | Workflow coordination | `events[]`, `intents[]` | `MixinWorkflowExecution` |

### Import Path (v0.4.0+)

```python
from omnibase_core.nodes import (
    NodeCompute,       # Pure computation
    NodeEffect,        # External I/O
    NodeReducer,       # FSM-driven state
    NodeOrchestrator,  # Workflow coordination
)
```

**v0.4.0 Breaking Change**: `NodeReducerDeclarative` → `NodeReducer`, `NodeOrchestratorDeclarative` → `NodeOrchestrator`.

> **Terminology Reference**: For canonical definitions of ONEX concepts (Event, Intent, Action, Reducer, Orchestrator, Effect, Handler, Projection, Runtime), see [ONEX Terminology Guide](docs/standards/onex_terminology.md).

### Handler Output Constraints

| Node Kind | Allowed | Forbidden |
|-----------|---------|-----------|
| **ORCHESTRATOR** | `events[]`, `intents[]` | `projections[]`, `result` |
| **REDUCER** | `projections[]` | `events[]`, `intents[]`, `result` |
| **EFFECT** | `events[]` | `intents[]`, `projections[]`, `result` |
| **COMPUTE** | `result` (required) | `events[]`, `intents[]`, `projections[]` |

```python
# ✅ CORRECT - ORCHESTRATOR emits events/intents only
output = ModelHandlerOutput.for_orchestrator(
    input_envelope_id=envelope.envelope_id,
    correlation_id=envelope.correlation_id,
    handler_id="my-orchestrator",
    events=(event,),
    intents=(intent,),
)

# ❌ WRONG - ORCHESTRATOR cannot return typed results (raises ModelOnexError)
output = ModelHandlerOutput(
    input_envelope_id=uuid4(),
    correlation_id=uuid4(),
    handler_id="bad-orchestrator",
    node_kind=EnumNodeKind.ORCHESTRATOR,
    result={"status": "done"},  # CONTRACT_VIOLATION!
)
```

**Enforcement**:
- Output shape validated at `ModelHandlerOutput` constructor (Pydantic validator)
- Runtime validates again before emitting to event bus
- CI includes `node-purity-check` job that audits node implementations

---

## Declarative Contracts

### FSM Subcontract (REDUCER)

```yaml
state_transitions:
  version: { major: 1, minor: 0, patch: 0 }
  state_machine_name: metrics_aggregation_fsm
  initial_state: idle

  states:
    - state_name: idle
      entry_actions: []
    - state_name: collecting
      entry_actions: ["start_collection"]
    - state_name: completed
      is_terminal: true

  transitions:
    - from_state: idle
      to_state: collecting
      trigger: collect_metrics
      conditions:
        - expression: "data_sources min_length 1"
    - from_state: "*"  # Wildcard
      to_state: failed
      trigger: error_occurred

  terminal_states: [completed, failed]
```

**Pure FSM Pattern**: `delta(state, event) -> (new_state, intents[])`. No side effects—external operations emitted as intents.

### Workflow Definition (ORCHESTRATOR)

```yaml
workflow_coordination:
  workflow_definition:
    workflow_metadata:
      workflow_name: data_processing_pipeline
      execution_mode: parallel

    execution_graph:
      nodes:
        - node_id: "fetch_data"
          node_type: effect
        - node_id: "validate_schema"
          node_type: compute
          depends_on: [fetch_data]
        - node_id: "persist_results"
          node_type: effect
          depends_on: [validate_schema]

    coordination_rules:
      parallel_execution_allowed: true
      failure_recovery_strategy: retry
      max_retries: 3
```

### Handler Routing Subcontract

```yaml
handler_routing:
  version: { major: 1, minor: 0, patch: 0 }
  routing_strategy: payload_type_match  # or operation_match, topic_pattern
  handlers:
    - routing_key: UserCreatedEvent
      handler_key: handle_user_created
      priority: 0
  default_handler: handle_unknown
```

---

## Handler System

### Two Handler Protocols

| Protocol | Purpose | Input/Output |
|----------|---------|--------------|
| `ProtocolHandler` | Envelope-based (runtime) | `ModelOnexEnvelope` → `ModelOnexEnvelope` |
| `ProtocolMessageHandler` | Category-based (dispatch) | `ModelEventEnvelope` → `ModelHandlerOutput` |

### ProtocolMessageHandler

```python
@runtime_checkable
class ProtocolMessageHandler(Protocol):
    @property
    def handler_id(self) -> str: ...

    @property
    def category(self) -> EnumMessageCategory: ...  # EVENT, COMMAND, INTENT

    @property
    def node_kind(self) -> EnumNodeKind: ...

    async def handle(self, envelope: ModelEventEnvelope[Any]) -> ModelHandlerOutput[Any]: ...
```

### Handler Registration

```python
# ServiceHandlerRegistry - thread-safe with "freeze after init" pattern
registry = ServiceHandlerRegistry()
registry.register_handler(my_handler, message_types={"UserCreated"})
registry.freeze()  # Lock for thread-safe reads

# Execution shape validation at registration:
# EVENT -> REDUCER ✅    COMMAND -> ORCHESTRATOR ✅    INTENT -> EFFECT ✅
# EVENT -> ORCHESTRATOR ✅    COMMAND -> EFFECT ✅
```

### Handler Routing via Mixin

```python
class NodeMyOrchestrator(NodeOrchestrator, MixinHandlerRouting):
    def __init__(self, container: ModelONEXContainer, contract: ModelContract):
        super().__init__(container)
        registry = container.get_service("ProtocolHandlerRegistry")
        self._init_handler_routing(contract.handler_routing, registry)

    async def process(self, input_data):
        handlers = self.route_to_handlers(
            routing_key="UserCreatedEvent",
            category=EnumMessageCategory.EVENT
        )
        for handler in handlers:
            result = await handler.handle(envelope)
```

---

## Data Flow Patterns

### Canonical Execution Shapes

| Shape | Pattern | Purpose |
|-------|---------|---------|
| `EVENT_TO_REDUCER` | Event → Reducer | State aggregation |
| `EVENT_TO_ORCHESTRATOR` | Event → Orchestrator | Workflow trigger |
| `INTENT_TO_EFFECT` | Intent → Effect | External action execution |
| `COMMAND_TO_ORCHESTRATOR` | Command → Orchestrator | Workflow execution |
| `COMMAND_TO_EFFECT` | Command → Effect | Direct execution |

**Forbidden Patterns**:
- Command → Reducer (bypasses orchestration)
- Reducer → I/O (violates purity)
- Orchestrator → Typed Result (only COMPUTE returns results)

### Event Envelope

```python
class ModelEventEnvelope[T](BaseModel):
    payload: T                    # Wrapped event
    envelope_id: UUID             # Auto-generated
    correlation_id: UUID | None   # Request tracing
    priority: int                 # 1-10
    trace_id: UUID | None         # OpenTelemetry compatible

    def infer_category(self) -> EnumMessageCategory:
        """Returns EVENT, COMMAND, or INTENT based on payload type."""
```

### ModelIntent (Reducer → Effect)

```python
class ModelIntent(BaseModel):
    intent_id: UUID
    intent_type: str        # Routing type (e.g., "log_event")
    target: str             # Target service
    payload: ProtocolIntentPayload  # Typed payload
    priority: int
    lease_id: UUID | None   # For leased workflows
```

**Typed Payloads**: `ModelPayloadLogEvent`, `ModelPayloadPersistState`, `ModelPayloadEmitEvent`, `ModelPayloadHTTP`, `ModelPayloadNotify`.

### ModelAction (Orchestrator → Effect)

```python
class ModelAction(BaseModel):
    action_id: UUID
    action_type: EnumActionType
    target_node_type: str
    payload: ProtocolActionPayload
    dependencies: list[UUID]    # Action dependencies

    # Single-writer semantics
    lease_id: UUID              # Orchestrator ownership
    epoch: int                  # Monotonic version
```

---

## Claude Code Hooks

> **Why in core?** These hook models are part of the shared contract surface used by multiple repos (omniclaude, omniarchon, etc.). They define the canonical event types for Claude Code integration.

### Hook Event Types

| Event | Purpose | Category |
|-------|---------|----------|
| `SESSION_START` | Session initialization | Lifecycle |
| `USER_PROMPT_SUBMIT` | Prompt submission | Lifecycle |
| `PRE_TOOL_USE` | Before tool execution | Agentic Loop |
| `POST_TOOL_USE` | After tool execution | Agentic Loop |
| `SUBAGENT_START/STOP` | Subagent lifecycle | Agentic Loop |
| `STOP` | Session stopping | Lifecycle |

### Hook Event Model

```python
class ModelClaudeCodeHookEvent(BaseModel):
    event_type: EnumClaudeCodeHookEventType
    session_id: str
    correlation_id: UUID | None
    timestamp_utc: datetime  # Must be timezone-aware
    payload: ModelClaudeCodeHookEventPayload
```

**Lifecycle Flow**:
```
SessionStart → UserPromptSubmit → [PreToolUse → PostToolUse]* → Stop → SessionEnd
```

---

## Dependency Injection

### Resolution Style Policy

| Style | When to Use | Example |
|-------|-------------|---------|
| **Type-based** (preferred) | Static dependencies, compile-time safety | `container.get_service(ProtocolLogger)` |
| **String-based** | Late-binding plugins, dynamic resolution | `container.get_service("ProtocolLogger")` |
| **Forbidden** | Mixing styles within the same module | — |

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# ✅ PREFERRED - Type-based resolution (compile-time safety)
service = await container.get_service_async(ProtocolLogger)
service = container.get_service(ProtocolLogger)

# ✅ ALLOWED - String-based for late-binding plugins
service = container.get_service("ProtocolLogger")

# ✅ Optional resolution (returns None if not found)
service = container.get_service_optional(ProtocolLogger)
```

### Container Types (CRITICAL)

| Type | Purpose | In Node `__init__` |
|------|---------|-------------------|
| `ModelContainer[T]` | Value wrapper | ❌ NEVER |
| `ModelONEXContainer` | Dependency injection | ✅ ALWAYS |

```python
# ✅ CORRECT
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyService(NodeCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY
        self.logger = container.get_service("ProtocolLogger")
```

---

## Error Handling

### ValueError vs ModelOnexError

| Use Case | Exception Type |
|----------|---------------|
| Standard Python validation at function boundaries | `ValueError` |
| Simple type/value validation | `ValueError` |
| Pydantic model validators | `ValueError` |
| ONEX-specific errors needing error codes | `ModelOnexError` |
| Errors that will be serialized/logged | `ModelOnexError` |
| Errors in node/workflow execution | `ModelOnexError` |

### ModelOnexError

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

raise ModelOnexError(
    message="Contract validation failed",
    error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR,
    context={"contract_id": contract_id, "field": "version"},
)
```

### Error Decorators

```python
from omnibase_core.decorators.decorator_error_handling import (
    standard_error_handling,
    validation_error_handling,
    io_error_handling,
)

@standard_error_handling("Contract processing")
def process_contract(self, data):
    return validate_and_transform(data)  # No try/catch needed

@io_error_handling("Config file reading")
def read_config(self, path):
    with open(path) as f:
        return yaml.safe_load(f)  # FileNotFoundError → FILE_NOT_FOUND code
```

**Decorator Contract**:
- Cancellation signals (`SystemExit`, `KeyboardInterrupt`, `asyncio.CancelledError`) always propagate
- `ModelOnexError` re-raised as-is
- Other exceptions wrapped in `ModelOnexError`

### Async Error Handling

Decorators **auto-detect async functions**:

```python
@standard_error_handling("Async data fetch")
async def fetch_data(self, url: str) -> dict:
    async with httpx.AsyncClient() as client:
        return await client.get(url).json()

@io_error_handling("Async file operation")
async def read_config_async(self, file_path: Path) -> dict:
    async with aiofiles.open(file_path) as f:
        content = await f.read()
        return yaml.safe_load(content)
```

**Critical**: `asyncio.CancelledError` must be caught separately and always re-raised:

```python
try:
    await async_operation()
except asyncio.CancelledError:
    await self._cleanup_resources()
    raise  # ALWAYS re-raise!
except ASYNC_ERRORS as e:
    # Handle other async errors
    pass
```

### Exception Groups

```python
from omnibase_core.errors.exception_groups import (
    VALIDATION_ERRORS,       # TypeError, ValidationError, ValueError
    PYDANTIC_MODEL_ERRORS,   # + AttributeError
    ATTRIBUTE_ACCESS_ERRORS, # AttributeError, IndexError, KeyError, TypeError
    FILE_IO_ERRORS,          # FileNotFoundError, IOError, OSError, PermissionError
    NETWORK_ERRORS,          # ConnectionError, OSError, TimeoutError
    ASYNC_ERRORS,            # asyncio.TimeoutError, RuntimeError
    YAML_PARSING_ERRORS,     # ValidationError, ValueError, yaml.YAMLError
    JSON_PARSING_ERRORS,     # json.JSONDecodeError, TypeError, ValidationError, ValueError
)

try:
    data = read_file(path)
except FILE_IO_ERRORS as e:
    # fallback-ok: use empty data if file unavailable
    data = {}
```

**Comment Markers**:
- `# fallback-ok:` - Graceful degradation
- `# boundary-ok:` - API boundaries
- `# cleanup-resilience-ok:` - Cleanup must complete

---

## Mixins

### Available Mixins

| Mixin | Purpose | Used By |
|-------|---------|---------|
| `MixinHandlerRouting` | Contract-driven handler routing | COMPUTE, EFFECT, ORCHESTRATOR |
| `MixinFSMExecution` | Pure FSM state transitions | REDUCER |
| `MixinEffectExecution` | External I/O coordination | EFFECT |
| `MixinWorkflowExecution` | DAG-based workflow execution | ORCHESTRATOR |
| `MixinEventHandler` | Event handling for introspection | All nodes |
| `MixinEventBus` | Thread-safe event bus publishing | Services |
| `MixinEventListener` | Event subscription management | Services |
| `MixinDiscoveryResponder` | Discovery protocol responses | Services |
| `MixinNodeLifecycle` | Node lifecycle management | All nodes |
| `MixinNodeExecutor` | Node execution orchestration | Runtime |

### Mixin Usage Pattern

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCompute, MixinDiscoveryResponder):
    """Node with discovery capabilities."""
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.logger = container.get_service("ProtocolLogger")
        self.event_bus = container.get_service("ProtocolEventBus")
```

---

## Node Classification Enums

### EnumNodeKind (Architectural Role)

```python
from omnibase_core.enums import EnumNodeKind

# 5 values: EFFECT, COMPUTE, REDUCER, ORCHESTRATOR, RUNTIME_HOST
```

### EnumNodeType (Implementation Type)

```python
from omnibase_core.enums import EnumNodeType

# Many values mapping to NodeKind:
EnumNodeType.TRANSFORMER     → EnumNodeKind.COMPUTE
EnumNodeType.AGGREGATOR      → EnumNodeKind.COMPUTE
EnumNodeType.TOOL            → EnumNodeKind.EFFECT
EnumNodeType.AGENT           → EnumNodeKind.EFFECT
EnumNodeType.GATEWAY         → EnumNodeKind.ORCHESTRATOR
EnumNodeType.WORKFLOW        → EnumNodeKind.ORCHESTRATOR

# Get kind from type
kind = EnumNodeType.get_node_kind(EnumNodeType.TRANSFORMER)  # → COMPUTE
```

---

## Project Structure

```
src/omnibase_core/
├── nodes/           # Node implementations (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)
├── models/          # Pydantic models
├── protocols/       # Protocol interfaces
├── mixins/          # Reusable behavior mixins
├── enums/           # Core enumerations
├── errors/          # Error handling and exception groups
├── decorators/      # Utility decorators
├── validation/      # Validation framework
├── container/       # DI container implementation
├── runtime/         # File registry and handlers
└── services/        # Service implementations
```

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

### ConfigDict Requirements

| Model Type | Required ConfigDict |
|------------|---------------------|
| **Immutable value** | `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` |
| **Mutable internal** | `ConfigDict(extra="forbid", from_attributes=True)` |
| **Contract/external** | `ConfigDict(extra="ignore", ...)` |

```python
class ModelSemVer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    major: int = Field(ge=0)
    minor: int = Field(ge=0)
    patch: int = Field(ge=0)
```

**`from_attributes=True`**: Required on frozen models for pytest-xdist compatibility. Workers import classes independently, and without this setting Pydantic rejects valid instances due to class identity differences.

### Field Patterns

```python
# Simple default - no Field() needed
field_name: str | None = None

# Field() justified by metadata
field_name: str = Field(default="value", description="Helpful description")
field_name: int = Field(ge=0, le=100)

# Mutable defaults - ALWAYS use default_factory
items: list[str] = Field(default_factory=list)
```

---

## Thread Safety

| Component | Thread-Safe? | Mitigation |
|-----------|-------------|------------|
| `NodeCompute` | No | Thread-local instances |
| `NodeEffect` | No | Thread-local instances |
| `NodeReducer` | No | Thread-local instances |
| `NodeOrchestrator` | No | Thread-local instances |
| `ModelComputeCache` | No | Wrap with `threading.Lock` |
| `ModelONEXContainer` | Yes | Read-only after init |
| Frozen Pydantic Models | Yes | Immutable (see ConfigDict requirements) |
| Mutable Pydantic Models | No | Not guaranteed thread-safe |

**Critical Rule**: Do NOT share node instances across threads without synchronization.

### Node Lifecycle Ownership

Node instances are **single-request scoped** by the runtime:
- The runtime instantiates nodes per task/request
- Nodes must NOT retain request state after `process()` returns
- For concurrent access, use thread-local storage or instantiate per-thread

---

## Testing & CI

### Test Markers

```python
# Shared markers (unit, integration, slow) are in ~/.claude/CLAUDE.md
# Repo-specific markers:
@pytest.mark.performance       # Performance tests
@pytest.mark.memory_intensive  # Memory-heavy tests
@pytest.mark.isolated          # Requires fresh module state
```

### Running Tests

```bash
poetry run pytest tests/                    # All tests (sequential by default)
poetry run pytest tests/ -n 4               # With 4 parallel workers
poetry run pytest tests/unit/               # Unit tests only
poetry run pytest tests/ -n 0 -xvs          # Debug mode (no parallelism)
poetry run pytest tests/ --cov              # With coverage
poetry run pytest tests/ --timeout=60       # With timeout protection
```

### CI Overview

CI uses parallel test splits on GitHub Actions. Check the PR for current status.

**CI Phases**:

| Phase | Jobs | Purpose |
|-------|------|---------|
| **Phase 1** | lint, pyright, exports-validation, docs-validation, node-purity-check, enum-governance | Quick validation |
| **Phase 2** | test-parallel | Full test suite |
| **Phase 3** | test-summary | Aggregation |

**Coverage Requirement**: 60% minimum

---

## Code Quality

### Type Checking

```bash
poetry run mypy src/omnibase_core/    # Strict mode (0 errors required)
poetry run pyright src/omnibase_core/ # Basic mode (complementary)
```

### TODO Policy

```python
# ✅ Correct - with Linear ticket
# TODO(OMN-1234): Add validation for edge case

# ❌ Wrong - missing ticket
# TODO: Fix this later
```

### Type Ignore Policy

```python
# ✅ Correct - specific code + explanation
# NOTE(OMN-1234): mypy false-positive due to Protocol-based DI.
value = container.get_service("ProtocolLogger")  # type: ignore[arg-type]

# ❌ Wrong - generic ignore
value = some_call()  # type: ignore
```

### Docstring Guidelines

**Avoid tautological docstrings** that just restate the method name:

```python
# ❌ BAD - These add no value
def get_name(self):
    """Get the name."""  # Just restates method name

def validate_input(self):
    """Validate input."""  # No new information

# ✅ GOOD - These add value
def get_name(self) -> str:
    """Return canonical name, falling back to id if name is None."""

def validate_input(self) -> bool:
    """Validate against schema v2 rules. Raises ValidationError if malformed."""
```

**When to write docstrings**:
- Complex logic, algorithms, state machines
- Non-obvious behavior, side effects, caching
- Public APIs
- Edge cases and error conditions

**When NOT to write docstrings**:
- Simple getter/setter methods
- Obvious from signature (`def add(a: int, b: int) -> int`)
- Private helpers

### Enum vs Literal Policy

| Context | Use | Example |
|---------|-----|---------|
| **External contract surface** | Enums | `EnumNodeKind.COMPUTE` |
| **Internal parsing glue** | Literals allowed | `Literal["compute", "effect"]` |
| **Cross-process boundaries** | Enums only | Never use Literal for serialized values |

```python
# ✅ External API - use Enum
def process_node(kind: EnumNodeKind) -> None: ...

# ✅ Internal YAML parsing helper - Literal OK
RawNodeKind = Literal["compute", "effect", "reducer", "orchestrator"]
def _parse_kind(raw: RawNodeKind) -> EnumNodeKind: ...

# ❌ WRONG - Literal in serialized model field
class BadModel(BaseModel):
    kind: Literal["compute", "effect"]  # Use EnumNodeKind instead
```

---

## Common Pitfalls

### ❌ Don't

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

### ✅ Do

1. Always call `super().__init__(container)` in node constructors
2. Use `ModelONEXContainer` for dependency injection
3. Use protocol names for DI: `container.get_service("ProtocolEventBus")`
4. Use `poetry run` for all Python commands
5. Use thread-local instances for multi-threaded access

---

## Documentation

| Topic | Document |
|-------|----------|
| Four-Node Architecture | `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md` |
| Execution Shapes | `docs/architecture/CANONICAL_EXECUTION_SHAPES.md` |
| Container Types | `docs/architecture/CONTAINER_TYPES.md` |
| Node Building Guide | `docs/guides/node-building/README.md` |
| Migration Guide | `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` |
| Threading | `docs/guides/THREADING.md` |
| Error Handling | `docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md` |

---

## Recent Updates

### v0.4.0 - Node Architecture Overhaul

- **NodeReducer and NodeOrchestrator are now PRIMARY** (FSM/workflow-driven)
- **"Declarative" suffix removed** - `NodeReducerDeclarative` → `NodeReducer`
- **Unified import path** - All nodes: `from omnibase_core.nodes import ...`
- **Handler output constraints** enforced at model level (Option A Semantic Model)

### Key Files

| Purpose | Location |
|---------|----------|
| Node implementations | `src/omnibase_core/nodes/` |
| Handler output model | `src/omnibase_core/models/dispatch/model_handler_output.py` |
| FSM subcontract | `src/omnibase_core/models/contracts/subcontracts/model_fsm_subcontract.py` |
| Workflow definition | `src/omnibase_core/models/contracts/subcontracts/model_workflow_definition.py` |
| Event envelope | `src/omnibase_core/models/events/model_event_envelope.py` |
| Error handling | `src/omnibase_core/decorators/decorator_error_handling.py` |
| Exception groups | `src/omnibase_core/errors/exception_groups.py` |

---

**Python**: 3.12+ | **Ready?** → [Node Building Guide](docs/guides/node-building/README.md)
