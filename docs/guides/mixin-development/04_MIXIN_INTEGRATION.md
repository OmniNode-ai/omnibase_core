# Mixin Integration Guide

**Status**: Active
**Difficulty**: Beginner to Intermediate
**Time**: 15-30 minutes
**Prerequisites**: [Creating Mixins](01_CREATING_MIXINS.md), [Pydantic Models](03_PYDANTIC_MODELS.md)

## Overview

This guide teaches you how to integrate mixins into ONEX nodes. You'll learn how to reference mixins in node contracts, access mixin configuration at runtime, and use mixin capabilities in your node implementations.

## Integration Flow

```
1. Create Mixin YAML Contract
2. Create Pydantic Backing Model
3. Reference Mixin in Node Contract     ← This guide
4. Access Mixin Config in Node Code     ← This guide
5. Use Mixin Capabilities              ← This guide
```

## Step 1: Reference Mixin in Node Contract

### Basic Subcontract Reference

**Node Contract Location**: `src/your_project/nodes/your_node/v1_0_0/contract.yaml`

```
# node_api_client_effect/v1_0_0/contract.yaml
node_name: "api_client_effect"
node_type: "EFFECT"
version: "1.0.0"
description: "EFFECT node for external API interactions"

# === SUBCONTRACT REFERENCES ===
subcontracts:
  - path: "../../../mixins/mixin_error_handling.yaml"
    integration_field: "error_handling_configuration"
```

### Multiple Mixin References

```
# node_data_processor_compute/v1_0_0/contract.yaml
node_name: "data_processor_compute"
node_type: "COMPUTE"
version: "1.0.0"

subcontracts:
  # Core mixins (all nodes)
  - path: "../../../mixins/mixin_health_check.yaml"
    integration_field: "health_check_configuration"

  - path: "../../../mixins/mixin_performance_monitoring.yaml"
    integration_field: "performance_monitoring_configuration"

  - path: "../../../mixins/mixin_event_handling.yaml"
    integration_field: "event_handling_configuration"

  # Custom mixin for this node
  - path: "../../../mixins/mixin_error_handling.yaml"
    integration_field: "error_handling_configuration"
```

### Path Resolution

**Relative Paths**: Paths are relative to the node contract file location.

```
Project Structure:
src/your_project/
├── mixins/
│   └── mixin_error_handling.yaml
└── nodes/
    └── api_client_effect/
        └── v1_0_0/
            └── contract.yaml  ← You are here

Path from contract to mixin:
../../../mixins/mixin_error_handling.yaml
    ^    ^    ^
    │    │    │
    │    │    └─ Up to your_project/
    │    └────── Up to nodes/
    └─────────── Up to api_client_effect/
```

### Integration Field Naming

**Pattern**: `{capability}_configuration`

**Examples**:
```
# ✓ Good: Clear, descriptive
integration_field: "error_handling_configuration"
integration_field: "circuit_breaker_configuration"
integration_field: "caching_configuration"

# ✗ Bad: Too generic or unclear
integration_field: "config"
integration_field: "settings"
integration_field: "error_config"  # Missing '_configuration' suffix
```

## Step 2: Validate Contract with Mixins

### Use Contract Validator

```
# Validate node contract (including mixins)
poetry run onex run contract_validator \
    --contract src/your_project/nodes/api_client_effect/v1_0_0/contract.yaml

# Expected output:
# ✓ YAML syntax valid
# ✓ Node contract valid
# ✓ Subcontract references resolved
# ✓ Mixin 'mixin_error_handling' loaded
# ✓ Node type constraints validated (EFFECT can use mixin_error_handling)
# ✓ Integration fields valid
# ✓ Contract complete and valid
```

### Common Validation Errors

**Error 1: Path Not Found**
```
Error: Subcontract file not found: ../../../mixins/mixin_error_handling.yaml
```

**Solution**: Verify relative path is correct from contract location.

**Error 2: Node Type Constraint Violation**
```
Error: Mixin 'mixin_state_management' not applicable to node type 'COMPUTE'
       Applicable types: ['REDUCER', 'ORCHESTRATOR']
```

