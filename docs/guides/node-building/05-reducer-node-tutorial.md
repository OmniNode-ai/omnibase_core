# REDUCER Node Tutorial

**Status**: Coming Soon
**Reading Time**: 30 minutes (when complete)
**Prerequisites**: [COMPUTE Node Tutorial](03-compute-node-tutorial.md)
**What You'll Build**: A data aggregation node with streaming support

## Overview

In this tutorial, you'll build a complete REDUCER node that aggregates data from multiple sources. You'll learn:

- ✅ How to structure a REDUCER node
- ✅ Implementing fold/reduce operations
- ✅ Streaming support for large datasets
- ✅ Conflict resolution strategies
- ✅ State management
- ✅ Testing REDUCER nodes

## Quick Reference

Until this tutorial is complete, here's a minimal REDUCER node structure:

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeDataAggregatorReducer(NodeCoreBase):
    """REDUCER node for data aggregation."""

    async def process(self, input_data):
        """
        Aggregate data from multiple sources.

        Args:
            input_data: Data collection to aggregate

        Returns:
            Aggregated result
        """
        data_sources = input_data.sources

        # Reduce operation: Aggregate
        aggregated = {}

        for source in data_sources:
            for key, value in source.items():
                if key not in aggregated:
                    aggregated[key] = value
                else:
                    # Conflict resolution
                    aggregated[key] = self._merge_values(
                        aggregated[key],
                        value
                    )

        return {
            "aggregated_data": aggregated,
            "sources_processed": len(data_sources)
        }

    def _merge_values(self, value_a, value_b):
        """Resolve conflicts when merging values."""
        # Simple strategy: sum if numeric, latest if not
        if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
            return value_a + value_b
        return value_b  # Use latest value
```

## Key REDUCER Patterns

### Streaming Reduction

```python
async def process(self, input_data):
    """Process large dataset incrementally."""
    accumulator = self._initialize_accumulator()

    async for chunk in input_data.stream.chunks(size=1000):
        accumulator = self._reduce_chunk(accumulator, chunk)

    return accumulator
```

### Conflict Resolution

```python
def _resolve_conflict(self, value_a, value_b, strategy="latest"):
    """Resolve conflicts when merging."""
    if strategy == "latest":
        return value_b
    elif strategy == "sum":
        return value_a + value_b
    elif strategy == "max":
        return max(value_a, value_b)
```

### State Management

```python
def __init__(self, container):
    super().__init__(container)
    self.state_manager = container.state_manager

async def process(self, input_data):
    # Load existing state
    state = await self.state_manager.get_state(input_data.key)

    # Update state with new data
    updated_state = self._reduce(state, input_data.new_data)

    # Persist updated state
    await self.state_manager.set_state(input_data.key, updated_state)

    return updated_state
```

## Related Documentation

- [ONEX Four-Node Architecture](../../ONEX_FOUR_NODE_ARCHITECTURE.md) - See REDUCER node examples
- [REDUCER Node Template](../../reference/templates/REDUCER_NODE_TEMPLATE.md) - Production template
- [Node Types](02-node-types.md) - REDUCER node characteristics

## Coming Soon

This full tutorial is under development. In the meantime:

1. Review the [COMPUTE Node Tutorial](03-compute-node-tutorial.md) for general node patterns
2. See [REDUCER Node Template](../../reference/templates/REDUCER_NODE_TEMPLATE.md) for detailed examples
3. Check actual implementations in `src/omnibase_core/nodes/node_reducer.py`

**Next**: [ORCHESTRATOR Node Tutorial](06-orchestrator-node-tutorial.md) →
