# Mixin Development Guide

**Status**: Active
**Target Audience**: Developers creating reusable ONEX mixins
**Prerequisites**: Understanding of ONEX node types, YAML, Pydantic
**Related**: [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md), [Node Building Guide](../node-building/README.md)

## Overview

This comprehensive guide teaches you how to create production-ready mixins (subcontracts) for the ONEX framework. Mixins provide reusable cross-cutting concerns that can be composed into nodes while maintaining architectural boundaries.

## What You'll Learn

- **Mixin Fundamentals**: Understanding the three-layer mixin architecture
- **YAML Schema**: Complete reference for mixin contract structure
- **Pydantic Models**: Creating strongly-typed backing models
- **Integration**: Connecting mixins to nodes
- **Best Practices**: Patterns, tools, and validation strategies

## Guide Structure

### Fundamentals

- **[Architecture Overview](../../architecture/MIXIN_ARCHITECTURE.md)** - Three-layer mixin architecture
- Understanding node type constraints and separation of concerns

### Step-by-Step Guides

1. **[Creating Mixins](01_CREATING_MIXINS.md)** - Complete step-by-step guide to creating a new mixin
2. **[Mixin YAML Schema](02_MIXIN_YAML_SCHEMA.md)** - Comprehensive YAML schema reference
3. **[Pydantic Models](03_PYDANTIC_MODELS.md)** - Creating and validating backing models
4. **[Mixin Integration](04_MIXIN_INTEGRATION.md)** - Integrating mixins into nodes
5. **[Best Practices](05_BEST_PRACTICES.md)** - Patterns, tools, and utilities

## Quick Start

**Never created a mixin before?** Start here:

1. Read [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md) (10 min)
2. Follow [Creating Mixins](01_CREATING_MIXINS.md) guide (30 min)
3. Reference [YAML Schema](02_MIXIN_YAML_SCHEMA.md) as needed
4. Create [Pydantic Models](03_PYDANTIC_MODELS.md) (15 min)
5. [Integrate](04_MIXIN_INTEGRATION.md) into a node (10 min)

**Created mixins before?** Jump to:

- [Best Practices](05_BEST_PRACTICES.md) for advanced patterns
- [YAML Schema](02_MIXIN_YAML_SCHEMA.md) for quick reference
- [Pydantic Models](03_PYDANTIC_MODELS.md) for model patterns

## Prerequisites

### Required Knowledge

- **ONEX Node Types**: Understanding of COMPUTE, EFFECT, REDUCER, ORCHESTRATOR
- **YAML**: Basic YAML syntax and structure
- **Pydantic**: Understanding of Pydantic models and validation
- **Python 3.11+**: Async/await, type hints, dataclasses

### Required Tools

- **Poetry**: `poetry --version` (1.0+)
- **omnibase_core**: Installed in your project
- **Text editor**: VSCode, PyCharm, or similar with YAML support

### Verification

```bash
# Verify environment
poetry run python -c "from omnibase_core.model.subcontracts import ModelHealthCheckSubcontract; print('✓ Mixin system ready!')"

# Check existing mixins
ls /Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/nodes/canary/mixins/
```

## Learning Path

### Beginner Path (First Mixin)

1. **Understand Architecture** (15 min)
   - Read: [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)
   - Review: Existing mixins in `nodes/canary/mixins/`

2. **Create Your First Mixin** (1-2 hours)
   - Follow: [Creating Mixins](01_CREATING_MIXINS.md)
   - Reference: [YAML Schema](02_MIXIN_YAML_SCHEMA.md)
   - Create: Simple logging or metrics mixin

3. **Add Pydantic Model** (30 min)
   - Follow: [Pydantic Models](03_PYDANTIC_MODELS.md)
   - Validate: Your mixin contract

4. **Integrate and Test** (30 min)
   - Follow: [Mixin Integration](04_MIXIN_INTEGRATION.md)
   - Test: In a COMPUTE node first (simplest)

### Intermediate Path (Multiple Mixins)

1. **Review Patterns** (20 min)
   - Read: [Best Practices](05_BEST_PRACTICES.md)
   - Study: Core mixins (`mixin_health_check`, `mixin_performance_monitoring`)

2. **Create Complex Mixin** (2-3 hours)
   - Design: Mixin with multiple actions
   - Implement: With dependencies and metrics
   - Validate: Using enhanced contract validator

3. **Node Type Specialization** (1 hour)
   - Create: EFFECT-specific mixin (e.g., circuit breaker)
   - Create: REDUCER-specific mixin (e.g., state management)
   - Respect: Node type constraints

### Advanced Path (Mixin System Expert)

1. **Deep Architecture** (1 hour)
   - Study: `EnhancedContractValidator` implementation
   - Understand: Contract loading and resolution
   - Review: Node type constraint enforcement

2. **Custom Patterns** (2-4 hours)
   - Design: Domain-specific mixin patterns
   - Implement: Advanced composition strategies
   - Optimize: Performance and memory usage

3. **Contribute** (Ongoing)
   - Share: Your mixins with the community
   - Document: New patterns and best practices
   - Improve: Existing mixin documentation

## Mixin Types Reference

### Core Mixins (Universal)

Applicable to all node types:

| Mixin | Purpose | Guide Reference |
|-------|---------|-----------------|
| `mixin_health_check` | Health monitoring | [Creating Mixins](01_CREATING_MIXINS.md) |
| `mixin_introspection` | Node discovery | [YAML Schema](02_MIXIN_YAML_SCHEMA.md) |
| `mixin_event_handling` | Event bus integration | [Integration](04_MIXIN_INTEGRATION.md) |
| `mixin_service_resolution` | Service discovery | [Best Practices](05_BEST_PRACTICES.md) |
| `mixin_performance_monitoring` | Metrics collection | [Creating Mixins](01_CREATING_MIXINS.md) |
| `mixin_request_response` | Request/response patterns | [Integration](04_MIXIN_INTEGRATION.md) |

