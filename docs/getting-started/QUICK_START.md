# Quick Start Guide - omnibase_core

**Status**: ✅ Complete
**Estimated Time**: 10 minutes

## Your First 10 Minutes with ONEX

This guide gets you building ONEX nodes as quickly as possible. You'll create a working node using pre-configured convenience wrappers in under 10 minutes.

## Prerequisites

- ✅ [Installation completed](INSTALLATION.md)
- ✅ Basic Python knowledge
- ✅ Understanding of async/await

## What You'll Build

A simple COMPUTE node that doubles numbers - demonstrating how to use ONEX convenience wrappers with minimal boilerplate.

## The Four Convenience Wrappers

ONEX provides pre-configured convenience classes for each node type. These eliminate 80+ lines of boilerplate initialization:

### **NodeCompute** - Data Processing
```python
from omnibase_core.nodes.node_compute import NodeCompute

class NodeMyCompute(NodeCompute):
    async def process(self, input_data):
        # Transform data, calculate, validate
        return result
```

**Includes**: Caching layer, parallel processing, computation registry, performance monitoring

### **NodeEffect** - External Interactions
```python
from omnibase_core.nodes.node_effect import NodeEffect

class NodeMyEffect(NodeEffect):
    async def process(self, input_data):
        # Call APIs, database, file system
        return result
```

**Includes**: Transaction management, circuit breakers, retry policies, file operations, event emission

### **NodeReducer** - State Management
```python
from omnibase_core.nodes.node_reducer import NodeReducer

class NodeMyReducer(NodeReducer):
    async def process(self, input_data):
        # Aggregate state, reduce data, manage FSM
        return result
```

**Includes**: Streaming support, conflict resolution, reduction functions, batch processing

### **NodeOrchestrator** - Workflow Coordination
```python
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

class NodeMyOrchestrator(NodeOrchestrator):
    async def process(self, input_data):
        # Coordinate workflows, emit actions, manage dependencies
        return result
```

**Includes**: Action emission (thunks), dependency management, parallel coordination, load balancing

---

## Tutorial: Building a COMPUTE Node

Let's build a simple number doubler using **NodeCompute** to see how easy it is.

## Step 1: Create Your Project

```bash
# Create a new directory for your project
mkdir my-first-onex-node
cd my-first-onex-node

# Initialize with Poetry
poetry init --no-interaction
poetry add omnibase_core
poetry add --group dev pytest pytest-asyncio

# Create project structure
mkdir -p src/my_project/nodes
mkdir -p tests
touch src/my_project/__init__.py
touch src/my_project/nodes/__init__.py
```python

## Step 2: Create Your Node

**File**: `src/my_project/nodes/node_doubler_compute.py`

```python
"""A simple COMPUTE node that doubles numbers."""

from typing import Dict, Any
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeDoublerCompute(NodeCompute):
    """
    A simple COMPUTE node that doubles numbers.

    Uses NodeCompute convenience wrapper for production-ready features:
    - Caching layer for expensive computations
    - Parallel processing support
    - Computation registry
    - Performance monitoring
    - Automatic error handling
    """

    def __init__(self, container: ModelONEXContainer):
        """Initialize the doubler node."""
        super().__init__(container)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Double the input value.

        Args:
            input_data: Dictionary containing 'value' key with numeric value

        Returns:
            Dictionary with 'result' key containing doubled value

        Raises:
            ValueError: If input value is not numeric
        """
        # Extract and validate input
        value = input_data.get("value")
        if value is None:
            raise ValueError("Input must contain 'value' key")

        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Value must be numeric, got: {type(value).__name__}")

        # Perform computation
        result = numeric_value * 2

        return {
            "result": result,
            "original_value": numeric_value,
            "operation": "double"
        }
```python

