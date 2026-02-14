> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Node Building](./README.md) > COMPUTE Node Tutorial

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../../CLAUDE.md).

# COMPUTE Node Tutorial

**Reading Time**: 30 minutes
**Prerequisites**: [What is a Node?](01_WHAT_IS_A_NODE.md), [Node Types](02_NODE_TYPES.md)
**What You'll Build**: A price calculation node with tax, discounts, and caching

## Recommended Approach

This tutorial shows **TWO approaches**:

1. **RECOMMENDED (95% of use cases)**: `ModelServiceCompute` wrapper
   - Production-ready with built-in features (health checks, metrics, caching)
   - Service mode for long-running MCP servers
   - Minimal boilerplate

2. **DIRECT (5% of use cases)**: `NodeCompute` base class
   - Direct access to computation registry system
   - Built-in caching (ModelComputeCache) and parallel processing
   - More control over computation execution

**Start with ModelServiceCompute unless you need direct access to NodeCompute features.**

See [Node Class Hierarchy Guide](../../architecture/NODE_CLASS_HIERARCHY.md) for detailed comparison.

## Execution Shape

> **Canonical Execution Shape**: COMPUTE nodes are **pure transformations** with no I/O.
> They receive data from EFFECT nodes and pass results to REDUCER or ORCHESTRATOR nodes.
> See [Canonical Execution Shapes](../../architecture/CANONICAL_EXECUTION_SHAPES.md) for the complete pattern.

**Key Constraint**: COMPUTE nodes must not perform any I/O operations (no network calls, no file writes, no database access). All I/O should be handled by EFFECT nodes. See [Node Purity Guarantees](../../architecture/NODE_PURITY_GUARANTEES.md) for enforcement details.

---

## Handler Architecture

> **Architectural Rule**: Nodes are thin coordination shells. Business logic belongs in **handlers**, not in the node class itself. The node delegates to a handler, and the handler returns a `ModelHandlerOutput`.

### COMPUTE Output Constraints

| Field | COMPUTE | EFFECT | REDUCER | ORCHESTRATOR |
|-------|---------|--------|---------|--------------|
| `result` | **Required** | Forbidden | Forbidden | Forbidden |
| `events[]` | Forbidden | Allowed | Forbidden | Allowed |
| `intents[]` | Forbidden | Forbidden | Forbidden | Allowed |
| `projections[]` | Forbidden | Forbidden | Allowed | Forbidden |

COMPUTE is the **only** node kind that returns a typed `result`.

### Handler-Based Pattern (Recommended)

In production ONEX code, the node delegates to a handler. The handler performs the computation and returns `ModelHandlerOutput.for_compute(result=...)`:

```python
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.enums.enum_node_kind import EnumNodeKind


class HandlerPriceCalculator:
    """Handler containing the actual computation logic."""

    def execute(
        self,
        input_data: ModelPriceCalculatorInput,
    ) -> ModelHandlerOutput:
        """
        Pure computation -- no I/O allowed.

        Returns:
            ModelHandlerOutput with result set (COMPUTE constraint).
        """
        subtotal = sum(
            item.price * item.quantity for item in input_data.items
        )
        discount = self._calculate_discount(subtotal, input_data.discount_code)
        discounted = subtotal - discount
        tax = discounted * input_data.tax_rate
        total = discounted + tax

        result = ModelPriceCalculatorOutput(
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            tax=round(tax, 2),
            total=round(total, 2),
            discount_code_applied=input_data.discount_code,
            items_count=len(input_data.items),
        )

        # COMPUTE nodes MUST return result; events/intents/projections forbidden
        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,  # from handler args
            correlation_id=correlation_id,         # from handler args
            result=result,
        )

    def _calculate_discount(self, subtotal: float, code: str | None) -> float:
        if not code:
            return 0.0
        # ... discount logic ...
        return 0.0


class NodePriceCalculatorCompute(NodeCompute):
    """Thin shell -- delegates to handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self._handler = HandlerPriceCalculator()

    async def process(self, input_data):
        return self._handler.execute(input_data)
```

