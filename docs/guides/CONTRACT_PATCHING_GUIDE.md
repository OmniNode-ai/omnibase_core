# Contract Patching Guide

**Version**: 1.0.0
**Last Updated**: 2025-12-30
**Status**: Comprehensive Reference

> **New in v0.4.0**: Contract patches provide a declarative way to extend base contracts produced by profile factories. This guide explains the patching system architecture, model reference, and end-to-end usage examples.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Model Reference](#model-reference)
4. [Profile Reference](#profile-reference)
5. [Examples](#examples)
6. [Validation](#validation)
7. [Best Practices](#best-practices)

---

## Overview

### What is Contract Patching?

Contract patching is a system that allows you to extend base contracts with partial specifications rather than writing complete contracts from scratch. The core principle is:

> **"User authored files are patches, not full contracts."**

Instead of manually configuring dozens of fields with complex interdependencies, you:

1. Choose a profile that provides sensible defaults for your use case
2. Write a patch that only specifies what you want to change
3. The system merges your patch with the base contract

### Why Use Contract Patching?

| Benefit | Description |
|---------|-------------|
| **Reduced Boilerplate** | Only specify what you need to change |
| **Safe Defaults** | Profiles provide validated, production-ready defaults |
| **Consistency** | Teams share the same base configurations |
| **Evolution** | Profile updates automatically improve all patches |
| **Validation** | Patches are validated before merge |
| **Type Safety** | All patch fields have known types |

### Traditional vs Patch Approach

```python
# Traditional: 80+ lines of configuration
contract = ModelContractCompute(
    name="my_compute",
    version=ModelSemVer(major=1, minor=0, patch=0),
    description="My compute node",
    node_type=EnumNodeType.COMPUTE_GENERIC,
    input_model="mypackage.models.Input",
    output_model="mypackage.models.Output",
    performance=ModelPerformanceRequirements(
        single_operation_max_ms=5000,
        batch_operation_max_s=30,
        memory_limit_mb=512,
    ),
    descriptor=ModelHandlerBehaviorDescriptor(
        handler_kind="compute",
        purity="pure",
        idempotent=True,
        concurrency_policy="parallel_ok",
        # ... 20+ more fields
    ),
)
```

```python
# Patch: Only specify what matters
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives import ModelSemVer

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="compute_pure",
        version="1.0.0",
    ),
    name="my_compute",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="My compute node",
)
```

---

## Architecture

### Three-Layer Architecture

Contract patching uses a three-layer architecture:

```
Profile (Environment Policy)
    |
    | influences
    v
Behavior (Handler Configuration)
    |
    | embedded in
    v
Contract (Authoring Surface) <-- PATCHES TARGET THIS
    |
    | produced by
    v
Factory --> Base Contract + Patch = Expanded Contract
```

### Expansion Flow

```
+-------------------+     +------------------+     +--------------------+
| ModelProfileRef   |---->| Profile Factory  |---->| Base Contract      |
| (e.g., compute_   |     | (resolves        |     | (fully configured  |
|  pure @ 1.0.0)    |     |  profile)        |     |  defaults)         |
+-------------------+     +------------------+     +--------------------+
                                                            |
                                                            v
+-------------------+     +------------------+     +--------------------+
| User Patch        |---->| Merge Operation  |---->| Expanded Contract  |
| (partial          |     | (apply patch to  |     | (ready for         |
|  overrides)       |     |  base)           |     |  runtime)          |
+-------------------+     +------------------+     +--------------------+
```

### Key Concepts

1. **Profile**: Named template with environment-specific defaults (e.g., `compute_pure`, `effect_http`)
2. **Base Contract**: Complete contract produced by profile factory
3. **Patch**: Partial specification with only the fields you want to override
4. **Expanded Contract**: Result of merging base contract with patch

### Patch Semantics

- **Partial**: Only specify fields you want to change
- **Declarative**: Describe the desired state, not the operations
- **Structural**: Validation is syntax-based, not resolution-based
- **List Operations**: Use `__add` / `__remove` suffixes for lists

---

## Model Reference

### ModelContractPatch

The main patch model that extends a profile with partial overrides.

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch

patch = ModelContractPatch(
    extends=...,              # Required: Profile to extend
    name=...,                 # Optional: Contract name (for new contracts)
    node_version=...,         # Optional: Version (for new contracts)
    description=...,          # Optional: Description override
    input_model=...,          # Optional: Input model reference
    output_model=...,         # Optional: Output model reference
    descriptor=...,           # Optional: Behavior overrides
    handlers__add=...,        # Optional: Handlers to add
    handlers__remove=...,     # Optional: Handler names to remove
    dependencies__add=...,    # Optional: Dependencies to add
    dependencies__remove=..., # Optional: Dependency names to remove
    # ... more list operations
)
```

**Key Properties**:

| Property | Description |
|----------|-------------|
| `is_new_contract` | True if name and node_version are both set |
| `is_override_only` | True if neither name nor node_version are set |
| `has_list_operations()` | True if any `__add`/`__remove` field is set |

### ModelProfileReference

Reference to the profile that a patch extends.

```python
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference

ref = ModelProfileReference(
    profile="compute_pure",   # Profile identifier
    version="1.0.0",          # Version constraint (semver)
)
```

**Version Constraints**:

| Format | Meaning | Example |
|--------|---------|---------|
| `1.0.0` | Exact version | Only 1.0.0 |
| `^1.0.0` | Compatible version | 1.x.x (same major) |
| `>=1.0.0` | Minimum version | 1.0.0 or higher |
| `~1.0.0` | Approximate version | ~1.0.x |

### ModelDescriptorPatch

Partial behavior overrides for handler settings.

```python
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch

descriptor = ModelDescriptorPatch(
    purity="pure",                        # "pure" | "side_effecting"
    idempotent=True,                      # Safe to retry?
    timeout_ms=30000,                     # Max execution time
    concurrency_policy="parallel_ok",     # Concurrency handling
    isolation_policy="none",              # Process isolation
    observability_level="standard",       # Logging verbosity
    retry_policy=...,                     # Retry configuration
    circuit_breaker=...,                  # Circuit breaker config
)
```

**All fields are optional** - only set what you want to override.

### ModelHandlerSpec

Specification for adding handlers to contracts.

```python
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec

handler = ModelHandlerSpec(
    name="http_client",                          # Handler identifier
    handler_type="http",                         # Type (http, kafka, db, etc.)
    import_path="mypackage.handlers.HttpClient", # Optional: Python import
    config={"timeout": 30, "retries": 3},        # Optional: Configuration
)
```

**Config Value Types** (HandlerConfigValue):
- `str`, `int`, `float`, `bool`
- `list[str]`
- `None`

Nested dicts are **not supported** by design to maintain type safety.

### ModelCapabilityProvided

Declaration of capabilities that a handler provides.

```python
from omnibase_core.models.contracts.model_capability_provided import ModelCapabilityProvided

capability = ModelCapabilityProvided(
    name="event_emit",           # Capability identifier
    version="1.0.0",             # Optional: version
    description="Emits events",  # Optional: description
)
```

### ModelReference

Reference to a Pydantic model type for input/output specifications.

```python
from omnibase_core.models.contracts.model_reference import ModelReference

ref = ModelReference(
    module="mypackage.models.events",
    class_name="OrderCreatedEvent",
    version="1.0.0",             # Optional
)

# Access fully qualified name
print(ref.fully_qualified_name)  # mypackage.models.events.OrderCreatedEvent

# Resolve at runtime
model_class = ref.resolve()  # Returns the actual class or None
```

---

## Profile Reference

Profiles are pre-configured contract templates for each node type. Use the profile that best matches your use case.

### Compute Profiles

| Profile | Description | Use When |
|---------|-------------|----------|
| `compute_pure` | Pure, side-effect-free computation | Data transformations, calculations, parsing |
| `compute_stateful` | Computation with internal state | Aggregations, running totals, caching |

**compute_pure** characteristics:
```python
purity="pure"
idempotent=True
concurrency_policy="parallel_ok"
observability_level="minimal"
```

**compute_stateful** characteristics:
```python
purity="side_effecting"
idempotent=False
concurrency_policy="singleflight"
```

### Effect Profiles

| Profile | Description | Use When |
|---------|-------------|----------|
| `effect_http` | HTTP/REST API interactions | External API calls, webhooks |
| `effect_kafka` | Kafka/message queue operations | Event publishing, message consumption |
| `effect_db` | Database operations | CRUD operations, queries |

**effect_http** characteristics:
```python
idempotent=True
timeout_ms=30000
retry_policy.enabled=True
retry_policy.max_retries=3
circuit_breaker.enabled=True
```

**effect_kafka** characteristics:
```python
idempotent=True  # For producers with idempotency key
audit_trail.enabled=True
```

**effect_db** characteristics:
```python
transaction_isolation="serializable"
audit_trail.enabled=True
```

### Orchestrator Profiles

| Profile | Description | Use When |
|---------|-------------|----------|
| `orchestrator_safe` | Conservative, sequential execution | Starting out, debugging, critical paths |
| `orchestrator_full` | Full parallel execution | Independent steps, performance optimization |

**orchestrator_safe** characteristics:
```python
execution_mode="serial"
max_parallel_branches=1
checkpoint_enabled=False
idempotent=False
concurrency_policy="serialized"
```

**orchestrator_full** (parallel) characteristics:
```python
execution_mode="parallel"
max_parallel_branches=4
checkpoint_enabled=True
concurrency_policy="parallel_ok"
```

### Reducer Profiles

| Profile | Description | Use When |
|---------|-------------|----------|
| `reducer_fsm` | Finite state machine reducer | Entity lifecycle, approval workflows |
| `reducer_saga` | Saga pattern for distributed transactions | Multi-step compensating transactions |

**reducer_fsm** characteristics:
```python
states=["idle", "processing", "completed", "error"]
initial_state="idle"
idempotent=True
concurrency_policy="singleflight"
```

**reducer_saga** characteristics:
```python
idempotent=True
checkpoint_enabled=True
compensation_enabled=True
```

---

## Examples

### Example 1: Minimal Patch (Override Only)

The simplest patch that just extends a profile without adding identity:

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference

# Override patch - uses profile as-is
patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="compute_pure",
        version="1.0.0",
    ),
)

# Verify it's an override patch
assert patch.is_override_only is True
assert patch.is_new_contract is False
```

### Example 2: New Contract with Identity

Creating a new named contract that extends a profile:

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.primitives import ModelSemVer

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="effect_http",
        version="1.0.0",
    ),
    # Identity fields (both required for new contracts)
    name="order_api_client",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="HTTP client for Order Service API",
    # Model references
    input_model=ModelReference(
        module="mypackage.models.orders",
        class_name="OrderRequest",
    ),
    output_model=ModelReference(
        module="mypackage.models.orders",
        class_name="OrderResponse",
    ),
)

# Verify it's a new contract
assert patch.is_new_contract is True
assert patch.name == "order_api_client"
```

### Example 3: Adding Handlers and Dependencies

Extending a contract with handlers and dependencies:

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts import ModelDependency
from omnibase_core.models.primitives import ModelSemVer

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="effect_kafka",
        version="1.0.0",
    ),
    name="event_publisher",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Publishes domain events to Kafka",
    # Add handlers
    handlers__add=[
        ModelHandlerSpec(
            name="kafka_producer",
            handler_type="kafka",
            import_path="mypackage.handlers.KafkaProducerHandler",
            config={
                "bootstrap_servers": "localhost:9092",
                "acks": "all",
                "retries": 3,
            },
        ),
        ModelHandlerSpec(
            name="serializer",
            handler_type="json",
            config={"encoding": "utf-8"},
        ),
    ],
    # Add dependencies
    dependencies__add=[
        ModelDependency(
            name="schema_registry",
            version="^2.0.0",
            required=True,
        ),
        ModelDependency(
            name="metrics_client",
            version=">=1.0.0",
            required=False,  # Optional dependency
        ),
    ],
)

# Verify list operations
assert len(patch.handlers__add) == 2
assert len(patch.dependencies__add) == 2
assert patch.has_list_operations() is True
```

### Example 4: Behavior Overrides

Customizing handler behavior settings:

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="effect_http",
        version="1.0.0",
    ),
    name="payment_gateway_client",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Client for payment gateway with custom resilience",
    # Override behavior settings
    descriptor=ModelDescriptorPatch(
        timeout_ms=60000,  # 60 second timeout (payment APIs are slow)
        idempotent=True,
        retry_policy=ModelDescriptorRetryPolicy(
            enabled=True,
            max_retries=5,
            backoff_strategy="exponential",
            base_delay_ms=2000,  # 2 second base delay
        ),
        circuit_breaker=ModelDescriptorCircuitBreaker(
            enabled=True,
            failure_threshold=3,  # Open after 3 failures
            reset_timeout_ms=60000,  # Try again after 1 minute
        ),
        observability_level="verbose",  # Detailed logging for payments
    ),
)

# Verify descriptor overrides
assert patch.descriptor.timeout_ms == 60000
assert patch.descriptor.retry_policy.max_retries == 5
```

### Example 5: Removing Items from Lists

Removing handlers or dependencies inherited from the profile:

```python
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives import ModelSemVer

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="orchestrator_full",
        version="1.0.0",
    ),
    name="simplified_orchestrator",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Orchestrator with minimal handlers",
    # Remove handlers we don't need
    handlers__remove=[
        "checkpoint_handler",
        "metrics_handler",
    ],
    # Remove events we don't consume
    consumed_events__remove=[
        "system.metrics.collected",
        "system.health.changed",
    ],
)

