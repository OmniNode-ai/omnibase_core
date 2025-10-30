# CLAUDE.md - Omnibase Core Project Instructions

> **Version**: 0.2.0 (Release Branch: `release/0.2.0`)
> **Python**: 3.12+
> **Framework**: ONEX Core - Foundational implementations for the ONEX architecture

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Python Development - Poetry](#python-development---always-use-poetry)
3. [Architecture Fundamentals](#architecture-fundamentals)
4. [Project Structure](#project-structure)
5. [Development Workflow](#development-workflow)
6. [Testing Guide](#testing-guide)
7. [Code Quality](#code-quality)
8. [Key Patterns & Conventions](#key-patterns--conventions)
9. [Thread Safety](#thread-safety)
10. [Documentation](#documentation)
11. [Common Pitfalls](#common-pitfalls)

---

## Project Overview

**omnibase_core** provides the foundational building blocks for the ONEX framework:

- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Protocol-Driven DI**: Container-based dependency injection with `container.get_service("ProtocolName")`
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per node
- **Structured Errors**: ModelOnexError with Pydantic models for consistent error handling
- **Event-Driven**: ModelEventEnvelope for inter-service communication
- **Comprehensive Testing**: 400+ tests with 60%+ coverage requirement
- **Strict Type Checking**: 100% mypy strict mode compliance (0 errors across 1865 source files)

### Dependencies

- **Core**: omnibase_spi (v0.1.1) - Protocol definitions
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
- Include explicit examples showing Poetry usage
- Reference this CLAUDE.md for project-specific conventions

---

## Architecture Fundamentals

### ONEX Four-Node Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│   (Input)   │    │ (Process)   │    │(Aggregate)  │    │(Coordinate) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Data Flow**: Unidirectional left-to-right, no backwards dependencies.

#### Node Responsibilities

| Node Type | Purpose | Examples |
|-----------|---------|----------|
| **EFFECT** | External interactions (I/O) | API calls, database ops, file system, message queues |
| **COMPUTE** | Data processing & transformation | Calculations, validations, data mapping |
| **REDUCER** | State aggregation & management | State machines, accumulators, event reduction |
| **ORCHESTRATOR** | Workflow coordination | Multi-step workflows, parallel execution, error recovery |

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

### Base Classes Usage

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCoreBase):
    """COMPUTE node example."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate

        # Protocol-based dependencies
        self.logger = container.get_service("ProtocolLogger")

        # Your business logic initialization
```

**CRITICAL**: Always call `super().__init__(container)` - this eliminates 80+ lines of boilerplate.

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

---

## Project Structure

```
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
│   ├── mixins/                 # Reusable behavior mixins
│   ├── models/                 # Pydantic models
│   ├── nodes/                  # Node implementations
│   ├── primitives/             # Primitive types
│   ├── types/                  # Type definitions
│   ├── utils/                  # Utility functions
│   ├── validation/             # Validation framework
│   └── validators/             # Specific validators
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests (400+ tests)
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

- **Unit Tests**: 400+ tests in `tests/unit/` - test individual components in isolation
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
- 12 parallel splits across isolated runners
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

## Code Quality

### Type Checking

**Status**: ✅ 100% strict mypy compliance (0 errors in 1865 source files)

```bash
# Type check entire codebase
poetry run mypy src/omnibase_core/

# Type check specific file
poetry run mypy src/omnibase_core/models/common/model_typed_mapping.py
```

**Configuration**: See `[tool.mypy]` in pyproject.toml

**Strict Mode Features**:
- `disallow_untyped_defs = true` - All functions must have type annotations
- `warn_return_any = true` - Warns on functions returning Any
- `warn_unused_configs = true` - Detects unused mypy configuration
- Pydantic plugin enabled for model validation

**Enforcement**:
- ✅ Pre-commit hooks (strict configuration)
- ✅ CI/CD pipeline (strict configuration)
- ✅ Local development (strict configuration)

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

**Always use ModelOnexError, never generic Exception:**

```python
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode

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

**Use @standard_error_handling decorator:**

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
| **New Developers** | [Getting Started Guide](docs/getting-started/) | 15 min |
| **Building Nodes** | [Node Building Guide](docs/guides/node-building/README.md) ⭐ | 30-60 min |
| **Understanding Architecture** | [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) | 30 min |
| **Reference & Templates** | [Node Templates](docs/reference/templates/) | - |
| **Error Handling** | [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md) | 20 min |
| **Thread Safety** | [Threading Guide](docs/guides/THREADING.md) | 15 min |

### Node Building Guide ⭐ CRITICAL

**Recommended starting point for developers and AI agents:**

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
- **12 Parallel Splits**: Each split runs subset of tests
- **Coverage Required**: 60% minimum
- **Timeout Protection**: 60s per test

---

## Recent Updates (v0.2.0)

- ✅ **Upgraded to omnibase_spi v0.2.0** - 9 new protocols for enhanced type safety
- ✅ Added container types documentation (ModelContainer vs ModelONEXContainer)
- ✅ Fixed formatter conflicts (isort/ruff) with --filter-files flag
- ✅ Added 400+ comprehensive tests (commit: 0c28533e)
- ✅ Increased CI splits from 10 to 12 for better resource management
- ✅ Fixed event loop hangs in CI
- ✅ Updated security dependencies (pypdf 6.0+, starlette 0.48.0+)
- ✅ Reorganized documentation structure
- ✅ Added comprehensive node building guides

---

**Last Updated**: 2025-10-30
**Project Version**: 0.2.0
**Python Version**: 3.12+
**Branch**: release/0.2.0

---

**Ready to build?** → [Node Building Guide](docs/guides/node-building/README.md) ⭐
**Need help?** → [Documentation Index](docs/INDEX.md)
**Want to contribute?** → [Contributing Guide](CONTRIBUTING.md)