The tutorial below shows computation logic inline for teaching clarity. In production, always extract logic into a handler.

---

## Overview

In this tutorial, you'll build a complete COMPUTE node that calculates prices with tax and discounts. You'll learn:

- ✅ How to structure a COMPUTE node
- ✅ Implementing typed input/output models
- ✅ Adding caching for performance
- ✅ Error handling and validation
- ✅ Testing your node

**Final result**: A production-ready price calculator node.

## What We're Building

```
# Usage example
calculator = NodePriceCalculatorCompute(container)

result = await calculator.process(
    ModelComputeInput(
        items=[
            {"name": "Widget", "price": 10.00, "quantity": 2},
            {"name": "Gadget", "price": 25.00, "quantity": 1}
        ],
        discount_code="SAVE10",
        tax_rate=0.08
    )
)

print(result.result)
# {
#     "subtotal": 45.00,
#     "discount": 4.50,  # 10% off
#     "tax": 3.24,       # 8% tax on discounted amount
#     "total": 43.74
# }
```

## Project Setup

### 1. Create Project Structure

```
# Navigate to your project
cd your_project

# Create node directory
mkdir -p src/your_project/nodes
mkdir -p tests/nodes

# Create files
touch src/your_project/nodes/__init__.py
touch src/your_project/nodes/node_price_calculator_compute.py
touch tests/nodes/test_node_price_calculator.py
```

### 2. Install Dependencies

```
# Ensure you have omnibase_core
poetry add omnibase_core

# Add dev dependencies for testing
poetry add --group dev pytest pytest-asyncio
```

### 3. Verify Installation

```
poetry run python -c "from omnibase_core.nodes import NodeCompute; print('✓ Ready!')"
```

## Step 1: Define Input Model

First, define what data your node accepts.

**File**: `src/your_project/nodes/model_price_calculator_input.py`

```
"""Input model for price calculator."""

from pydantic import BaseModel, Field, field_validator


class CartItem(BaseModel):
    """Individual item in shopping cart."""

    name: str = Field(description="Product name")
    price: float = Field(gt=0, description="Unit price (must be positive)")
    quantity: int = Field(gt=0, description="Quantity (must be positive)")


class ModelPriceCalculatorInput(BaseModel):
    """Input for price calculation."""

    items: list[CartItem] = Field(
        min_items=1,
        description="Cart items to calculate price for"
    )

    discount_code: str | None = Field(
        default=None,
        description="Optional discount code"
    )

    tax_rate: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        description="Tax rate (0.0 to 1.0)"
    )

    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing"
    )

    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        """Ensure at least one item exists."""
        if not v or len(v) == 0:
            raise ValueError("Cart must contain at least one item")
        return v

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "items": [
                    {"name": "Widget", "price": 10.00, "quantity": 2},
                    {"name": "Gadget", "price": 25.00, "quantity": 1}
                ],
                "discount_code": "SAVE10",
                "tax_rate": 0.08
            }
        }
    }
```

**Key points**:
- ✅ Uses Pydantic for automatic validation
- ✅ Descriptive field documentation
- ✅ Validation constraints (gt=0, min_items=1)
- ✅ Example in schema_extra for documentation

## Step 2: Define Output Model

Define what your node returns.

**File**: `src/your_project/nodes/model_price_calculator_output.py`

```
"""Output model for price calculator."""

from pydantic import BaseModel, Field


class ModelPriceCalculatorOutput(BaseModel):
    """Output from price calculation."""

    subtotal: float = Field(description="Sum of all items before discounts")
    discount: float = Field(description="Total discount amount")
    tax: float = Field(description="Tax amount on discounted subtotal")
    total: float = Field(description="Final total price")

    discount_code_applied: str | None = Field(
        default=None,
        description="Discount code that was applied, if any"
    )

    items_count: int = Field(description="Number of items in cart")

    processing_time_ms: float = Field(
        default=0.0,
        description="Computation time in milliseconds"
    )

    cache_hit: bool = Field(
        default=False,
        description="Whether result came from cache"
    )

    model_config = {
        "validate_assignment": True,
        "json_schema_extra": {
            "example": {
                "subtotal": 45.00,
                "discount": 4.50,
                "tax": 3.24,
                "total": 43.74,
                "discount_code_applied": "SAVE10",
                "items_count": 2,
                "processing_time_ms": 2.5,
                "cache_hit": False
            }
        }
    }
```

