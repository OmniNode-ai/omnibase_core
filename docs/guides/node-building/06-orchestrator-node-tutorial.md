# ORCHESTRATOR Node Tutorial

**Status**: Coming Soon
**Reading Time**: 45 minutes (when complete)
**Prerequisites**: All other node tutorials
**What You'll Build**: A workflow coordination node managing multiple nodes

## Overview

In this tutorial, you'll build a complete ORCHESTRATOR node that coordinates a multi-step workflow. You'll learn:

- ✅ How to structure an ORCHESTRATOR node
- ✅ Coordinating multiple nodes
- ✅ Dependency management
- ✅ Parallel execution patterns
- ✅ Error recovery and compensation
- ✅ Testing ORCHESTRATOR nodes

## Quick Reference

Until this tutorial is complete, here's a minimal ORCHESTRATOR node structure:

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodeWorkflowOrchestrator(NodeCoreBase):
    """ORCHESTRATOR node for workflow coordination."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Inject dependent nodes
        self.validator = NodeDataValidatorCompute(container)
        self.fetcher = NodeDataFetcherEffect(container)
        self.processor = NodeDataProcessorCompute(container)
        self.saver = NodeDataSaverEffect(container)

    async def process(self, input_data):
        """
        Coordinate multi-step workflow.

        Args:
            input_data: Workflow request

        Returns:
            Workflow result
        """
        # Step 1: Validate input
        validation = await self.validator.process(input_data)
        if not validation.result["valid"]:
            return {"success": False, "errors": validation.result["errors"]}

        # Step 2: Fetch data
        fetched = await self.fetcher.process(input_data)

        # Step 3: Process data
        processed = await self.processor.process(fetched)

        # Step 4: Save results
        saved = await self.saver.process(processed)

        return {
            "success": True,
            "result": saved.result,
            "steps_completed": ["validate", "fetch", "process", "save"]
        }
```

## Key ORCHESTRATOR Patterns

### Sequential Workflow

```python
async def process(self, input_data):
    """Execute steps in sequence."""
    result_1 = await self.step_1.process(input_data)
    result_2 = await self.step_2.process(result_1)
    result_3 = await self.step_3.process(result_2)
    return result_3
```

### Parallel Workflow

```python
async def process(self, input_data):
    """Execute independent operations in parallel."""
    results = await asyncio.gather(
        self.operation_a.process(input_data),
        self.operation_b.process(input_data),
        self.operation_c.process(input_data)
    )
    return results
```

### Error Recovery

```python
async def process(self, input_data):
    """Workflow with compensation logic."""
    try:
        result_1 = await self.step_1.process(input_data)
        result_2 = await self.step_2.process(result_1)
        return result_2
    except Step2Error:
        # Compensate for step 1 (undo)
        await self.step_1_compensate.process(result_1)
        raise
```

### Dependency Management

```python
async def process(self, input_data):
    """Execute with dependency graph."""
    # Level 1: Independent tasks
    task_a, task_b = await asyncio.gather(
        self.task_a.process(input_data),
        self.task_b.process(input_data)
    )

    # Level 2: Depends on Level 1
    task_c = await self.task_c.process({"a": task_a, "b": task_b})

    # Level 3: Depends on Level 2
    final = await self.task_d.process(task_c)

    return final
```

## Related Documentation

- [ONEX Four-Node Architecture](../../ONEX_FOUR_NODE_ARCHITECTURE.md) - See ORCHESTRATOR node examples
- [ORCHESTRATOR Node Template](../../reference/templates/ORCHESTRATOR_NODE_TEMPLATE.md) - Production template
- [Node Types](02-node-types.md) - ORCHESTRATOR node characteristics

## Coming Soon

This full tutorial is under development. In the meantime:

1. Review the [COMPUTE Node Tutorial](03-compute-node-tutorial.md) for general node patterns
2. See [ORCHESTRATOR Node Template](../../reference/templates/ORCHESTRATOR_NODE_TEMPLATE.md) for detailed examples
3. Check actual implementations in `src/omnibase_core/nodes/node_orchestrator.py`

**Next**: [Patterns Catalog](07-patterns-catalog.md) →
