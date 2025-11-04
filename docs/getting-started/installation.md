# Installation Guide - omnibase_core

**Status**: ✅ Complete
**Estimated Time**: 5 minutes

## Overview

This guide walks you through setting up your development environment for building ONEX nodes with omnibase_core.

## Prerequisites

- **Python 3.12+** (required for modern async features)
- **Poetry** (recommended package manager)
- **Git** (for version control)

## Installation Methods

### Method 1: Poetry (Recommended)

Poetry provides better dependency management and virtual environment handling.

#### 1. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add to your shell profile)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
poetry --version
```bash

#### 2. Install omnibase_core

**Option A: As a dependency in your project**
```bash
# In your project directory
poetry add omnibase_core
```bash

**Option B: For development**
```bash
# Clone the repository
git clone https://github.com/OmniNode-ai/omnibase_core.git
cd omnibase_core

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```bash

### Method 2: pip (Alternative)

If you prefer pip, you can install directly:

```bash
# Clone the repository
git clone https://github.com/OmniNode-ai/omnibase_core.git
cd omnibase_core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```python

## Verification

### 1. Basic Import Test

```bash
# With Poetry
poetry run python -c "from omnibase_core.nodes.node_compute import NodeCompute; print('✅ Installation successful!')"

# With pip
python -c "from omnibase_core.nodes.node_compute import NodeCompute; print('✅ Installation successful!')"
```python

### 2. All Node Types Test

```bash
poetry run python -c "
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
print('✅ All node types imported successfully!')
"
```bash

## Development Setup

### 1. Install Development Dependencies

```bash
# With Poetry
poetry install --with dev

# With pip
pip install -e ".[dev]"
```python

### 2. Run Tests

```bash
# With Poetry
poetry run pytest

# With pip
pytest
```bash

### 3. Run Linting

```bash
# With Poetry
poetry run ruff check .
poetry run mypy .

# With pip
ruff check .
mypy .
```text

## IDE Setup

### VS Code

1. Install the Python extension
2. Install the Pylance extension for type checking
3. Configure settings:

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black"
}
```python

### PyCharm

1. Open the project
2. Configure Python interpreter to use the virtual environment
3. Enable type checking in Settings → Editor → Inspections → Python → Type checker

## Troubleshooting

### Common Issues

#### Import Errors

```bash
# If you see import errors, ensure you're in the virtual environment
poetry shell  # or source venv/bin/activate

# Reinstall if needed
poetry install --force
```text

#### Python Version Issues

```bash
# Check Python version
python --version  # Should be 3.12+

# If using pyenv, install correct version
pyenv install 3.12.0
pyenv local 3.12.0
```bash

#### Poetry Issues

```bash
# Clear Poetry cache
poetry cache clear --all pypi

# Reinstall Poetry
curl -sSL https://install.python-poetry.org | python3 -
```python

### Verification Commands

```bash
# Check installation
poetry run python -c "
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
print('✅ All node types imported successfully!')
"

# Check version
poetry run python -c "import omnibase_core; print(f'omnibase_core version: {omnibase_core.__version__}')"
```yaml

## Next Steps

- [Quick Start Guide](QUICK_START.md) - Build your first node in 10 minutes
- [First Node Tutorial](FIRST_NODE.md) - Step-by-step node creation
- [Node Building Guide](../guides/node-building/README.md) - Comprehensive tutorials

## Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Search [existing issues](https://github.com/OmniNode-ai/omnibase_core/issues)
4. Create a [new issue](https://github.com/OmniNode-ai/omnibase_core/issues/new) with:
   - Python version
   - Installation method used
   - Full error message
   - Steps to reproduce

---

**Related Documentation**:
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Node Building Guide](../guides/node-building/README.md)
