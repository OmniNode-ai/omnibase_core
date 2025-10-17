# ONEX Core Framework (omnibase_core)

Foundational implementations for the ONEX framework, providing base classes, dependency injection, and essential models.

## Overview

This repository contains the core building blocks that all ONEX tools and services inherit from. It implements the contracts defined in `omnibase_spi` and provides the foundational architecture for the 4-node ONEX pattern.

## Architecture Principles

- **Protocol-Driven Dependency Injection**: Uses ONEXContainer with `container.get_service("ProtocolName")` pattern
- **4-Node Architecture**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow pattern
- **Zero Boilerplate**: Base classes eliminate 80+ lines of initialization code per tool
- **Structured Error Handling**: OnexError with Pydantic models for consistent error management
- **Event-Driven Processing**: ModelEventEnvelope for inter-service communication

## Repository Structure

```
src/omnibase_core/
├── core/                           # Core framework components
│   ├── infrastructure_service_bases.py  # Consolidated 4-node base class exports
│   ├── node_effect_service.py           # EFFECT node base class
│   ├── node_compute_service.py          # COMPUTE node base class  
│   ├── node_reducer_service.py          # REDUCER node base class
│   ├── node_orchestrator_service.py     # ORCHESTRATOR node base class
│   ├── onex_container.py                # Protocol-driven DI container
│   ├── monadic/                         # Result type and error handling
│   └── mixins/                          # Reusable behavior mixins
├── model/
│   ├── core/                           # Core data models
│   │   ├── model_event_envelope.py    # Event communication envelope
│   │   ├── model_health_status.py     # Service health reporting
│   │   └── model_semver.py            # Semantic versioning
│   └── coordination/                   # Service coordination models
├── enums/                             # Core enumerations
│   ├── enum_health_status.py         # Health status values
│   ├── enum_node_type.py             # Node type classifications
│   └── enum_node_current_status.py   # Node operational status
├── exceptions/                        # Error handling system
│   ├── base_onex_error.py            # OnexError exception class
│   └── model_onex_error.py           # Pydantic error model
├── decorators/                        # Utility decorators
│   └── error_handling.py             # @standard_error_handling decorator
└── examples/                          # Canonical node implementations
    ├── tool_infrastructure_consul_adapter_effect/     # EFFECT example
    ├── tool_infrastructure_message_aggregator_compute/ # COMPUTE example
    ├── tool_infrastructure_reducer/                   # REDUCER example
    └── tool_infrastructure_orchestrator/              # ORCHESTRATOR example
```

## Concurrency and Thread Safety

⚠️ **Important**: Most ONEX node components are **NOT thread-safe by default**.

For production multi-threaded environments, see **[docs/THREADING.md](docs/THREADING.md)** for:

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

See [docs/THREADING.md](docs/THREADING.md) for complete guidelines and mitigation strategies.

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

### 3. Strip Legacy Registry Dependencies from ONEXContainer
**Current Issue**: ONEXContainer still has references to legacy registries that need removal:

```python
# TODO: Remove these legacy registry imports and dependencies
# from omnibase.core.registries.* import ...
# self._specialized_registries = {...}
```

**Action Required**: Update `ONEXContainer` to use pure protocol-based resolution:
```python
def get_service(self, protocol_name: str) -> Any:
    """Get service by protocol name, not registry lookup."""
    # Clean protocol-based resolution only
```

### 4. Create Package Structure
```bash
# Create all missing __init__.py files
find src/omnibase -type d -exec touch {}/__init__.py \;

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

### 7. Validate Example Node Implementations
The canonical examples in `examples/` demonstrate proper ONEX architecture:

**EFFECT Node Pattern** (`tool_infrastructure_consul_adapter_effect`):
```python
class ToolInfrastructureConsulAdapterEffect(NodeEffectService):
    def __init__(self, container: ONEXContainer):
        super().__init__(container)  # All boilerplate handled!
        # Only business logic here
