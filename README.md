# ONEX Core Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](https://mypy.readthedocs.io/)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Framework: Core](https://img.shields.io/badge/framework-core-purple.svg)](https://github.com/OmniNode-ai/omnibase_core)
[![Node Types: 4](https://img.shields.io/badge/node%20types-4-blue.svg)](https://github.com/OmniNode-ai/omnibase_core)

**Contract-driven execution layer for tools and workflows.** Deterministic execution, zero boilerplate, full observability.

## What is ONEX?

**ONEX is a declarative, contract-driven execution layer for tools and distributed workflows.** It standardizes how agents execute, communicate, and share context. Instead of custom glue code for each agent or tool, ONEX provides a deterministic execution protocol that behaves the same from local development to distributed production.

Use ONEX when you need predictable, testable, observable agent tools with consistent error handling across distributed systems.

## Four-Node Architecture

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│   (I/O)     │    │ (Transform) │    │(Aggregate)  │    │(Coordinate) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

- **EFFECT**: External interactions (APIs, DBs, queues)
- **COMPUTE**: Transformations and pure logic
- **REDUCER**: State aggregation, finite state machines
- **ORCHESTRATOR**: Multi-step workflows, coordination

Unidirectional flow only. No backwards dependencies.

**See**: [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

## Why ONEX Exists

Most agent frameworks reinvent execution logic, leading to:
- inconsistent inputs/outputs
- implicit state
- opaque or framework-specific failures
- framework/vendor lock-in
- untestable tools

ONEX solves this with:
- typed schemas (Pydantic + protocols)
- deterministic lifecycle
- event-driven contracts: `ModelEventEnvelope`
- full traceability
- framework-agnostic design

## What This Repository Provides

OmniBase Core is the execution engine used by all ONEX-compatible nodes and services.
- Base classes that remove 80+ lines of boilerplate per node
- Protocol-driven dependency injection: `ModelONEXContainer`
- Structured errors with proper error codes: `ModelOnexError`
- Event system via `ModelEventEnvelope`
- Full 4-node architecture
- Mixins for reusable behaviors
- Subcontracts for declarative configuration

## Quick Start

Install:
```bash
poetry add omnibase_core
```

Minimal example:
```python
from omnibase_core.nodes import NodeCompute, ModelComputeInput, ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeCalculator(NodeCompute):
    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    async def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
        value = input_data.data.get("value", 0)
        return ModelComputeOutput(
            result={"result": value * 2},
            operation_id=input_data.operation_id,
            computation_type=input_data.computation_type,
        )
```

Run tests:
```bash
poetry run pytest
```

**Next**: [Node Building Guide](docs/guides/node-building/README.md)

## How ONEX Compares

- **LangChain/LangGraph**: Pipeline-first. ONEX standardizes execution semantics.
- **Ray**: Distributed compute. ONEX focuses on agent tool determinism.
- **Temporal**: Workflow durability. ONEX defines tool and agent interaction.
- **Microservices**: Boundary-driven. ONEX defines the protocol services speak.

## Repository Structure

```text
src/omnibase_core/
├── container/          # DI container
├── infrastructure/     # NodeCoreBase, ModelService*
├── models/             # Pydantic models
├── nodes/              # EFFECT, COMPUTE, REDUCER, ORCHESTRATOR
├── events/             # Event system
├── errors/             # Structured errors
└── mixins/             # Declarative behaviors
```

**See**: [Architecture Overview](docs/architecture/overview.md)

## Advanced Topics

- **Subcontracts**: Declarative behavior modules. See [SUBCONTRACT_ARCHITECTURE.md](docs/architecture/SUBCONTRACT_ARCHITECTURE.md).
- **Manifest Models**: Typed metadata loaders. See [MANIFEST_MODELS.md](docs/reference/MANIFEST_MODELS.md).

## Thread Safety

Most ONEX nodes are not thread-safe. See [THREADING.md](docs/guides/THREADING.md).

## Documentation

**Start here**: [Node Building Guide](docs/guides/node-building/README.md)

**Reference**: [Complete Documentation Index](docs/INDEX.md)

## Development

Uses Poetry for all package management.

```bash
poetry install
poetry run pytest tests/
poetry run mypy src/omnibase_core/
poetry run black src/ tests/
poetry run isort src/ tests/
```

**See**: [CONTRIBUTING.md](CONTRIBUTING.md) for PR requirements.
