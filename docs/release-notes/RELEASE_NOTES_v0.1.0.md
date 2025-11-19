# ONEX Core Framework v0.1.0 - Initial Release

**Release Date**: October 20, 2025
**Status**: Production-Ready (with known limitations)

## Summary

The ONEX Core Framework v0.1.0 is the foundational implementation of the 4-node ONEX architecture, providing production-ready base classes, dependency injection, and essential models for building scalable, type-safe distributed systems.

This release enables developers to build EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes with minimal boilerplate while maintaining strict type safety and architectural compliance.

## Key Features

### 4-Node Architecture
Complete implementation of the ONEX workflow pattern:
- **EFFECT**: External I/O, APIs, side effects with transaction support
- **COMPUTE**: Pure transformations and algorithms with caching
- **REDUCER**: State aggregation with FSM-based Intent emission
- **ORCHESTRATOR**: Workflow coordination with Action lease management

### Protocol-Driven Dependency Injection
Type-safe service resolution without registry coupling:
```python
logger = container.get_service("ProtocolLogger")
event_bus = container.get_service("ProtocolEventBus")
```python

### Zero Boilerplate Development
Pre-composed service classes eliminate 80+ lines of initialization:
```python
class MyNode(ModelServiceCompute):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)  # All boilerplate handled!
```python

### Comprehensive Mixin System
15+ reusable mixins for cross-cutting concerns:
- Service mode for persistent MCP servers
- Health monitoring and reporting
- Event publishing/subscription
- Performance metrics collection
- Result caching with TTL
- And more...

### Event-Driven Communication
ModelEventEnvelope for inter-service messaging with correlation tracking and structured data flow.

### Structured Error Handling
ModelOnexError with Pydantic models for consistent, context-rich error management:
```python
raise ModelOnexError(
    message="Operation failed",
    error_code=EnumErrorCode.OPERATION_FAILED,
    context={"correlation_id": correlation_id}
)
```python

### Production-Ready Validation
- 60+ Pydantic models with comprehensive runtime validation
- 27 pre-commit hooks for ONEX architectural compliance
- Pattern validation and anti-pattern detection
- Strict type checking with MyPy (in progress)

## Installation

### Requirements
- Python 3.12+
- Poetry (package manager)

### Install from GitHub
```bash
# Using Poetry (recommended)
poetry add git+https://github.com/OmniNode-ai/omnibase_core.git@v0.1.0

# Using pip
pip install git+https://github.com/OmniNode-ai/omnibase_core.git@v0.1.0
```python

### Development Installation
```bash
# Clone the repository
git clone https://github.com/OmniNode-ai/omnibase_core.git
cd omnibase_core

# Install with Poetry
poetry install

# Run tests
poetry run pytest tests/

# Run type checking
poetry run mypy src/omnibase_core/
```python

## Quick Start

### Your First Node

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeMyServiceCompute(NodeCoreBase):
    """My first COMPUTE node."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data):
        """Transform input data."""
        result = input_data.value * 2  # Simple computation
        return {"result": result}
```python

### Learn More
- **Getting Started**: [Quick Start Guide](../getting-started/QUICK_START.md)
- **Node Building**: [Complete Node Building Guide](../guides/node-building/README.md)
- **Architecture**: [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Documentation Index**: [docs/INDEX.md](../INDEX.md)

## Breaking Changes

### Thunk → Action Refactoring

This release renames "Thunk" to "Action" for clearer semantics:

**Import Changes**:
```python
# v0.0.x
from omnibase_core.models.orchestrator.model_action import ModelThunk
from omnibase_core.enums.enum_workflow_execution import EnumThunkType

# v0.1.0
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.enums.enum_workflow_execution import EnumActionType
```python

**Field Changes**:
- `thunk_id` → `action_id`
- `thunk_type` → `action_type`
- `operation_data` → `payload`
- Added: `lease_id` (required for single-writer semantics)
- Added: `epoch` (required for lease management)

**Migration Path**: See [CHANGELOG.md](../../CHANGELOG.md) for detailed migration guide.

### Reducer FSM Changes

Removed backward compatibility methods in Reducer. Now uses pure FSM with Intent emission:

```python
# OLD (removed)
await self.update_state(new_state)

# NEW (v0.1.0)
intent = ModelIntent(
    intent_type=EnumIntentType.UPDATE_STATE,
    target_state=EnumMyState.PROCESSING,
    payload={"data": value}
)
await self.emit_intent(intent)
```python

## Known Issues

### Type Safety (In Progress)
- **267 MyPy errors remaining** - Protocol refinement and attribute definitions in progress
- Target: 0 mypy errors before v0.2.0

### Code Quality (In Progress)
- **873 Ruff violations remaining** (down from 1037)
  - 366 deprecated typing imports (UP035)
  - 80 undefined star imports (F403)
- Target: <100 violations before v0.2.0

### Thread Safety
Most ONEX node components are NOT thread-safe by default. See [Threading Guide](../guides/THREADING.md) for:
- Thread safety guarantees per component
- Synchronization patterns
- Production deployment checklist

### Documentation
- API documentation generation pending
- Architecture diagrams in progress
- More real-world examples needed

### Test Coverage
- Current: >60% overall coverage
- Target: >80% before v0.2.0

## What's Next (v0.2.0 Roadmap)

### Planned for v0.2.0
- **Type Safety**: Resolve all 267 MyPy errors
- **Code Quality**: Reduce Ruff violations to <100
- **PEP 621 Compliance**: Migrate pyproject.toml to modern format
- **Test Coverage**: Achieve >80% coverage
- **API Documentation**: Auto-generated API docs with Sphinx
- **Performance Tests**: Baseline and regression testing framework
- **Architecture Diagrams**: Visual workflow and architecture diagrams

### Future Enhancements
- **Enhanced Caching**: Advanced cache invalidation strategies
- **Circuit Breaker**: Built-in resilience patterns
- **Distributed Tracing**: OpenTelemetry integration
- **Kubernetes Operators**: ONEX node deployment operators

## Documentation

### Essential Reading
- [README.md](../../README.md) - Project overview
- [CHANGELOG.md](../../CHANGELOG.md) - Detailed change log
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [docs/INDEX.md](../INDEX.md) - Complete documentation index

### Quick Links
- [Installation Guide](../getting-started/INSTALLATION.md)
- [COMPUTE Node Tutorial](../guides/node-building/03_COMPUTE_NODE_TUTORIAL.md)
- [EFFECT Node Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md)
- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Threading Guide](../guides/THREADING.md)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Development setup
- Code standards
- Testing requirements
- Pull request process

### Code Quality Standards
- All code must pass 27 pre-commit hooks
- Zero tolerance for `Any` types
- Comprehensive test coverage (target: >80%)
- Pydantic models for all data structures
- Protocol-based dependency injection

## License

MIT License - See [LICENSE](../../LICENSE) for details.

## Acknowledgments

Built with ONEX framework principles:
- **Zero Boilerplate**: Eliminate repetitive code through base classes
- **Protocol-Driven**: Type-safe dependency injection via Protocols
- **Event-Driven**: Inter-service communication via ModelEventEnvelope
- **4-Node Pattern**: EFFECT → COMPUTE → REDUCER → ORCHESTRATOR workflow

---

**Ready to build?** → [Node Building Guide](../guides/node-building/README.md)

**Need help?** → [Documentation Index](../INDEX.md)

**Found a bug?** → [GitHub Issues](https://github.com/OmniNode-ai/omnibase_core/issues)

---

**Note**: This is the initial public release (v0.1.0). While production-ready for many use cases, some rough edges remain (see Known Issues). Your feedback and contributions are welcome!
