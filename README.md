# omnibase_core

Contract-driven execution layer for agent tools and workflows.

[![CI](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/test.yml/badge.svg)](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/test.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Install

```bash
uv add omnibase_core
```

## Minimal Example

Every ONEX node starts as a contract-driven declaration with zero custom code:

```python
from omnibase_core.nodes import NodeCompute

class NodeMyFeature(NodeCompute):
    pass  # All behavior driven by contract YAML
```

The contract YAML defines inputs, outputs, state transitions, and configuration:

```yaml
name: node_my_feature
version: 1.0.0
type: COMPUTE
input_schema: MyInput
output_schema: MyOutput
```

When you need custom logic, opt in by overriding `process()`:

```python
class NodeMyFeature(NodeCompute):
    async def process(self, input_data):
        # Custom logic here
        return {"result": input_data.value * 2}
```

## Why ONEX

| Problem | ONEX Solution |
|---------|--------------|
| Inconsistent tool I/O | Typed schemas (Pydantic + protocols) |
| Implicit state | Deterministic lifecycle with contract FSMs |
| Opaque failures | Structured errors with `ModelOnexError` |
| Framework lock-in | Framework-agnostic protocol design |
| Untestable tools | Pure nodes with injected dependencies |

## Key Features

- **Four-node architecture**: EFFECT (I/O), COMPUTE (transform), REDUCER (aggregate), ORCHESTRATOR (coordinate) -- [details](https://github.com/OmniNode-ai/omnibase_core/blob/main/docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Contract-driven execution**: YAML contracts define behavior; code is opt-in
- **Protocol-driven DI**: `ModelONEXContainer` for dependency injection
- **Structured errors**: `ModelOnexError` with proper error codes and traceability
- **Event system**: `ModelEventEnvelope` for event-driven communication
- **40+ mixins**: Reusable behavior modules for common patterns
- **Subcontracts**: Declarative configuration for FSM, caching, routing, and more
- **12,000+ tests**: Comprehensive test suite with strict type checking

## Documentation

- [Node Building Guide](docs/guides/node-building/README.md) -- start here
- [Architecture Overview](docs/architecture/overview.md)
- [Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Subcontract Architecture](docs/architecture/SUBCONTRACT_ARCHITECTURE.md)
- [Complete Documentation Index](docs/INDEX.md)
- [CLAUDE.md](CLAUDE.md) -- developer context and conventions

## License

[MIT](LICENSE)