```

**COMPUTE Node Pattern** (`tool_infrastructure_message_aggregator_compute`):
- Inherits from `NodeComputeService`
- Data processing and aggregation logic
- State management with PostgreSQL persistence

**REDUCER Node Pattern** (`tool_infrastructure_reducer`):
- Inherits from `NodeReducerService`  
- State aggregation with FSM (Finite State Machine)
- Infrastructure adapter coordination

**ORCHESTRATOR Node Pattern** (`tool_infrastructure_orchestrator`):
- Inherits from `NodeOrchestratorService`
- Workflow coordination and service orchestration
- Infrastructure connection management

## Core Framework Components

### 1. Node Service Base Classes
The foundation of all ONEX tools:

```python
from omnibase.core.infrastructure_service_bases import (
    NodeEffectService,      # External interactions (APIs, databases, files)
    NodeComputeService,     # Data processing and computation  
    NodeReducerService,     # State aggregation and management
    NodeOrchestratorService # Workflow coordination
)

class MyTool(NodeEffectService):
    def __init__(self, container: ONEXContainer):
        super().__init__(container)  # 80+ lines of boilerplate eliminated!
```

### 2. Protocol-Driven Dependency Injection
```python
# Get services by protocol interface
event_bus = container.get_service("ProtocolEventBus")
logger = container.get_service("ProtocolLogger")
```

### 3. Structured Error Handling
```python
from omnibase.decorators.error_handling import standard_error_handling
from omnibase.exceptions.base_onex_error import OnexError

@standard_error_handling  # Eliminates 6+ lines of try/catch boilerplate
async def my_operation(self):
    if error_condition:
        raise OnexError(
            message="Operation failed",
            error_code=CoreErrorCode.OPERATION_FAILED
        )
```

### 4. Event-Driven Communication
```python
from omnibase.model.core.model_event_envelope import ModelEventEnvelope

# Process events through envelope pattern
async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
    envelope_payload = input_data.operation_data.get("envelope_payload", {})
    # Event-driven processing logic
```

## Development Guidelines

### 1. Node Implementation Pattern
```python
class YourTool(NodeTypeService):  # EFFECT/COMPUTE/REDUCER/ORCHESTRATOR
    def __init__(self, container: ONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate

        # Protocol-based dependency resolution
        self.logger = container.get_service("ProtocolLogger")
        self.event_bus = container.get_service("ProtocolEventBus")

        # Business-specific initialization only
```

### 2. Error Handling Requirements
- **NEVER use generic Exception** - always OnexError with proper error codes
- **Use @standard_error_handling** decorator to eliminate boilerplate
- **Chain exceptions**: `raise OnexError(...) from original_exception`

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

## Next Steps

### Immediate Tasks (Required for functionality)
1. **Strip legacy registry dependencies** from ONEXContainer
2. **Create complete package structure** with all __init__.py files
3. **Verify Python packaging** - Poetry configuration in pyproject.toml is already set up
4. **Initialize git repository** and commit current state

### Development Setup (Required for development)
5. **Set up development environment** with `poetry install`
6. **Create test framework** for validating base classes and DI container
7. **Run code quality tools** - `poetry run mypy`, `poetry run black`, etc.

### Documentation and Examples (Enhancement)
8. **Create comprehensive tests** for all base classes and error handling
9. **Document canonical patterns** from example implementations
10. **Create migration guide** for converting existing tools to new architecture

## Architecture Benefits

- **80+ Lines Less Code**: Base classes eliminate initialization boilerplate
- **Type Safety**: Protocol-driven DI with full type checking
- **Event-Driven**: Scalable inter-service communication
- **Structured Errors**: Consistent error handling with rich context
- **Zero Registry Coupling**: Clean protocol-based dependencies

This repository provides the foundational layer that makes ONEX tool development fast, type-safe, and consistent across the entire ecosystem.
# Test change
