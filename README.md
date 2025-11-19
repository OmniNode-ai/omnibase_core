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

### Core Framework Structure

**Note**: This is a high-level view. The framework contains 1,865 source files organized into these main directories:

```text
src/omnibase_core/
├── constants/                  # Project constants and configuration
├── container/                  # DI container implementation
├── decorators/                 # Utility decorators
│   └── error_handling.py       # @standard_error_handling decorator
├── discovery/                  # Service discovery mechanisms
├── enums/                      # Core enumerations (325+ enum files)
│   ├── enum_core_error_code.py
│   ├── enum_health_status.py
│   ├── enum_node_type.py
│   └── ... (many more)
├── errors/                     # Error handling utilities
├── events/                     # Event system implementation
├── infrastructure/             # Base classes and core infrastructure
│   ├── node_core_base.py       # Core base class for all nodes (RECOMMENDED)
│   ├── node_base.py            # Base node functionality
│   ├── infrastructure_bases.py # Production-ready service wrappers
│   ├── computation_cache.py    # Caching utilities
│   ├── load_balancer.py        # Load balancing
│   └── node_config_provider.py # Configuration management
├── logging/                    # Logging utilities
├── mixins/                     # Reusable behavior mixins (45+ mixin files)
│   ├── mixin_discovery_responder.py
│   ├── mixin_event_handler.py
│   ├── mixin_workflow_support.py
│   └── ... (many more)
├── models/                     # Pydantic models (60+ subdirectories)
│   ├── container/
│   │   └── model_onex_container.py  # Protocol-driven DI container
│   ├── errors/
│   │   └── model_onex_error.py      # Structured error model
│   ├── events/
│   │   └── model_event_envelope.py  # Event communication envelope
│   ├── nodes/
│   │   └── node_services/
│   │       ├── model_service_compute.py
│   │       ├── model_service_effect.py
│   │       ├── model_service_orchestrator.py
│   │       └── model_service_reducer.py
│   └── ... (configuration, contracts, fsm, workflow, etc.)
├── nodes/                      # Node implementations
│   ├── node_compute.py                  # COMPUTE node base class
│   ├── node_effect.py                   # EFFECT node base class
│   ├── node_orchestrator.py             # ORCHESTRATOR node base class
│   ├── node_orchestrator_declarative.py # Declarative workflow support
│   ├── node_reducer.py                  # REDUCER node base class
│   └── node_reducer_declarative.py      # Declarative FSM support
├── primitives/                 # Primitive types
├── types/                      # Type definitions (94+ type files)
├── utils/                      # Utility functions (16+ util files)
└── validation/                 # Validation framework (20+ validation files)
```

### Production Node Structure

When building production nodes, follow this directory structure:

```text
{REPOSITORY_NAME}/
└── nodes/
    └── node_{domain}_{microservice_name}_{type}/
        ├── __init__.py
        ├── v1_0_0/
        │   ├── __init__.py
        │   ├── node.py                    # Main node implementation
        │   ├── config.py                  # Configuration
        │   ├── contracts/
        │   │   └── subcontracts/
        │   │       # Subcontracts are Pydantic models in omnibase_core
        │   │       # See "Available Subcontracts" section below
        │   ├── models/
        │   │   ├── model_*_input.py       # Typed input model
        │   │   ├── model_*_output.py      # Typed output model
        │   │   └── model_*_config.py      # Configuration model
        │   ├── enums/
        │   │   └── enum_*_operation_type.py  # Operation types
        │   ├── utils/
        │   │   └── (domain-specific utilities)
        │   └── manifest.yaml              # Node metadata, deps, deployment specs
        └── tests/
            ├── __init__.py
            ├── unit/
            │   └── test_node.py
            └── integration/
                └── test_integration.py
```

## Manifest Models

ONEX provides **structured manifest models** for validating and working with system-wide configuration files.

### Available Manifests

#### ModelMixinMetadata

**Purpose**: Load, validate, and query mixin metadata from `mixin_metadata.yaml`

**Location**: `src/omnibase_core/models/core/model_mixin_metadata.py`