# Verify remove operations
assert "checkpoint_handler" in patch.handlers__remove
```

### Example 6: Adding Capabilities

Declaring capabilities that your contract provides:

```python
from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.primitives import ModelSemVer

patch = ModelContractPatch(
    extends=ModelProfileReference(
        profile="effect_kafka",
        version="1.0.0",
    ),
    name="notification_publisher",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    description="Publishes user notifications",
    # Declare required capabilities
    capability_inputs__add=[
        "user_context",
        "template_engine",
    ],
    # Declare provided capabilities
    capability_outputs__add=[
        ModelCapabilityProvided(
            name="notification_emit",
            version="1.0.0",
            description="Emits notification events to Kafka",
        ),
        ModelCapabilityProvided(
            name="delivery_tracking",
            version="1.0.0",
            description="Tracks notification delivery status",
        ),
    ],
)
```

### Example 7: Complete Real-World Example

A complete example of an order processing effect:

```python
from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.contracts import ModelDependency
from omnibase_core.models.primitives import ModelSemVer
from omnibase_core.models.runtime.model_descriptor_circuit_breaker import (
    ModelDescriptorCircuitBreaker,
)
from omnibase_core.models.runtime.model_descriptor_retry_policy import (
    ModelDescriptorRetryPolicy,
)

