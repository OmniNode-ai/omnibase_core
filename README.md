# omnibase_core

`omnibase_core` is the ONEX platform kernel. It owns node execution, contracts,
core models, validation tooling, and the canonical architecture vocabulary used
by downstream OmniNode repos.

[![CI](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/test.yml/badge.svg)](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/test.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Who Uses It

Use this repo when you need to:

- Use ONEX core types, nodes, contracts, and validation tools.
- Build a contract-driven EFFECT, COMPUTE, REDUCER, or ORCHESTRATOR node.
- Extend Core internals such as validation, contracts, node execution, handlers,
  model conventions, or runtime-development scaffolding.

Downstream runtime implementations, infrastructure clients, workflow packages,
dashboard projections, and thin wrapper tooling should link back here for Core
architecture and validation truth rather than duplicating it.

## What This Repo Owns

- ONEX node base classes and execution vocabulary.
- Contract models, handler contracts, subcontracts, and contract validation.
- Core event envelopes, error models, container patterns, and dependency
  injection conventions.
- Core documentation standards for ONEX architecture and node construction.
- Shared validation entrypoints such as `onex-validate-links`,
  `onex-validate-topics`, `check-local-paths`, and string-version checks.

## What This Repo Does Not Own

- Concrete infrastructure, Kafka/Postgres/Infisical clients, runtime host
  deployment, or registration operations. Those belong in `omnibase_infra`.
- Protocol-only service interfaces for downstream implementation packages.
  Those belong in `omnibase_spi`.
- Zero-upstream structural DTOs and compatibility shims. Those belong in
  `omnibase_compat`.
- Portable workflow package ownership. That belongs in `omnimarket`.

## Track 1: Use The Package

Install:

```bash
uv add omnibase_core
```

Install optional surfaces only when needed:

```bash
uv add "omnibase_core[spi]"
uv add "omnibase_core[compat]"
uv add "omnibase_core[full]"
```

Common imports:

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.models.errors.model_onex_error import ModelOnexError
```

Core is a Python 3.12+ package. Package metadata, optional dependency groups,
and CLI entrypoints are declared in `pyproject.toml`.

## Track 2: Build A Node

Every ONEX node starts from one of the four core archetypes:

- EFFECT: external I/O
- COMPUTE: transformation and validation
- REDUCER: state aggregation
- ORCHESTRATOR: workflow coordination

Minimal COMPUTE node:

```python
from omnibase_core.nodes import NodeCompute


class NodeMyFeature(NodeCompute):
    pass
```

The preferred path is contract-driven: YAML declares inputs, outputs,
capabilities, bindings, and lifecycle constraints; custom Python behavior is
added only when the contract cannot express the behavior.

Start here:

- [Quick Start](docs/getting-started/QUICK_START.md)
- [First Node Tutorial](docs/getting-started/FIRST_NODE.md)
- [Node Building Guide](docs/guides/node-building/README.md)
- [ONEX Four-Node Architecture](docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

## Track 3: Extend Validation Or Runtime Internals

Core owns validators and development/runtime internals that other repos consume.
Use these commands before changing validation, contracts, docs, or architecture
surface:

```bash
uv sync --dev --frozen
uv run onex-validate-links --verbose
uv run pytest tests/ -q
```

Focused validation entrypoints:

```bash
uv run onex-validate-topics . --verbose
uv run check-local-paths docs src scripts
uv run validate-string-versions src
```

For ownership, downstream-consumer guidance, and cross-repo usage, see
[Validation Ownership](docs/reference/VALIDATION_OWNERSHIP.md).

## Documentation Map

[docs/INDEX.md](docs/INDEX.md) is the canonical full docs map.

High-signal entrypoints:

- [Architecture Overview](docs/architecture/overview.md)
- [Contract System](docs/architecture/CONTRACT_SYSTEM.md)
- [Handler Contract Guide](docs/contracts/HANDLER_CONTRACT_GUIDE.md)
- [Validation Ownership](docs/reference/VALIDATION_OWNERSHIP.md)
- [Validation Framework](docs/reference/VALIDATION_FRAMEWORK.md)
- [ADR Index](docs/decisions/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## Current Versus Historical Docs

Root `README.md`, `CLAUDE.md`, and `docs/INDEX.md` are the primary human entry
surfaces. Dated plans and migration notes are historical or execution context
unless a stable architecture, reference, runbook, or migration page explicitly
promotes them.

Current topic naming truth lives in Core topic validators and standards docs.

## License

[MIT](LICENSE)
