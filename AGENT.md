# AGENT.md -- omnibase_core

> LLM navigation guide. Points to context sources -- does not duplicate them.

## Context

- **Architecture**: `docs/architecture/overview.md`
- **Four-node types**: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md`
- **Subcontracts**: `docs/architecture/SUBCONTRACT_ARCHITECTURE.md`
- **Node building**: `docs/guides/node-building/README.md`
- **Full index**: `docs/INDEX.md`
- **Conventions**: `CLAUDE.md`

## Commands

- Tests: `uv run pytest -m unit`
- Lint: `uv run ruff check src/ tests/`
- Type check: `uv run mypy src/ --strict`
- Format: `uv run ruff format src/ tests/`
- Pre-commit: `pre-commit run --all-files`

## Cross-Repo

- Shared platform standards: `~/.claude/CLAUDE.md`
- SPI protocols: `omnibase_spi/CLAUDE.md`

## Rules

- Never import from omnibase_infra or omnibase_spi implementations
- All nodes follow 4-node architecture: EFFECT, COMPUTE, REDUCER, ORCHESTRATOR
- Zero backwards-compatibility shims