**Key points**:
- ✅ All calculation results included
- ✅ Performance metrics (processing_time_ms, cache_hit)
- ✅ Metadata for debugging (items_count, discount_code_applied)

## Step 3: Implement the COMPUTE Node

Now build the actual node.

### ✅ RECOMMENDED: Using ModelServiceCompute Wrapper

For **95% of use cases**, use the production-ready `ModelServiceCompute` wrapper that includes all standard features:

**File**: `src/your_project/nodes/node_price_calculator_compute.py`

```
"""COMPUTE node for price calculation with tax and discounts."""

import time
from omnibase_core.infrastructure.infra_bases import ModelServiceCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

from .model_price_calculator_input import ModelPriceCalculatorInput
from .model_price_calculator_output import ModelPriceCalculatorOutput


class NodePriceCalculatorCompute(ModelServiceCompute):
    """
    COMPUTE node for price calculations.

    Calculates cart total with discounts and tax. Implements caching
    for performance on repeated calculations.

    Production-ready features (via ModelServiceCompute):
    - ✅ Health checks
    - ✅ Metrics tracking
    - ✅ Event bus integration
    - ✅ Circuit breaker
    - ✅ Result caching
    - ✅ Performance tracking
    """

    # Discount codes (in production, fetch from database)
    DISCOUNT_CODES: dict[str, float] = {
        "SAVE10": 0.10,   # 10% off
        "SAVE20": 0.20,   # 20% off
        "SAVE30": 0.30,   # 30% off
        "FLAT5": 5.00,    # $5 off (flat amount)
    }

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize price calculator node.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)

        # Simple in-memory cache (in production, use Redis)
        self._cache: dict[str, ModelPriceCalculatorOutput] = {}

        # Performance tracking
        self.computation_count = 0
        self.cache_hits = 0

    async def process(
        self,
        input_data: ModelPriceCalculatorInput
    ) -> ModelPriceCalculatorOutput:
        """
        Calculate price with tax and discounts.

        Args:
            input_data: Cart items and calculation parameters

        Returns:
            Calculated price breakdown

        Raises:
            ModelOnexError: If calculation fails or validation error
        """
        start_time = time.time()

        try:
            # Validate input
            self._validate_input(input_data)

            # Generate cache key
            cache_key = self._generate_cache_key(input_data)

            # Check cache
            if cache_key in self._cache:
                self.cache_hits += 1
                cached_result = self._cache[cache_key]
                cached_result.cache_hit = True
                return cached_result

            # Execute calculation
            result = self._calculate_price(input_data)

            # Add performance metadata
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time
            result.cache_hit = False

            # Cache result
            self._cache[cache_key] = result

            # Update metrics
            self.computation_count += 1

            return result

        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Validation failed: {str(e)}",
                context={"input_data": input_data.model_dump()}
            ) from e

        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                message=f"Price calculation failed: {str(e)}",
                context={"input_data": input_data.model_dump()}
            ) from e

    def _calculate_price(
        self,
        input_data: ModelPriceCalculatorInput
    ) -> ModelPriceCalculatorOutput:
        """
        Core calculation logic.

        Args:
            input_data: Validated input data

        Returns:
            Calculated price breakdown
        """
        # Step 1: Calculate subtotal
        subtotal = sum(
            item.price * item.quantity
            for item in input_data.items
        )

        # Step 2: Apply discount
        discount = self._calculate_discount(
            subtotal,
            input_data.discount_code
        )

        # Step 3: Calculate tax on discounted amount
        discounted_subtotal = subtotal - discount
        tax = discounted_subtotal * input_data.tax_rate

        # Step 4: Calculate total
        total = discounted_subtotal + tax

        return ModelPriceCalculatorOutput(
            subtotal=round(subtotal, 2),
            discount=round(discount, 2),
            tax=round(tax, 2),
            total=round(total, 2),
            discount_code_applied=input_data.discount_code,
            items_count=len(input_data.items)
        )

    def _calculate_discount(
        self,
        subtotal: float,
        discount_code: str | None
    ) -> float:
        """
        Calculate discount amount.

        Args:
            subtotal: Cart subtotal
            discount_code: Optional discount code

        Returns:
            Discount amount (0.0 if no code or invalid code)
        """
        if not discount_code:
            return 0.0

        discount_code = discount_code.upper()

        if discount_code not in self.DISCOUNT_CODES:
            # Invalid code: no discount (could also raise error)
            return 0.0

        discount_value = self.DISCOUNT_CODES[discount_code]

        # Check if percentage or flat amount
        if discount_code.startswith("FLAT"):
            # Flat amount (e.g., $5 off)
            return min(discount_value, subtotal)  # Don't exceed subtotal
        else:
            # Percentage (e.g., 10% off)
            return subtotal * discount_value

    def _validate_input(self, input_data: ModelPriceCalculatorInput) -> None:
        """
        Additional business logic validation.

        Args:
            input_data: Input to validate

        Raises:
            ValueError: If validation fails
        """
        # Pydantic handles basic validation, but add business logic here

        # Example: Validate maximum cart size
        if len(input_data.items) > 100:
            raise ValueError("Cart cannot exceed 100 items")

        # Example: Validate maximum item price
        for item in input_data.items:
            if item.price > 10000:
                raise ValueError(f"Item '{item.name}' price exceeds maximum")

    def _generate_cache_key(
        self,
        input_data: ModelPriceCalculatorInput
    ) -> str:
        """
        Generate cache key for input data.

        Args:
            input_data: Input data to generate key for

        Returns:
            Cache key string
        """
        # Create deterministic key from input
        items_key = ",".join(
            f"{item.name}:{item.price}:{item.quantity}"
            for item in sorted(input_data.items, key=lambda x: x.name)
        )

        return f"{items_key}|{input_data.discount_code}|{input_data.tax_rate}"

    def get_metrics(self) -> dict[str, float]:
        """
        Get node performance metrics.

        Returns:
            Dictionary with metrics
        """
        total_requests = self.computation_count + self.cache_hits

        return {
            "total_requests": total_requests,
            "computations": self.computation_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / total_requests
                if total_requests > 0 else 0.0
            )
        }
```

