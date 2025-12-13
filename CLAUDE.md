# CLAUDE.md - Omnibase Core Project Instructions

> **Version**: 0.4.0
> **Python**: 3.12+
> **Framework**: ONEX Core - Foundational implementations for the ONEX architecture
>
> **⚠️ No Backwards Compatibility**: Until v0.4.0 is released, this project does NOT maintain backwards compatibility. Breaking changes may occur between commits. This is acceptable during the pre-release development phase.
>
> **📚 Shared Infrastructure**: For common OmniNode infrastructure (PostgreSQL, Kafka/Redpanda, remote server topology, Docker networking, environment variables), see **`~/.claude/CLAUDE.md`**. This file contains omnibase_core-specific architecture, patterns, and development only.

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
10. [Thread Safety](#thread-safety)
11. [Documentation](#documentation)
12. [Common Pitfalls](#common-pitfalls)

---

## Project Overview

**omnibase_core** provides the foundational building blocks for the ONEX framework:

- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Protocol-Driven DI**: Container-based dependency injection with `container.get_service("ProtocolName")`
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per node
- **Structured Errors**: ModelOnexError with Pydantic models for consistent error handling
- **Event-Driven**: ModelEventEnvelope for inter-service communication
- **Comprehensive Testing**: 12,000+ tests (12,198 collected) with 60%+ coverage requirement
- **Strict Type Checking**: 100% mypy strict mode compliance (0 errors across 1865 source files)

### Dependencies

- **Framework**: Pydantic 2.11+, FastAPI 0.120+
- **Testing**: pytest 8.4+, pytest-asyncio, pytest-xdist, pytest-split, pytest-cov

---

## Python Development - ALWAYS USE POETRY

**CRITICAL**: This project uses Poetry for all Python package management and task execution.

### Required Patterns

✅ **CORRECT - Always use Poetry:**
```bash
poetry run pytest tests/unit/
poetry run mypy src/omnibase_core/
poetry run python -m module.name
poetry install
poetry add package-name
poetry run black src/
poetry run isort src/
```

❌ **WRONG - Never use pip or python directly:**
```bash
python -m pip install -e .          # NEVER
pip install package                 # NEVER
python -m pytest tests/             # NEVER
python script.py                    # NEVER
```

### Why Poetry?

1. **Dependency Isolation**: Poetry manages virtualenvs automatically
2. **Lock File**: Ensures reproducible builds across environments
3. **Project Consistency**: All developers and CI use same environment
4. **ONEX Standards**: Poetry is the mandated tool for all ONEX projects

### Agent Instructions

When spawning polymorphic agents or AI assistants:
- **ALWAYS** instruct them to use `poetry run` for Python commands
- **NEVER** allow direct pip or python execution
- **NEVER** run `git commit` or `git push` in background mode - always foreground
- Include explicit examples showing Poetry usage
- Reference this CLAUDE.md for project-specific conventions

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

#### Node Responsibilities

| Node Type | Purpose | Examples | Import |
|-----------|---------|----------|--------|
| **EFFECT** | External interactions (I/O) | API calls, database ops, file system, message queues | `from omnibase_core.nodes import NodeEffect` |
| **COMPUTE** | Data processing & transformation | Calculations, validations, data mapping | `from omnibase_core.nodes import NodeCompute` |
| **REDUCER** | State aggregation & management (FSM-driven) | State machines (FSM w/ ModelIntent), accumulators, event reduction | `from omnibase_core.nodes import NodeReducer` |
| **ORCHESTRATOR** | Workflow coordination (workflow-driven) | Multi-step workflows (ModelAction w/ Leases), parallel execution, error recovery | `from omnibase_core.nodes import NodeOrchestrator` |

**v0.4.0 Architecture Change**: `NodeReducer` and `NodeOrchestrator` are now the PRIMARY implementations (FSM/workflow-driven). All nodes use declarative YAML contracts.

### Protocol-Driven Dependency Injection

```python
# Get services by protocol interface (never by concrete class)
event_bus = container.get_service("ProtocolEventBus")
logger = container.get_service("ProtocolLogger")
```

**Key Principles**:
- Use protocol names, not concrete classes
- No isinstance checks - use duck typing
- No registry dependencies - pure protocol-based resolution

### Contract Loading with FileRegistry

FileRegistry provides fail-fast loading of RuntimeHostContract YAML files:

```python
from omnibase_core.runtime.file_registry import FileRegistry
from pathlib import Path

registry = FileRegistry()

# Load single contract
contract = registry.load(Path("config/runtime_host.yaml"))

# Load all contracts from directory (fail-fast on first error)
contracts = registry.load_all(Path("config/contracts/"))

# Access contract data
print(contract.event_bus.kind)  # "kafka"
print(len(contract.handlers))   # Number of handlers
```

**Error Handling**: All errors are `ModelOnexError` with specific error codes:
- `FILE_NOT_FOUND` - Contract file does not exist
- `FILE_READ_ERROR` - Cannot read file (permissions, I/O errors)
- `CONFIGURATION_PARSE_ERROR` - Invalid YAML syntax
- `CONTRACT_VALIDATION_ERROR` - Pydantic schema validation failure
- `DUPLICATE_REGISTRATION` - Duplicate handler types in contract
- `DIRECTORY_NOT_FOUND` - Directory does not exist (for `load_all`)

**Thread Safety**: FileRegistry instances are stateless and thread-safe.

**See**: `src/omnibase_core/runtime/file_registry.py` for full documentation.

### Base Classes Usage

**v0.4.0+**: Import nodes directly from `omnibase_core.nodes`:

```python
from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCompute):
    """COMPUTE node example - inherits from NodeCompute."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate

        # Protocol-based dependencies
        self.logger = container.get_service("ProtocolLogger")

        # Your business logic initialization


class NodeMyReducer(NodeReducer):
    """REDUCER node example - FSM-driven state management."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # FSM configuration is handled by the base class


class NodeMyOrchestrator(NodeOrchestrator):
    """ORCHESTRATOR node example - workflow-driven coordination."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Workflow configuration is handled by the base class
```

**CRITICAL**: Always call `super().__init__(container)` - this eliminates 80+ lines of boilerplate.

**Migration Guide**: If migrating from pre-v0.4.0, see `docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`.

### Advanced Patterns (ONEX v2.0 / v0.4.0+)

**ModelIntent Pattern** (REDUCER nodes - `NodeReducer`):
- Pure FSM transitions without direct side effects
- Intent-based state machines for FSM-driven state management
- Separates state transition logic from side effect execution
- **v0.4.0**: `NodeReducer` is now the primary implementation (formerly `NodeReducerDeclarative`)

**ModelAction Pattern** (ORCHESTRATOR nodes - `NodeOrchestrator`):
- Lease-based single-writer semantics for distributed coordination
- Workflow-driven action definitions with automatic retry and rollback
- Resource locking and conflict resolution for concurrent workflows
- **v0.4.0**: `NodeOrchestrator` is now the primary implementation (formerly `NodeOrchestratorDeclarative`)

**See**: [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) for complete details and [Migration Guide](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) for upgrade instructions.

### Container Types: CRITICAL DISTINCTION

⚠️ **IMPORTANT**: omnibase_core has TWO different container types that are NOT interchangeable!

#### ModelONEXContainer - Dependency Injection Container

**Location**: `omnibase_core.models.container.model_onex_container`

**Purpose**: Service resolution, workflow orchestration, lifecycle management

**Usage**: ✅ **ALWAYS use in node constructors**

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase):
    def __init__(self, container: ModelONEXContainer):  # ✅ Correct
        super().__init__(container)
        self.logger = container.get_service(ProtocolLogger)
```

#### ModelContainer[T] - Generic Value Wrapper

**Location**: `omnibase_core.models.core.model_container`

**Purpose**: Wrapping single values with metadata and validation

**Usage**: ✅ **NEVER use in node constructors** - only for value wrapping

```python
from omnibase_core.models.core.model_container import ModelContainer

# Wrap a value with metadata
config = ModelContainer.create(
    value="production",
    container_type="environment",
    source="env_var"
)
```

#### Quick Reference

| Feature | ModelContainer[T] | ModelONEXContainer |
|---------|-------------------|-------------------|
| **Purpose** | Value wrapper | Dependency injection |
| **In Node `__init__`** | ❌ NEVER | ✅ ALWAYS |
| **Service Resolution** | ❌ No | ✅ Yes (`get_service()`) |
| **Primary Use** | Wrapping values | Resolving services |

**See**: [docs/architecture/CONTAINER_TYPES.md](docs/architecture/CONTAINER_TYPES.md) for complete details.

### Node Classification Enums: EnumNodeKind vs EnumNodeType

⚠️ **IMPORTANT**: omnibase_core has TWO node classification enums with different purposes!

#### EnumNodeKind - Architectural Classification

**Location**: `omnibase_core.enums.enum_node_kind`

**Purpose**: High-level architectural role in the ONEX workflow

**Values**: `EFFECT`, `COMPUTE`, `REDUCER`, `ORCHESTRATOR`, `RUNTIME_HOST`

**Use When**: Routing data through the pipeline, enforcing architectural patterns

```python
from omnibase_core.enums import EnumNodeKind

# Classify a node's architectural role
if node_kind == EnumNodeKind.COMPUTE:
    # Route to processing pipeline
    pass

# Check if it's a core 4-node type
if EnumNodeKind.is_core_node_type(node_kind):
    # Handle core node
    pass
```

#### EnumNodeType - Implementation Type

**Location**: `omnibase_core.enums.enum_node_type`

**Purpose**: Specific implementation type for discovery and capability matching

**Values**: `COMPUTE_GENERIC`, `TRANSFORMER`, `AGGREGATOR`, `GATEWAY`, `VALIDATOR`, etc.

**Use When**: Node discovery, capability matching, specific behavior selection

```python
from omnibase_core.enums import EnumNodeType

# Check specific implementation type
if node_type == EnumNodeType.TRANSFORMER:
    # Handle transformer-specific logic
    pass

# Get architectural kind from type
kind = EnumNodeType.get_node_kind(node_type)  # Returns EnumNodeKind
```

#### Quick Reference

| Question | Use This Enum |
|----------|---------------|
| "What role in the ONEX workflow?" | `EnumNodeKind` |
| "What specific implementation?" | `EnumNodeType` |
| "Routing through pipeline?" | `EnumNodeKind` |
| "Node discovery/matching?" | `EnumNodeType` |

**Relationship**: Multiple `EnumNodeType` values map to each `EnumNodeKind`:
- `TRANSFORMER`, `AGGREGATOR`, `COMPUTE_GENERIC` → `EnumNodeKind.COMPUTE`
- `GATEWAY`, `VALIDATOR`, `ORCHESTRATOR_GENERIC` → `EnumNodeKind.ORCHESTRATOR`

**See**: [docs/guides/ENUM_NODE_KIND_MIGRATION.md](docs/guides/ENUM_NODE_KIND_MIGRATION.md) for migration guidance.

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
│   ├── logging/                # Logging utilities
│   ├── mixins/                 # Reusable behavior mixins (with mixin_metadata.yaml)
│   ├── models/                 # Pydantic models
│   │   ├── base/               # Base model classes
│   │   ├── cli/                # CLI-related models
│   │   ├── common/             # Common/shared models
│   │   ├── configuration/      # System runtime configuration
│   │   ├── connections/        # Connection models
│   │   ├── container/          # DI container models
│   │   ├── contracts/          # Contract models
│   │   ├── core/               # Core domain models
│   │   ├── dedup/              # Deduplication models
│   │   ├── detection/          # Detection models
│   │   ├── discovery/          # Discovery models
│   │   ├── docker/             # Docker-related models
│   │   ├── endpoints/          # Endpoint models
│   │   ├── errors/             # Error models
│   │   ├── event_bus/          # Event bus models
│   │   ├── events/             # Event models
│   │   ├── examples/           # Example/artifact configurations
│   │   ├── fsm/                # Finite state machine models
│   │   ├── graph/              # Graph models
│   │   ├── health/             # Health check models
│   │   ├── infrastructure/     # Infrastructure models
│   │   ├── logging/            # Logging models
│   │   ├── metadata/           # Metadata models
│   │   ├── mixins/             # Mixin models
│   │   ├── node_metadata/      # Node metadata models
│   │   ├── nodes/              # Node models
│   │   ├── operations/         # Operation models
│   │   ├── orchestrator/       # Orchestrator models
│   │   ├── primitives/         # Primitive type models
│   │   ├── projection/         # Projection models
│   │   ├── registry/           # Registry models
│   │   ├── results/            # Result models
│   │   ├── security/           # Security models
│   │   ├── service/            # Service models
│   │   ├── state/              # State models
│   │   ├── tools/              # Tool models
│   │   ├── types/              # Type models
│   │   ├── utils/              # Utility models
│   │   ├── validation/         # Validation models
│   │   └── workflow/           # Workflow models
│   │       ├── api/            # Workflow API interface
│   │       └── execution/      # Workflow execution internals
│   ├── nodes/                  # Node implementations (v0.4.0+)
│   │   ├── node_compute.py     # NodeCompute - data processing
│   │   ├── node_effect.py      # NodeEffect - external I/O
│   │   ├── node_reducer.py     # NodeReducer - FSM-driven state
│   │   └── node_orchestrator.py# NodeOrchestrator - workflow-driven
│   ├── primitives/             # Primitive types
│   ├── types/                  # Type definitions
│   ├── utils/                  # Utility functions
│   └── validation/             # Validation framework
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests (12,000+ tests)
│   │   ├── enums/              # Enum tests
│   │   ├── models/             # Model tests
│   │   ├── mixins/             # Mixin tests
│   │   ├── nodes/              # Node tests
│   │   ├── utils/              # Utility tests
│   │   └── ...
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test fixtures
├── docs/                       # Documentation
│   ├── getting-started/        # Onboarding guides
│   ├── guides/                 # Step-by-step tutorials
│   │   └── node-building/      # Node building guide (CRITICAL)
│   ├── architecture/           # Architecture documentation
│   ├── patterns/               # Design patterns
│   ├── reference/              # API docs and templates
│   └── testing/                # Testing documentation
└── scripts/                    # Build and validation scripts
```

---

## Development Workflow

### Initial Setup

```bash
# Clone repository
git clone https://github.com/OmniNode-ai/omnibase_core.git
cd omnibase_core

# Install dependencies
poetry install

# Set up pre-commit hooks
pre-commit install

# Verify setup
poetry run pytest tests/ -x
poetry run mypy src/omnibase_core/
```

### Development Cycle

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Follow architecture patterns
3. **Run tests**: `poetry run pytest tests/`
4. **Check types**: `poetry run mypy src/omnibase_core/`
5. **Format code**: `poetry run black src/ tests/ && poetry run isort src/ tests/`
6. **Run pre-commit**: `pre-commit run --all-files`
7. **Commit**: Follow conventional commits
8. **Push & PR**: Target `main` branch

---

## Testing Guide

### Test Categories

- **Unit Tests**: 12,000+ tests (12,198 collected) in `tests/unit/` - test individual components in isolation
- **Integration Tests**: `tests/integration/` - test multiple components together
- **Coverage Requirement**: Minimum 60% (configured in pyproject.toml)

### Running Tests

```bash
# Run all tests (default: 4 parallel workers)
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/exceptions/test_onex_error.py -v

# Run with coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Run specific test class
poetry run pytest tests/unit/exceptions/test_onex_error.py::TestOnexErrorEdgeCases -xvs

# Disable parallelism for debugging
poetry run pytest tests/ -n 0 -xvs

# Run tests with timeout protection (prevents hangs)
poetry run pytest tests/ --timeout=60
```

### Parallel Testing Configuration

**Local Testing**:
- Default: `-n4` (4 parallel workers)
- Timeout: 60s per test
- Distribution: `loadscope` (groups by module)

**CI Testing**:
- 20 parallel splits across isolated runners
- Each split runs subset of tests
- Prevents resource exhaustion
- See `.github/workflows/test.yml`

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

### Expected Runtime Per Split

**Configuration**: 20 parallel splits running on GitHub Actions runners

**Benchmark Data** (from CI run [#18997947041](https://github.com/OmniNode-ai/omnibase_core/actions/runs/18997947041)):

| Metric | Value |
|--------|-------|
| **Average Runtime** | 2m58s per split |
| **Fastest Split** | 2m35s (Split 6/20) |
| **Slowest Split** | 3m35s (Split 12/20) |
| **Runtime Range** | 60s variation |
| **Total CI Time** | ~3 minutes (parallel execution) |

### Full Split Timings (Baseline)

Actual runtimes from successful CI run on 2025-11-01:

```
Split  1/20: 2m49s    Split 11/20: 2m52s
Split  2/20: 3m1s     Split 12/20: 3m35s ⚠️  (slowest)
Split  3/20: 2m44s    Split 13/20: 2m56s
Split  4/20: 3m8s     Split 14/20: 2m57s
Split  5/20: 2m47s    Split 15/20: 2m53s
Split  6/20: 2m35s ✅  (fastest)   Split 16/20: 3m12s
Split  7/20: 2m55s    Split 17/20: 3m1s
Split  8/20: 2m58s    Split 18/20: 2m56s
Split  9/20: 3m5s     Split 19/20: 3m1s
Split 10/20: 2m56s    Split 20/20: 2m58s
```

### Performance Thresholds

| Threshold | Duration | Action |
|-----------|----------|--------|
| **Normal** | 2m30s - 3m30s | Expected range - no action needed |
| **Warning** | 3m30s - 4m30s | Review split for slow tests or resource issues |
| **Critical** | > 4m30s | Investigate immediately - likely regression |

### Investigating Anomalies

If a split exceeds expected thresholds:

1. **Check Split Distribution**
   ```bash
   # View which tests are in the slow split
   poetry run pytest --collect-only --split-splits=20 --split-group=<split-number>
   ```

2. **Profile Slow Tests**
   ```bash
   # Run the slow split with duration reporting
   poetry run pytest --durations=10 --split-splits=20 --split-group=<split-number>
   ```

3. **Common Causes**:
   - **Test Hangs**: Check for missing `@pytest.mark.timeout` or event loop issues
   - **Resource Exhaustion**: Parallel workers consuming too much memory/CPU
   - **Slow Fixtures**: Database fixtures or heavy setup/teardown
   - **Network Issues**: External API calls or network-dependent tests

4. **Mitigation Strategies**:
   - Move slow tests to dedicated split group
   - Add `@pytest.mark.slow` to identify candidates for optimization
   - Increase split count if consistently hitting 4+ minute runs
   - Use `pytest-xdist` with fewer workers for problematic splits

### CI Health Indicators

✅ **Healthy CI**:
- All splits complete within 2m30s - 3m30s
- No individual split > 4 minutes
- Consistent timings across runs

⚠️ **Warning Signs**:
- Individual splits > 3m30s
- Increasing variance between fastest/slowest
- Frequent timeouts or hangs

🚨 **Critical Issues**:
- Any split > 5 minutes
- Multiple splits timing out
- Total CI time > 6 minutes

### Historical Context

- **Initial Configuration**: 10 splits (Nov 2024)
- **First Optimization**: 12 splits (Dec 2024)
- **Current Configuration**: 20 splits (Jan 2025)
- **Next Review**: When average runtime exceeds 4 minutes

**Benchmark Source**: [CI Run #18997947041](https://github.com/OmniNode-ai/omnibase_core/actions/runs/18997947041)
**Last Updated**: 2025-12-04
**Correlation ID**: `95cac850-05a3-43e2-9e57-ccbbef683f43`

### Operational Monitoring

For detailed guidance on monitoring CI health, detecting anomalies, and investigating performance regressions, see:

📊 **[CI Monitoring Guide](docs/ci/CI_MONITORING_GUIDE.md)** - Comprehensive operational procedures including:
- Alert thresholds and severity levels
- Step-by-step investigation workflow
- Common issues and resolutions
- Metrics tracking and historical analysis
- Tools and commands for CI monitoring

---

## Code Quality

### Type Checking

**Status**:
- ✅ mypy: 100% strict mode compliance (0 errors in 1865 source files)
- ✅ pyright: basic mode compliance (0 errors, warnings only)

**Note**: Both mypy AND pyright must pass in CI. This dual-checker approach catches different categories of type errors.

```bash
# Type check with mypy (strict mode)
poetry run mypy src/omnibase_core/

# Type check with pyright (basic mode)
poetry run pyright src/omnibase_core/

# Type check specific file with mypy
poetry run mypy src/omnibase_core/models/common/model_typed_mapping.py

# Type check specific file with pyright
poetry run pyright src/omnibase_core/models/common/model_typed_mapping.py
```

**Configuration**:
- mypy: See `[tool.mypy]` in pyproject.toml
- pyright: See `pyrightconfig.json` at repo root

**mypy Strict Mode Features**:
- `disallow_untyped_defs = true` - All functions must have type annotations
- `warn_return_any = true` - Warns on functions returning Any
- `warn_unused_configs = true` - Detects unused mypy configuration
- Pydantic plugin enabled for model validation

**pyright Configuration**:
- Basic type checking mode (planned migration to stricter settings per OMN-200)
- Targets Python 3.12
- Configured for Pydantic compatibility

**Enforcement**:
- ✅ Pre-commit hooks (mypy strict, pyright basic)
- ✅ CI/CD pipeline (both checkers must pass)
- ✅ Local development (both checkers available)

### Formatting

```bash
# Format code with black
poetry run black src/ tests/

# Sort imports with isort
poetry run isort src/ tests/

# Check formatting without changes
poetry run black --check src/ tests/
```

### Linting

```bash
# Lint with ruff
poetry run ruff check src/ tests/

# Fix auto-fixable issues
poetry run ruff check --fix src/ tests/
```

**Configuration**: See `[tool.ruff]` in pyproject.toml

### Pre-commit Hooks

```bash
# Run all hooks
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run mypy --all-files
```

---

## Key Patterns & Conventions

### Error Handling

#### Always use ModelOnexError, never generic Exception:

```python
from omnibase_core.errors import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Raise structured error
raise ModelOnexError(
    message="Operation failed",
    error_code=EnumCoreErrorCode.OPERATION_FAILED,
    context={"user_id": user_id}
)

# Chain exceptions
try:
    risky_operation()
except Exception as e:
    raise ModelOnexError("Operation failed") from e
```

#### Use @standard_error_handling decorator:

```python
from omnibase_core.decorators.error_handling import standard_error_handling

@standard_error_handling  # Eliminates 6+ lines of try/catch boilerplate
async def my_operation(self):
    # Your logic here
    pass
```

### Event-Driven Communication

```python
from omnibase_core.models.event.model_event_envelope import ModelEventEnvelope

# Process events through envelope pattern
async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    envelope_payload = input_data.operation_data.get("envelope_payload", {})
    # Event-driven processing logic
```

### Mixin System

```python
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder

class MyNode(NodeCoreBase, MixinDiscoveryResponder):
    """Node with discovery capabilities."""
    pass
```

**Available Mixins**:
- `MixinDiscoveryResponder` - Service discovery
- `MixinEventHandler` - Event handling
- `MixinEventListener` - Event listening
- `MixinNodeExecutor` - Node execution
- `MixinNodeLifecycle` - Lifecycle management
- `MixinRequestResponseIntrospection` - Request/response inspection
- `MixinWorkflowSupport` - Workflow support

### Pydantic `from_attributes=True` for Value Objects

**When to use**: Add `from_attributes=True` to `ConfigDict` for immutable value objects that:
1. Are nested inside other Pydantic models
2. May be used in tests with pytest-xdist parallel execution

**Why**: pytest-xdist runs tests across multiple workers. Each worker imports classes independently,
so `id(ModelSemVer)` in Worker A != `id(ModelSemVer)` in Worker B. Without `from_attributes=True`,
Pydantic rejects already-valid instances because class identity differs.

**Technical Details**:
- Default Pydantic validation uses `isinstance()` which checks class identity
- `from_attributes=True` enables attribute-based validation instead
- This allows Pydantic to accept objects with matching attributes regardless of class identity
- Essential for immutable value objects where equality is defined by DATA, not class identity

**Example**:
```python
from pydantic import BaseModel, ConfigDict

class ModelSemVer(BaseModel):
    """Immutable semantic version - value defined by data, not class identity."""
    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    major: int
    minor: int
    patch: int
```

**Models using this pattern**:
- `ModelSemVer` - Semantic versioning (`models/primitives/model_semver.py`)
- `ModelWorkflowNode` - Workflow nodes (`models/workflow/model_workflow_node.py`)
- `ModelExecutionGraph` - Execution graphs (`models/graph/model_execution_graph.py`)
- `ModelWorkflowDefinitionMetadata` - Workflow metadata (`models/workflow/model_workflow_definition_metadata.py`)
- `ModelServiceMetadata` - Service metadata (`models/service/model_service_metadata.py`)

**When NOT to use**:
- Models that are never nested in other Pydantic models
- Models that are not used in parallel test execution
- Models where class identity IS significant (e.g., singletons, service instances)

---

## Thread Safety

⚠️ **CRITICAL**: Most ONEX components are **NOT thread-safe by default**.

### Thread Safety Matrix

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

**See**: [docs/guides/THREADING.md](docs/guides/THREADING.md) for complete guidelines.

---

## Documentation

### Complete Documentation Index

📚 **[docs/INDEX.md](docs/INDEX.md)** - Central hub for all documentation

### Quick Links

| For... | Start Here | Time |
|--------|-----------|------|
| **New Developers** | [Getting Started Guide](docs/getting-started/QUICK_START.md) | 15 min |
| **Building Nodes** | [Node Building Guide](docs/guides/node-building/README.md) ⭐ | 30-60 min |
| **Choosing Base Classes** | [Node Class Hierarchy](docs/architecture/NODE_CLASS_HIERARCHY.md) ⭐ | 20 min |
| **Understanding Architecture** | [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) | 30 min |
| **Reference & Templates** | [Node Templates](docs/reference/templates/COMPUTE_NODE_TEMPLATE.md) | - |
| **Error Handling** | [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md) | 20 min |
| **Thread Safety** | [Threading Guide](docs/guides/THREADING.md) | 15 min |

### Node Building Guide ⭐ CRITICAL

**Recommended starting point for developers:**

1. [What is a Node?](docs/guides/node-building/01_WHAT_IS_A_NODE.md) (5 min)
2. [Node Types](docs/guides/node-building/02_NODE_TYPES.md) (10 min)
3. [COMPUTE Node Tutorial](docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) (30 min)
4. [EFFECT Node Tutorial](docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md) (30 min)
5. [REDUCER Node Tutorial](docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md) (30 min)
6. [ORCHESTRATOR Node Tutorial](docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md) (45 min)

---

## Common Pitfalls

### ❌ Don't

1. **Skip base class initialization**
   ```python
   # WRONG
   def __init__(self, container):
       # Missing super().__init__(container)
   ```

2. **Use generic Exception**
   ```python
   # WRONG
   raise Exception("Something failed")
   ```

3. **Use pip instead of Poetry**
   ```bash
   # WRONG
   pip install package-name
   ```

4. **Confuse ModelContainer with ModelONEXContainer**
   ```python
   # WRONG - ModelContainer[T] is a value wrapper, NOT a DI container
   from omnibase_core.models.core.model_container import ModelContainer

   class MyNode(NodeCoreBase):
       def __init__(self, container: ModelContainer):  # ❌ WRONG!
           super().__init__(container)  # Will fail!
   ```

5. **Share node instances across threads**
   ```python
   # WRONG
   node = NodeCompute(container)
   threading.Thread(target=node.process).start()  # UNSAFE
   ```

6. **Use concrete class names for DI**
   ```python
   # WRONG
   service = container.get_service("EventBusService")
   ```

7. **Skip isinstance checks with protocols**
   ```python
   # WRONG - protocols use duck typing
   if isinstance(service, ProtocolEventBus):
       pass
   ```

8. **Poll background jobs repeatedly (AI Agent Anti-Pattern)**
   ```text
   # WRONG - Burns tokens polling every few seconds
   BashOutput(bash_id) → still running
   BashOutput(bash_id) → still running
   BashOutput(bash_id) → still running
   ... (repeated 10+ times)
   ```
   **Instead**: Call `BashOutput` once with a longer `wait_up_to` timeout (e.g., 300 seconds), or continue working on other tasks while waiting. Pre-commit/pre-push hooks can take 2-5 minutes on this codebase (1865+ source files with mypy strict).

### ✅ Do

1. **Always call super().__init__()**
   ```python
   def __init__(self, container: ModelONEXContainer):
       super().__init__(container)  # REQUIRED
   ```

2. **Use structured errors**
   ```python
   raise ModelOnexError(message="...", error_code=EnumCoreErrorCode....)
   ```

3. **Always use Poetry**
   ```bash
   poetry run pytest tests/
   poetry add package-name
   ```

4. **Use ModelONEXContainer for dependency injection**
   ```python
   # ✅ Correct - use ModelONEXContainer in node constructors
   from omnibase_core.models.container.model_onex_container import ModelONEXContainer

   class MyNode(NodeCoreBase):
       def __init__(self, container: ModelONEXContainer):  # ✅ Correct
           super().__init__(container)
   ```

5. **Use thread-local or separate instances**
   ```python
   # Each thread gets its own instance
   node = NodeCompute(container)
   ```

6. **Use protocol names for DI**
   ```python
   event_bus = container.get_service("ProtocolEventBus")
   ```

7. **Use duck typing with protocols**
   ```python
   # Just use the protocol interface directly
   service.publish(event)
   ```

---

## Quick Reference Commands

### Development

```bash
# Setup
poetry install
pre-commit install

# Cleanup
poetry run python scripts/cleanup.py --tmp-only       # Clean tmp/ only (preserves caches) - USE THIS!
poetry run python scripts/cleanup.py                  # FULL cleanup (deletes ALL caches - slow rebuild!)
poetry run python scripts/cleanup.py --remove-from-git --tmp-only  # Remove tracked tmp files from git
poetry run python scripts/cleanup.py --dry-run        # Preview what would be cleaned
poetry run python scripts/cleanup.py --verbose        # Detailed output

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
poetry update                               # Update dependencies
poetry show                                 # List dependencies
```

### CI/CD

- **GitHub Actions**: `.github/workflows/test.yml`
- **20 Parallel Splits**: Each split runs subset of tests
- **Coverage Required**: 60% minimum
- **Timeout Protection**: 60s per test

---

## Recent Updates (v0.4.0)

### v0.4.0 - Node Architecture Overhaul

- ✅ **NodeReducer and NodeOrchestrator are now PRIMARY** - FSM/workflow-driven implementations
- ✅ **"Declarative" suffix removed** - `NodeReducerDeclarative` → `NodeReducer`, `NodeOrchestratorDeclarative` → `NodeOrchestrator`
- ✅ **Unified import path** - All nodes: `from omnibase_core.nodes import NodeCompute, NodeReducer, NodeOrchestrator, NodeEffect`
- ✅ **Input/Output models exported** - `ModelComputeInput`, `ModelReducerInput`, etc. available from `omnibase_core.nodes`
- ✅ **Public enums exported** - Reducer and Orchestrator enums available from `omnibase_core.nodes`

### v0.3.6 - Foundation

- ✅ **Enhanced cleanup.py script** - Added `tmp/` cleanup with git index removal and `.venv` exclusion
- ✅ **Updated .gitignore** - Added `tmp/` to ignore list for temporary files
- ✅ **Pre-push hook** - Automated cleanup before every push using Python script
- ✅ **Removed omnibase_spi dependency** - v0.3.6 transition to dependency inversion (SPI now depends on Core)
- ✅ Added container types documentation (ModelContainer vs ModelONEXContainer)
- ✅ Fixed formatter conflicts (isort/ruff) with --filter-files flag
- ✅ Comprehensive test suite with 12,000+ tests (12,198 collected)
- ✅ Increased CI splits from 10 to 12 to 20 for better resource management
- ✅ Fixed event loop hangs in CI
- ✅ Updated security dependencies (pypdf 6.0+, starlette 0.48.0+)
- ✅ Reorganized documentation structure
- ✅ Added comprehensive node building guides
- ✅ **Added CI Performance Benchmarks** - Expected runtime per split with investigation guide

---

**Last Updated**: 2025-12-05
**Project Version**: 0.4.0
**Python Version**: 3.12+
**Branch**: main

---

**Ready to build?** → [Node Building Guide](docs/guides/node-building/README.md) ⭐
**Need help?** → [Documentation Index](docs/INDEX.md)
**Want to contribute?** → [Contributing Guide](CONTRIBUTING.md)