order_processor_patch = ModelContractPatch(
    # Extend the HTTP effect profile
    extends=ModelProfileReference(
        profile="effect_http",
        version="^1.0.0",
    ),
    # New contract identity
    name="order_processor_effect",
    node_version=ModelSemVer(major=2, minor=1, patch=0),
    description="Processes orders by calling external fulfillment service",
    # Input/Output models
    input_model=ModelReference(
        module="myapp.models.orders",
        class_name="ProcessOrderRequest",
    ),
    output_model=ModelReference(
        module="myapp.models.orders",
        class_name="ProcessOrderResponse",
    ),
    # Custom behavior
    descriptor=ModelDescriptorPatch(
        timeout_ms=45000,
        idempotent=True,
        observability_level="verbose",
        retry_policy=ModelDescriptorRetryPolicy(
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=1000,
        ),
        circuit_breaker=ModelDescriptorCircuitBreaker(
            enabled=True,
            failure_threshold=5,
            reset_timeout_ms=30000,
        ),
    ),
    # Add handlers
    handlers__add=[
        ModelHandlerSpec(
            name="fulfillment_client",
            handler_type="http",
            import_path="myapp.handlers.FulfillmentClient",
            config={
                "base_url": "https://fulfillment.example.com",
                "api_key_env": "FULFILLMENT_API_KEY",
            },
        ),
        ModelHandlerSpec(
            name="order_validator",
            handler_type="validator",
            import_path="myapp.handlers.OrderValidator",
        ),
    ],
    # Add dependencies
    dependencies__add=[
        ModelDependency(
            name="fulfillment_sdk",
            version="^3.0.0",
            required=True,
        ),
    ],
    # Add events this effect consumes
    consumed_events__add=[
        "order.created.v1",
        "order.updated.v1",
    ],
    # Declare capabilities
    capability_inputs__add=[
        "authentication",
        "rate_limiting",
    ],
    capability_outputs__add=[
        ModelCapabilityProvided(
            name="order_fulfillment",
            version="2.0.0",
            description="Fulfills orders via external service",
        ),
    ],
)
```

---

## Validation

### What Gets Validated

The `ContractPatchValidator` performs validation at three levels:

#### 1. Structural Validation (via Pydantic)

- **Field Types**: All fields match expected types
- **Required Fields**: `extends` is always required
- **Extra Fields**: Unknown fields are rejected (`extra="forbid"`)
- **Constraints**: min_length, max_length, ge, le, etc.

#### 2. Semantic Validation

| Check | Description | Error Code |
|-------|-------------|------------|
| Identity Consistency | If `name` is set, `node_version` must also be set (and vice versa) | `IDENTITY_INCONSISTENT` |
| Add/Remove Conflicts | Same item cannot appear in both `__add` and `__remove` | `CONFLICTING_LIST_OPERATIONS` |
| Duplicate Entries | Items in `__add` lists must be unique | `DUPLICATE_LIST_ENTRIES` |
| Empty Descriptor | Warning if descriptor patch has no overrides | `EMPTY_DESCRIPTOR_PATCH` |
| Purity/Idempotent | Warning if `purity="pure"` but `idempotent=False` | `PURITY_IDEMPOTENT_MISMATCH` |

#### 3. Format Validation

| Check | Description | Error Code |
|-------|-------------|------------|
| Profile Name | Should be lowercase_with_underscores | `NON_STANDARD_PROFILE_NAME` |
| Version Format | Should contain digits (semver) | `NON_STANDARD_VERSION_FORMAT` |
| Handler Names | Alphanumeric and underscores only | `INVALID_HANDLER_NAME` |
| Import Paths | Valid Python dotted paths | `INVALID_IMPORT_PATH` |

### What Is NOT Validated (Deferred)

These checks are deferred to expansion time:

- **Profile Existence**: Whether the profile actually exists in the factory
- **Model Resolution**: Whether input/output model references can be imported
- **Capability Compatibility**: Whether required capabilities are provided
- **Version Satisfaction**: Whether profile version constraints are met

### Using the Validator

```python
from pathlib import Path
from omnibase_core.validation import ContractPatchValidator