**What `ModelServiceCompute` Provides**:
- ✅ **Health Checks**: Built-in readiness and liveness endpoints
- ✅ **Metrics**: Automatic prometheus-style metrics tracking
- ✅ **Event Bus**: Kafka/Redpanda integration for event publishing
- ✅ **Circuit Breaker**: Automatic failure protection
- ✅ **Computation Cache**: Built-in `ModelComputeCache` with TTL and eviction policies
- ✅ **Thread Pool**: `ThreadPoolExecutor` for parallel computation support
- ✅ **Computation Registry**: Register and manage computation functions
- ✅ **Performance Tracking**: Built-in metrics for cache hits, processing time
- ✅ **Configuration Support**: Automatic config loading from `NodeConfigProvider`

**Key Implementation Points**:
- ✅ Inherits from `ModelServiceCompute` production wrapper
- ✅ Typed `process()` method
- ✅ Zero boilerplate for production features
- ✅ Comprehensive error handling
- ✅ Performance tracking built-in
- ✅ Clear separation of concerns

### When to Use Which Approach

| Feature | ModelServiceCompute | NodeCompute |
|---------|---------------------|-------------|
| **Health Checks** | ✅ Included | Manual setup |
| **Metrics** | ✅ Included | ✅ Built-in computation_metrics |
| **Service Mode** | ✅ MixinNodeService | Not included |
| **Computation Cache** | ✅ Via MixinCaching | ✅ Built-in ModelComputeCache |
| **Computation Registry** | Via NodeCompute | ✅ Built-in register_computation() |
| **Parallel Processing** | Via NodeCompute | ✅ Built-in ThreadPoolExecutor |
| **Setup Complexity** | Minimal | Moderate |
| **Production Ready** | ✅ Yes | ✅ Yes (core features only) |
| **Use Case** | 95% of applications | Direct computation control |

