# CLAUDE.md - Omnibase Core Project Instructions

> **Version**: 0.4.0 | **Python**: 3.12+ | **Framework**: ONEX Core
>
> **No Backwards Compatibility**: Until v0.4.0 is released, breaking changes may occur between commits.
>
> **Shared Infrastructure**: See **`~/.claude/CLAUDE.md`** for common OmniNode infrastructure (PostgreSQL, Kafka/Redpanda, Docker networking, environment variables).

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

### Protocol-Driven Dependency Injection

```python
# Get services by protocol interface (never by concrete class)
event_bus = container.get_service("ProtocolEventBus")
logger = container.get_service("ProtocolLogger")
```

**Key Principles**: Use protocol names (not concrete classes), duck typing (no isinstance checks), pure protocol-based resolution.

### Contract Loading with FileRegistry

```python
from omnibase_core.runtime.file_registry import FileRegistry
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
from omnibase_core.decorators.error_handling import standard_error_handling

@standard_error_handling  # Eliminates 6+ lines of try/catch boilerplate
async def my_operation(self):
    pass
```

### Mixin System

```python
from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder

class MyNode(NodeCoreBase, MixinDiscoveryResponder):
    """Node with discovery capabilities."""
    pass
```

**Available Mixins**: `MixinDiscoveryResponder`, `MixinEventHandler`, `MixinEventListener`, `MixinNodeExecutor`, `MixinNodeLifecycle`, `MixinRequestResponseIntrospection`, `MixinWorkflowExecution`

### Pydantic `from_attributes=True` for Value Objects

Add `from_attributes=True` to `ConfigDict` for immutable value objects nested in other Pydantic models used with pytest-xdist parallel execution.

**Why**: pytest-xdist workers import classes independently. Without `from_attributes=True`, Pydantic rejects valid instances due to class identity differences.

```python
class ModelSemVer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)
    major: int
    minor: int
    patch: int
```

To find models using this pattern: `grep -r "from_attributes.*True" src/omnibase_core/models/`

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

**Last Updated**: 2025-12-19 | **Version**: 0.4.0 | **Python**: 3.12+

**Ready to build?** → [Node Building Guide](docs/guides/node-building/README.md)
**Need help?** → [Documentation Index](docs/INDEX.md)
**Want to contribute?** → [Contributing Guide](CONTRIBUTING.md)