**Features**:
- 11 nested Pydantic models for complete mixin metadata
- Version management with semantic versioning
- Configuration schema validation
- Code pattern definitions for generation
- Performance characteristics tracking
- Compatibility validation between mixins

**Usage Example**:
```python
from pathlib import Path
from omnibase_core.models.core.model_mixin_metadata import ModelMixinMetadataCollection

# Load all mixin metadata
collection = ModelMixinMetadataCollection.load_from_yaml(
    Path("src/omnibase_core/mixins/mixin_metadata.yaml")
)

# Get specific mixin
retry_mixin = collection.get_mixin("retry")
print(f"Version: {retry_mixin.version}")
print(f"Category: {retry_mixin.category}")

# Check compatibility
mixins_to_use = ["retry", "circuit_breaker", "caching"]
is_compatible, conflicts = collection.validate_compatibility(mixins_to_use)

# Get all mixins by category
flow_control_mixins = collection.get_mixins_by_category("flow_control")
```

#### ModelDockerComposeManifest

**Purpose**: Validate and manipulate complete `docker-compose.yaml` files

**Location**: `src/omnibase_core/models/docker/model_docker_compose_manifest.py`

**Features**:
- Integrates 16 existing Docker models into unified structure
- Service, network, volume, config, and secret definitions
- Dependency validation (circular dependency detection)
- Port conflict detection
- Load from/save to YAML with full validation

**Usage Example**:
```python
from pathlib import Path
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest
)

# Load from YAML
manifest = ModelDockerComposeManifest.load_from_yaml(
    Path("docker-compose.yaml")
)

# Access services
api_service = manifest.get_service("api")
print(f"Image: {api_service.image}")
print(f"Ports: {api_service.ports}")

# Validate dependencies
dep_warnings = manifest.validate_dependencies()
if dep_warnings:
    print("Dependency issues:", dep_warnings)

# Detect port conflicts
port_warnings = manifest.detect_port_conflicts()
if port_warnings:
    print("Port conflicts:", port_warnings)

# Save to YAML
manifest.save_to_yaml(Path("output.yaml"))
```

**See Also**:
- [Mixin Metadata Tests](tests/unit/models/core/test_model_mixin_metadata.py) - 39 comprehensive tests
- [Docker Compose Manifest Tests](tests/unit/models/docker/test_model_docker_compose_manifest.py) - 25 comprehensive tests

---

## Available Subcontracts (23)

ONEX provides **23 specialized subcontract models** for declarative node configuration. Subcontracts enable nodes to declare their behavior, requirements, and capabilities using Pydantic models instead of imperative code.

**Location**: `src/omnibase_core/models/contracts/subcontracts/`

**Architecture Documentation**: [Subcontract Architecture Guide](docs/architecture/SUBCONTRACT_ARCHITECTURE.md)

### Core Behavioral Subcontracts (6)

Define the fundamental behavior patterns for ONEX nodes:

| Subcontract | Purpose | Primary Node Type | Key Features |
|-------------|---------|-------------------|--------------|
| **ModelFSMSubcontract** | Finite state machine definitions | REDUCER | State transitions, guards, actions |
| **ModelEventTypeSubcontract** | Event type definitions | ALL | Event schemas, versioning, routing |
| **ModelAggregationSubcontract** | Data aggregation rules | REDUCER | Windowing, grouping, rollups |
| **ModelStateManagementSubcontract** | State persistence | REDUCER | Snapshotting, recovery, TTL |
| **ModelRoutingSubcontract** | Message routing | ORCHESTRATOR | Load balancing, routing rules |
| **ModelWorkflowCoordinationSubcontract** | Workflow orchestration | ORCHESTRATOR | Step definitions, dependencies, rollback |

### Infrastructure Subcontracts (6)

Configure infrastructure concerns like caching, events, and fault tolerance:

| Subcontract | Purpose | Primary Node Type | Key Features |
|-------------|---------|-------------------|--------------|
| **ModelCachingSubcontract** | Cache strategies | COMPUTE | TTL, eviction policies, size limits |
| **ModelEventBusSubcontract** | Event bus configuration | ALL | Topics, partitions, serialization |
| **ModelHealthCheckSubcontract** | Health monitoring | ALL | Endpoints, thresholds, dependencies |
| **ModelMetricsSubcontract** | Metrics collection | ALL | Counters, gauges, histograms |
| **ModelLoggingSubcontract** | Logging configuration | ALL | Levels, formats, destinations |
| **ModelCircuitBreakerSubcontract** | Fault tolerance | EFFECT | Thresholds, timeouts, fallbacks |

