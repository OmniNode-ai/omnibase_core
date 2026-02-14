> **Navigation**: [Home](../INDEX.md) > Guides > Contract Profile Guide

# Contract Profile Guide

**Version**: 1.0.0
**Last Updated**: 2025-12-29
**Status**: Comprehensive Reference

> **New in v0.4.0**: Contract profile factories provide pre-configured contract templates for each node type (orchestrator, reducer, effect, compute). This guide explains when to use each profile and how to create custom profiles.

## Table of Contents

1. [Overview](#overview)
2. [Why Use Profiles?](#why-use-profiles)
3. [Available Profiles](#available-profiles)
   - [Orchestrator Profiles](#orchestrator-profiles)
   - [Reducer Profiles](#reducer-profiles)
   - [Effect Profiles](#effect-profiles)
   - [Compute Profiles](#compute-profiles)
4. [Profile Selection Decision Tree](#profile-selection-decision-tree)
5. [Using Profiles](#using-profiles)
6. [Creating Custom Profiles](#creating-custom-profiles)
7. [Best Practices](#best-practices)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Contract profiles are **pre-configured contract templates** that provide safe, validated defaults for common use cases. Instead of manually configuring every field in a contract model, you can start with a profile that matches your needs and customize from there.

```python
from omnibase_core.factories import get_default_orchestrator_profile

# Get a fully valid contract in one line
contract = get_default_orchestrator_profile("orchestrator_safe")
```

### What Profiles Configure

Each profile sets values for:

- **Handler Descriptor**: Purity, idempotency, concurrency policy, isolation, observability
- **Performance Requirements**: Timeout limits, memory limits, batch sizes
- **Resilience Settings**: Retry policies, circuit breakers, checkpointing
- **Execution Profile**: Ordering policy, deterministic execution
- **Node-Specific Settings**: FSM states, IO operations, algorithm configs, workflow coordination

---

## Why Use Profiles?

### Problem: Contract Complexity

ONEX contracts have dozens of fields with complex interdependencies:

```python
# Manual contract creation is verbose and error-prone
contract = ModelContractOrchestrator(
    name="my_orchestrator",
    version=ModelSemVer(major=1, minor=0, patch=0),
    description="...",
    node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    input_model="...",
    output_model="...",
    performance=ModelPerformanceRequirements(
        single_operation_max_ms=5000,
        batch_operation_max_s=30,
        memory_limit_mb=512,
    ),
    action_emission=ModelActionEmissionConfig(
        emission_strategy="sequential",
        batch_size=1,
    ),
    workflow_coordination=ModelWorkflowConfig(
        execution_mode="serial",
        max_parallel_branches=1,
        checkpoint_enabled=False,
        checkpoint_interval_ms=100,
    ),
    # ... 20+ more fields
)
```

### Solution: Profiles

Profiles encapsulate best practices and safe defaults:

```python
# One line, fully valid, production-ready
contract = get_default_orchestrator_profile("orchestrator_safe")
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Reduced Boilerplate** | 80+ lines of configuration reduced to 1 line |
| **Safe Defaults** | Conservative settings prevent common mistakes |
| **Consistency** | Teams use the same base configurations |
| **Type Safety** | Return types are specific (not `Any`) |
| **Validation** | All profiles produce valid contracts |
| **Customizable** | Modify after creation for specific needs |

---

## Available Profiles

### Orchestrator Profiles

#### orchestrator_safe (Default)

The most conservative orchestrator profile. Use this when starting out or when you need predictable, sequential execution.

**Use When**:
- Starting a new orchestrator node
- Debugging workflow issues
- Sequential dependencies between steps
- Maximum predictability required

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| Execution Mode | Serial | Steps run one at a time |
| Max Parallel Branches | 1 | No parallel execution |
| Checkpoint Enabled | false | No complex state management |
| Idempotent | false | Does not assume safe to retry |
| Concurrency Policy | `serialized` | Single execution at a time |
| Observability Level | `standard` | Balanced logging |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="orchestrator",
    purity="side_effecting",
    idempotent=False,
    concurrency_policy="serialized",
    isolation_policy="none",
    observability_level="standard",
)
```

**Example Usage**:
```python
from omnibase_core.factories import get_default_orchestrator_profile

contract = get_default_orchestrator_profile("orchestrator_safe")
# Ready to use with serial, predictable execution
```

---

#### orchestrator_parallel

Enables parallel execution for workflows with independent steps.

**Use When**:
- Workflow steps can run concurrently
- No data dependencies between parallel branches
- Performance optimization needed
- Fan-out/fan-in patterns

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| Execution Mode | Parallel | Steps can run concurrently |
| Max Parallel Branches | 4 | Up to 4 concurrent branches |
| Event Correlation | Enabled | Track parallel results |
| Batch Size | 5 | Emit actions in batches |
| Concurrency Policy | `parallel_ok` | Allows concurrent execution |
| Memory Limit | 1024 MB | Higher for parallel processing |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="orchestrator",
    purity="side_effecting",
    idempotent=False,
    concurrency_policy="parallel_ok",
    isolation_policy="none",
    observability_level="standard",
)
```

**Example Usage**:
```python
contract = get_default_orchestrator_profile("orchestrator_parallel")
# Execute independent steps concurrently
```

**When NOT to Use**:
- Steps have data dependencies
- Order matters for side effects
- Resource contention is a concern

---

#### orchestrator_resilient

Fault-tolerant orchestrator with checkpointing, retries, and circuit breaker protection.

**Use When**:
- Critical workflows that must complete
- Long-running processes
- External service dependencies
- Recovery from failures required
- Audit trail needed

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| Checkpoint Enabled | true | Recover from failures |
| Checkpoint Interval | 1000 ms | Frequent state snapshots |
| Failure Isolation | Enabled | Contain failures |
| Idempotent | true | Safe to retry |
| Retry Policy | 3 retries, exponential backoff | Automatic recovery |
| Circuit Breaker | 5 failure threshold | Protect dependencies |
| Observability Level | `verbose` | Detailed monitoring |
| Timeout | 10000 ms | Longer for retries |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="orchestrator",
    purity="side_effecting",
    idempotent=True,
    concurrency_policy="serialized",
    isolation_policy="none",
    observability_level="verbose",
    retry_policy=ModelDescriptorRetryPolicy(
        enabled=True,
        max_retries=3,
        backoff_strategy="exponential",
    ),
    circuit_breaker=ModelDescriptorCircuitBreaker(
        enabled=True,
        failure_threshold=5,
    ),
)
```

**Example Usage**:
```python
contract = get_default_orchestrator_profile("orchestrator_resilient")
# Fault-tolerant workflow with automatic recovery
```

---

### Reducer Profiles

#### reducer_fsm_basic

Basic finite state machine reducer for state transitions.

**Use When**:
- Implementing state machines
- Order lifecycle management
- Approval workflows
- Any entity with defined state transitions

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| FSM States | idle, processing, completed, error | Basic 4-state machine |
| Initial State | idle | Starting point |
| Terminal States | completed | End states |
| Idempotent | true | FSM transitions are repeatable |
| Concurrency Policy | `singleflight` | One transition at a time |
| Incremental Processing | Enabled | Process partial updates |
| Result Caching | Enabled | Cache reduction results |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="reducer",
    purity="side_effecting",
    idempotent=True,
    concurrency_policy="singleflight",
    isolation_policy="none",
    observability_level="standard",
)
```

**FSM Configuration**:
```text
States: idle -> processing -> completed
                    |
                    v
                  error -> (recover) -> idle
```

**Example Usage**:
```python
from omnibase_core.factories import get_default_reducer_profile

contract = get_default_reducer_profile("reducer_fsm_basic")
# Basic FSM ready for customization
```

**Customization Example**:
```python
# Get base profile
contract = get_default_reducer_profile("reducer_fsm_basic")

# Add custom states (contracts are mutable)
contract.state_transitions.states.append(
    ModelFSMStateDefinition(
        version=contract.version,
        state_name="pending_approval",
        state_type="operational",
        description="Awaiting manager approval",
    )
)
```

---

### Effect Profiles

#### effect_idempotent

Idempotent effect for external system interactions with retry support.

**Use When**:
- API calls to external services
- Database operations
- File system operations
- Any I/O that can be safely retried

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| Idempotent | true | Safe to retry operations |
| Timeout | 30000 ms | Reasonable for I/O |
| Retry Policy | 3 attempts, exponential backoff | Automatic retry |
| Circuit Breaker | 3 failure threshold | Protect external services |
| Audit Trail | Enabled | Track all operations |
| Transaction Isolation | serializable | Strong consistency |
| Concurrency Policy | `parallel_ok` | Idempotent effects parallelize safely |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="effect",
    purity="side_effecting",
    idempotent=True,
    timeout_ms=30000,
    concurrency_policy="parallel_ok",
    isolation_policy="none",
    observability_level="standard",
    retry_policy=ModelDescriptorRetryPolicy(
        enabled=True,
        max_retries=3,
        backoff_strategy="exponential",
        base_delay_ms=1000,
    ),
    capability_outputs=["external_system"],
)
```

**Example Usage**:
```python
from omnibase_core.factories import get_default_effect_profile

contract = get_default_effect_profile("effect_idempotent")
# Ready for external service interactions with retry
```

**Important**: Only use this profile for truly idempotent operations. If your operation is NOT idempotent (e.g., INSERT without duplicate check), disable retry:

```python
contract = get_default_effect_profile("effect_idempotent")
contract.descriptor.retry_policy.enabled = False
contract.descriptor.idempotent = False
```

---

### Compute Profiles

#### compute_pure

Pure computation profile for deterministic, side-effect-free transformations.

**Use When**:
- Data transformations
- Mathematical calculations
- Parsing and formatting
- Any pure function with no I/O

**Characteristics**:
| Setting | Value | Reason |
|---------|-------|--------|
| Purity | `pure` | No side effects |
| Deterministic | true | Same input = same output |
| Idempotent | true | Pure functions are always idempotent |
| Concurrency Policy | `parallel_ok` | Pure functions parallelize safely |
| Parallel Processing | Disabled | Single-threaded by default |
| Intermediate Caching | Disabled | Pure = no state |
| Observability Level | `minimal` | Low overhead |
| Memory Optimization | Enabled | Efficient memory use |

**Handler Descriptor**:
```python
descriptor=ModelHandlerBehaviorDescriptor(
    node_archetype="compute",
    purity="pure",
    idempotent=True,
    concurrency_policy="parallel_ok",
    isolation_policy="none",
    observability_level="minimal",
)
```

**Example Usage**:
```python
from omnibase_core.factories import get_default_compute_profile

contract = get_default_compute_profile("compute_pure")
# Pure computation with minimal overhead
```

**When NOT to Use**:
- Operations with side effects (use EFFECT)
- State modifications (use REDUCER)
- Workflow coordination (use ORCHESTRATOR)

---

## Profile Selection Decision Tree

Use this decision tree to select the right profile:

```text
                    What type of node are you building?
                                   |
          +------------------------+------------------------+
          |            |           |           |
     ORCHESTRATOR   REDUCER     EFFECT     COMPUTE
          |            |           |           |
          v            v           v           v
    Does it need   Is it a     Is the      Is the
    parallel       state       operation   computation
    execution?     machine?    idempotent? pure?
          |            |           |           |
    +-----+-----+      |      +----+----+     |
    |     |     |      |      |         |     |
   YES   NO    FAULT   |     YES       NO     |
    |     |   TOLERANT?|      |         |     |
    |     |     |      |      |    (create    |
    v     v     v      v      v    custom)    v
 parallel safe resilient fsm   idempotent   pure
```

### Quick Reference Table

| Use Case | Profile | Key Settings |
|----------|---------|--------------|
| New orchestrator, debugging | `orchestrator_safe` | Serial, no retry |
| Independent workflow steps | `orchestrator_parallel` | Parallel, batched |
| Critical long-running workflow | `orchestrator_resilient` | Checkpoints, retries |
| State machine entity | `reducer_fsm_basic` | FSM, singleflight |
| Retryable API calls | `effect_idempotent` | Retry, circuit breaker |
| Data transformation | `compute_pure` | Pure, minimal overhead |

---

## Using Profiles

### Basic Usage

```python
from omnibase_core.factories import (
    get_default_orchestrator_profile,
    get_default_reducer_profile,
    get_default_effect_profile,
    get_default_compute_profile,
)

# Type-safe factory functions return specific types
orchestrator_contract = get_default_orchestrator_profile("orchestrator_safe")
reducer_contract = get_default_reducer_profile("reducer_fsm_basic")
effect_contract = get_default_effect_profile("effect_idempotent")
compute_contract = get_default_compute_profile("compute_pure")
```

### Generic Factory

Use when node type is determined at runtime:

```python
from omnibase_core.factories import get_default_contract_profile
from omnibase_core.enums import EnumNodeType

# Returns ModelContractBase (base type)
contract = get_default_contract_profile(
    node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    profile="orchestrator_safe",
)
```

### Listing Available Profiles

```python
from omnibase_core.factories import available_profiles
from omnibase_core.enums import EnumNodeType

profiles = available_profiles(EnumNodeType.ORCHESTRATOR_GENERIC)
print(profiles)
# ['orchestrator_safe', 'orchestrator_parallel', 'orchestrator_resilient']
```

### Class-Based Factory

For dependency injection:

```python
from omnibase_core.factories import ContractProfileFactory
from omnibase_core.enums import EnumNodeType

factory = ContractProfileFactory()
contract = factory.get_profile(
    node_type=EnumNodeType.COMPUTE_GENERIC,
    profile="compute_pure",
)
```

### Specifying Version

```python
contract = get_default_orchestrator_profile(
    profile="orchestrator_safe",
    version="2.0.0",  # Custom version
)
print(contract.version)  # ModelSemVer(major=2, minor=0, patch=0)
```

---

## Creating Custom Profiles

### Option 1: Modify After Creation

Get a profile and modify the returned contract:

```python
from omnibase_core.factories import get_default_orchestrator_profile

# Start with safe profile
contract = get_default_orchestrator_profile("orchestrator_safe")

# Customize for your use case
contract.name = "my_custom_orchestrator"
contract.description = "Custom orchestrator for order processing"

# Enable specific features
contract.workflow_coordination.checkpoint_enabled = True
contract.workflow_coordination.checkpoint_interval_ms = 5000

# Modify handler behavior
contract.descriptor.observability_level = "verbose"
contract.descriptor.retry_policy = ModelDescriptorRetryPolicy(
    enabled=True,
    max_retries=5,
    backoff_strategy="linear",
    base_delay_ms=500,
)
```

### Option 2: Create New Profile Function

Add a new profile to the registry:

```python
# In your project's profiles module
from omnibase_core.models.contracts import (
    ModelContractOrchestrator,
    ModelHandlerBehaviorDescriptor,
    ModelWorkflowConfig,
    # ... other imports
)

def get_orchestrator_high_performance_profile(
    version: str = "1.0.0",
) -> ModelContractOrchestrator:
    """
    Create a high-performance orchestrator profile.

    Optimized for throughput with relaxed safety guarantees.
    """
    return ModelContractOrchestrator(
        name="orchestrator_high_performance_profile",
        version=_parse_version(version),
        description="High-performance orchestrator with parallel execution",
        node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
        input_model="omnibase_core.models.core.ModelInput",
        output_model="omnibase_core.models.core.ModelOutput",
        performance=ModelPerformanceRequirements(
            single_operation_max_ms=2000,  # Tighter timeout
            batch_operation_max_s=60,
            memory_limit_mb=2048,  # More memory
        ),
        workflow_coordination=ModelWorkflowConfig(
            execution_mode="parallel",
            max_parallel_branches=8,  # High parallelism
            checkpoint_enabled=False,  # No checkpoint overhead
            checkpoint_interval_ms=100,
        ),
        # ... other settings
        descriptor=ModelHandlerBehaviorDescriptor(
            node_archetype="orchestrator",
            purity="side_effecting",
            idempotent=False,
            concurrency_policy="parallel_ok",
            isolation_policy="none",
            observability_level="minimal",  # Low overhead
        ),
    )

# Register in your profile registry
MY_PROFILES = {
    "orchestrator_high_performance": get_orchestrator_high_performance_profile,
}
```

### Option 3: Extend Profile Registry

For project-wide custom profiles, extend the factory:

```python
from omnibase_core.factories.profiles import ORCHESTRATOR_PROFILES

# Add to existing registry (at module initialization)
ORCHESTRATOR_PROFILES["orchestrator_high_performance"] = (
    get_orchestrator_high_performance_profile
)

# Now available via standard factory
contract = get_default_orchestrator_profile("orchestrator_high_performance")
```

---

## Best Practices

### 1. Start with the Most Restrictive Profile

Always start with conservative defaults and relax as needed:

```python
# GOOD: Start safe
contract = get_default_orchestrator_profile("orchestrator_safe")
# Then enable parallelism if proven safe

# AVOID: Starting with parallel without testing
contract = get_default_orchestrator_profile("orchestrator_parallel")
```

### 2. Only Enable Parallelism for Truly Independent Operations

```python
# SAFE: Independent operations
async def process_orders(orders):
    # Each order is independent - parallel OK
    tasks = [process_order(o) for o in orders]
    return await asyncio.gather(*tasks)

# UNSAFE: Operations with shared state
async def update_inventory(items):
    # Items might update same inventory record - use serial
    for item in items:
        await update_item(item)
```

### 3. Enable Retries Only for Idempotent Operations

| Operation | Idempotent? | Enable Retry? |
|-----------|-------------|---------------|
| GET /users/123 | Yes | Yes |
| PUT /users/123 | Yes | Yes |
| POST /orders | No | No |
| DELETE /users/123 | Yes | Yes |
| INSERT INTO table | No | No |
| UPDATE SET x = 5 | Yes | Yes |
| UPDATE SET x = x + 1 | No | No |

### 4. Use Profile Names That Describe Behavior

```python
# GOOD: Descriptive names
"orchestrator_safe"       # Describes behavior
"orchestrator_parallel"   # Describes capability
"orchestrator_resilient"  # Describes characteristic

# AVOID: Generic names
"orchestrator_v1"         # What does v1 mean?
"orchestrator_default"    # Default what?
```

### 5. Document Custom Profile Decisions

```python
def get_order_processing_profile(version: str = "1.0.0"):
    """
    Order processing orchestrator profile.

    Design Decisions:
        - checkpoint_enabled=True: Orders are critical, must not lose progress
        - max_parallel_branches=1: Order steps must execute sequentially
        - retry_policy=3: Transient failures are common with payment gateway
        - circuit_breaker=5: Protect against payment gateway outages

    Use Cases:
        - Order lifecycle management
        - Payment processing workflows
        - Fulfillment coordination
    """
    return ModelContractOrchestrator(...)
```

### 6. Test Profile Configurations

```python
def test_custom_profile_is_valid():
    """Ensure custom profile produces valid contract."""
    contract = get_order_processing_profile()

    # Validate required fields
    assert contract.name is not None
    assert contract.version is not None
    assert contract.descriptor is not None

    # Validate business rules
    assert contract.workflow_coordination.checkpoint_enabled is True
    assert contract.descriptor.retry_policy.max_retries == 3
```

---

## API Reference

### Factory Functions

| Function | Return Type | Description |
|----------|-------------|-------------|
| `get_default_contract_profile(node_type, profile, version)` | `ModelContractBase` | Generic factory |
| `get_default_orchestrator_profile(profile, version)` | `ModelContractOrchestrator` | Orchestrator factory |
| `get_default_reducer_profile(profile, version)` | `ModelContractReducer` | Reducer factory |
| `get_default_effect_profile(profile, version)` | `ModelContractEffect` | Effect factory |
| `get_default_compute_profile(profile, version)` | `ModelContractCompute` | Compute factory |
| `available_profiles(node_type)` | `list[str]` | List available profiles |

### Profile Registries

| Registry | Location | Profiles |
|----------|----------|----------|
| `ORCHESTRATOR_PROFILES` | `omnibase_core.factories.profiles` | safe, parallel, resilient |
| `REDUCER_PROFILES` | `omnibase_core.factories.profiles` | fsm_basic |
| `EFFECT_PROFILES` | `omnibase_core.factories.profiles` | idempotent |
| `COMPUTE_PROFILES` | `omnibase_core.factories.profiles` | pure |

### Import Paths

```python
# Factory functions
from omnibase_core.factories import (
    get_default_contract_profile,
    get_default_orchestrator_profile,
    get_default_reducer_profile,
    get_default_effect_profile,
    get_default_compute_profile,
    available_profiles,
    ContractProfileFactory,
)

# Profile registries (for extension)
from omnibase_core.factories.profiles import (
    ORCHESTRATOR_PROFILES,
    REDUCER_PROFILES,
    EFFECT_PROFILES,
    COMPUTE_PROFILES,
)

# Individual profile functions
from omnibase_core.factories.profiles.factory_profile_orchestrator import (
    get_orchestrator_safe_profile,
    get_orchestrator_parallel_profile,
    get_orchestrator_resilient_profile,
)
```

---

## Troubleshooting

### Error: Unknown profile 'xxx' for orchestrator

**Cause**: Requested profile does not exist.

**Solution**: Use `available_profiles()` to see valid options:

```python
from omnibase_core.factories import available_profiles
from omnibase_core.enums import EnumNodeType

profiles = available_profiles(EnumNodeType.ORCHESTRATOR_GENERIC)
print(profiles)  # ['orchestrator_safe', 'orchestrator_parallel', 'orchestrator_resilient']
```

### Error: Unknown node type 'xxx'

**Cause**: Node type does not match any category.

**Solution**: Ensure node type contains orchestrator, reducer, effect, or compute:

```python
# Valid node types
EnumNodeType.ORCHESTRATOR_GENERIC  # Contains "orchestrator"
EnumNodeType.REDUCER_GENERIC       # Contains "reducer"
EnumNodeType.EFFECT_GENERIC        # Contains "effect"
EnumNodeType.COMPUTE_GENERIC       # Contains "compute"
```

### Type Error: Expected ModelContractOrchestrator, got ModelContractBase

**Cause**: Using generic factory when specific factory is needed.

**Solution**: Use the type-specific factory:

```python
# Generic returns base type
contract = get_default_contract_profile(
    node_type=EnumNodeType.ORCHESTRATOR_GENERIC,
    profile="orchestrator_safe",
)  # Returns ModelContractBase

# Specific returns precise type
contract = get_default_orchestrator_profile("orchestrator_safe")
# Returns ModelContractOrchestrator
```

### Profile Settings Not Taking Effect

**Cause**: Modified contract is not being used.

**Solution**: Ensure you're using the modified contract:

```python
# WRONG: Modifying but not using
contract = get_default_orchestrator_profile("orchestrator_safe")
contract.descriptor.observability_level = "verbose"
# ... somewhere else ...
new_contract = get_default_orchestrator_profile("orchestrator_safe")  # Gets original!

# RIGHT: Use the modified contract
contract = get_default_orchestrator_profile("orchestrator_safe")
contract.descriptor.observability_level = "verbose"
# Use `contract` everywhere
```

---

## Related Documentation

- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Node Building Guide](./node-building/README.md)
- [Effect Subcontract Guide](./EFFECT_SUBCONTRACT_GUIDE.md)

---

**Last Updated**: 2025-12-29
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