### DIRECT: Using NodeCompute Base Class

For **5% of use cases** where you need direct access to NodeCompute features:

```python
from omnibase_core.nodes import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class NodePriceCalculatorCompute(NodeCompute):
    """
    COMPUTE node with direct NodeCompute inheritance.

    Use this approach when:
    - You need direct access to NodeCompute's built-in features
    - You want to use the computation registry system
    - You're implementing custom computation types
    - You don't need the production service wrapper features
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

        # NodeCompute provides built-in features:
        # - self.computation_cache (ProtocolComputeCache)
        # - self.computation_registry (dict of computation functions)
        # - self.computation_metrics (performance tracking)
        # - Parallelization via ProtocolParallelExecutor injection

        # Register custom computation if needed
        self.register_computation("price_calculation", self._calculate_price_func)

    def _calculate_price_func(self, data: dict) -> dict:
        """Custom computation function registered with the node."""
        # Your computation logic here
        return {"result": "computed"}

    # ... rest of implementation uses NodeCompute's process() method
```

**When to use NodeCompute directly**:
- Direct access to computation registry system
- Custom computation types with register_computation()
- Built-in caching via ProtocolComputeCache
- Parallelization via ProtocolParallelExecutor injection
- You don't need the full production service wrapper

**When to use ModelServiceCompute** (recommended):
- Standard COMPUTE operations (95% of cases)
- Production deployment
- Need health checks, metrics, event bus out-of-the-box
- Following ONEX best practices

## Step 4: Write Tests

Always test your nodes!

**File**: `tests/nodes/test_node_price_calculator.py`