validator = ContractPatchValidator()

# Validate an already-parsed patch
result = validator.validate(patch)
if not result.is_valid:
    for issue in result.issues:
        print(f"{issue.severity}: {issue.message}")

# Validate from dictionary
result = validator.validate_dict({
    "extends": {"profile": "compute_pure", "version": "1.0.0"},
    "name": "my_node",
    "node_version": {"major": 1, "minor": 0, "patch": 0},
})

# Validate from YAML file
result = validator.validate_file(Path("contracts/my_patch.yaml"))
if result.is_valid:
    patch = result.validated_value  # The parsed patch
```

### Validation Result Structure

```python
class ModelValidationResult:
    is_valid: bool          # Overall pass/fail
    summary: str            # Human-readable summary
    issues: list[Issue]     # All issues (errors + warnings)
    errors: list[Issue]     # Only errors
    warnings: list[Issue]   # Only warnings
    validated_value: T      # The validated object (if valid)
```

---

## Best Practices

### Do

1. **Start with the Right Profile**
   ```python
   # Choose profile that matches your use case
   extends=ModelProfileReference(profile="compute_pure", ...)   # For pure computation
   extends=ModelProfileReference(profile="effect_http", ...)    # For HTTP calls
   extends=ModelProfileReference(profile="orchestrator_safe", ...)  # For workflows
   ```

2. **Only Override What You Need**
   ```python
   # Good: Minimal override
   descriptor=ModelDescriptorPatch(timeout_ms=60000)

   # Avoid: Repeating defaults
   descriptor=ModelDescriptorPatch(
       timeout_ms=60000,
       purity="side_effecting",  # Already default for effect profile
       idempotent=True,          # Already default
   )
   ```

3. **Use Version Constraints Wisely**
   ```python
   # Good: Allow compatible updates
   extends=ModelProfileReference(profile="compute_pure", version="^1.0.0")

   # Cautious: Lock to specific version
   extends=ModelProfileReference(profile="compute_pure", version="1.0.0")
   ```

4. **Document Your Patches**
   ```python
   patch = ModelContractPatch(
       extends=...,
       name="payment_processor",
       description="Processes payments via Stripe. Uses 60s timeout for slow API.",
   )
   ```

5. **Validate Before Expansion**
   ```python
   validator = ContractPatchValidator()
   result = validator.validate(patch)
   if not result.is_valid:
       raise ValueError(f"Invalid patch: {result.summary}")
   ```

### Don't

1. **Mix Add and Remove for Same Item**
   ```python
   # ERROR: Conflicting operations
   handlers__add=[ModelHandlerSpec(name="http_client", ...)],
   handlers__remove=["http_client"],  # Can't add AND remove!
   ```

2. **Partial Identity**
   ```python
   # ERROR: Must have both or neither
   name="my_node",
   # Missing node_version!
   ```

3. **Invalid Handler Config Types**
   ```python
   # ERROR: Nested dicts not allowed
   config={"headers": {"Content-Type": "application/json"}}

   # OK: Flat structure
   config={"content_type": "application/json"}
   ```

4. **Override Profile Defaults Unnecessarily**
   ```python
   # Unnecessary: compute_pure already sets these
   descriptor=ModelDescriptorPatch(
       purity="pure",
       idempotent=True,
       concurrency_policy="parallel_ok",
   )
   ```

5. **Non-Idempotent with Retry Enabled**
   ```python
   # ERROR: Semantic conflict
   descriptor=ModelDescriptorPatch(
       idempotent=False,
       retry_policy=ModelDescriptorRetryPolicy(enabled=True),
   )
   ```

### Common Patterns

#### Pattern: Environment-Specific Patches

```python
# Base patch (shared)
base_patch = ModelContractPatch(
    extends=ModelProfileReference(profile="effect_http", version="^1.0.0"),
    name="api_client",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
)

