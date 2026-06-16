> **Navigation**: [Home](../INDEX.md) > Getting Started > Installation

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# Installation Guide - omnibase_core

**Status**: ✅ Complete
**Estimated Time**: 5 minutes

## Overview

This guide walks you through setting up your development environment for building ONEX nodes with omnibase_core.

## Prerequisites

- **Python 3.12+** (required for modern async features)
- **uv** (required package manager)
- **Git** (for version control)

## Installation Methods

### Method 1: uv (Recommended)

uv is the required package manager for this project. All Python commands must be run via `uv run`.

#### 1. Install uv

```bash
# Install uv (see https://docs.astral.sh/uv/getting-started/installation/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

#### 2. Install omnibase_core

**Option A: As a dependency in your project**

```bash
# In your project directory
uv add omnibase_core
```

**Option B: For development**

```bash
# Clone the repository
git clone https://github.com/OmniNode-ai/omnibase_core.git
cd omnibase_core

# Install all dependencies (including dev extras)
uv sync --all-extras

# Install pre-commit hooks
pre-commit install
```

## Verification

### 1. Basic Import Test

```bash
uv run python -c "from omnibase_core.nodes.node_compute import NodeCompute; print('Installation successful!')"
```

### 2. All Node Types Test

```bash
uv run python -c "
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
print('All node types imported successfully!')
"
```

## Development Setup

### 1. Install Development Dependencies

```bash
uv sync --all-extras
```

### 2. Run Tests

```bash
uv run pytest tests/
```

### 3. Run Linting

```bash
uv run ruff check src/ tests/
uv run mypy src/omnibase_core/
```

## IDE Setup

### VS Code

1. Install the Python extension
2. Install the Pylance extension for type checking
3. Install the [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) (`charliermarsh.ruff`)
4. Configure settings:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    "mypy.enabled": true
}
```

### PyCharm

1. Open the project
2. Configure Python interpreter to use `.venv/bin/python` (created by `uv sync`)
3. Enable type checking in Settings → Editor → Inspections → Python → Type checker

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# Ensure uv sync has been run
uv sync --all-extras

# Confirm the venv is active or prefix commands with uv run
uv run python -c "import omnibase_core"
```

#### Python Version Issues

```bash
# Check Python version
python --version  # Should be 3.12+

# If using pyenv, install correct version
pyenv install 3.12.0
pyenv local 3.12.0
```

### Verification Commands

```bash
# Check installation
uv run python -c "
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
print('All node types imported successfully!')
"

# Check version
uv run python -c "import omnibase_core; print(f'omnibase_core version: {omnibase_core.__version__}')"
```

## Next Steps

- [Quick Start Guide](QUICK_START.md) - Build your first node in 10 minutes
- [First Node Tutorial](FIRST_NODE.md) - Step-by-step node creation
- [Node Building Guide](../guides/node-building/README.md) - Comprehensive tutorials

## Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Search [existing issues](https://github.com/OmniNode-ai/omnibase_core/issues)
3. Create a [new issue](https://github.com/OmniNode-ai/omnibase_core/issues/new) with:
   - Python version
   - Installation method used
   - Full error message
   - Steps to reproduce

---

**Related Documentation**:
- [uv Documentation](https://docs.astral.sh/uv/)
- [Node Building Guide](../guides/node-building/README.md)