```
"""Tests for price calculator node."""

import pytest
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from your_project.nodes.node_price_calculator_compute import NodePriceCalculatorCompute
from your_project.nodes.model_price_calculator_input import (
    ModelPriceCalculatorInput,
    CartItem
)


@pytest.fixture
def container():
    """Create test container."""
    return ModelONEXContainer()


@pytest.fixture
def calculator(container):
    """Create calculator node."""
    return NodePriceCalculatorCompute(container)


@pytest.mark.asyncio
async def test_basic_calculation(calculator):
    """Test basic price calculation without discount."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=2),
            CartItem(name="Gadget", price=25.00, quantity=1)
        ],
        tax_rate=0.08
    )

    result = await calculator.process(input_data)

    assert result.subtotal == 45.00  # 10*2 + 25*1
    assert result.discount == 0.0
    assert result.tax == 3.60  # 45 * 0.08
    assert result.total == 48.60  # 45 + 3.60
    assert not result.cache_hit


@pytest.mark.asyncio
async def test_percentage_discount(calculator):
    """Test calculation with percentage discount."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=2)
        ],
        discount_code="SAVE10",  # 10% off
        tax_rate=0.08
    )

    result = await calculator.process(input_data)

    assert result.subtotal == 20.00
    assert result.discount == 2.00  # 10% of 20
    assert result.tax == 1.44  # (20 - 2) * 0.08
    assert result.total == 19.44  # 18 + 1.44
    assert result.discount_code_applied == "SAVE10"


@pytest.mark.asyncio
async def test_flat_discount(calculator):
    """Test calculation with flat discount."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=2)
        ],
        discount_code="FLAT5",  # $5 off
        tax_rate=0.08
    )

    result = await calculator.process(input_data)

    assert result.subtotal == 20.00
    assert result.discount == 5.00  # Flat $5
    assert result.tax == 1.20  # (20 - 5) * 0.08
    assert result.total == 16.20  # 15 + 1.20


@pytest.mark.asyncio
async def test_invalid_discount_code(calculator):
    """Test with invalid discount code."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=1)
        ],
        discount_code="INVALID",
        tax_rate=0.08
    )

    result = await calculator.process(input_data)

    # Invalid code should not apply discount
    assert result.discount == 0.0


@pytest.mark.asyncio
async def test_caching(calculator):
    """Test result caching."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=1)
        ],
        tax_rate=0.08
    )

    # First call: should compute
    result_1 = await calculator.process(input_data)
    assert not result_1.cache_hit

    # Second call with same input: should use cache
    result_2 = await calculator.process(input_data)
    assert result_2.cache_hit
    assert result_2.total == result_1.total


@pytest.mark.asyncio
async def test_validation_error_empty_cart(calculator):
    """Test validation error with empty cart."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ModelPriceCalculatorInput(
            items=[],  # Empty cart
            tax_rate=0.08
        )


@pytest.mark.asyncio
async def test_validation_error_negative_price(calculator):
    """Test validation error with negative price."""
    with pytest.raises(Exception):  # Pydantic ValidationError
        ModelPriceCalculatorInput(
            items=[
                CartItem(name="Widget", price=-10.00, quantity=1)  # Negative price
            ],
            tax_rate=0.08
        )


@pytest.mark.asyncio
async def test_metrics(calculator):
    """Test performance metrics tracking."""
    input_data = ModelPriceCalculatorInput(
        items=[
            CartItem(name="Widget", price=10.00, quantity=1)
        ],
        tax_rate=0.08
    )

    # Process twice
    await calculator.process(input_data)
    await calculator.process(input_data)

    metrics = calculator.get_metrics()

    assert metrics["total_requests"] == 2
    assert metrics["computations"] == 1  # First request computed
    assert metrics["cache_hits"] == 1    # Second request cached
    assert metrics["cache_hit_rate"] == 0.5  # 50% hit rate
```

## Step 5: Run Tests

```
# Run all tests
poetry run pytest tests/nodes/test_node_price_calculator.py -v

# Run specific test
poetry run pytest tests/nodes/test_node_price_calculator.py::test_basic_calculation -v

# Run with coverage
poetry run pytest tests/nodes/test_node_price_calculator.py --cov=src/your_project/nodes --cov-report=term-missing
```

**Expected output**:
```
tests/nodes/test_node_price_calculator.py::test_basic_calculation PASSED
tests/nodes/test_node_price_calculator.py::test_percentage_discount PASSED
tests/nodes/test_node_price_calculator.py::test_flat_discount PASSED
tests/nodes/test_node_price_calculator.py::test_invalid_discount_code PASSED
tests/nodes/test_node_price_calculator.py::test_caching PASSED
tests/nodes/test_node_price_calculator.py::test_validation_error_empty_cart PASSED
tests/nodes/test_node_price_calculator.py::test_validation_error_negative_price PASSED
tests/nodes/test_node_price_calculator.py::test_metrics PASSED

================================ 8 passed in 0.12s ================================
```

## Step 6: Use Your Node

Now use it in your application!

```
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from your_project.nodes.node_price_calculator_compute import NodePriceCalculatorCompute
from your_project.nodes.model_price_calculator_input import (
    ModelPriceCalculatorInput,
    CartItem
)

# Initialize container and node
container = ModelONEXContainer()
calculator = NodePriceCalculatorCompute(container)

# Create input
cart_input = ModelPriceCalculatorInput(
    items=[
        CartItem(name="Python Course", price=99.00, quantity=1),
        CartItem(name="eBook Bundle", price=49.00, quantity=2)
    ],
    discount_code="SAVE20",  # 20% off
    tax_rate=0.08
)

# Calculate price
result = await calculator.process(cart_input)

# Use result
print(f"Subtotal: ${result.subtotal:.2f}")
print(f"Discount: -${result.discount:.2f}")
print(f"Tax: ${result.tax:.2f}")
print(f"Total: ${result.total:.2f}")
print(f"Processing time: {result.processing_time_ms:.2f}ms")
```