### Cross-Cutting Subcontracts (7)

Handle cross-cutting concerns that apply to multiple node types:

| Subcontract | Purpose | Primary Node Type | Key Features |
|-------------|---------|-------------------|--------------|
| **ModelRetrySubcontract** | Retry policies | EFFECT | Max attempts, backoff, jitter |
| **ModelSecuritySubcontract** | Security configuration | ALL | Authentication, authorization, encryption |
| **ModelSerializationSubcontract** | Serialization rules | ALL | Formats, codecs, compression |
| **ModelValidationSubcontract** | Validation rules | ALL | Schemas, constraints, sanitization |
| **ModelConfigurationSubcontract** | Configuration management | ALL | Sources, precedence, reloading |
| **ModelObservabilitySubcontract** | Observability | ALL | Tracing, profiling, instrumentation |
| **ModelToolExecutionSubcontract** | Tool execution | ALL | Timeouts, concurrency, isolation |

### Discovery & Introspection Subcontracts (4)

Enable service discovery and runtime introspection:

| Subcontract | Purpose | Primary Node Type | Key Features |
|-------------|---------|-------------------|--------------|
| **ModelDiscoverySubcontract** | Service discovery | ALL | Endpoints, capabilities, versions |
| **ModelIntrospectionSubcontract** | Introspection rules | ALL | Schema exposure, capabilities listing |
| **ModelEventHandlingSubcontract** | Event handling | ALL | Handlers, filters, ordering |
| **ModelLifecycleSubcontract** | Node lifecycle | ALL | Startup, shutdown, health transitions |

### Declarative Mixins with Subcontract Support

Eight mixins support declarative YAML configuration via subcontracts:

| Mixin | Subcontract | Purpose | Usage Pattern |
|-------|-------------|---------|---------------|
| **MixinFSMExecution** | ModelFSMSubcontract | State machine execution | REDUCER nodes with state transitions |
| **MixinCaching** | ModelCachingSubcontract | Cache strategies | COMPUTE nodes with memoization |
| **MixinWorkflowExecution** | ModelWorkflowCoordinationSubcontract | Workflow coordination | ORCHESTRATOR nodes with multi-step workflows |
| **MixinHealthCheck** | ModelHealthCheckSubcontract | Health monitoring | ALL nodes with health endpoints |
| **MixinMetrics** | ModelMetricsSubcontract | Metrics collection | ALL nodes with observability |
| **MixinDiscoveryResponder** | ModelDiscoverySubcontract | Service discovery | ALL nodes with discovery support |
| **MixinIntrospection** | ModelIntrospectionSubcontract | Introspection rules | ALL nodes with schema exposure |
| **MixinEventHandler** | ModelEventHandlingSubcontract | Event handling | ALL nodes with event processing |

### Subcontract Usage Example

```python
from omnibase_core.models.contracts.subcontracts.model_caching_subcontract import ModelCachingSubcontract
from omnibase_core.models.contracts.subcontracts.model_health_check_subcontract import ModelHealthCheckSubcontract

# Define subcontract in your node contract
class MyNodeContract(BaseContract):
    """Node contract with declarative subcontracts."""

    # Caching configuration
    caching: ModelCachingSubcontract = ModelCachingSubcontract(
        cache_ttl_seconds=300,
        max_cache_size=1000,
        eviction_policy="lru"
    )

    # Health check configuration
    health: ModelHealthCheckSubcontract = ModelHealthCheckSubcontract(
        health_check_interval_seconds=30,
        health_check_timeout_seconds=5,
        required_dependencies=["database", "event_bus"]
    )
```

