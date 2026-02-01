> **Navigation**: [Home](../index.md) > [Architecture](./overview.md) > Ecosystem Directory Structure

# ONEX Ecosystem Directory Structure

**Status**: Current as of 2025-11-27  
**Purpose**: Document the actual directory structure and manifest patterns across the ONEX ecosystem  

## Overview

The ONEX ecosystem consists of multiple repositories with distinct purposes and directory structures. This document reflects the actual implementation patterns found across all repositories.

## Repository Structure

### Core Repository: `omnibase_core`

**Purpose**: Core framework providing base classes, mixins, and essential implementations
**Location**: `/Volumes/PRO-G40/Code/omnibase_core`
**Package Name**: `omnibase_core`
**Version**: `0.2.0`

```
omnibase_core/
├── src/
│   └── omnibase_core/
│       ├── __init__.py
│       ├── constants/           # Framework constants
│       ├── container/           # Dependency injection
│       ├── decorators/          # Framework decorators
│       ├── discovery/           # Service discovery
│       ├── enums/              # Core enumerations (310 files)
│       ├── errors/             # Error handling
│       ├── infrastructure/     # Infrastructure components
│       ├── logging/            # Structured logging
│       ├── mixins/             # Reusable mixins (49 files)
│       │   ├── mixin_caching.py
│       │   ├── mixin_health_check.py
│       │   ├── mixin_event_bus.py
│       │   ├── mixin_introspection.py
│       │   ├── mixin_metrics.py
│       │   ├── mixin_node_service.py
│       │   └── ... (43 more mixins)
│       ├── models/             # Data models (60 directories)
│       │   ├── service/        # Service wrapper classes
│       │   │   ├── model_service_compute.py
│       │   │   ├── model_service_effect.py
│       │   │   ├── model_service_reducer.py
│       │   │   └── model_service_orchestrator.py
│       │   ├── events/         # Event models
│       │   ├── primitives/     # Primitive type models
│       │   └── ... (other model categories)
│       ├── nodes/              # Base node classes
│       ├── types/              # Type definitions (93 files)
│       ├── utils/              # Utility functions
│       ├── validation/         # Validation framework
│       └── validators/         # Custom validators
├── tests/                      # Test suite
├── docs/                       # Documentation
├── pyproject.toml             # Project manifest
└── README.md
```

**Key Mixins Available**:
- `MixinNodeService` - Persistent service capabilities
- `MixinHealthCheck` - Health monitoring
- `MixinEventBus` - Event publishing/subscribing
- `MixinCaching` - Caching capabilities
- `MixinIntrospection` - Node introspection
- `MixinMetrics` - Performance metrics
- `MixinIntentPublisher` - Intent publishing
- `MixinWorkflowSupport` - Workflow management
- `MixinCircuitBreaker` - Circuit breaker pattern
- `MixinStateManagement` - State management

### Bridge Repository: `omninode_bridge`

**Purpose**: Bridge between ONEX framework and external services  
**Location**: `/Volumes/PRO-G40/Code/omninode_bridge`
**Package Name**: `omninode_bridge`
**Version**: `0.1.0`

```
omninode_bridge/
├── src/
│   └── omninode_bridge/
│       ├── nodes/              # Bridge-specific nodes
│       │   ├── deployment_receiver_effect/
│       │   │   └── v1_0_0/
│       │   │       ├── node.py
│       │   │       └── models/
│       │   ├── database_adapter_effect/
│       │   ├── reducer/
│       │   ├── orchestrator/
│       │   └── mixins/         # Bridge-specific mixins
│       │       ├── health_mixin.py
│       │       └── introspection_mixin.py
│       ├── mixins/             # Custom bridge mixins
│       │   └── mixin_intent_publisher.py
│       ├── services/           # Bridge services
│       ├── events/             # Event definitions
│       └── models/             # Bridge models
├── FOR_OMNIBASE_CORE/         # Mixins for core integration
├── tests/
├── docs/
├── pyproject.toml
└── BRIDGE_MIGRATION_PLAN.md   # Migration strategy
```

**Bridge Node Patterns**:
- `NodeDeploymentReceiverEffect(NodeEffect)` - Docker deployment
- `NodeBridgeDatabaseAdapterEffect(NodeEffect, HealthCheckMixin)` - DB operations
- `NodeBridgeReducer(NodeReducer, HealthCheckMixin, IntrospectionMixin)` - Bridge operations
- `NodeBridgeOrchestrator(NodeOrchestrator, HealthCheckMixin, IntrospectionMixin)` - Bridge coordination

