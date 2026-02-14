> **Navigation**: [Home](../../INDEX.md) > [Guides](../README.md) > [Node Building](./README.md) > Common Pitfalls

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../../CLAUDE.md).

# Common Pitfalls - What to Avoid When Building Nodes

**Status**: ✅ Complete

## Overview

This guide identifies common mistakes and pitfalls when building ONEX nodes, along with best practices to avoid them. Learning from these common errors will help you build more robust, maintainable, and performant nodes.

## Table of Contents

1. [Architecture Pitfalls](#architecture-pitfalls) -- includes handler delegation, container types
2. [Error Handling Pitfalls](#error-handling-pitfalls)
3. [Performance Pitfalls](#performance-pitfalls)
4. [Threading Pitfalls](#threading-pitfalls) -- per-request instances, not locks
5. [Testing Pitfalls](#testing-pitfalls)
6. [Configuration Pitfalls](#configuration-pitfalls)
7. [Memory Management Pitfalls](#memory-management-pitfalls)
8. [Best Practices Summary](#best-practices-summary)

## Architecture Pitfalls

### 1. Putting Business Logic in Nodes Instead of Handlers

**This is the most common and most critical mistake.**

Nodes are thin coordination shells. All business logic belongs in **handlers**, which are resolved from YAML contracts. If you find yourself writing domain logic inside a node class, you are violating the fundamental architecture.

**Bad Practice**: Business logic directly in the node

```python
class NodePriceCalculatorCompute(NodeCompute):
    """BAD: Business logic lives in the node."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: This computation logic belongs in a handler
        subtotal = sum(item["price"] * item["qty"] for item in input_data["items"])
        tax = subtotal * 0.08
        discount = self._calculate_discount(subtotal, input_data.get("code"))
        return {"total": subtotal - discount + tax}

    def _calculate_discount(self, subtotal: float, code: str | None) -> float:
        # BAD: Domain logic in the node
        if code == "SAVE20":
            return subtotal * 0.20
        return 0.0
```

**Good Practice**: Node delegates to handler; handler owns the logic

```python
class NodePriceCalculatorCompute(NodeCompute):
    """GOOD: Thin shell -- delegates to handler."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)

    # The node resolves a handler from its YAML contract.
    # The handler contains all price calculation logic.


class HandlerPriceCalculator:
    """GOOD: Handler owns the business logic."""

    async def execute(self, envelope: ModelOnexEnvelope, input_data: dict[str, Any]) -> ModelHandlerOutput:
        subtotal = sum(item["price"] * item["qty"] for item in input_data["items"])
        tax = subtotal * 0.08
        discount = self._calculate_discount(subtotal, input_data.get("code"))
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.metadata.envelope_id,
            correlation_id=envelope.metadata.correlation_id,
            result={"total": subtotal - discount + tax},
        )

    def _calculate_discount(self, subtotal: float, code: str | None) -> float:
        if code == "SAVE20":
            return subtotal * 0.20
        return 0.0
```

**Why this matters**:
- Handlers are independently testable without node lifecycle overhead
- YAML contracts can swap handlers without changing the node
- Handler output constraints are enforced by `ModelHandlerOutput` validators
- Nodes remain reusable across different domains

### 2. Mixing Node Responsibilities

**❌ Bad Practice**: Combining multiple node types in one class

```
class BadNode(NodeCompute):
    """BAD: Mixing COMPUTE and EFFECT responsibilities."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # COMPUTE: Calculate result
        result = input_data["value"] * 2

        # EFFECT: Save to database (side effect!)
        await self.database.save(result)

        # EFFECT: Send email (side effect!)
        await self.email_service.send("result@example.com", result)

        return {"result": result}
```

**✅ Good Practice**: Separate concerns into different node types

```
class GoodComputeNode(NodeCompute):
    """GOOD: Pure computation only."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        result = input_data["value"] * 2
        return {"result": result}

class GoodEffectNode(NodeEffect):
    """GOOD: Handle side effects separately."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        result = input_data["result"]

        # Save to database
        await self.database.save(result)

        # Send email
        await self.email_service.send("result@example.com", result)

        return {"status": "saved"}
```

### 3. Ignoring Node Type Contracts

**❌ Bad Practice**: Not following node type contracts

```
class BadComputeNode(NodeCompute):
    """BAD: COMPUTE node with side effects."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # This violates COMPUTE contract (no side effects)
        self.global_state["last_result"] = input_data["value"]
        return {"result": input_data["value"] * 2}
```

**✅ Good Practice**: Follow node type contracts strictly

```
class GoodComputeNode(NodeCompute):
    """GOOD: Pure computation following COMPUTE contract."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Pure computation only
        result = input_data["value"] * 2
        return {"result": result}
```

### 4. Tight Coupling Between Nodes

**❌ Bad Practice**: Direct dependencies between nodes

```
class BadNode(NodeCompute):
    """BAD: Tight coupling to specific node implementation."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Direct dependency on specific implementation
        self.database_node = DatabaseEffectNode(container)

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Direct call to another node
        result = await self.database_node.process(input_data)
        return result
```

**✅ Good Practice**: Use dependency injection and protocols

```
class GoodNode(NodeCompute):
    """GOOD: Loose coupling through dependency injection."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        # Resolve by protocol, not concrete implementation
        self.database_service = container.get_service("DatabaseService")

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # Use service interface
        result = await self.database_service.query(input_data["query"])
        return {"result": result}
```

### 5. Using ModelContainer Instead of ModelONEXContainer

**Bad Practice**: Using the wrong container type for dependency injection

```python
from omnibase_core.models.core.model_container import ModelContainer

class BadNode(NodeCompute):
    """BAD: Wrong container type."""

    def __init__(self, container: ModelContainer):  # WRONG
        super().__init__(container)
```

**Good Practice**: Always use `ModelONEXContainer` for node constructors

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class GoodNode(NodeCompute):
    """GOOD: Correct container type."""

    def __init__(self, container: ModelONEXContainer) -> None:  # CORRECT
        super().__init__(container)
        # ModelONEXContainer provides protocol-based service resolution
        self.logger = container.get_service(ProtocolLogger)
```

**Why this matters**:
- `ModelContainer[T]` is a generic value wrapper -- it is never used in node `__init__`
- `ModelONEXContainer` is the dependency injection container with `get_service()` for protocol-based resolution
- Mixing them up causes type errors and breaks DI resolution

## Error Handling Pitfalls

### 1. Swallowing Exceptions

**❌ Bad Practice**: Catching and ignoring exceptions

```
class BadNode(NodeCompute):
    """BAD: Swallowing exceptions silently."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.risky_operation(input_data)
            return {"result": result}
        except Exception as e:
            # BAD: Swallowing exception
            return {"result": None, "error": "Something went wrong"}
```

**✅ Good Practice**: Proper error handling with context

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class GoodNode(NodeCompute):
    """GOOD: Proper error handling."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.risky_operation(input_data)
            return {"result": result}
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid input: {str(e)}",
                context={"input_data": input_data}
            ) from e
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                message=f"Processing failed: {str(e)}",
                context={"input_data": input_data}
            ) from e
```

### 2. Generic Error Messages

**❌ Bad Practice**: Non-descriptive error messages

```
class BadNode(NodeCompute):
    """BAD: Generic error messages."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if not input_data.get("value"):
            raise ValueError("Error")  # BAD: Too generic

        if input_data["value"] < 0:
            raise ValueError("Error")  # BAD: Same generic message
```

**✅ Good Practice**: Specific, actionable error messages

```
class GoodNode(NodeCompute):
    """GOOD: Specific error messages."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if not input_data.get("value"):
            raise ValueError("Value is required but not provided")

        if input_data["value"] < 0:
            raise ValueError(f"Value must be non-negative, got: {input_data['value']}")
```

### 3. Not Handling Async Exceptions

**❌ Bad Practice**: Not handling async-specific exceptions

```
class BadNode(NodeCompute):
    """BAD: Not handling async exceptions."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: No handling of asyncio.TimeoutError, CancelledError, etc.
        result = await self.async_operation(input_data)
        return {"result": result}
```

**✅ Good Practice**: Handle async exceptions appropriately

```
import asyncio
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

class GoodNode(NodeCompute):
    """GOOD: Proper async exception handling."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self.async_operation(input_data)
            return {"result": result}
        except asyncio.TimeoutError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.TIMEOUT_ERROR,
                message="Operation timed out",
                context={"input_data": input_data}
            ) from e
        except asyncio.CancelledError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                message="Operation was cancelled",
                context={"input_data": input_data}
            ) from e
```

## Performance Pitfalls

### 1. Blocking Operations in Async Code

**❌ Bad Practice**: Blocking operations in async methods

```
import time
import requests

class BadNode(NodeCompute):
    """BAD: Blocking operations in async code."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: Blocking HTTP request
        response = requests.get("https://api.example.com/data")

        # BAD: Blocking sleep
        time.sleep(5)

        return {"result": response.json()}
```

**✅ Good Practice**: Use async alternatives

```
import aiohttp
import asyncio

class GoodNode(NodeCompute):
    """GOOD: Async operations."""

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # GOOD: Async HTTP request
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/data") as response:
                data = await response.json()

        # GOOD: Async sleep
        await asyncio.sleep(5)

        return {"result": data}
```

### 2. Memory Leaks in Long-Running Nodes

**❌ Bad Practice**: Accumulating data without cleanup

```
class BadNode(NodeCompute):
    """BAD: Memory leak from accumulating data."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.processed_data = []  # BAD: Never cleared

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        result = input_data["value"] * 2
        self.processed_data.append(result)  # BAD: Keeps growing
        return {"result": result}
```

**✅ Good Practice**: Implement proper cleanup

```
class GoodNode(NodeCompute):
    """GOOD: Proper memory management."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.processed_data = []
        self.max_data_size = 1000

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        result = input_data["value"] * 2

        # GOOD: Limit data size
        self.processed_data.append(result)
        if len(self.processed_data) > self.max_data_size:
            self.processed_data = self.processed_data[-self.max_data_size:]

        return {"result": result}

    def cleanup(self):
        """GOOD: Explicit cleanup method."""
        self.processed_data.clear()
```

### 3. Inefficient Caching

**❌ Bad Practice**: Inefficient cache implementation

```
class BadNode(NodeCompute):
    """BAD: Inefficient caching."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.cache = {}  # BAD: No size limit, no TTL

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        cache_key = str(input_data)  # BAD: Inefficient key generation

        if cache_key in self.cache:
            return self.cache[cache_key]  # BAD: No TTL check

        result = await self.expensive_operation(input_data)
        self.cache[cache_key] = result  # BAD: No size limit
        return result
```

**✅ Good Practice**: Efficient caching with limits

```
import hashlib
import json
import time
from collections import OrderedDict

class GoodNode(NodeCompute):
    """GOOD: Efficient caching."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.cache = OrderedDict()
        self.max_cache_size = 1000
        self.cache_ttl = 300  # 5 minutes

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        cache_key = self._generate_cache_key(input_data)

        # GOOD: Check cache with TTL
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                # Move to end (LRU)
                self.cache.move_to_end(cache_key)
                return cache_entry["value"]
            else:
                # Remove expired entry
                del self.cache[cache_key]

        result = await self.expensive_operation(input_data)

        # GOOD: Add with TTL and size limit
        self.cache[cache_key] = {
            "value": result,
            "timestamp": time.time()
        }

        # GOOD: Enforce size limit
        if len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)

        return result

    def _generate_cache_key(self, input_data: dict[str, Any]) -> str:
        """GOOD: Efficient cache key generation."""
        sorted_data = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(sorted_data.encode()).hexdigest()
```

## Threading Pitfalls

### 1. Sharing Node Instances Across Threads

**Nodes are single-request scoped.** Do not share node instances across threads. Instead, create a separate node instance per thread or per request.

**Bad Practice**: Sharing a node instance across threads

```python
class BadNode(NodeCompute):
    """BAD: Sharing mutable state across threads."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.shared_data: dict[str, Any] = {}  # BAD: Shared mutable state

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: Race condition when called from multiple threads
        self.shared_data[input_data["key"]] = input_data["value"]
        return {"result": "processed"}

# BAD: Sharing the same instance
shared_node = BadNode(container)
threading.Thread(target=lambda: asyncio.run(shared_node.process(data1))).start()
threading.Thread(target=lambda: asyncio.run(shared_node.process(data2))).start()
```

**Good Practice**: Create per-request or per-thread instances

```python
class GoodNode(NodeCompute):
    """GOOD: Designed for single-request scope."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.request_data: dict[str, Any] = {}  # Safe: one instance per request

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        self.request_data[input_data["key"]] = input_data["value"]
        return {"result": "processed"}

# GOOD: Each thread/request gets its own instance
def handle_request(container: ModelONEXContainer, data: dict[str, Any]):
    node = GoodNode(container)  # Fresh instance per request
    return asyncio.run(node.process(data))

threading.Thread(target=handle_request, args=(container, data1)).start()
threading.Thread(target=handle_request, args=(container, data2)).start()
```

### 2. Sharing Circuit Breaker State Across Threads

Circuit breaker state (failure counts, timestamps) should not be shared across threads via a shared node instance. Instead, use a shared circuit breaker service resolved through the container, or use per-request node instances.

**Bad Practice**: Circuit breaker with shared mutable state on a node instance

```python
class BadNode(NodeEffect):
    """BAD: Circuit breaker state on a shared node instance."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        self.failure_count = 0  # BAD: Race condition if node is shared
        self.last_failure_time = 0.0

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if self.failure_count >= 5:
            return {"error": "Circuit breaker open"}
        try:
            result = await self.risky_operation(input_data)
            self.failure_count = 0  # BAD: Race condition
            return result
        except Exception:
            self.failure_count += 1  # BAD: Race condition
            raise
```

**Good Practice**: Resolve a shared circuit breaker service via the container

```python
class GoodNode(NodeEffect):
    """GOOD: Circuit breaker resolved as a shared service via DI."""

    def __init__(self, container: ModelONEXContainer) -> None:
        super().__init__(container)
        # The circuit breaker service is designed for concurrent access
        self.circuit_breaker = container.get_service(ProtocolCircuitBreaker)

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        if self.circuit_breaker.is_open():
            return {"error": "Circuit breaker open"}
        try:
            result = await self.risky_operation(input_data)
            self.circuit_breaker.record_success()
            return result
        except Exception:
            self.circuit_breaker.record_failure()
            raise
```

**Key principle**: Nodes are single-request scoped. If you need shared state (like circuit breaker counters), put it in a service resolved through `ModelONEXContainer`, not on the node instance itself.

## Testing Pitfalls

### 1. Not Testing Error Conditions

**❌ Bad Practice**: Only testing happy path

```
def test_node_success():
    """BAD: Only testing success case."""
    node = MyNode(container)
    result = await node.process({"value": 5})
    assert result["result"] == 10
```

**✅ Good Practice**: Test error conditions

```
def test_node_success():
    """GOOD: Test success case."""
    node = MyNode(container)
    result = await node.process({"value": 5})
    assert result["result"] == 10

def test_node_validation_error():
    """GOOD: Test validation error."""
    node = MyNode(container)
    with pytest.raises(ModelOnexError) as exc_info:
        await node.process({"value": -1})

    error = exc_info.value
    assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR

def test_node_missing_input():
    """GOOD: Test missing input."""
    node = MyNode(container)
    with pytest.raises(ModelOnexError) as exc_info:
        await node.process({})

    error = exc_info.value
    assert "required" in error.message.lower()
```

### 2. Not Mocking External Dependencies

**❌ Bad Practice**: Testing with real external services

```
def test_node_with_real_api():
    """BAD: Using real API in tests."""
    node = MyNode(container)
    result = await node.process({"url": "https://api.example.com/data"})
    # BAD: This makes real API calls
    assert result["status"] == 200
```

**✅ Good Practice**: Mock external dependencies

```
from unittest.mock import AsyncMock, patch

def test_node_with_mocked_api():
    """GOOD: Mocking external API."""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status = 200

        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

        node = MyNode(container)
        result = await node.process({"url": "https://api.example.com/data"})

        assert result["status"] == 200
        assert result["data"] == {"data": "test"}
```

### 3. Not Testing Async Behavior

**❌ Bad Practice**: Not testing async-specific behavior

```
def test_node():
    """BAD: Not testing async behavior."""
    node = MyNode(container)
    result = node.process({"value": 5})  # BAD: Not awaiting
    assert result["result"] == 10
```

**✅ Good Practice**: Proper async testing

```
@pytest.mark.asyncio
async def test_node_async():
    """GOOD: Proper async testing."""
    node = MyNode(container)
    result = await node.process({"value": 5})  # GOOD: Awaiting
    assert result["result"] == 10

@pytest.mark.asyncio
async def test_node_concurrent():
    """GOOD: Test concurrent execution."""
    node = MyNode(container)

    # Test concurrent execution
    tasks = [node.process({"value": i}) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert all(r["result"] == i * 2 for i, r in enumerate(results))
```

## Configuration Pitfalls

### 1. Hardcoded Configuration

**❌ Bad Practice**: Hardcoded configuration values

```
class BadNode(NodeCompute):
    """BAD: Hardcoded configuration."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.timeout = 30  # BAD: Hardcoded
        self.retry_count = 3  # BAD: Hardcoded
        self.api_url = "https://api.example.com"  # BAD: Hardcoded
```

**✅ Good Practice**: Configurable parameters

```
class GoodNode(NodeCompute):
    """GOOD: Configurable parameters."""

    def __init__(self, container: ModelONEXContainer, config: dict[str, Any] = None):
        super().__init__(container)
        config = config or {}

        # GOOD: Configurable with defaults
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)
        self.api_url = config.get("api_url", "https://api.example.com")
```

### 2. Not Validating Configuration

**❌ Bad Practice**: Not validating configuration

```
class BadNode(NodeCompute):
    """BAD: No configuration validation."""

    def __init__(self, container: ModelONEXContainer, config: dict[str, Any]):
        super().__init__(container)
        # BAD: No validation
        self.timeout = config["timeout"]
        self.retry_count = config["retry_count"]
```

**✅ Good Practice**: Validate configuration

```
class GoodNode(NodeCompute):
    """GOOD: Configuration validation."""

    def __init__(self, container: ModelONEXContainer, config: dict[str, Any]):
        super().__init__(container)

        # GOOD: Validate configuration
        self.timeout = self._validate_timeout(config.get("timeout", 30))
        self.retry_count = self._validate_retry_count(config.get("retry_count", 3))

    def _validate_timeout(self, timeout: Any) -> int:
        """Validate timeout configuration."""
        if not isinstance(timeout, (int, float)):
            raise ValueError("Timeout must be a number")
        if timeout <= 0:
            raise ValueError("Timeout must be positive")
        return int(timeout)

    def _validate_retry_count(self, retry_count: Any) -> int:
        """Validate retry count configuration."""
        if not isinstance(retry_count, int):
            raise ValueError("Retry count must be an integer")
        if retry_count < 0:
            raise ValueError("Retry count must be non-negative")
        return retry_count
```

## Memory Management Pitfalls

### 1. Not Cleaning Up Resources

**❌ Bad Practice**: Not cleaning up resources

```
class BadNode(NodeEffect):
    """BAD: Not cleaning up resources."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.session = aiohttp.ClientSession()  # BAD: Never closed

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: Session never closed
        async with self.session.get("https://api.example.com") as response:
            return await response.json()
```

**✅ Good Practice**: Proper resource cleanup

```
class GoodNode(NodeEffect):
    """GOOD: Proper resource cleanup."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.session = None

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # GOOD: Create session per operation or use context manager
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com") as response:
                return await response.json()

    async def __aenter__(self):
        """GOOD: Context manager support."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """GOOD: Cleanup on exit."""
        if self.session:
            await self.session.close()
```

### 2. Accumulating Data Without Bounds

**❌ Bad Practice**: Unlimited data accumulation

```
class BadNode(NodeReducer):
    """BAD: Unlimited data accumulation."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.state_history = []  # BAD: Never cleared

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # BAD: Keeps growing indefinitely
        self.state_history.append({
            "timestamp": time.time(),
            "data": input_data
        })
        return {"processed": True}
```

**✅ Good Practice**: Bounded data accumulation

```
class GoodNode(NodeReducer):
    """GOOD: Bounded data accumulation."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.state_history = []
        self.max_history_size = 1000

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        # GOOD: Bounded accumulation
        self.state_history.append({
            "timestamp": time.time(),
            "data": input_data
        })

        # GOOD: Enforce size limit
        if len(self.state_history) > self.max_history_size:
            self.state_history = self.state_history[-self.max_history_size:]

        return {"processed": True}
```

## Best Practices Summary

### 1. Architecture Best Practices

- **Handlers Own Logic**: Business logic belongs in handlers, not nodes. Nodes are thin shells.
- **Separate Concerns**: Use appropriate node types for their intended purpose
- **Follow Contracts**: Respect node type output constraints (COMPUTE = result, EFFECT = events, etc.)
- **Use ModelONEXContainer**: Always use `ModelONEXContainer` for DI, never `ModelContainer`
- **Loose Coupling**: Use protocol-based dependency injection instead of direct dependencies
- **Single Responsibility**: Each node should have one clear responsibility

### 2. Error Handling Best Practices

- **Don't Swallow Exceptions**: Always handle exceptions appropriately
- **Specific Error Messages**: Provide clear, actionable error messages
- **Handle Async Exceptions**: Be aware of asyncio-specific exceptions
- **Use ONEX Error Types**: Use `ModelOnexError` with proper error codes

### 3. Performance Best Practices

- **Use Async Operations**: Avoid blocking operations in async code
- **Implement Caching**: Use efficient caching with size limits and TTL
- **Memory Management**: Implement proper cleanup and bounded accumulation
- **Resource Cleanup**: Always clean up resources (sessions, connections, etc.)

### 4. Threading Best Practices

- **Per-Request Instances**: Create a new node instance per request or per thread -- nodes are single-request scoped
- **Never Share Node Instances**: Do not pass node instances across threads
- **Shared Services via DI**: If you need shared state (circuit breakers, connection pools), resolve it as a service through `ModelONEXContainer`, not as node instance state
- **Avoid Locks on Nodes**: If you need a lock, you are probably sharing a node instance incorrectly

### 5. Testing Best Practices

- **Test Error Conditions**: Don't just test the happy path
- **Mock External Dependencies**: Use mocks for external services
- **Test Async Behavior**: Properly test async functionality
- **Test Concurrency**: Test concurrent execution scenarios

### 6. Configuration Best Practices

- **Avoid Hardcoding**: Make configuration configurable
- **Validate Configuration**: Always validate configuration parameters
- **Use Defaults**: Provide sensible defaults for configuration
- **Environment Variables**: Support environment variable configuration

### 7. Memory Management Best Practices

- **Resource Cleanup**: Always clean up resources
- **Bounded Accumulation**: Limit data accumulation to prevent memory leaks
- **Efficient Data Structures**: Use appropriate data structures for your use case
- **Monitor Memory Usage**: Keep track of memory usage in long-running nodes

## Related Documentation

- [Node Building Guide](README.md) - Complete implementation tutorials
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Comprehensive testing strategies
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [Threading Guide](../THREADING.md) - Thread safety considerations
- [API Reference](../../reference/api/nodes.md) - Complete API documentation