**See Also**:
- [Subcontract Architecture Guide](docs/architecture/SUBCONTRACT_ARCHITECTURE.md) - Complete architecture documentation
- [Declarative Node Migration Guide](docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md) - Migration from imperative to declarative patterns
- [Mixin Metadata](src/omnibase_core/mixins/mixin_metadata.yaml) - Complete mixin-to-subcontract mappings

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
| **Choosing Base Classes** | [Node Class Hierarchy](docs/architecture/NODE_CLASS_HIERARCHY.md) ⭐ | 20 min |
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
# ✅ RECOMMENDED: Use production-ready service wrapper
from omnibase_core.infrastructure.infrastructure_bases import ModelServiceCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.model_compute_input import ModelComputeInput
from omnibase_core.models.model_compute_output import ModelComputeOutput

class NodeMyServiceCompute(ModelServiceCompute):
    """
    My first COMPUTE node using production-ready wrapper.

    Built-in features from ModelServiceCompute:
    - Automatic caching with TTL and max size controls
    - Circuit breaker for fault tolerance
    - Result validation with Pydantic models
    - Error handling with structured errors
    - Health checks and monitoring
    - Event bus integration
    - Metrics tracking
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

### 3. Create Package Structure
```bash
# Create all missing __init__.py files
find src/omnibase_core -type d -exec touch {}/__init__.py \;

# Create consolidated exports in infrastructure_bases.py
# (Currently exports: ModelServiceEffect, ModelServiceCompute)
# (Coming soon: ModelServiceReducer, ModelServiceOrchestrator)
```

### 4. Set Up Development Environment
```bash
# Install all dependencies (Poetry manages virtual environment automatically)
poetry install

# Alternatively, activate Poetry's virtual environment shell
poetry shell

# Add local dependencies (if omnibase_spi is a local package)
poetry add ../omnibase_spi --editable
```

### 5. Configure Testing Framework
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

### 6. Explore Example Scripts
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
# ✅ RECOMMENDED: Production-ready service wrappers (currently available)
from omnibase_core.infrastructure.infrastructure_bases import (
    ModelServiceEffect,    # EFFECT node wrapper (available)
    ModelServiceCompute,   # COMPUTE node wrapper (available)
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Note: ModelServiceReducer and ModelServiceOrchestrator coming soon
# For now, use NodeReducer and NodeOrchestrator from omnibase_core.nodes

class MyDatabaseWriter(ModelServiceEffect):
    """
    Built-in features:
    - Health checks
    - Event bus integration
    - Metrics tracking
    - Standard error handling
    """
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # 80+ lines of boilerplate eliminated!

# ⚙️ ADVANCED: Direct node classes (use when you need lower-level control)
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

class MyCustomEffect(NodeEffect):
    """
    Advanced usage - provides foundation for building custom wrappers.
    Most developers should use ModelServiceEffect instead.
    """
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

# 🔧 EXPERT: Base class for completely custom node types
from omnibase_core.infrastructure.node_core_base import NodeCoreBase

class MyCustomNode(NodeCoreBase):
    """Use this only when building a completely new node type."""
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
```

**When to use which?**

| Base Class | Use When | Features |
|-----------|----------|----------|
| **ModelService*** | Production nodes (95% of cases) | Health checks, event bus, metrics, error handling |
| **Node*** | Custom wrappers or special needs | Core node features, more control |
| **NodeCoreBase** | New node type entirely | Minimal foundation, full control |

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
# ✅ RECOMMENDED: Use production-ready service wrappers (currently available)
from omnibase_core.infrastructure.infrastructure_bases import (
    ModelServiceEffect,      # For I/O operations (available)
    ModelServiceCompute,     # For data processing (available)
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Note: For REDUCER and ORCHESTRATOR nodes, use direct node classes for now
from omnibase_core.nodes.node_reducer import NodeReducer           # For state aggregation
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator # For workflow coordination

class YourTool(ModelServiceCompute):  # Choose appropriate service wrapper
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # MANDATORY - handles all boilerplate

        # Protocol-based dependency resolution (if needed beyond what wrapper provides)
        self.logger = container.get_service("ProtocolLogger")
        self.event_bus = container.get_service("ProtocolEventBus")

        # Business-specific initialization only

# ⚙️ ADVANCED: Direct node classes (only when you need lower-level control)
from omnibase_core.nodes.node_compute import NodeCompute

class YourCustomTool(NodeCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Advanced customization here
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