### Intelligence Repository: `omniarchon`

**Purpose**: AI coding assistant intelligence platform  
**Location**: `/Volumes/PRO-G40/Code/omniarchon`
**Package Name**: `archon`
**Version**: `0.1.0`

```
omniarchon/
├── python/                     # Main Python package
│   ├── src/
│   │   ├── intelligence/       # Intelligence services
│   │   ├── mcp_server/         # MCP server implementation
│   │   ├── omninode_bridge/    # Bridge integration
│   │   └── server/             # Server components
│   └── pyproject.toml
├── agents/                     # AI agents
├── claude_hooks/              # Claude integration
├── consumers/                 # Event consumers
├── deployment/                # Deployment configs
├── docs/                      # Documentation
├── monitoring/                # Monitoring setup
├── scripts/                   # Utility scripts
├── services/                  # Service implementations
├── shared_lib/                # Shared libraries
├── skills/                    # AI skills
├── tests/                     # Test suite
└── README.md
```

**Note**: Uses `omnibase_core` as dependency via Git repository

### Infrastructure Repository: `omnibase_infra`

**Purpose**: Infrastructure-specific nodes and services  
**Location**: `/Volumes/PRO-G40/Code/omnibase_infra`
**Package Name**: `omnibase_infra`
**Version**: `0.1.0`

```
omnibase_infra/
├── src/
│   └── omnibase_infra/
│       ├── nodes/              # Infrastructure nodes
│       │   ├── hook_node/      # Webhook notifications
│       │   ├── consul/         # Consul integration
│       │   ├── kafka_adapter/  # Kafka integration
│       │   ├── node_postgres_adapter_effect/  # PostgreSQL adapter
│       │   └── ... (other infrastructure nodes)
│       ├── infrastructure/     # Infrastructure components
│       └── models/             # Infrastructure models
├── tests/
├── archive/                    # Archived implementations
└── pyproject.toml
```

**Infrastructure Node Patterns**:
- `ModelServiceEffect` - Legacy service base class
- Custom mixin compositions for infrastructure needs
- Direct integration with external systems (PostgreSQL, Kafka, Consul)

### Memory Repository: `omnimemory`

**Purpose**: Memory and persistence layer  
**Location**: `/Volumes/PRO-G40/Code/omnimemory`
**Package Name**: `omnimemory`
**Version**: `0.1.0`

```
omnimemory/
├── src/
│   └── omnimemory/
│       ├── enums/              # Memory-related enums
│       ├── models/             # Memory models
│       ├── protocols/          # Memory protocols
│       └── utils/              # Memory utilities
├── tests/
└── pyproject.toml
```

### Legacy Repository: `omnibase_3`

**Purpose**: Legacy implementation and reference  
**Location**: `/Volumes/PRO-G40/Code/omnibase_3`
**Package Name**: `omnibase`
**Version**: `0.1.0`

```
omnibase_3/
├── src/
│   └── omnibase/               # Legacy core implementation
├── tests/
├── reference_implementations/  # Reference patterns
├── examples/
└── scripts/
```

## Manifest Patterns

### Standard pyproject.toml Structure

All repositories follow a consistent manifest pattern:

```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[project]
name = "package_name"
version = "0.1.0"
description = "Package description"
authors = [{name = "OmniNode Team", email = "team@omninode.ai"}]
license = "MIT"
readme = "README.md"
requires-python = ">=3.12"

[project.scripts]
package-cli = "package.cli.commands:cli"

[project.optional-dependencies]
monitoring = ["prometheus-client", "sentry-sdk"]
kubernetes = ["kubernetes"]
full = ["psutil", "prometheus-client", "sentry-sdk", "kubernetes"]

[tool.poetry]
name = "package_name"
version = "0.1.0"
packages = [{include = "package_name", from = "src"}]

[tool.poetry.dependencies]
python = "^3.12"
# Core dependencies
pydantic = "^2.11.7"
# ... other dependencies
```

### Dependency Relationships

```
omnibase_core (core framework)
├── omninode_bridge (depends on omnibase_core)
├── omnibase_infra (depends on omnibase_core)
├── omniarchon (depends on omnibase_core via Git)
└── omnimemory (standalone)
```

## Node Implementation Patterns

### 1. Service Wrapper Pattern (Recommended)

