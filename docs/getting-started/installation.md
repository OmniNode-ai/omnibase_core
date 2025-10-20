# Installation Guide - omnibase_core

**Status**: 🚧 Coming Soon
**Estimated Time**: 5 minutes

## Overview

This guide will walk you through setting up your development environment for building ONEX nodes with omnibase_core.

## Prerequisites

- Python 3.12+
- Poetry (for package management)
- Git

## Installation Steps

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Clone or Install omnibase_core

**Option A: As a dependency in your project**
```bash
poetry add omnibase_core
```

**Option B: For development**
```bash
git clone <repository-url>
cd omnibase_core
poetry install
```

### 3. Verify Installation

```bash
poetry run python -c "from omnibase_core.core.infrastructure_service_bases import NodeCoreBase; print('✅ Installation successful!')"
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Build your first node in 10 minutes
- [First Node Tutorial](first-node.md) - Step-by-step node creation

## Troubleshooting

**Common issues and solutions will be documented here.**

---

**Related Documentation**:
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Node Building Guide](../guides/node-building/README.md)
