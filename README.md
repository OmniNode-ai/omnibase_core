# ONEX Core Framework (omnibase_core)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Framework: Core](https://img.shields.io/badge/framework-core-purple.svg)](https://github.com/OmniNode-ai/omnibase_core)
[![Node Types: 4](https://img.shields.io/badge/node%20types-4-blue.svg)](https://github.com/OmniNode-ai/omnibase_core)

Foundational implementations for the ONEX framework, providing base classes, dependency injection, and essential models.

## Overview

This repository contains the core building blocks that all ONEX tools and services inherit from. It implements the contracts defined in `omnibase_spi` and provides the foundational architecture for the 4-node ONEX pattern.

## Architecture Principles

- **Protocol-Driven Dependency Injection**: Uses ModelONEXContainer with `container.get_service("ProtocolName")` pattern
- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per tool
- **Structured Error Handling**: ModelOnexError with Pydantic models for consistent error management
- **Event-Driven Processing**: ModelEventEnvelope for inter-service communication

## Repository Structure

```text
src/omnibase_core/
├── infrastructure/                 # Node base classes
│   └── node_core_base.py          # Core base class with built-in features
├── nodes/                          # Specialized node implementations
│   ├── node_compute.py            # COMPUTE node base class
│   ├── node_effect.py             # EFFECT node base class
│   ├── node_reducer.py            # REDUCER node base class
│   └── node_orchestrator.py       # ORCHESTRATOR node base class
├── models/                         # Pydantic models
│   ├── container/                 # Container models
│   │   └── model_onex_container.py  # Protocol-driven DI container
│   ├── events/                    # Event models
│   │   └── model_event_envelope.py  # Event communication envelope
│   └── errors/                    # Error models
│       └── model_onex_error.py    # Structured error model
├── enums/                         # Core enumerations
│   ├── enum_health_status.py     # Health status values
│   ├── enum_node_type.py         # Node type classifications
│   └── enum_core_error_code.py   # Error code classifications
├── decorators/                    # Utility decorators
│   └── error_handling.py         # @standard_error_handling decorator
├── mixins/                        # Reusable behavior mixins
│   ├── mixin_discovery_responder.py  # Service discovery
│   ├── mixin_event_handler.py        # Event handling
│   └── mixin_workflow_support.py     # Workflow support
└── examples/                      # Example usage scripts
    ├── contract_validator_usage.py    # Contract validation examples
    ├── field_accessor_migration.py    # Field accessor migration guide
    ├── mixin_discovery_usage.py       # Mixin system usage examples
    ├── practical_migration_example.py # Migration patterns and examples
    └── validation_usage_example.py    # Validation system examples
```

## Concurrency and Thread Safety

⚠️ **Important**: Most ONEX node components are **NOT thread-safe by default**.

For production multi-threaded environments, see **[docs/THREADING.md](docs/guides/THREADING.md)** for:

- **Thread safety guarantees** for each component
- **Synchronization patterns** and mitigation strategies
- **Production checklist** for concurrent deployments
- **Code examples** of thread-safe wrappers

### Key Thread Safety Warnings

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

See [docs/THREADING.md](docs/guides/THREADING.md) for complete guidelines and mitigation strategies.

## Why Poetry?

**This project uses Poetry as the mandated package manager for all ONEX projects.**

### Benefits:
- **Dependency Isolation**: Poetry manages virtual environments automatically
- **Reproducible Builds**: Lock file ensures consistency across all environments
- **Unified Tooling**: Single tool for dependency management, virtual environments, and task execution
- **ONEX Standards**: Required for all ONEX framework projects

### Key Principles:
✅ **ALWAYS use `poetry run` for Python commands**
✅ **ALWAYS use `poetry add` for dependencies**
✅ **ALWAYS use `poetry install` for setup**

❌ **NEVER use `pip install`**
❌ **NEVER use direct `python` commands**
❌ **NEVER manually manage virtual environments**

## Documentation

**📚 Complete Documentation**: [docs/INDEX.md](docs/INDEX.md)

### Quick Links

| For... | Start Here | Time |
|--------|-----------|------|
| **New Developers** | [Getting Started Guide](docs/getting-started/) | 15 min |
| **Building Nodes** | [Node Building Guide](docs/guides/node-building/README.md) ⭐ | 30-60 min |
| **Understanding Architecture** | [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) | 30 min |
| **Reference & Templates** | [Node Templates](docs/reference/templates/) | - |
| **Error Handling** | [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md) | 20 min |
| **Thread Safety** | [Threading Guide](docs/guides/THREADING.md) | 15 min |

### Node Building Guide ⭐ **Recommended Starting Point**

Complete guide to building ONEX nodes - perfect for developers and AI agents:

1. [What is a Node?](docs/guides/node-building/01_WHAT_IS_A_NODE.md) (5 min)
2. [Node Types](docs/guides/node-building/02_NODE_TYPES.md) (10 min)
3. [COMPUTE Node Tutorial](docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) (30 min)
4. [EFFECT, REDUCER, ORCHESTRATOR Tutorials](docs/guides/node-building/) (coming soon)

**See [Documentation Index](docs/INDEX.md) for complete navigation.**

## Quick Start

```bash
# Install all dependencies (including dev dependencies)
poetry install

# Run tests
poetry run pytest tests/

# Run type checking
poetry run mypy src/omnibase_core/

# Run code formatting
poetry run black src/ tests/
poetry run isort src/ tests/

# Add a new dependency
poetry add package-name

# Add a dev dependency
poetry add --group dev package-name
```

### Your First Node

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.model_compute_input import ModelComputeInput
from omnibase_core.models.model_compute_output import ModelComputeOutput

class NodeMyServiceCompute(NodeCompute):
    """
    My first COMPUTE node.

    Built-in features from NodeCompute:
    - Automatic caching with TTL and max size controls
    - Circuit breaker for fault tolerance
    - Result validation with Pydantic models
    - Error handling with structured errors
    - Health checks and monitoring
    """

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate
        # Your business-specific initialization here

    async def execute_compute(
        self,
        input_data: ModelComputeInput
    ) -> ModelComputeOutput:
        """Transform input data with automatic caching and validation."""
        # Access validated input
        value = input_data.operation_data.get("value", 0)

        # Perform computation
        result = value * 2

        # Return validated output
        return ModelComputeOutput(
            success=True,
            result={"result": result}
        )
```

**Next**: Follow the [COMPUTE Node Tutorial](docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) for a complete walkthrough.

## Setup Tasks

### 1. Initialize Git Repository
```bash
# From the project root directory
git init
git add .
git commit -m "Initial commit: ONEX core framework implementation"
```

### 2. Python Packaging Configuration
The project uses Poetry for package management. Configuration is in `pyproject.toml` with Poetry-specific sections for:
- Build system configuration
- Project metadata and dependencies
- Development dependencies
- Tool configurations (ruff, pytest, mypy, etc.)

### 3. Strip Legacy Registry Dependencies from ModelONEXContainer
**Current Issue**: ModelONEXContainer still has references to legacy registries that need removal:

```python
# TODO: Remove these legacy registry imports and dependencies
# from omnibase.core.registries.* import ...
# self._specialized_registries = {...}
```

**Action Required**: Update `ModelONEXContainer` to use pure protocol-based resolution:
```python
def get_service(self, protocol_name: str) -> Any:
    """Get service by protocol name, not registry lookup."""
    # Clean protocol-based resolution only
```

### 4. Create Package Structure
```bash
# Create all missing __init__.py files
find src/omnibase_core -type d -exec touch {}/__init__.py \;

# Create consolidated exports in infrastructure_service_bases.py
# (Already complete - exports all 4 node base classes)
```

### 5. Set Up Development Environment
```bash
# Install all dependencies (Poetry manages virtual environment automatically)
poetry install

# Alternatively, activate Poetry's virtual environment shell
poetry shell

# Add local dependencies (if omnibase_spi is a local package)
poetry add ../omnibase_spi --editable
```

### 6. Configure Testing Framework
Create `tests/` directory structure:
```bash
mkdir -p tests/{unit,integration,examples}
touch tests/__init__.py
touch tests/test_node_services.py
touch tests/test_onex_container.py
touch tests/test_error_handling.py
```

Run tests with Poetry:
```bash
# Run all tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/test_node_services.py -v

# Run with coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing
```

### 7. Explore Example Scripts
The `examples/` directory contains usage examples demonstrating framework patterns:

**Available Examples**:
- `contract_validator_usage.py` - Contract validation patterns
- `field_accessor_migration.py` - Field accessor migration guide
- `mixin_discovery_usage.py` - Mixin system usage patterns
- `practical_migration_example.py` - Real-world migration examples
- `validation_usage_example.py` - Validation system demonstrations

**Node Implementation Examples**: See the [Node Building Guide](docs/guides/node-building/) for complete tutorials on building EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes

## Core Framework Components

### 1. Node Base Classes
The foundation of all ONEX tools:

```python
# Option 1: Import specific node type directly (RECOMMENDED)
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyTool(NodeEffect):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # 80+ lines of boilerplate eliminated!

# Option 2: Import base class for custom nodes
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

class MyCustomNode(NodeCoreBase):
    """Use this when building a custom node type."""
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
```

### 2. Protocol-Driven Dependency Injection
```python
# Get services by protocol interface
event_bus = container.get_service("ProtocolEventBus")
logger = container.get_service("ProtocolLogger")
```

### 3. Structured Error Handling
```python
from omnibase_core.decorators.error_handling import standard_error_handling
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

@standard_error_handling  # Eliminates 6+ lines of try/catch boilerplate
async def my_operation(self):
    if error_condition:
        raise ModelOnexError(
            message="Operation failed",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            context={"additional": "context"}
        )
```

### 4. Event-Driven Communication
```python
from omnibase_core.models.model_effect_input import ModelEffectInput
from omnibase_core.models.model_effect_output import ModelEffectOutput

# Process events through envelope pattern
async def execute_effect(
    self,
    input_data: ModelEffectInput
) -> ModelEffectOutput:
    envelope_payload = input_data.operation_data.get("envelope_payload", {})
    # Event-driven processing logic
    return ModelEffectOutput(success=True, result={})
```

## Development Guidelines

### 1. Node Implementation Pattern
```python
from omnibase_core.nodes.node_compute import NodeCompute  # Or NodeEffect, NodeReducer, NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class YourTool(NodeCompute):  # Choose: NodeEffect, NodeCompute, NodeReducer, NodeOrchestrator
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate

        # Protocol-based dependency resolution
        self.logger = container.get_service("ProtocolLogger")
        self.event_bus = container.get_service("ProtocolEventBus")

        # Business-specific initialization only
```

### 2. Error Handling Requirements
- **NEVER use generic Exception** - always ModelOnexError with proper error codes
- **Use @standard_error_handling** decorator to eliminate boilerplate
- **Chain exceptions**: `raise ModelOnexError(...) from original_exception`

### 3. Dependency Resolution
- **Protocol names only**: `container.get_service("ProtocolEventBus")`
- **No isinstance checks**: Use duck typing through protocols
- **No registry dependencies**: Pure protocol-based resolution

## Integration with omnibase_spi

This repository implements the protocols defined in omnibase_spi:

```python
# Protocol definition (in omnibase_spi)
class ProtocolEventBus(Protocol):
    def publish(self, event: ModelEvent) -> None: ...

# Implementation (in omnibase_core)  
class EventBusService(ProtocolEventBus):
    def publish(self, event: ModelEvent) -> None:
        # Concrete implementation
```

## Learning Path

### Beginner Path (First Time with ONEX)

1. **Understand Basics** (30 min)
   - Read: [What is a Node?](docs/guides/node-building/01_WHAT_IS_A_NODE.md)
   - Read: [Node Types](docs/guides/node-building/02_NODE_TYPES.md)

2. **Build Your First Node** (30 min)
   - Tutorial: [COMPUTE Node Tutorial](docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md)
   - Practice: Build a simple calculator node

3. **Explore Architecture** (30 min)
   - Read: [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

### Intermediate Path

1. **Master All Node Types** (2-3 hours)
   - [EFFECT Node Tutorial](docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md) (coming soon)
   - [REDUCER Node Tutorial](docs/guides/node-building/05_REDUCER_NODE_TUTORIAL.md) (coming soon)
   - [ORCHESTRATOR Node Tutorial](docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md) (coming soon)

2. **Best Practices** (1 hour)
   - [Error Handling Best Practices](docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md)
   - [Threading Guide](docs/guides/THREADING.md)
   - [Patterns Catalog](docs/guides/node-building/07_PATTERNS_CATALOG.md) (coming soon)

### Advanced Path

1. **Deep Dives**
   - [Subcontract Architecture](docs/architecture/SUBCONTRACT_ARCHITECTURE.md)
   - [Mixin System](docs/reference/architecture-research/)
   - Production Templates: [Node Templates](docs/reference/templates/)

## Next Steps

### Immediate Tasks (For New Projects)
1. **Install omnibase_core**: `poetry add omnibase_core`
2. **Follow Quick Start**: Build your first node (above)
3. **Read Documentation**: [Node Building Guide](docs/guides/node-building/README.md)

### For Contributors

1. **Development Setup**: `poetry install`
2. **Run Tests**: `poetry run pytest tests/`
3. **Quality Tools**: `poetry run mypy src/`, `poetry run black src/`
4. **See**: Development Workflow (coming soon)

## Architecture Benefits

- **80+ Lines Less Code**: Base classes eliminate initialization boilerplate
- **Type Safety**: Protocol-driven DI with full type checking
- **Event-Driven**: Scalable inter-service communication
- **Structured Errors**: Consistent error handling with rich context
- **Zero Registry Coupling**: Clean protocol-based dependencies

This repository provides the foundational layer that makes ONEX tool development fast, type-safe, and consistent across the entire ecosystem.

---

**Ready to build?** → [Node Building Guide](docs/guides/node-building/README.md) ⭐

**Need help?** → [Documentation Index](docs/INDEX.md)

**Want to contribute?** → [Contributing Guide](CONTRIBUTING.md) (coming soon)