**Location**: `omnibase_core/src/omnibase_core/models/services/`

```
from omnibase_core.models.services import ModelServiceCompute

class MyComputeNode(ModelServiceCompute):
    """Production-ready compute node with all capabilities."""
    pass
```

**Benefits**:
- ✅ All production capabilities included
- ✅ Consistent error handling
- ✅ Built-in health checks and metrics
- ✅ Event publishing capabilities
- ✅ Standardized initialization

### 2. Bridge Pattern (Legacy/Compatibility)

**Location**: `omninode_bridge/src/omninode_bridge/nodes/`

```
from omnibase_core.nodes.node_effect import NodeEffect
from omninode_bridge.nodes.mixins.health_mixin import HealthCheckMixin

class MyBridgeEffect(NodeEffect, HealthCheckMixin):
    """Bridge-style node with custom mixin composition."""
    pass
```

**Use Cases**:
- Legacy compatibility
- Custom mixin combinations not available in wrappers
- Bridge-specific capabilities

### 3. Infrastructure Pattern (Legacy)

**Location**: `omnibase_infra/src/omnibase_infra/nodes/`

```
from omnibase_core.infrastructure.infra_bases import ModelServiceEffect

class MyInfraEffect(ModelServiceEffect):
    """Legacy infrastructure node."""
    pass
```

**Note**: `ModelServiceEffect` is deprecated in favor of `ModelService*` wrappers

## Mixin Distribution

### Core Mixins (omnibase_core)
- `MixinNodeService` - Service capabilities
- `MixinHealthCheck` - Health monitoring
- `MixinEventBus` - Event system
- `MixinCaching` - Caching
- `MixinIntrospection` - Introspection
- `MixinMetrics` - Metrics collection
- `MixinIntentPublisher` - Intent publishing
- `MixinWorkflowSupport` - Workflow management
- `MixinCircuitBreaker` - Circuit breaker
- `MixinStateManagement` - State management

### Bridge Mixins (omninode_bridge)
- `HealthCheckMixin` - Custom health check implementation
- `IntrospectionMixin` - Custom introspection implementation
- `MixinIntentPublisher` - Bridge-specific intent publishing

### Missing Mixins Identified
Based on ecosystem analysis, these capabilities may need to be added to core:

1. **Database Connection Management** - Used in bridge and infra
2. **Custom Authentication Mixins** - Used in bridge nodes
3. **Docker Integration Mixins** - Used in bridge deployment nodes
4. **Kafka Integration Mixins** - Used in infrastructure nodes
5. **PostgreSQL Adapter Mixins** - Used in infrastructure nodes

## Migration Recommendations

### Immediate Actions
1. **Update Documentation** - Use service wrapper patterns in all examples
2. **Add Missing Mixins** - Implement identified missing capabilities in core
3. **Create Bridge Wrappers** - Add bridge-specific service wrappers
4. **Deprecate Legacy Patterns** - Mark `ModelServiceEffect` as deprecated

### Long-term Strategy
1. **Standardize on Wrappers** - All new nodes use `ModelService*` wrappers
2. **Migrate Bridge Nodes** - Gradually migrate bridge nodes to wrappers
3. **Consolidate Mixins** - Move bridge-specific mixins to core
4. **Unify Patterns** - Ensure consistent patterns across all repositories

## File Naming Conventions

### Node Files
- `node.py` - Main node implementation
- `models/` - Node-specific data models
- `contracts/` - Node contracts (if separate)

### Mixin Files
- `mixin_*.py` - Core mixins (omnibase_core)
- `*_mixin.py` - Custom mixins (repositories)

### Service Files
- `*_service.py` - Service implementations
- `model_service_*.py` - Service wrapper classes

## Version Management

All repositories use semantic versioning with `0.1.0` as the current version. Dependencies are managed through:

1. **Git Dependencies** - For development dependencies
2. **PyPI Dependencies** - For stable releases
3. **Local Dependencies** - For local development

## Testing Structure

Each repository follows a consistent testing pattern:

```
tests/
├── unit/                       # Unit tests
│   ├── mixins/                # Mixin tests
│   ├── models/                # Model tests
│   └── nodes/                 # Node tests
├── integration/               # Integration tests
└── fixtures/                  # Test fixtures
```

---

**Last Updated**: 2025-11-27  
**Maintainer**: OmniNode Development Team  
**Next Review**: After migration plan implementation