## What You've Built

✅ **Structured Input/Output**: Type-safe with Pydantic validation
✅ **Core Logic**: Clear separation of calculation concerns
✅ **Caching**: Performance optimization for repeated calculations
✅ **Error Handling**: Comprehensive validation and error reporting
✅ **Testing**: Full test coverage with pytest
✅ **Metrics**: Performance tracking and monitoring
✅ **Production-Ready**: Following ONEX best practices

## Common Enhancements

### 1. Add Logging

```
from omnibase_core.logging.logging_structured import emit_log_event_sync

async def process(self, input_data):
    emit_log_event_sync(
        level="INFO",
        message="Processing price calculation",
        context={
            "items_count": len(input_data.items),
            "discount_code": input_data.discount_code
        }
    )
    # ... rest of processing
```

### 2. Add Redis Caching

```
import redis.asyncio as redis

def __init__(self, container):
    super().__init__(container)
    self.redis = redis.from_url("redis://localhost")

async def process(self, input_data):
    cache_key = self._generate_cache_key(input_data)

    # Try Redis cache
    cached = await self.redis.get(cache_key)
    if cached:
        return ModelPriceCalculatorOutput.model_validate_json(cached)

    # Calculate and cache
    result = self._calculate_price(input_data)
    await self.redis.setex(
        cache_key,
        300,  # 5 minutes TTL
        result.model_dump_json()
    )
    return result
```

### 3. Add Parallel Processing

```
async def process_batch(
    self,
    inputs: list[ModelPriceCalculatorInput]
) -> list[ModelPriceCalculatorOutput]:
    """Process multiple calculations in parallel."""
    tasks = [self.process(input_data) for input_data in inputs]
    results = await asyncio.gather(*tasks)
    return results
```

## Next Steps

You've successfully built a COMPUTE node! Now:

1. **Build more complex nodes**: Try EFFECT, REDUCER, or ORCHESTRATOR
2. **Integrate with real systems**: Connect to databases, APIs
3. **Add monitoring**: Prometheus metrics, distributed tracing
4. **Deploy to production**: Containerize and deploy

## Related Tutorials

- [EFFECT Node Tutorial](04_EFFECT_NODE_TUTORIAL.md) - Build a database interaction node
- [REDUCER Node Tutorial](05_REDUCER_NODE_TUTORIAL.md) - Build a data aggregation node
- [ORCHESTRATOR Node Tutorial](06_ORCHESTRATOR_NODE_TUTORIAL.md) - Coordinate workflows
- [Patterns Catalog](07_PATTERNS_CATALOG.md) - Reusable patterns
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Advanced testing strategies

## Troubleshooting

### Import Errors

```
# If you see import errors
poetry install
poetry run python -c "from omnibase_core.nodes import NodeCompute"
```

### Type Checking Failures

```
# Run mypy to check types
poetry run mypy src/your_project/nodes/node_price_calculator_compute.py
```

### Test Failures

```
# Run tests with verbose output
poetry run pytest tests/nodes/test_node_price_calculator.py -vvs
```

## Summary

You've learned:

- COMPUTE node structure and patterns
- **ModelServiceCompute** - Production-ready wrapper (RECOMMENDED)
- **NodeCompute** - Direct computation control (DIRECT)
- When to use which approach
- Type-safe input/output models with Pydantic v2
- Caching implementation
- Error handling and validation
- Comprehensive testing
- Performance tracking

**Key Takeaway**: Start with `ModelServiceCompute` for 95% of use cases. Only use `NodeCompute` directly when you need access to the computation registry or parallel processing features.

**Congratulations!** You've built a production-ready COMPUTE node!

**Next**: [EFFECT Node Tutorial](04_EFFECT_NODE_TUTORIAL.md) →