**Solution**: Only use mixins allowed for your node type.

**Error 3: Duplicate Integration Field**
```
Error: Integration field 'error_handling_configuration' used multiple times
```

**Solution**: Each mixin must have unique integration field name.

## Step 3: Access Mixin Configuration in Node

### Import Mixin Model

```
# src/your_project/nodes/node_api_client_effect.py

from omnibase_core.nodes import NodeEffect
from omnibase_core.model.contracts import ModelContractEffect
from omnibase_core.model.subcontracts import ModelErrorHandlingSubcontract
```

### Access Configuration in Node

```
class NodeApiClientEffect(NodeEffect):
    """EFFECT node with error handling mixin."""

    async def execute_effect(self, contract: ModelContractEffect):
        """Execute effect with error handling."""

        # Access mixin configuration
        error_config: ModelErrorHandlingSubcontract = (
            contract.error_handling_configuration
        )

        # Use mixin configuration
        if error_config.enable_circuit_breaker:
            self.logger.info(
                f"Circuit breaker enabled: threshold={error_config.circuit_failure_threshold}"
            )

        try:
            # Your effect logic
            result = await self._call_external_api(contract)
            return result

        except Exception as e:
            # Use mixin capabilities
            return await self._handle_error_with_mixin(e, error_config)
```

### Pattern: Mixin Configuration Check

```
async def execute_effect(self, contract: ModelContractEffect):
    """Execute with optional mixin configuration."""

    # Check if mixin configuration exists
    if hasattr(contract, "error_handling_configuration"):
        error_config = contract.error_handling_configuration
        # Use mixin capabilities
    else:
        # Fallback to default behavior
        error_config = None

    # Your logic here
```

## Step 4: Implement Mixin Capabilities

### Pattern 1: Error Handling Mixin

```
from typing import Any
from omnibase_core.models.errors.model_onex_error import ModelOnexError

class NodeApiClientEffect(NodeEffect):
    """EFFECT node with error handling."""

    async def execute_effect(self, contract: ModelContractEffect):
        """Execute with error handling mixin."""
        error_config = contract.error_handling_configuration

        try:
            return await self._execute_with_retry(contract, error_config)

        except Exception as e:
            return await self._handle_error(e, error_config)

    async def _execute_with_retry(
        self,
        contract: ModelContractEffect,
        error_config: ModelErrorHandlingSubcontract
    ) -> Any:
        """Execute operation with retry logic from mixin."""
        attempt = 1

        while attempt <= error_config.error_retry_attempts:
            try:
                # Attempt operation
                result = await self._call_external_api(contract)
                return result

            except Exception as e:
                error_type = type(e).__name__

                # Check if error is retriable
                if not error_config.is_error_retriable(error_type):
                    raise

                # Check if max attempts reached
                if attempt >= error_config.error_retry_attempts:
                    raise

                # Calculate retry delay
                delay_ms = error_config.calculate_retry_delay(attempt)
                await asyncio.sleep(delay_ms / 1000.0)

                attempt += 1

    async def _handle_error(
        self,
        error: Exception,
        error_config: ModelErrorHandlingSubcontract
    ) -> Any:
        """Handle error using mixin configuration."""
        error_type = type(error).__name__

        # Categorize error
        if error_config.is_error_fatal(error_type):
            # Fatal error - don't retry
            raise ModelOnexError(
                message=f"Fatal error occurred: {error_type}",
                error_code="FATAL_ERROR",
                original_error=error
            )

        # Record error metric (if enabled)
        if error_config.enable_error_metrics:
            await self._record_error_metric(error_type, error_config)

        # Re-raise with context
        raise ModelOnexError(
            message=f"Error after {error_config.error_retry_attempts} retries",
            error_code="MAX_RETRIES_EXCEEDED",
            original_error=error
        )
```

### Pattern 2: Circuit Breaker Mixin