### Node Type-Specific Mixins

#### EFFECT Mixins

- `mixin_external_dependencies`: External system integration
- `mixin_circuit_breaker`: Fault tolerance
- `mixin_retry_policy`: Retry strategies

#### REDUCER Mixins

- `mixin_state_management`: State persistence
- `mixin_aggregation`: Data aggregation
- `mixin_caching`: Caching strategies

#### ORCHESTRATOR Mixins

- `mixin_workflow_coordination`: Workflow management
- `mixin_fsm`: Finite state machine processing
- `mixin_routing`: Request routing

## Common Use Cases

### Creating a Logging Mixin

**Goal**: Add structured logging to any node

**Steps**:
1. Define YAML contract with logging actions
2. Create Pydantic model with log level configuration
3. Integrate into nodes via `subcontracts` section

**See**: [Creating Mixins](01_CREATING_MIXINS.md) for complete example

### Creating an Authentication Mixin

**Goal**: Add authentication to EFFECT nodes

**Steps**:
1. Define YAML contract with auth actions (validate, refresh)
2. Add auth configuration (token URL, credentials)
3. Restrict to EFFECT nodes only
4. Create Pydantic model with validation

**See**: [Node Type Constraints](../../architecture/MIXIN_ARCHITECTURE.md#node-type-constraints)

### Creating a Caching Mixin

**Goal**: Add caching to REDUCER nodes

**Steps**:
1. Define YAML contract with cache operations
2. Add cache configuration (TTL, size, eviction policy)
3. Restrict to REDUCER nodes only
4. Implement cache invalidation actions

**See**: [Pydantic Models](03_PYDANTIC_MODELS.md) for validation patterns

## Project Integration

### Adding Mixins to Your Project

```bash
# In your project directory
mkdir -p src/your_project/mixins
mkdir -p src/your_project/model/subcontracts

# Create your mixin YAML
touch src/your_project/mixins/mixin_your_feature.yaml

# Create backing Pydantic model
touch src/your_project/model/subcontracts/model_your_feature_subcontract.py
```

### Project Structure

```text
your_project/
├── pyproject.toml
├── src/
│   └── your_project/
│       ├── mixins/                              # Your mixin contracts
│       │   ├── mixin_logging.yaml
│       │   ├── mixin_authentication.yaml
│       │   └── mixin_rate_limiting.yaml
│       │
│       ├── model/subcontracts/                  # Pydantic models
│       │   ├── model_logging_subcontract.py
│       │   ├── model_authentication_subcontract.py
│       │   └── model_rate_limiting_subcontract.py
│       │
│       └── nodes/                               # Your nodes
│           ├── node_api_client_effect.py        # Uses auth mixin
│           └── contract.yaml                    # References mixins
└── tests/
    └── mixins/                                  # Mixin tests
        ├── test_mixin_logging.py
        └── test_mixin_authentication.py
```

## Validation and Testing

### Contract Validation

```bash
# Validate mixin contract
poetry run onex run contract_validator --contract src/your_project/mixins/mixin_your_feature.yaml

# Validate complete node contract (with mixins)
poetry run onex run contract_validator --contract src/your_project/nodes/your_node/v1_0_0/contract.yaml
```

### Testing Mixins

```python
# Test mixin Pydantic model
import pytest
from your_project.model.subcontracts import ModelYourFeatureSubcontract

def test_mixin_validation():
    """Test mixin model validation."""
    mixin = ModelYourFeatureSubcontract(
        feature_enabled=True,
        timeout_ms=5000
    )
    assert mixin.feature_enabled is True
    assert mixin.timeout_ms == 5000
```

**See**: [Best Practices](05_BEST_PRACTICES.md) for comprehensive testing strategies

## Getting Help

- **Architecture Questions**: See [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)
- **YAML Syntax**: See [YAML Schema](02_MIXIN_YAML_SCHEMA.md)
- **Pydantic Issues**: See [Pydantic Models](03_PYDANTIC_MODELS.md)
- **Integration Problems**: See [Mixin Integration](04_MIXIN_INTEGRATION.md)
- **Code Examples**: Review `src/omnibase_core/nodes/canary/mixins/`

## Contributing

Found a better pattern? Want to share a mixin? Contributions welcome!

1. Follow [Best Practices](05_BEST_PRACTICES.md)
2. Include complete YAML and Pydantic model
3. Add comprehensive tests
4. Document node type constraints
5. Update this README if adding new concepts

## What's Next?

Ready to create mixins? Choose your path:

- **New to mixins?** → [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)
- **Ready to create?** → [Creating Mixins](01_CREATING_MIXINS.md)
- **Need schema reference?** → [YAML Schema](02_MIXIN_YAML_SCHEMA.md)
- **Creating models?** → [Pydantic Models](03_PYDANTIC_MODELS.md)
- **Integrating into nodes?** → [Mixin Integration](04_MIXIN_INTEGRATION.md)
- **Want best practices?** → [Best Practices](05_BEST_PRACTICES.md)

Happy mixin development! 🚀

---

**Related Documentation**:
- [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md) - Architectural overview
- [Subcontract Architecture](../../architecture/SUBCONTRACT_ARCHITECTURE.md) - Implementation patterns
- [Node Building Guide](../node-building/README.md) - Building nodes with mixins
