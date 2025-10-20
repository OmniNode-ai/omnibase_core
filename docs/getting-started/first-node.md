# Your First Node - omnibase_core

**Status**: 🚧 Coming Soon
**Estimated Time**: 20 minutes

## Overview

This tutorial guides you through creating your first complete ONEX node from scratch, with testing and deployment.

## What You'll Build

A temperature converter COMPUTE node that:
- Converts between Celsius and Fahrenheit
- Validates input ranges
- Handles errors gracefully
- Includes comprehensive tests

## Prerequisites

- Completed [Installation](installation.md)
- Completed [Quick Start](quick-start.md)
- Basic Python knowledge

## Step-by-Step Guide

### Step 1: Project Setup

```bash
mkdir my-first-node
cd my-first-node
poetry init
poetry add omnibase_core
```

### Step 2: Create Your Node

**Full implementation coming soon...**

### Step 3: Write Tests

**Test examples coming soon...**

### Step 4: Run and Validate

```bash
poetry run pytest tests/
poetry run mypy src/
```

## What You Learned

By completing this tutorial, you've learned:
- ✅ How to structure an ONEX node project
- ✅ How to implement a COMPUTE node
- ✅ How to write node tests
- ✅ How to validate with type checking

## Next Steps

**Continue learning**:
- [Node Building Guide](../guides/node-building/README.md) - Comprehensive guide
- [EFFECT Node Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md) - External interactions
- [REDUCER Node Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md) - State management

**Challenge**: Extend your node to support Kelvin conversions!

---

**Related Documentation**:
- [Node Types](../guides/node-building/02_NODE_TYPES.md)
- [Testing Guide](../guides/testing-guide.md)
- [Error Handling](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