```
from datetime import datetime, timedelta
from omnibase_core.model.subcontracts import (
    ModelCircuitBreakerStatus,
    EnumCircuitBreakerState
)

class NodeApiClientEffect(NodeEffect):
    """EFFECT node with circuit breaker."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._circuit_states: dict[str, ModelCircuitBreakerStatus] = {}

    async def execute_effect(self, contract: ModelContractEffect):
        """Execute with circuit breaker protection."""
        error_config = contract.error_handling_configuration

        if not error_config.enable_circuit_breaker:
            # Circuit breaker disabled
            return await self._call_external_api(contract)

        # Check circuit breaker
        operation_key = self._get_operation_key(contract)
        circuit_status = self._get_circuit_status(operation_key)

        if circuit_status.status == EnumCircuitBreakerState.OPEN:
            # Circuit open - fail fast
            raise ModelOnexError(
                message="Circuit breaker open - operation blocked",
                error_code="CIRCUIT_BREAKER_OPEN"
            )

        try:
            # Attempt operation
            result = await self._call_external_api(contract)

            # Record success
            self._record_success(operation_key, error_config)

            return result

        except Exception as e:
            # Record failure
            self._record_failure(operation_key, error_config)
            raise

    def _get_circuit_status(
        self,
        operation_key: str
    ) -> ModelCircuitBreakerStatus:
        """Get current circuit breaker status."""
        if operation_key not in self._circuit_states:
            # Initialize circuit
            self._circuit_states[operation_key] = ModelCircuitBreakerStatus(
                status=EnumCircuitBreakerState.CLOSED,
                failure_count=0,
                failure_rate=0.0
            )

        circuit = self._circuit_states[operation_key]

        # Check if half-open timeout expired
        if circuit.status == EnumCircuitBreakerState.OPEN:
            if circuit.next_retry_time and datetime.now() >= circuit.next_retry_time:
                # Transition to half-open
                circuit.status = EnumCircuitBreakerState.HALF_OPEN

        return circuit

    def _record_failure(
        self,
        operation_key: str,
        error_config: ModelErrorHandlingSubcontract
    ):
        """Record operation failure."""
        circuit = self._circuit_states[operation_key]
        circuit.failure_count += 1
        circuit.last_failure_time = datetime.now()

        # Check if should open circuit
        if error_config.should_open_circuit(circuit.failure_count):
            circuit.status = EnumCircuitBreakerState.OPEN
            circuit.next_retry_time = (
                datetime.now() +
                timedelta(milliseconds=error_config.circuit_timeout_ms)
            )

    def _record_success(
        self,
        operation_key: str,
        error_config: ModelErrorHandlingSubcontract
    ):
        """Record operation success."""
        circuit = self._circuit_states[operation_key]

        if circuit.status == EnumCircuitBreakerState.HALF_OPEN:
            # Success in half-open - close circuit
            circuit.status = EnumCircuitBreakerState.CLOSED
            circuit.failure_count = 0

        elif circuit.status == EnumCircuitBreakerState.CLOSED:
            # Reset failure count on success
            circuit.failure_count = max(0, circuit.failure_count - 1)
```

### Pattern 3: Health Check Mixin

```
from omnibase_core.model.subcontracts import ModelHealthCheckSubcontract

class NodeDataProcessorCompute(NodeCompute):
    """COMPUTE node with health check mixin."""

    async def execute_compute(self, contract: ModelContractCompute):
        """Execute with health checks."""
        health_config = contract.health_check_configuration

        # Pre-execution health check
        if health_config.check_before_execution:
            health_status = await self._perform_health_check(health_config)
            if health_status.status != "healthy":
                raise ModelOnexError(
                    message=f"Health check failed: {health_status.message}",
                    error_code="HEALTH_CHECK_FAILED"
                )

        # Execute computation
        result = await self._compute(contract)

        return result

    async def _perform_health_check(
        self,
        health_config: ModelHealthCheckSubcontract
    ):
        """Perform health check using mixin configuration."""
        checks = []

        # Check memory usage
        if health_config.check_memory:
            memory_ok = await self._check_memory_usage(
                health_config.memory_threshold_percent
            )
            checks.append(("memory", memory_ok))

        # Check CPU usage
        if health_config.check_cpu:
            cpu_ok = await self._check_cpu_usage(
                health_config.cpu_threshold_percent
            )
            checks.append(("cpu", cpu_ok))

        # Determine overall health
        all_healthy = all(ok for _, ok in checks)

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": dict(checks),
            "timestamp": datetime.now()
        }
```

