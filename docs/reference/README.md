> **Navigation**: [Home](../INDEX.md) > Reference

# Reference Documentation

API documentation and reference materials for omnibase_core.

## Contents

- **api/** - API documentation for all modules and classes
  - [`enums.md`](api/enums.md) - Enumeration types and constants
  - [`models.md`](api/models.md) - Pydantic models and data structures
  - [`nodes.md`](api/nodes.md) - Node base classes and interfaces
  - [`utils.md`](api/utils.md) - Utility functions and helpers

## API Documentation

The API documentation provides comprehensive reference for all public interfaces:

- **Node Classes**: Base classes for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes
- **Models**: Pydantic models for input/output validation and data structures
- **Enums**: Constants and enumeration types used throughout the system
- **Utilities**: Helper functions, decorators, and common patterns

## Related Documentation

- **Templates**: Node implementation templates moved to [guides/templates/](../guides/templates/COMPUTE_NODE_TEMPLATE.md)
- **Architecture Research**: Design research moved to [architecture/architecture-research/](../architecture/architecture-research/RESEARCH_REPORT_4_NODE_ARCHITECTURE.md)
- **Patterns**: Design patterns moved to [patterns/](../patterns/CIRCUIT_BREAKER_PATTERN.md)
- **Performance Guides**: Performance documentation moved to [guides/](../guides/PERFORMANCE_BENCHMARKS.md)

## Quick Reference

### Core Node Classes
```
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
```

### Container and Models
```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
```

### Error Handling
```python
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
```
