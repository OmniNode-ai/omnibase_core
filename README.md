<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/omninode-inline-white.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/omninode-inline-full-color.svg">
    <img alt="omninode" src="docs/assets/brand/omninode-inline-full-color.svg" width="420">
  </picture>
</p>

# omnibase_core

`omnibase_core` is the ONEX (OmniNode eXecution) platform kernel. It owns node execution, contracts,
core models, validation tooling, and the canonical architecture vocabulary used
by downstream OmniNode repos.

[![CI](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/ci.yml/badge.svg?event=pull_request&branch=dev)](https://github.com/OmniNode-ai/omnibase_core/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Badge note:** this tracks the PR-triggered `ci.yml` run (`event=pull_request`), not the push-triggered run on `dev`. The push/schedule-triggered run is permanently red by design: its Contract Compliance Check job fails closed on every non-PR event because its DoD checks are PR-scoped and correctly refuse to vacuously pass outside PR context. That is an intentional, documented tradeoff, not a regression — see the `contract-compliance` job comment in `.github/workflows/ci.yml` for the rationale.

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
uv add "omnibase_core[kafka]"
uv add "omnibase_core[full]"
```

Common imports:

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core import ModelOnexError
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

Start here, in the knowledge base:

- [Quick Start](https://github.com/OmniNode-ai/knowledge-base/blob/main/guides/omnibase-core-quick-start.md)
- [First Node Tutorial](https://github.com/OmniNode-ai/knowledge-base/blob/main/guides/omnibase-core-first-node.md)
- [Node Building Guide](https://github.com/OmniNode-ai/knowledge-base/blob/main/guides/onex-node-building-overview.md)
- [ONEX Four-Node Architecture](https://github.com/OmniNode-ai/knowledge-base/blob/main/architecture/onex-four-node-architecture.md)

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
[Validation Ownership](https://github.com/OmniNode-ai/knowledge-base/blob/main/reference/omnibase-core-validation-ownership.md).

## Documentation

**Full documentation → https://github.com/OmniNode-ai/knowledge-base**

This repository ships code, contracts, and executable configuration. Its prose
documentation lives in the OmniNode knowledge base; nothing is duplicated here,
and the `kb-doc-gate` check (`.kb-doc-gate.yaml`, `mode: strict`) fails any pull
request that reintroduces markdown outside the allowed set.

High-signal entrypoints:

- [Architecture Overview](https://github.com/OmniNode-ai/knowledge-base/blob/main/architecture/omnibase-core-overview.md)
- [ONEX Four-Node Architecture](https://github.com/OmniNode-ai/knowledge-base/blob/main/architecture/onex-four-node-architecture.md)
- [Contract System](https://github.com/OmniNode-ai/knowledge-base/blob/main/architecture/onex-contract-system.md)
- [Handler Contract Guide](https://github.com/OmniNode-ai/knowledge-base/blob/main/guides/onex-handler-contracts.md)
- [Validation Framework](https://github.com/OmniNode-ai/knowledge-base/blob/main/reference/omnibase-core-validation-framework.md)
- [Validation Ownership](https://github.com/OmniNode-ai/knowledge-base/blob/main/reference/omnibase-core-validation-ownership.md)
- [Decision records](https://github.com/OmniNode-ai/knowledge-base/blob/main/adrs)
- [Contributing](.github/CONTRIBUTING.md)
- [Security](SECURITY.md)

Internal-only and in-flight-migration material for this package (per-repo
architecture handshakes, the mixin/handler/protocol migration guides, repo CI
operations, and the validator generation-provenance records) lives in the
OmniNode internal knowledge base instead — teammates have access; it is not
linked from here because that repository is private.

## License

[MIT](LICENSE)