### Pattern 4: Performance Monitoring Mixin

```
import time
from omnibase_core.model.subcontracts import ModelPerformanceMonitoringSubcontract

class NodeAggregatorReducer(NodeReducer):
    """REDUCER node with performance monitoring."""

    async def execute_reduction(self, contract: ModelContractReducer):
        """Execute with performance monitoring."""
        perf_config = contract.performance_monitoring_configuration

        if not perf_config.enabled:
            # Monitoring disabled
            return await self._reduce(contract)

        # Start performance tracking
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            # Execute reduction
            result = await self._reduce(contract)

            # Record success metrics
            await self._record_performance_metrics(
                operation="reduction",
                duration_ms=(time.time() - start_time) * 1000,
                memory_delta_mb=self._get_memory_usage() - start_memory,
                success=True,
                config=perf_config
            )

            return result

        except Exception as e:
            # Record failure metrics
            await self._record_performance_metrics(
                operation="reduction",
                duration_ms=(time.time() - start_time) * 1000,
                memory_delta_mb=self._get_memory_usage() - start_memory,
                success=False,
                config=perf_config
            )
            raise

    async def _record_performance_metrics(
        self,
        operation: str,
        duration_ms: float,
        memory_delta_mb: float,
        success: bool,
        config: ModelPerformanceMonitoringSubcontract
    ):
        """Record performance metrics to configured backend."""
        if not config.enabled:
            return

        metrics = {
            "operation": operation,
            "duration_ms": duration_ms,
            "memory_delta_mb": memory_delta_mb,
            "success": success,
            "timestamp": datetime.now()
        }

        # Send to metrics backend
        if config.metrics_backend == "prometheus":
            await self._send_to_prometheus(metrics)
        elif config.metrics_backend == "statsd":
            await self._send_to_statsd(metrics)
```

## Step 5: Testing Integrated Mixins

### Unit Test with Mixin

```
# tests/nodes/test_node_api_client_effect.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from omnibase_core.model.contracts import ModelContractEffect
from omnibase_core.model.subcontracts import ModelErrorHandlingSubcontract
from your_project.nodes import NodeApiClientEffect

@pytest.fixture
def error_handling_config():
    """Create error handling mixin configuration."""
    return ModelErrorHandlingSubcontract(
        enable_circuit_breaker=True,
        circuit_failure_threshold=3,
        error_retry_attempts=2,
        retriable_error_types=["TimeoutError", "ConnectionError"]
    )

@pytest.fixture
def node_contract(error_handling_config):
    """Create node contract with mixin."""
    contract = ModelContractEffect(
        node_name="api_client_effect",
        operation="call_api"
    )
    contract.error_handling_configuration = error_handling_config
    return contract

async def test_node_with_error_handling_mixin(node_contract):
    """Test node with error handling mixin integration."""
    node = NodeApiClientEffect()

    # Mock external API call
    node._call_external_api = AsyncMock(return_value={"status": "success"})

    # Execute node
    result = await node.execute_effect(node_contract)

    # Verify result
    assert result["status"] == "success"
    assert node._call_external_api.called

async def test_node_retry_logic_with_mixin(node_contract):
    """Test retry logic from mixin."""
    node = NodeApiClientEffect()

    # Mock API call: fail once, then succeed
    node._call_external_api = AsyncMock(
        side_effect=[TimeoutError("Connection timeout"), {"status": "success"}]
    )

    # Execute node (should retry)
    result = await node.execute_effect(node_contract)

    # Verify retry occurred
    assert result["status"] == "success"
    assert node._call_external_api.call_count == 2

async def test_node_circuit_breaker_with_mixin(node_contract):
    """Test circuit breaker from mixin."""
    node = NodeApiClientEffect()

    # Mock API call: always fail
    node._call_external_api = AsyncMock(side_effect=ConnectionError("Connection failed"))

    # Execute multiple times until circuit opens
    for i in range(4):
        with pytest.raises(Exception):
            await node.execute_effect(node_contract)

    # Circuit should now be open
    circuit_status = node._get_circuit_status("default")
    assert circuit_status.status == "open"
```