# Production patch (extends base)
prod_patch = ModelContractPatch(
    extends=ModelProfileReference(profile="effect_http", version="^1.0.0"),
    name="api_client",
    node_version=ModelSemVer(major=1, minor=0, patch=0),
    descriptor=ModelDescriptorPatch(
        timeout_ms=30000,
        observability_level="verbose",
        retry_policy=ModelDescriptorRetryPolicy(
            enabled=True,
            max_retries=5,
        ),
    ),
)
```

#### Pattern: Feature Flags via Handlers

```python
# Add handlers conditionally
handlers_to_add = [
    ModelHandlerSpec(name="core_handler", handler_type="core"),
]

if enable_metrics:
    handlers_to_add.append(
        ModelHandlerSpec(name="metrics_handler", handler_type="metrics")
    )

patch = ModelContractPatch(
    extends=...,
    handlers__add=handlers_to_add,
)
```

#### Pattern: Capability-Based Composition

```python
# Define capabilities your node provides
patch = ModelContractPatch(
    extends=...,
    capability_outputs__add=[
        ModelCapabilityProvided(name="event_emit", version="1.0.0"),
        ModelCapabilityProvided(name="audit_log", version="1.0.0"),
    ],
    # And capabilities it requires
    capability_inputs__add=["authentication", "rate_limiting"],
)
```

---

## Related Documentation

- [Contract Profile Guide](./CONTRACT_PROFILE_GUIDE.md) - Profile factory reference
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Node types
- [Effect Subcontract Guide](./EFFECT_SUBCONTRACT_GUIDE.md) - Effect handlers
- [Node Building Guide](./node-building/README.md) - Building nodes

---

**Last Updated**: 2025-12-30
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