> **💡 Why Use Convenience Wrappers?**
>
> ONEX provides four pre-configured convenience wrappers (**NodeCompute**, **NodeEffect**, **NodeReducer**, **NodeOrchestrator**):
> - ✅ Eliminate 80+ lines of boilerplate initialization
> - ✅ Include all necessary mixins (caching, logging, metrics, error handling)
> - ✅ Production-ready with best-practice patterns
> - ✅ Type-safe and fully tested
>
> **When to use each**:
> - **NodeCompute**: Pure data processing (calculations, transformations, validations)
> - **NodeEffect**: External interactions (APIs, databases, file systems, events)
> - **NodeReducer**: State aggregation (streaming data, conflict resolution, FSM)
> - **NodeOrchestrator**: Workflow coordination (multi-step workflows, dependencies, parallel execution)
>
> For detailed guides on each type, see:
> - [COMPUTE Tutorial](../guides/node-building/03_COMPUTE_NODE_TUTORIAL.md)
> - [EFFECT Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md)
> - [REDUCER Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)
> - [ORCHESTRATOR Tutorial](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)

## Step 3: Create a Test

**File**: `tests/test_doubler.py`

```python
"""Tests for the doubler compute node."""

import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from my_project.nodes.node_doubler_compute import NodeDoublerCompute


@pytest.fixture
def container():
    """Create a test container."""
    return ModelONEXContainer()


@pytest.fixture
def doubler_node(container):
    """Create a doubler node instance."""
    return NodeDoublerCompute(container)


@pytest.mark.asyncio
async def test_double_positive_number(doubler_node):
    """Test doubling a positive number."""
    result = await doubler_node.process({"value": 5})

    assert result["result"] == 10
    assert result["original_value"] == 5
    assert result["operation"] == "double"


@pytest.mark.asyncio
async def test_double_negative_number(doubler_node):
    """Test doubling a negative number."""
    result = await doubler_node.process({"value": -3})

    assert result["result"] == -6
    assert result["original_value"] == -3


@pytest.mark.asyncio
async def test_double_zero(doubler_node):
    """Test doubling zero."""
    result = await doubler_node.process({"value": 0})

    assert result["result"] == 0
    assert result["original_value"] == 0


@pytest.mark.asyncio
async def test_double_float(doubler_node):
    """Test doubling a float."""
    result = await doubler_node.process({"value": 2.5})

    assert result["result"] == 5.0
    assert result["original_value"] == 2.5


@pytest.mark.asyncio
async def test_missing_value_raises_error(doubler_node):
    """Test that missing value raises ValueError."""
    with pytest.raises(ValueError, match="Input must contain 'value' key"):
        await doubler_node.process({})


@pytest.mark.asyncio
async def test_non_numeric_value_raises_error(doubler_node):
    """Test that non-numeric value raises ValueError."""
    with pytest.raises(ValueError, match="Value must be numeric"):
        await doubler_node.process({"value": "not a number"})
```python

## Step 4: Run Your Tests

```bash
# Run the tests
poetry run pytest tests/test_doubler.py -v

# Expected output:
# tests/test_doubler.py::test_double_positive_number PASSED
# tests/test_doubler.py::test_double_negative_number PASSED
# tests/test_doubler.py::test_double_zero PASSED
# tests/test_doubler.py::test_double_float PASSED
# tests/test_doubler.py::test_missing_value_raises_error PASSED
# tests/test_doubler.py::test_non_numeric_value_raises_error PASSED
```python

## Step 5: Use Your Node

**File**: `example_usage.py`

```python
"""Example usage of the doubler node."""

import asyncio
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from my_project.nodes.node_doubler_compute import NodeDoublerCompute


async def main():
    """Demonstrate the doubler node."""
    # Create container and node
    container = ModelONEXContainer()
    doubler = NodeDoublerCompute(container)

    # Test different inputs
    test_cases = [
        {"value": 10},
        {"value": -5},
        {"value": 0},
        {"value": 3.14},
    ]

    print("Doubler Node Demo")
    print("=" * 20)

    for test_case in test_cases:
        try:
            result = await doubler.process(test_case)
            print(f"Input: {test_case['value']} → Output: {result['result']}")
        except ValueError as e:
            print(f"Error with {test_case}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```bash

Run it:

```bash
poetry run python example_usage.py

# Expected output:
# Doubler Node Demo
# ====================
# Input: 10 → Output: 20
# Input: -5 → Output: -10
# Input: 0 → Output: 0
# Input: 3.14 → Output: 6.28
```python

## What Just Happened?

You created a production-ready COMPUTE node with:

- ✅ **Convenience Wrapper** - NodeCompute eliminates 80+ lines of boilerplate
- ✅ **Zero setup** - All mixins pre-configured (caching, logging, metrics, error handling)
- ✅ **Built-in caching** - Automatic result caching for expensive computations
- ✅ **Type safety** - Proper typing and validation
- ✅ **Error handling** - Comprehensive input validation with ModelOnexError
- ✅ **Testing** - Full test coverage with pytest
- ✅ **ONEX compliance** - Follows 4-node architecture patterns
- ✅ **Async support** - Non-blocking computation with parallel processing support

## Key ONEX Concepts You Used

1. **NodeCompute (Convenience Wrapper)** - Pre-configured COMPUTE node with caching and parallel processing
2. **Container Pattern** - Dependency injection via ModelONEXContainer
3. **Async Processing** - Non-blocking computation with async/await
4. **Error Handling** - Proper exception management
5. **Type Safety** - Input/output validation

## Next Steps

Choose your learning path:

### 🚀 **Build Each Node Type** (Recommended)

Start building with the other convenience wrappers:

1. **[EFFECT Tutorial](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md)** - Build a file backup system
   - Learn: Transaction management, circuit breakers, retry policies
   - Use case: APIs, databases, file operations, event emission

2. **[REDUCER Tutorial](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md)** - Build a metrics aggregator
   - Learn: Streaming data, conflict resolution, batch processing
   - Use case: State machines, data aggregation, reduce operations

3. **[ORCHESTRATOR Tutorial](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)** - Build a workflow coordinator
   - Learn: Action emission (thunks), dependency management, parallel execution
   - Use case: Multi-step workflows, coordinating multiple nodes

### 📚 **Deep Dive**
- [First Node Tutorial](FIRST_NODE.md) - Complete example with Pydantic models
- [COMPUTE Tutorial](../guides/node-building/03_COMPUTE_NODE_TUTORIAL.md) - Advanced COMPUTE patterns
- [Node Types](../guides/node-building/02_NODE_TYPES.md) - Understanding all four node types
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - System design principles

## Common Enhancements

### Add Input/Output Models

```python
from pydantic import BaseModel, Field

class DoublerInput(BaseModel):
    value: float = Field(description="Number to double")

class DoublerOutput(BaseModel):
    result: float = Field(description="Doubled value")
    original_value: float = Field(description="Original input value")
    operation: str = Field(default="double", description="Operation performed")
```python

### Add Caching

```python
def __init__(self, container: ModelONEXContainer):
    super().__init__(container)
    self._cache = {}  # Simple cache

async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    cache_key = str(input_data.get("value"))
    if cache_key in self._cache:
        return self._cache[cache_key]

    result = await self._compute(input_data)
    self._cache[cache_key] = result
    return result
```python

### Add Logging

```python
import logging

logger = logging.getLogger(__name__)

async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Processing input: {input_data}")
    result = await self._compute(input_data)
    logger.info(f"Result: {result}")
    return result
```python

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the virtual environment
poetry shell

# Check installation
poetry run python -c "from omnibase_core.nodes.node_compute import NodeCompute; print('OK')"
```python

### Test Failures

```bash
# Run with verbose output
poetry run pytest tests/test_doubler.py -vvs

# Run specific test
poetry run pytest tests/test_doubler.py::test_double_positive_number -v
```bash

### Type Checking

```bash
# Install mypy
poetry add --group dev mypy

# Run type checking
poetry run mypy src/my_project/nodes/node_doubler_compute.py
```yaml

## Summary

🎉 **Congratulations!** You've built your first ONEX node using convenience wrappers!

You now understand:
- ✅ How to use **NodeCompute** convenience wrapper
- ✅ The four node types (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)
- ✅ What mixins each wrapper includes
- ✅ ONEX 4-node architecture patterns
- ✅ Async processing with proper error handling
- ✅ Testing strategies
- ✅ Type safety and validation

**Ready for more?**
- Try building other node types: [EFFECT](../guides/node-building/04_EFFECT_NODE_TUTORIAL.md), [REDUCER](../guides/node-building/05_REDUCER_NODE_TUTORIAL.md), [ORCHESTRATOR](../guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md)
- Or dive deeper: [First Node Tutorial](FIRST_NODE.md) with Pydantic models and advanced patterns

---

**Related Documentation**:
- [Installation Guide](INSTALLATION.md)
- [Node Building Guide](../guides/node-building/README.md)
- [ONEX Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