## Best Practices

### 1. Configuration Validation

Validate mixin configuration early:

```
async def execute_effect(self, contract: ModelContractEffect):
    """Execute with configuration validation."""
    # Validate mixin configuration exists
    if not hasattr(contract, "error_handling_configuration"):
        raise ModelOnexError(
            message="Error handling configuration missing",
            error_code="MISSING_MIXIN_CONFIGURATION"
        )

    error_config = contract.error_handling_configuration

    # Validate configuration values
    if error_config.circuit_failure_threshold < 1:
        raise ModelOnexError(
            message="Invalid circuit breaker threshold",
            error_code="INVALID_MIXIN_CONFIGURATION"
        )

    # Execute with validated configuration
    return await self._execute_with_config(contract, error_config)
```

### 2. Mixin Configuration Override

Allow runtime configuration overrides:

```
async def execute_effect(self, contract: ModelContractEffect):
    """Execute with optional config override."""
    # Get mixin configuration
    error_config = contract.error_handling_configuration

    # Check for runtime overrides
    if contract.runtime_config and "retry_attempts" in contract.runtime_config:
        # Override retry attempts
        error_config.error_retry_attempts = contract.runtime_config["retry_attempts"]

    return await self._execute_with_config(contract, error_config)
```

### 3. Graceful Degradation

Handle missing mixin gracefully:

```
async def execute_effect(self, contract: ModelContractEffect):
    """Execute with optional mixin."""
    # Try to use mixin if available
    if hasattr(contract, "error_handling_configuration"):
        error_config = contract.error_handling_configuration
        return await self._execute_with_error_handling(contract, error_config)
    else:
        # Fall back to basic execution
        self.logger.warning("Error handling mixin not configured, using default behavior")
        return await self._call_external_api(contract)
```

### 4. Mixin Capability Documentation

Document which mixins your node supports:

```
class NodeApiClientEffect(NodeEffect):
    """
    EFFECT node for external API interactions.

    **Supported Mixins**:
    - `mixin_error_handling`: Circuit breaker and retry logic
    - `mixin_health_check`: Pre-execution health validation
    - `mixin_performance_monitoring`: Request/response metrics

    **Required Mixins**:
    - `mixin_error_handling`: Required for fault tolerance

    **Optional Mixins**:
    - `mixin_health_check`: Recommended for production
    - `mixin_performance_monitoring`: Recommended for observability
    """
```

## Troubleshooting

### Issue: Configuration Not Found

**Symptom**: `AttributeError: 'ModelContractEffect' has no attribute 'error_handling_configuration'`

**Solutions**:
1. Verify `subcontracts` section in node contract
2. Check `integration_field` matches attribute name
3. Validate contract with contract validator
4. Ensure mixin path is correct

### Issue: Type Mismatch

**Symptom**: Configuration has wrong type

**Solutions**:
1. Import correct Pydantic model
2. Check model version matches mixin version
3. Verify model exported in `__init__.py`

### Issue: Mixin Not Applicable

**Symptom**: Validation fails with node type constraint error

**Solutions**:
1. Check mixin's `applicable_node_types`
2. Use only mixins allowed for your node type
3. Create node-type-specific variant if needed

## Next Steps

- **[Best Practices](05_BEST_PRACTICES.md)**: Advanced patterns and optimization
- **[Node Building Guide](../node-building/README.md)**: Complete node development guide
- **[Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)**: Deep architectural understanding

---

**Congratulations!** You've successfully integrated mixins into your ONEX nodes.
