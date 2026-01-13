# CLAUDE.md - Omnibase Core Project Instructions

> **Version**: 0.6.4 | **Python**: 3.12+ | **Framework**: ONEX Core | **Shared Infrastructure**: See **`~/.claude/CLAUDE.md`** for common OmniNode infrastructure (PostgreSQL, Kafka/Redpanda, Docker networking, environment variables).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Python Development - Poetry](#python-development---always-use-poetry)
3. [Architecture Fundamentals](#architecture-fundamentals)
4. [Project Structure](#project-structure)
5. [Development Workflow](#development-workflow)
6. [Testing Guide](#testing-guide)
7. [CI Performance Benchmarks](#ci-performance-benchmarks)
8. [Code Quality](#code-quality)
9. [Key Patterns & Conventions](#key-patterns--conventions)
10. [Code Hygiene Policies](#code-hygiene-policies)
11. [Thread Safety](#thread-safety)
12. [Documentation](#documentation)
13. [Common Pitfalls](#common-pitfalls)

---

## Project Overview

**omnibase_core** provides the foundational building blocks for the ONEX framework:

- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Protocol-Driven DI**: Container-based dependency injection with `container.get_service("ProtocolName")`
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per node
- **Structured Errors**: ModelOnexError with Pydantic models for consistent error handling
- **Event-Driven**: ModelEventEnvelope for inter-service communication
- **Comprehensive Testing**: 12,000+ tests with 60%+ coverage requirement
- **Strict Type Checking**: 100% mypy strict mode compliance (0 errors across 1865 source files)

### Dependencies

- **Framework**: Pydantic 2.11+, FastAPI 0.120+
- **Testing**: pytest 8.4+, pytest-asyncio, pytest-xdist, pytest-split, pytest-cov

---

## Python Development - ALWAYS USE POETRY

**CRITICAL**: This project uses Poetry for all Python package management and task execution.

### Required Patterns

```bash
# ✅ CORRECT - Always use Poetry:
poetry run pytest tests/unit/
poetry run mypy src/omnibase_core/
poetry run python -m module.name
poetry install
poetry add package-name

# ❌ WRONG - Never use pip or python directly:
python -m pip install -e .          # NEVER
pip install package                 # NEVER
python -m pytest tests/             # NEVER
```

### Why Poetry?

1. **Dependency Isolation**: Poetry manages virtualenvs automatically
2. **Lock File**: Ensures reproducible builds across environments
3. **ONEX Standards**: Poetry is the mandated tool for all ONEX projects

### Agent Instructions

When spawning polymorphic agents or AI assistants:
- **ALWAYS** instruct them to use `poetry run` for Python commands
- **NEVER** allow direct pip or python execution
- **NEVER** run `git commit` or `git push` in background mode - always foreground
- **NEVER** run agents in background mode (`run_in_background: true`) - run parallel polymorphic agents in the foreground instead by dispatching multiple agents in a single message

### Git Commit Rules

⚠️ **CRITICAL - ABSOLUTELY FORBIDDEN**:
- **NEVER use `--no-verify`** when committing. Pre-commit hooks exist for a reason.
- **NEVER use `--no-gpg-sign`** unless explicitly requested by the user.
- **NEVER skip hooks** - if hooks fail, fix the issues instead of bypassing them.

---

## Architecture Fundamentals

### ONEX Four-Node Architecture

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│   (Input)   │    │ (Process)   │    │(Aggregate)  │    │(Coordinate) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Data Flow**: Unidirectional left-to-right, no backwards dependencies.

| Node Type | Purpose | Import |
|-----------|---------|--------|
| **EFFECT** | External interactions (I/O) | `from omnibase_core.nodes import NodeEffect` |
| **COMPUTE** | Data processing & transformation | `from omnibase_core.nodes import NodeCompute` |
| **REDUCER** | State aggregation (FSM-driven) | `from omnibase_core.nodes import NodeReducer` |
| **ORCHESTRATOR** | Workflow coordination | `from omnibase_core.nodes import NodeOrchestrator` |

**v0.4.0**: `NodeReducer` and `NodeOrchestrator` are now the PRIMARY implementations. All nodes use declarative YAML contracts.

> **Terminology Reference**: For canonical definitions of ONEX concepts (Event, Intent, Action, Reducer, Orchestrator, Effect, Handler, Projection, Runtime), see [ONEX Terminology Guide](docs/standards/onex_terminology.md).

**⚠️ CRITICAL: ORCHESTRATOR Result Constraint**

ORCHESTRATOR nodes **CANNOT return typed results** - they can only emit **events** and **intents**. Only COMPUTE nodes return typed results. This enforces clear separation between coordination (ORCHESTRATOR) and transformation (COMPUTE).

```python
# ✅ CORRECT
return ModelHandlerOutput[None](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    events=[...], intents=[...], result=None
)

# ❌ WRONG - Raises ValueError
return ModelHandlerOutput[dict](
    node_kind=EnumNodeKind.ORCHESTRATOR,
    result={"status": "done"}  # ERROR!
)
```

See [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md#4-orchestrator-node) for details.

### Protocol-Driven Dependency Injection

```python
# Get services by protocol interface (never by concrete class)
event_bus = container.get_service("ProtocolEventBus")
logger = container.get_service("ProtocolLogger")
```

**Key Principles**: Use protocol names (not concrete classes), duck typing (no isinstance checks), pure protocol-based resolution.

### Contract Loading with FileRegistry

```python
from omnibase_core.runtime.runtime_file_registry import FileRegistry
from pathlib import Path

registry = FileRegistry()
contract = registry.load(Path("config/runtime_host.yaml"))
contracts = registry.load_all(Path("config/contracts/"))
```

**Error Codes**: `FILE_NOT_FOUND`, `FILE_READ_ERROR`, `CONFIGURATION_PARSE_ERROR`, `CONTRACT_VALIDATION_ERROR`, `DUPLICATE_REGISTRATION`, `DIRECTORY_NOT_FOUND`

**Thread Safety**: FileRegistry instances are stateless and thread-safe.

### Base Classes Usage

```python
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate
        self.logger = container.get_service("ProtocolLogger")
```

**CRITICAL**: Always call `super().__init__(container)` - this eliminates 80+ lines of boilerplate.

**Migration Guide**: See `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md` for pre-v0.4.0 migration.

### Advanced Patterns (v0.4.0+)

- **ModelIntent Pattern** (REDUCER): Pure FSM transitions, intent-based state machines
- **ModelAction Pattern** (ORCHESTRATOR): Lease-based single-writer semantics, workflow-driven actions

**See**: [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

**Execution Shapes**: For allowed/forbidden data flow patterns (e.g., Event→Reducer, Intent→Effect), see [Canonical Execution Shapes](docs/architecture/CANONICAL_EXECUTION_SHAPES.md).

### Container Types: CRITICAL DISTINCTION

⚠️ **IMPORTANT**: omnibase_core has TWO different container types that are NOT interchangeable!

| Feature | ModelContainer[T] | ModelONEXContainer |
|---------|-------------------|-------------------|
| **Purpose** | Value wrapper | Dependency injection |
| **In Node `__init__`** | ❌ NEVER | ✅ ALWAYS |
| **Service Resolution** | ❌ No | ✅ Yes (`get_service()`) |
| **Location** | `omnibase_core.models.core.model_container` | `omnibase_core.models.container.model_onex_container` |

**See**: [docs/architecture/CONTAINER_TYPES.md](docs/architecture/CONTAINER_TYPES.md)

### Node Classification Enums

⚠️ **IMPORTANT**: Two node classification enums with different purposes!

| Enum | Purpose | Values |
|------|---------|--------|
| **EnumNodeKind** | Architectural role (pipeline routing) | `EFFECT`, `COMPUTE`, `REDUCER`, `ORCHESTRATOR`, `RUNTIME_HOST` |
| **EnumNodeType** | Implementation type (discovery/matching) | `COMPUTE_GENERIC`, `TRANSFORMER`, `AGGREGATOR`, `GATEWAY`, `VALIDATOR`, etc. |

**Relationship**: Multiple `EnumNodeType` values map to each `EnumNodeKind`.

**See**: [docs/guides/ENUM_NODE_KIND_MIGRATION.md](docs/guides/ENUM_NODE_KIND_MIGRATION.md)

---

## Project Structure

```text
omnibase_core/
├── src/omnibase_core/          # Source code
│   ├── constants/              # Project constants
│   ├── container/              # DI container implementation
│   ├── decorators/             # Utility decorators (@standard_error_handling)
│   ├── discovery/              # Service discovery mechanisms
│   ├── enums/                  # Core enumerations
│   ├── errors/                 # Error handling
│   ├── events/                 # Event system
│   ├── infrastructure/         # Base node classes
│   ├── mixins/                 # Reusable behavior mixins
│   ├── models/                 # Pydantic models (base, cli, common, configuration,
│   │                           # connections, container, contracts, core, dedup,
│   │                           # detection, discovery, docker, endpoints, errors,
│   │                           # event_bus, events, examples, fsm, graph, health,
│   │                           # infrastructure, logging, metadata, mixins,
│   │                           # node_metadata, nodes, operations, orchestrator,
│   │                           # primitives, projection, registry, results, security,
│   │                           # service, state, tools, types, utils, validation, workflow)
│   ├── nodes/                  # Node implementations (v0.4.0+)
│   ├── primitives/             # Primitive types
│   ├── types/                  # Type definitions
│   ├── utils/                  # Utility functions
│   └── validation/             # Validation framework
├── tests/                      # Test suite (unit/, integration/, fixtures/)
├── docs/                       # Documentation
└── scripts/                    # Build and validation scripts
```

---

## Development Workflow

### Initial Setup

```bash
git clone https://github.com/OmniNode-ai/omnibase_core.git && cd omnibase_core
poetry install
pre-commit install
poetry run pytest tests/ -x && poetry run mypy src/omnibase_core/
```

### Development Cycle

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following architecture patterns
3. Run tests: `poetry run pytest tests/`
4. Check types: `poetry run mypy src/omnibase_core/`
5. Format: `poetry run black src/ tests/ && poetry run isort src/ tests/`
6. Pre-commit: `pre-commit run --all-files`
7. Commit (conventional commits) and push

---

## Testing Guide

### Test Categories

- **Unit Tests**: 12,000+ tests in `tests/unit/`
- **Integration Tests**: `tests/integration/`
- **Coverage Requirement**: Minimum 60%

### Running Tests

```bash
poetry run pytest tests/                              # All tests (4 parallel workers)
poetry run pytest tests/unit/                        # Unit tests only
poetry run pytest tests/ -n 0 -xvs                   # Debug mode (no parallelism)
poetry run pytest tests/ --cov=src/omnibase_core     # With coverage
poetry run pytest tests/ --timeout=60                # With timeout protection
```

### Parallel Testing

- **Local**: `-n4` (4 workers), 60s timeout, `loadscope` distribution
- **CI**: 20 parallel splits across isolated runners. See `.github/workflows/test.yml`

### Test Markers

```python
@pytest.mark.unit         # Unit test
@pytest.mark.integration  # Integration test
@pytest.mark.slow         # Slow test (>1s)
@pytest.mark.smoke        # Smoke test
@pytest.mark.performance  # Performance test
```

---

## CI Performance Benchmarks

**Configuration**: 20 parallel splits on GitHub Actions

| Metric | Value |
|--------|-------|
| **Average Runtime** | ~3 minutes per split |
| **Expected Range** | 2m30s - 3m30s |
| **Warning Threshold** | > 3m30s |
| **Critical Threshold** | > 4m30s |

### Performance Thresholds

| Threshold | Duration | Action |
|-----------|----------|--------|
| **Normal** | 2m30s - 3m30s | No action needed |
| **Warning** | 3m30s - 4m30s | Review for slow tests |
| **Critical** | > 4m30s | Investigate immediately |

### Investigating Slow Splits

```bash
# View tests in a specific split
poetry run pytest --collect-only --splits=20 --group=<N>

# Profile slow tests
poetry run pytest --durations=10 --splits=20 --group=<N>
```

**Common Causes**: Test hangs (missing timeout), resource exhaustion, slow fixtures, network-dependent tests.

**See**: [CI Monitoring Guide](docs/ci/CI_MONITORING_GUIDE.md) for comprehensive operational procedures.

---

## Code Quality

### Type Checking

Both mypy AND pyright must pass in CI.

```bash
poetry run mypy src/omnibase_core/       # Strict mode (0 errors required)
poetry run pyright src/omnibase_core/    # Basic mode
```

**Configuration**: `[tool.mypy]` in pyproject.toml, `pyrightconfig.json` at repo root.

### Formatting & Linting

```bash
poetry run black src/ tests/             # Format
poetry run isort src/ tests/             # Sort imports
poetry run ruff check src/ tests/        # Lint
poetry run ruff check --fix src/ tests/  # Auto-fix
pre-commit run --all-files               # Run all hooks
```

### Docstring Guidelines

Follow these guidelines to avoid "AI slop" - docstrings that add noise without value.

#### Docstrings to AVOID (Tautological)

Do NOT write docstrings that simply restate the method name:

```python
# BAD - These add no value
def get_name(self):
    """Get the name."""  # Just restates method name

def set_status(self, value):
    """Set the status."""  # Obvious from signature

def validate_input(self):
    """Validate input."""  # No new information

def is_active(self) -> bool:
    """Check if active."""  # Obvious from name and return type
```

#### Docstrings to WRITE (Valuable)

Write docstrings that explain WHY, describe non-obvious behavior, or document edge cases:

```python
# GOOD - These add value
def get_name(self) -> str:
    """Return canonical name, falling back to id if name is None."""

def set_status(self, value: str) -> None:
    """Update status and emit StatusChanged event to all subscribers."""

def validate_input(self) -> bool:
    """
    Validate against schema v2 rules.

    Raises:
        ValidationError: If required fields are missing or malformed.
    """

def is_active(self) -> bool:
    """Check activation considering both enabled flag and expiry timestamp."""
```

#### When to Write Docstrings

| Situation | Docstring Needed? | Example |
|-----------|-------------------|---------|
| Complex logic | Yes | Algorithms, state machines, multi-step processes |
| Non-obvious behavior | Yes | Side effects, event emission, caching |
| Public API | Yes | Module/class/function interfaces |
| Edge cases | Yes | Error conditions, boundary values |
| Simple getter/setter | No | `get_id()`, `set_name()` |
| Obvious from signature | No | `def add(a: int, b: int) -> int` |
| Private helpers | Usually no | `_parse_line()`, `_normalize()` |

#### Module and Class Docstrings

Keep module docstrings concise (3-6 lines max for simple modules):

```python
# GOOD - Concise module docstring
"""Enumeration for node execution status.

Defines lifecycle states for node execution from pending to completed.
"""

# BAD - Verbose module docstring (avoid)
"""
Enumeration for node execution status.

This module provides a comprehensive enumeration of all possible
execution states that a node can be in during its lifecycle...
[18 more lines of obvious information]
"""
```

### Type Annotation Style (PEP 604)

**Always use PEP 604 union syntax** (enforced by ruff UP007):

```python
# ✅ Correct
def process(value: str | None) -> int | str: ...

# ❌ Wrong - Legacy syntax
def process(value: Optional[str]) -> Union[int, str]: ...  # Don't use
```

### `from __future__ import annotations` Policy

**Use when**: Forward references needed, circular import prevention.

**Do NOT use when**: Runtime type introspection needed (Pydantic models, FastAPI endpoints).

**Project Convention**: Pydantic models generally do NOT need it (Pydantic handles forward refs via `model_rebuild()`).

---

## Key Patterns & Conventions

### Error Handling

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Always use structured errors, never generic Exception
raise ModelOnexError(
    message="Operation failed",
    error_code=EnumCoreErrorCode.OPERATION_FAILED,
    context={"user_id": user_id}
)
```

#### Use @standard_error_handling decorator:

```python
from omnibase_core.decorators.decorator_error_handling import standard_error_handling

@standard_error_handling  # Eliminates 6+ lines of try/catch boilerplate
async def my_operation(self):
    pass
```

#### Exception Handling Comment Markers

When using catch-all or broad exception handlers, document the intent with these standardized markers:

| Marker | When to Use | Example Context |
|--------|-------------|-----------------|
| `# fallback-ok:` | Graceful degradation to default values | Config loading, optional features |
| `# catch-all-ok:` | Boundary handlers that must not crash | API endpoints, CLI entry points |
| `# cleanup-resilience-ok:` | Cleanup that must complete | Resource release, rollback |
| `# boundary-ok:` | System/API boundaries | Event handlers, webhooks |
| `# init-errors-ok:` | Initialization with safe defaults | Service startup, lazy loading |
| `# tool-resilience-ok:` | Tool/plugin isolation | mypy plugins, linters |

**Example Usage**:
```python
try:
    config = load_config(path)
except (OSError, ValidationError) as e:
    # fallback-ok: use defaults if config unavailable
    config = DEFAULT_CONFIG
```

#### Exception Tuple Ordering

Exception tuples should be **alphabetically ordered** by exception class name:

```python
# Correct - alphabetical
except (AttributeError, TypeError, ValidationError, ValueError) as e:

# Wrong - not alphabetical
except (ValueError, TypeError, AttributeError) as e:
```

#### Centralized Exception Groups

Use centralized exception constants from `omnibase_core.errors.exception_groups`:

```python
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS

try:
    result = model.model_validate(data)
except PYDANTIC_MODEL_ERRORS as e:
    # Handle validation errors
    pass
```

Available groups: `VALIDATION_ERRORS`, `PYDANTIC_MODEL_ERRORS`, `ATTRIBUTE_ACCESS_ERRORS`,
`YAML_PARSING_ERRORS`, `JSON_PARSING_ERRORS`, `FILE_IO_ERRORS`, `NETWORK_ERRORS`, `ASYNC_ERRORS`

### Mixin System

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCompute, MixinDiscoveryResponder):
    """Node with discovery capabilities."""
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Always use protocol names for DI
        self.logger = container.get_service("ProtocolLogger")
        self.event_bus = container.get_service("ProtocolEventBus")
```

**Available Mixins**: `MixinDiscoveryResponder`, `MixinEventHandler`, `MixinEventListener`, `MixinNodeExecutor`, `MixinNodeLifecycle`, `MixinRequestResponseIntrospection`, `MixinWorkflowExecution`

### File Naming Conventions

All Python files in `src/omnibase_core/` must follow directory-specific naming prefixes. This is enforced by pre-commit hooks via `checker_naming_convention.py`.

| Directory | Required Prefix(es) | Example |
|-----------|---------------------|---------|
| `cli/` | `cli_*` | `cli_commands.py` |
| `constants/` | `constants_*` | `constants_event_types.py` |
| `container/` | `container_*` | `container_service_registry.py` |
| `context/` | `context_*` | `context_application.py` |
| `contracts/` | `contract_*` | `contract_hash_registry.py` |
| `decorators/` | `decorator_*` | `decorator_error_handling.py` |
| `enums/` | `enum_*` | `enum_node_kind.py` |
| `errors/` | `error_*` or `exception_*` | `error_runtime.py` |
| `factories/` | `factory_*` | `factory_contract_profile.py` |
| `infrastructure/` | `node_*` or `infra_*` | `node_base.py` |
| `logging/` | `logging_*` | `logging_structured.py` |
| `mixins/` | `mixin_*` | `mixin_discovery_responder.py` |
| `models/` | `model_*` | `model_event_envelope.py` |
| `nodes/` | `node_*` | `node_compute.py` |
| `pipeline/` | `builder_*`, `runner_*`, `manifest_*`, `composer_*`, `registry_*`, `pipeline_*`, `handler_*` | `builder_execution_plan.py` |
| `protocols/` | `protocol_*` | `protocol_event_bus.py` |
| `resolution/` | `resolver_*` | `resolver_execution.py` |
| `runtime/` | `runtime_*`, `handler_*` | `runtime_file_registry.py` |
| `schemas/` | `schema_*` | `schema_node.py` |
| `services/` | `service_*` | `service_compute_cache.py` |
| `tools/` | `tool_*` | `tool_dict_any_checker.py` |
| `types/` | `typed_dict_*`, `type_*`, or `converter_*` | `type_compute_pipeline.py` |
| `utils/` | `util_*` | `util_datetime_parser.py` |
| `validation/` | `validator_*` or `checker_*` | `validator_contracts.py` |

**Exceptions**: `__init__.py`, `conftest.py`, and `py.typed` files are always allowed.

**Validation**: Run `poetry run python -m omnibase_core.validation.checker_naming_convention` to check compliance.

### Architectural Exceptions

Some files are excluded from single-class-per-file validation due to architectural patterns:

| File | Reason |
|------|--------|
| `mixins/mixin_event_bus.py` | Duck-typed Protocol defined alongside the mixin that uses it. The protocol and implementation are tightly coupled for duck-typing support of legacy event bus implementations. |

These exclusions are documented in `.pre-commit-config.yaml` under `validate-single-class-per-file`.

### Enum String Serialization

All string-based enums should use `StrValueHelper` for consistent `__str__` behavior:

```python
from omnibase_core.utils.util_str_enum_base import StrValueHelper

class EnumStatus(StrValueHelper, str, Enum):
    """Status values for workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

# StrValueHelper provides __str__ that returns self.value
str(EnumStatus.PENDING)  # Returns: "pending"
```

**Note**: `StrValueHelper` is a utility mixin for enums, not a node mixin. It is located in `omnibase_core.utils`, not `omnibase_core.mixins`.

### Severity Enum Policy

**Canonical Enum**: Use `EnumSeverity` from `omnibase_core.enums` for all general severity classifications.

```python
from omnibase_core.enums import EnumSeverity

# Values: DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL
severity = EnumSeverity.WARNING
```

**Documented Exceptions** (do NOT merge into EnumSeverity):

| Enum | Location | Reason |
|------|----------|--------|
| `EnumSeverityLevel` | `omnibase_core.enums` | RFC 5424 logging compliance (11 values including TRACE, NOTICE, ALERT, EMERGENCY) |
| `EnumImpactSeverity` | `omnibase_core.enums` | Business impact scale (CRITICAL, HIGH, MEDIUM, LOW, MINIMAL) |

**Policy**: Do not create new severity enums. If you need additional severity levels:
1. Evaluate if `EnumSeverity` can be extended (requires ticket + review)
2. Check if `EnumSeverityLevel` or `EnumImpactSeverity` is more appropriate for your use case
3. If truly needed, create a ticket explaining why a new enum is necessary

### Pydantic Model Configuration Standards

Every Pydantic model MUST have an explicit `model_config`. Empty `ConfigDict()` is not allowed - it has ambiguous intent and provides no explicit policy for model behavior (extra fields, mutability, etc.). Models must declare their configuration explicitly.

#### ConfigDict Requirements

| Model Type | Required ConfigDict | Example |
|------------|---------------------|---------|
| **Immutable value object** | `ConfigDict(frozen=True, extra="forbid", from_attributes=True)` | ModelSemVer, ModelAuditEntry |
| **Mutable internal model** | `ConfigDict(extra="forbid", from_attributes=True)` | ModelRouteHop, ModelFilterCriteria |
| **Contract/external data** | `ConfigDict(extra="ignore", ...)` | YAML contracts |
| **Extension point** | `ConfigDict(extra="allow", ...)` | ModelNodeExtensions |

#### Key Rules

1. **frozen=True** - Model is immutable, MUST also have `from_attributes=True`
2. **Mutable models** - NO `frozen=True`, but still use `extra="forbid"` for internal models
3. **Contracts** - MUST explicitly declare `extra=` policy (no implicit defaults)
4. **`from_attributes=True`** - Required on ALL frozen models for pytest-xdist compatibility

**Why `from_attributes=True`?** pytest-xdist workers import classes independently. Without it, Pydantic rejects valid instances due to class identity differences.

#### Field Definition Patterns

```python
# Simple default - no Field() needed
field_name: str | None = None

# Using Field() for metadata - Field() justified
field_name: str | None = Field(default=None, description="Helpful description")
field_name: int | None = Field(default=None, ge=0, le=100)
field_name: str | None = Field(default=None, alias="fieldName")

# WRONG - Field() without metadata (use = None instead)
field_name: str | None = Field(default=None)  # Unnecessary wrapper

# Mutable defaults - ALWAYS use default_factory
items: list[str] = Field(default_factory=list)
mapping: dict[str, Any] = Field(default_factory=dict)

# WRONG - Mutable default values cause shared state bugs
items: list[str] = []  # Dangerous!
```

**See**: [Pydantic Best Practices](docs/conventions/PYDANTIC_BEST_PRACTICES.md) for comprehensive guidelines.

To find models using this pattern: `grep -r "from_attributes.*True" src/omnibase_core/models/`

---

## Code Hygiene Policies

### Import Policy

**Convention**: Absolute imports across packages, relative imports within tight module clusters.

- **Default**: Absolute imports for stability + readability
- **Allowed**: Relative imports within same subpackage to avoid long paths
- **Forbidden**: Relative imports that cross package boundaries

**Examples**:
```python
# Preferred across package/subsystem boundaries
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Allowed within a tight subpackage cluster
from .model_widget_definition import ModelWidgetDefinition
```

**Import Order** (enforced by ruff I001/I002):
1. Standard library imports
2. Third-party imports
3. First-party (`omnibase_core`) imports
4. Local/relative imports

**`__init__.py` Patterns**:

| Pattern | Purpose | Example |
|---------|---------|---------|
| **Barrel exports** | Public API boundary | `from .model_semver import ModelSemVer` |
| **Selective re-exports** | Controlled internal API | `from .internal import _helper` (underscore prefix) |
| **Empty** | Namespace package marker | Just `# empty` comment |

**Excluded Files**: Files excluded from import checks have inline comments:
```python
# NOTE(OMN-1302): This module is excluded from <TOOL> because <REASON>.
```

### TODO Policy

**Format**: All TODOs must reference a Linear ticket:
```python
# TODO(OMN-XXX): Description of work needed
```

**Rules**:
- `# TODO(OMN-1302): Add validation for edge case` - Correct
- `# TODO: Fix this later` - Missing ticket reference (forbidden)
- `# TODO(): Something` - Empty parentheses (forbidden)

**For new TODOs**: Create a Linear ticket first, then add the TODO with the ticket ID.

**Temporary marker** (during triage only):
```python
# TODO(OMN-TBD): <action>  [NEEDS TICKET]
```

**Multi-line TODOs**: For multi-line TODOs, always place `[NEEDS TICKET]` on the first line (same line as `TODO(OMN-TBD):`) for grep-ability:
```python
# Correct - [NEEDS TICKET] on first line (findable with grep)
# TODO(OMN-TBD): Add topic validation when topic-based publishing is implemented. [NEEDS TICKET]
# When the event bus supports explicit topic routing, validate alignment
# between message category and topic name using _validate_topic_alignment().

# Wrong - [NEEDS TICKET] on last line (not findable with single grep)
# TODO(OMN-TBD): Add topic validation when topic-based publishing is implemented.
# When the event bus supports explicit topic routing, validate alignment
# between message category and topic name using _validate_topic_alignment().  [NEEDS TICKET]
```

**Why first line?** Running `grep -r "TODO(OMN-TBD).*\[NEEDS TICKET\]"` finds all TODOs needing tickets only when the marker is on the first line.

### Type Ignore Policy

**Format**: All type ignores must have specific codes and explanations:
```python
# NOTE(OMN-XXXX): mypy false-positive due to <reason>. Safe because <invariant>.
value = some_call()  # type: ignore[arg-type]
```

**Rules**:
- Specific codes required (e.g., `[arg-type]`, `[return-value]`)
- Explanation comment on line above
- Generic `# type: ignore` without code (forbidden)
- No explanation of why ignore is safe (forbidden)

**When to use type ignores**:
- Third-party library typing is broken
- Unavoidable dynamic behavior (DI, duck typing)
- mypy false-positive that cannot be fixed

**When NOT to use type ignores**:
- Wrong types on Field defaults (fix the type)
- Optional vs non-Optional mismatch (fix the annotation)
- Any leaking from dicts (use TypedDict)

---

## Thread Safety

⚠️ **CRITICAL**: Most ONEX components are **NOT thread-safe by default**.

| Component | Thread-Safe? | Action Required |
|-----------|-------------|-----------------|
| `NodeCompute` | ❌ No | Use thread-local instances or lock cache |
| `NodeEffect` | ❌ No | Use separate instances per thread |
| `ModelComputeCache` | ❌ No | Wrap with `threading.Lock` |
| `ModelCircuitBreaker` | ❌ No | Use thread-local or synchronized wrapper |
| `ModelEffectTransaction` | ❌ No | Never share across threads |
| Pydantic Models | ✅ Yes | Immutable after creation |
| `ModelONEXContainer` | ✅ Yes | Read-only after initialization |

**Critical Rule**: Do NOT share node instances across threads without explicit synchronization.

**See**: [docs/guides/THREADING.md](docs/guides/THREADING.md)

---

## Documentation

### Quick Links

| For... | Start Here |
|--------|-----------|
| **New Developers** | [Getting Started Guide](docs/getting-started/QUICK_START.md) |
| **Building Nodes** | [Node Building Guide](docs/guides/node-building/README.md) |
| **Understanding Architecture** | [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) |
| **Error Handling** | [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md) |
| **Thread Safety** | [Threading Guide](docs/guides/THREADING.md) |

### Node Building Guide (CRITICAL)

1. [What is a Node?](docs/guides/node-building/01_WHAT_IS_A_NODE.md)
2. [Node Types](docs/guides/node-building/02_NODE_TYPES.md)
3. [COMPUTE Node Tutorial](docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md)
4. [EFFECT Node Tutorial](docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md)
5. [REDUCER Node Tutorial](docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
6. [ORCHESTRATOR Node Tutorial](docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)

📚 **Complete Index**: [docs/INDEX.md](docs/INDEX.md)

---

## Common Pitfalls

### ❌ Don't

1. **Skip base class initialization**
   ```python
   def __init__(self, container):
       pass  # WRONG - missing super().__init__(container)
   ```

   **Should be:**
   ```python
   def __init__(self, container: ModelONEXContainer):
       super().__init__(container)  # ✅ CORRECT
   ```

2. **Use generic Exception**
   ```python
   raise Exception("Something failed")  # WRONG - use ModelOnexError
   ```

3. **Use pip instead of Poetry**
   ```bash
   pip install package-name  # WRONG
   ```

4. **Confuse ModelContainer with ModelONEXContainer**
   ```python
   def __init__(self, container: ModelContainer):  # WRONG - use ModelONEXContainer
   ```

5. **Share node instances across threads**
   ```python
   threading.Thread(target=node.process).start()  # UNSAFE
   ```

6. **Use concrete class names for DI**
   ```python
   container.get_service("EventBusService")  # WRONG - use "ProtocolEventBus"
   ```

7. **Poll background jobs repeatedly (AI Agent Anti-Pattern)**
   - Call `BashOutput` once with longer timeout (e.g., 300 seconds)
   - Pre-commit hooks can take 2-5 minutes on this codebase (1865+ source files)

### ✅ Do

1. **Always call super().__init__(container)**
2. **Use ModelOnexError with error codes**
3. **Always use `poetry run` for Python commands**
4. **Use ModelONEXContainer in node constructors**
5. **Use thread-local or separate node instances**
6. **Use protocol names for DI** (`"ProtocolEventBus"`)
7. **Use duck typing with protocols** (no isinstance checks)

---

## Quick Reference Commands

```bash
# Setup
poetry install && pre-commit install

# Cleanup
poetry run python scripts/cleanup.py --tmp-only       # Clean tmp/ only (USE THIS)
poetry run python scripts/cleanup.py                  # FULL cleanup (slow rebuild)

# Testing
poetry run pytest tests/                    # All tests
poetry run pytest tests/unit/              # Unit tests only
poetry run pytest tests/ -n 0 -xvs         # Debug mode
poetry run pytest tests/ --cov             # With coverage

# Code Quality
poetry run mypy src/omnibase_core/         # Type checking
poetry run black src/ tests/               # Formatting
poetry run isort src/ tests/               # Import sorting
poetry run ruff check src/ tests/          # Linting
pre-commit run --all-files                 # All hooks

# Dependencies
poetry add package-name                     # Add dependency
poetry add --group dev package-name        # Add dev dependency
```

### CI/CD

- **GitHub Actions**: `.github/workflows/test.yml`
- **20 Parallel Splits**: Each split runs subset of tests
- **Coverage Required**: 60% minimum
- **Timeout Protection**: 60s per test

---

## Recent Updates

### v0.4.0 - Node Architecture Overhaul

- **NodeReducer and NodeOrchestrator are now PRIMARY** (FSM/workflow-driven)
- **"Declarative" suffix removed** - `NodeReducerDeclarative` → `NodeReducer`
- **Unified import path** - All nodes: `from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect`
- **Input/Output models and enums exported** from `omnibase_core.nodes`

### v0.3.6 - Foundation

- Enhanced cleanup.py script with tmp/ cleanup
- Removed omnibase_spi dependency (SPI now depends on Core)
- Comprehensive test suite with 12,000+ tests
- CI splits increased from 10 → 12 → 20
- Fixed event loop hangs, updated security dependencies

---

**Last Updated**: 2026-01-11 | **Version**: 0.6.4 | **Python**: 3.12+

**Ready to build?** → [Node Building Guide](docs/guides/node-building/README.md)
**Need help?** → [Documentation Index](docs/INDEX.md)
**Want to contribute?** → [Contributing Guide](CONTRIBUTING.md)
