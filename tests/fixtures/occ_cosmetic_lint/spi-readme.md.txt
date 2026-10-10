<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/omninode-inline-white.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/omninode-inline-full-color.svg">
    <img alt="omninode" src="docs/assets/brand/omninode-inline-full-color.svg" width="420">
  </picture>
</p>

# omnibase_spi

`omnibase_spi` is the Service Provider Interface package for ONEX (OmniNode eXecution). It defines
protocol contracts, small wire-format contracts, and SPI exceptions that other
repos implement or consume.

This package is intentionally not the implementation layer. Concrete runtime,
transport, service, registry, and I/O behavior belongs in implementation repos
such as `omnibase_infra`.

[![CI](https://github.com/OmniNode-ai/omnibase_spi/actions/workflows/ci.yml/badge.svg)](https://github.com/OmniNode-ai/omnibase_spi/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Current Role

- Defines 232 `protocol_*.py` files across 39 protocol domains.
- Provides runtime-checkable Python `Protocol` contracts for service boundaries.
- Provides frozen, data-only contracts in `src/omnibase_spi/contracts/` for
  selected cross-boundary wire formats.
- Imports `omnibase_core` models and types where protocol signatures need shared
  platform data shapes.
- Must not import implementation packages such as `omnibase_infra`.
- Must not contain service implementations, business workflows, state machines,
  transport clients, or general domain Pydantic models.

## Dependency Direction

The import direction is deliberate and non-obvious:

```text
Application and product repos
        |
        v
omnibase_spi  ---- imports models/types ---->  omnibase_core
        ^                                      ^
        | implements protocols                 | uses models/types
        |
omnibase_infra and other implementation repos --+
```

Allowed:

- `omnibase_spi -> omnibase_core`
- `omnibase_infra -> omnibase_spi`
- `omnibase_infra -> omnibase_core`
- Product repos importing SPI protocols for type boundaries

Forbidden:

- `omnibase_core -> omnibase_spi`
- `omnibase_spi -> omnibase_infra`
- Protocol files that perform I/O or instantiate concrete services
- General domain `BaseModel` classes in SPI protocol modules

See [Dependency Direction](https://github.com/OmniNode-ai/knowledge_base/blob/main/architecture/omnibase-spi-dependency-direction.md)
in the knowledge base for the full rule, examples, and rationale.

## Install

```bash
uv add omnibase_spi
```

For local workspace development, use the repository lockfile and the configured
`omnibase-core` source:

```bash
uv sync --group dev
```

## Minimal Protocol Example

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolExampleService(Protocol):
    """Service boundary implemented outside omnibase_spi."""

    async def run(self, payload: bytes) -> bytes:
        """Run the service operation."""
        ...
```

## Add A Protocol

1. Choose the domain under `src/omnibase_spi/protocols/`.
2. Create a `protocol_<domain>_<name>.py` file.
3. Name the public protocol `Protocol<Name>`.
4. Add `@runtime_checkable`.
5. Use `...` method bodies only.
6. Import shared models from `omnibase_core` only when the signature requires
   canonical platform models or types.
7. Add or update tests under `tests/`.
8. Export the protocol from the domain `__init__.py` if it is public.

## Common Commands

```bash
uv sync --group dev
uv run pytest
uv run mypy src/ --strict
uv run ruff check src/ tests/
uv run ruff format src/ tests/
python scripts/validation/run_all_validations.py
pre-commit run --all-files
uv build
```

## Documentation

Full documentation → https://github.com/OmniNode-ai/knowledge-base

The knowledge base is the single home for this package's prose documentation:
architecture, guides, patterns, standards, glossary, and testing. This
repository keeps only what must ship beside the code.

Start here:

- [Overview](https://github.com/OmniNode-ai/knowledge_base/blob/main/architecture/omnibase-spi-overview.md)
- [Dependency direction](https://github.com/OmniNode-ai/knowledge_base/blob/main/architecture/omnibase-spi-dependency-direction.md)
- [Quick start](https://github.com/OmniNode-ai/knowledge_base/blob/main/guides/omnibase-spi-quick-start.md)
- [Developer guide](https://github.com/OmniNode-ai/knowledge_base/blob/main/guides/omnibase-spi-developer-guide.md)
- [Testing](https://github.com/OmniNode-ai/knowledge_base/blob/main/guides/omnibase-spi-testing.md)
- [Glossary](https://github.com/OmniNode-ai/knowledge_base/blob/main/reference/omnibase-spi-glossary.md)

Kept in this repository:

- [API reference](docs/api-reference/README.md) — versioned, generated against
  this package's code tag, so it cannot live in the knowledge base
- [Contributing](.github/CONTRIBUTING.md), [Security](SECURITY.md)
- [Agent context](CLAUDE.md) — the single in-tree agent context file

## License

[MIT](LICENSE)
