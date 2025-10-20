# Quick Start Guide - omnibase_core

**Status**: 🚧 Coming Soon
**Estimated Time**: 10 minutes

## Your First 10 Minutes with ONEX

This guide gets you building ONEX nodes as quickly as possible.

## What You'll Build

A simple COMPUTE node that doubles numbers - demonstrating the core ONEX pattern.

## Step 1: Create Your Node

```python
from omnibase_core.core.infrastructure_service_bases import NodeComputeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeDoublerCompute(NodeComputeService):
    """A simple COMPUTE node that doubles numbers."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

    async def process(self, input_data):
        """Double the input value."""
        value = input_data.get("value", 0)
        return {"result": value * 2}
```

## Step 2: Test Your Node

```bash
poetry run pytest tests/test_doubler.py
```

## Step 3: Explore More

**Continue your journey**:
- [First Node Tutorial](first-node.md) - Detailed walkthrough
- [Node Types](../guides/node-building/02_NODE_TYPES.md) - Understanding node types
- [COMPUTE Tutorial](../guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) - Complete tutorial

## What Just Happened?

You created a COMPUTE node with:
- ✅ Zero boilerplate (handled by base class)
- ✅ Type safety (from base contracts)
- ✅ ONEX architectural compliance
- ✅ Ready for production patterns

## Next Steps

Choose your path:
- **Beginner**: Follow [First Node Tutorial](first-node.md)
- **Experienced**: Jump to [Node Building Guide](../guides/node-building/README.md)

---

**Related Documentation**:
- [What is a Node?](../guides/node-building/01_WHAT_IS_A_NODE.md)
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
