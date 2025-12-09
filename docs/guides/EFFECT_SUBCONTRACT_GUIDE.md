# Effect Subcontract Guide

**Version**: 1.0.0
**Last Updated**: 2025-12-09
**Correlation ID**: `effect-subcontract-guide-001`

> **New in PR #139**: Effect subcontract models provide a declarative, type-safe way to define external I/O operations in ONEX's 4-node architecture. This guide shows how to adopt these models for HTTP, database, Kafka, and filesystem operations.

## Table of Contents

1. [Overview](#overview)
2. [When to Use Effect Subcontracts](#when-to-use-effect-subcontracts)
3. [Core Concepts](#core-concepts)
4. [Practical Examples](#practical-examples)
   - [HTTP API Call](#example-1-http-api-call)
   - [Database Query](#example-2-database-query)
   - [Kafka Producer](#example-3-kafka-producer)
   - [Mixed Operations with Resilience](#example-4-mixed-operations-with-retry-and-circuit-breaker)
5. [Validation Rules](#validation-rules)
6. [Migration Path](#migration-path)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)

---

## Overview

Effect subcontracts are Pydantic models that declaratively define external I/O operations for EFFECT nodes in the ONEX 4-node architecture. They provide:

- **Type-Safe IO Configs**: Discriminated unions ensure correct configuration per handler type
- **Idempotency-Aware Retries**: Automatic validation prevents retrying non-idempotent operations
- **Transaction Boundaries**: DB-only transactions with isolation level control
- **Circuit Breaker Protection**: Process-local circuit breaker configuration
- **Template Variables**: `${input.*}` and `${env.*}` placeholders for dynamic values

### Architecture Position

```
EFFECT → COMPUTE → REDUCER → ORCHESTRATOR
  ^
  |
  Effect Subcontract defines this layer
```

EFFECT nodes handle all external I/O: API calls, database operations, message queues, and filesystem access. Effect subcontracts provide the contract for these operations.

---

## When to Use Effect Subcontracts

### Use Effect Subcontracts When:

| Scenario | Benefit |
|----------|---------|
| Building new EFFECT nodes | Type-safe configuration from day one |
| Multiple external operations in sequence | Declarative execution with abort/continue modes |
| Need retry/circuit breaker protection | Built-in resilience patterns with idempotency awareness |
| Database transactions across operations | Validated transaction boundaries |
| Code generation or tooling integration | Stable v1.0.0 interface locked for generators |

### Use Manual Effect Implementation When:

| Scenario | Reason |
|----------|--------|
| Custom protocol support | Subcontracts support HTTP, DB, Kafka, Filesystem only |
| Complex conditional logic between operations | Use NodeOrchestrator with workflow coordination |
| Real-time streaming operations | Subcontracts are request-response oriented |
| Operations requiring custom authentication flows | May need lower-level control |

---

## Core Concepts

- [Discriminated Union IO Configs](#1-discriminated-union-io-configs)
- [Idempotency Awareness](#2-idempotency-awareness)
- [Execution Modes](#3-execution-modes)
- [Template Variables](#4-template-variables)
- [Transaction Isolation Levels](#5-transaction-isolation-levels)

### 1. Discriminated Union IO Configs

Each operation uses a handler-specific IO config validated at contract load time:

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelHttpIOConfig,      # HTTP API calls
    ModelDbIOConfig,        # Database operations
    ModelKafkaIOConfig,     # Kafka message production
    ModelFilesystemIOConfig # Filesystem operations
)
```

The `handler_type` field acts as the discriminator, ensuring type-safe configuration.

### 2. Idempotency Awareness

Operations have default idempotency based on handler and operation type:

| Handler | Idempotent Operations | Non-Idempotent Operations |
|---------|----------------------|--------------------------|
| HTTP | GET, HEAD, OPTIONS, PUT, DELETE | POST, PATCH |
| DB | SELECT, UPDATE, DELETE, UPSERT | INSERT |
| Kafka | - | produce (all messages) |
| Filesystem | read, delete | write, move, copy |

**Critical**: Retry is only allowed for idempotent operations. This prevents duplicate side effects.

### 3. Execution Modes

Two execution semantics for multiple operations:

- **`sequential_abort`** (default): Stop on first failure, raise `ModelOnexError`
- **`sequential_continue`**: Run all operations, report all outcomes

### 4. Template Variables

Use `${input.*}` and `${env.*}` placeholders in templates:

```python
url_template="https://api.example.com/users/${input.user_id}"
headers={"Authorization": "Bearer ${env.API_TOKEN}"}
```

### 5. Transaction Isolation Levels

When using `ModelEffectTransactionConfig`, the `isolation_level` field controls how transactions interact with concurrent operations. Choosing the right level is critical for both correctness and performance.

#### Isolation Level Reference

| Level | Use Case | Trade-off | SELECT Retry Allowed |
|-------|----------|-----------|---------------------|
| `read_committed` | Most operations, general CRUD workflows | May see committed changes mid-transaction (non-repeatable reads) | Yes |
| `repeatable_read` | Snapshot consistency needed, reporting queries | Cannot retry SELECT operations; higher lock contention | No |
| `serializable` | Strict ordering required, financial transactions | Performance impact, retry restrictions, highest lock contention | No |

#### Detailed Guidance

**`read_committed`** (Recommended Default)
- Each statement sees only data committed before the statement began
- Allows SELECT retry because each retry gets fresh, consistent data
- Best for typical CRUD operations where snapshot consistency is not required
- Lowest performance overhead

```python
# Good for most operations
transaction=ModelEffectTransactionConfig(
    enabled=True,
    isolation_level="read_committed",  # Default, allows retry
)
```

**`repeatable_read`**
- Transaction sees a snapshot of data as of the transaction start
- SELECT operations within the transaction always return the same result
- Retry is forbidden because retrying would expect a new snapshot but operates on the original one
- Use when you need consistent reads across multiple SELECT operations

```python
# Use for consistent snapshot reads
transaction=ModelEffectTransactionConfig(
    enabled=True,
    isolation_level="repeatable_read",  # No SELECT retry allowed
)
```

**`serializable`**
- Strongest isolation: transactions execute as if they ran sequentially
- Prevents phantom reads, non-repeatable reads, and dirty reads
- Highest performance cost due to lock contention and potential serialization failures
- Retry forbidden for SELECT operations (same reason as `repeatable_read`)
- Use for financial transactions, inventory management, or strict ordering requirements

```python
# Use for critical financial operations
transaction=ModelEffectTransactionConfig(
    enabled=True,
    isolation_level="serializable",  # Strictest, no SELECT retry
)
```

#### SELECT Retry Restriction

When using `repeatable_read` or `serializable` isolation, SELECT operations with retry enabled will be rejected by the `validate_select_retry_in_transaction` validator. This prevents subtle consistency bugs:

```python
# INVALID - Will raise validation error
ModelEffectSubcontract(
    operations=[
        ModelEffectOperation(
            operation_name="read_balance",
            io_config=ModelDbIOConfig(operation="select", ...),
            retry_policy=ModelEffectRetryPolicy(enabled=True),  # FAILS
        ),
    ],
    transaction=ModelEffectTransactionConfig(
        enabled=True,
        isolation_level="repeatable_read",
    ),
)
# Error: "Operation 'read_balance' is a SELECT with retry enabled inside a repeatable_read transaction"
```

**Why?** In snapshot-based isolation, the first SELECT establishes the transaction's view of data. If that SELECT fails and retries, the retry would reset internal state but continue using the original snapshot, leading to potential inconsistencies between what the retry "expects" and what the snapshot "provides."

**Solution**: Either use `read_committed` (where each query sees fresh data), or disable retry for SELECT operations in snapshot-based transactions.

---

## Practical Examples

### Example 1: HTTP API Call

Fetch user data from an external API with retry and circuit breaker protection.

```python
from uuid import uuid4

from omnibase_core.models.contracts.subcontracts import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelHttpIOConfig,
    ModelEffectRetryPolicy,
    ModelEffectCircuitBreaker,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


def create_user_api_subcontract(user_id: str) -> ModelEffectSubcontract:
    """Create a subcontract to fetch user data from external API."""

    return ModelEffectSubcontract(
        subcontract_name="fetch_user_data",
        description="Fetch user profile from external user service",

        # Single operation - GET is idempotent, retry is safe
        operations=[
            ModelEffectOperation(
                operation_name="get_user_profile",
                description="Fetch user profile by ID",
                # GET is idempotent by default, no need to set explicitly
                io_config=ModelHttpIOConfig(
                    handler_type=EnumEffectHandlerType.HTTP,
                    url_template="https://api.userservice.com/v1/users/${input.user_id}",
                    method="GET",
                    headers={
                        "Authorization": "Bearer ${env.USER_SERVICE_TOKEN}",
                        "Accept": "application/json",
                        "X-Correlation-ID": "${input.correlation_id}",
                    },
                    timeout_ms=5000,
                    verify_ssl=True,
                ),
                # Override default retry policy for this operation
                retry_policy=ModelEffectRetryPolicy(
                    enabled=True,
                    max_retries=3,
                    backoff_strategy="exponential",
                    base_delay_ms=1000,
                    retryable_status_codes=[429, 500, 502, 503, 504],
                ),
                # Enable circuit breaker for external service protection
                circuit_breaker=ModelEffectCircuitBreaker(
                    enabled=True,
                    failure_threshold=5,
                    success_threshold=2,
                    timeout_ms=60000,
                ),
                operation_timeout_ms=30000,  # Total timeout including retries
            )
        ],

        # Observability
        observability=ModelEffectObservability(
            emit_metrics=True,
            log_level="INFO",
        ),

        correlation_id=uuid4(),
    )


# Usage in an Effect node
async def process_user_request(user_id: str) -> dict:
    """Process user request using effect subcontract."""
    subcontract = create_user_api_subcontract(user_id)

    # Execute through effect runtime (implementation depends on your infrastructure)
    result = await effect_runtime.execute(
        subcontract,
        input_data={"user_id": user_id, "correlation_id": str(uuid4())}
    )

    return result
```

**Key Points**:
- GET requests are idempotent by default, so retry is safe
- Circuit breaker protects against cascading failures
- Template variables (`${input.*}`, `${env.*}`) enable dynamic configuration

---

### Example 2: Database Query

Execute a parameterized database query with transaction support.

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelDbIOConfig,
    ModelEffectTransactionConfig,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


def create_order_processing_subcontract() -> ModelEffectSubcontract:
    """
    Create a subcontract to process an order with transactional semantics.

    This example demonstrates:
    - Multiple DB operations in a single transaction
    - Parameterized queries with $N placeholders
    - Proper isolation level selection
    """

    return ModelEffectSubcontract(
        subcontract_name="process_order",
        description="Process order with inventory update in transaction",

        operations=[
            # Operation 1: Check inventory (SELECT is idempotent)
            ModelEffectOperation(
                operation_name="check_inventory",
                description="Check product availability",
                io_config=ModelDbIOConfig(
                    handler_type=EnumEffectHandlerType.DB,
                    operation="select",
                    connection_name="primary_db",
                    query_template="""
                        SELECT product_id, quantity_available
                        FROM inventory
                        WHERE product_id = $1 AND quantity_available >= $2
                        FOR UPDATE
                    """,
                    query_params=["${input.product_id}", "${input.quantity}"],
                    timeout_ms=5000,
                    read_only=False,  # FOR UPDATE requires write mode
                ),
                # Disable retry for SELECT in transaction (snapshot semantics)
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),

            # Operation 2: Create order (INSERT is NOT idempotent - no retry)
            ModelEffectOperation(
                operation_name="create_order",
                description="Insert new order record",
                idempotent=False,  # Non-idempotent by design - INSERT creates new row each time
                io_config=ModelDbIOConfig(
                    handler_type=EnumEffectHandlerType.DB,
                    operation="insert",
                    connection_name="primary_db",
                    query_template="""
                        INSERT INTO orders (customer_id, product_id, quantity, status, created_at)
                        VALUES ($1, $2, $3, 'pending', NOW())
                        RETURNING order_id
                    """,
                    query_params=[
                        "${input.customer_id}",
                        "${input.product_id}",
                        "${input.quantity}",
                    ],
                    timeout_ms=5000,
                ),
                # No retry for non-idempotent operation
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),

            # Operation 3: Update inventory (UPDATE is idempotent)
            ModelEffectOperation(
                operation_name="decrement_inventory",
                description="Reduce inventory quantity",
                idempotent=True,  # Same decrement produces same result
                io_config=ModelDbIOConfig(
                    handler_type=EnumEffectHandlerType.DB,
                    operation="update",
                    connection_name="primary_db",
                    query_template="""
                        UPDATE inventory
                        SET quantity_available = quantity_available - $1,
                            updated_at = NOW()
                        WHERE product_id = $2
                    """,
                    query_params=["${input.quantity}", "${input.product_id}"],
                    timeout_ms=5000,
                ),
                # Retry is safe for idempotent UPDATE
                retry_policy=ModelEffectRetryPolicy(
                    enabled=True,
                    max_retries=2,
                    backoff_strategy="fixed",
                    base_delay_ms=500,
                ),
            ),
        ],

        # Transaction wraps all operations
        transaction=ModelEffectTransactionConfig(
            enabled=True,
            isolation_level="read_committed",  # Allows retry for UPDATE
            rollback_on_error=True,
            timeout_ms=30000,
        ),

        # Abort on first failure - ensures atomicity
        execution_mode="sequential_abort",
    )
```

**Key Points**:
- All operations use the same `connection_name` (required for transactions)
- INSERT has retry disabled (non-idempotent)
- SELECT has retry disabled in transaction (snapshot semantics)
- UPDATE can have retry enabled (idempotent operation)
- `FOR UPDATE` requires `read_only=False`

---

### Example 3: Kafka Producer

Publish events to Kafka with delivery guarantees.

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelKafkaIOConfig,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


def create_event_publishing_subcontract() -> ModelEffectSubcontract:
    """
    Create a subcontract to publish user events to Kafka.

    This example demonstrates:
    - Kafka message production with acks configuration
    - Partition key for message ordering
    - Compression for efficiency
    """

    return ModelEffectSubcontract(
        subcontract_name="publish_user_events",
        description="Publish user activity events to Kafka",

        operations=[
            ModelEffectOperation(
                operation_name="publish_activity_event",
                description="Publish user activity to event stream",
                # Kafka produce is NOT idempotent by default
                # Mark as idempotent only if using Kafka's idempotent producer
                idempotent=False,
                io_config=ModelKafkaIOConfig(
                    handler_type=EnumEffectHandlerType.KAFKA,
                    topic="user-activity-events",
                    payload_template="""{
                        "event_type": "${input.event_type}",
                        "user_id": "${input.user_id}",
                        "action": "${input.action}",
                        "metadata": ${input.metadata_json},
                        "timestamp": "${input.timestamp}",
                        "correlation_id": "${input.correlation_id}"
                    }""",
                    # Partition by user_id ensures ordering per user
                    partition_key_template="${input.user_id}",
                    headers={
                        "content-type": "application/json",
                        "event-version": "1.0",
                        "source-service": "user-service",
                    },
                    # Strong delivery guarantee
                    acks="all",  # Wait for all replicas
                    compression="snappy",  # Good balance of speed/compression
                    timeout_ms=10000,
                ),
                # No retry for non-idempotent Kafka produce
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ],

        execution_mode="sequential_abort",
    )


def create_metrics_publishing_subcontract() -> ModelEffectSubcontract:
    """
    Example with fire-and-forget (acks=0) for high-throughput metrics.

    WARNING: Messages may be lost with acks=0. Use only for non-critical data.
    """

    return ModelEffectSubcontract(
        subcontract_name="publish_metrics",
        description="Publish metrics to Kafka (best-effort)",

        operations=[
            ModelEffectOperation(
                operation_name="publish_metric",
                description="Publish metric data point",
                idempotent=False,
                io_config=ModelKafkaIOConfig(
                    handler_type=EnumEffectHandlerType.KAFKA,
                    topic="service-metrics",
                    payload_template="""{
                        "metric_name": "${input.name}",
                        "value": ${input.value},
                        "tags": ${input.tags_json},
                        "timestamp_ms": ${input.timestamp_ms}
                    }""",
                    # Fire-and-forget - requires explicit acknowledgment
                    acks="0",
                    acks_zero_acknowledged=True,  # REQUIRED for acks=0
                    compression="lz4",  # Fast compression for high throughput
                    timeout_ms=5000,
                ),
            ),
        ],

        execution_mode="sequential_continue",  # Continue on failure for metrics
    )
```

**Key Points**:
- `acks="all"` provides strongest delivery guarantee
- `acks="0"` requires `acks_zero_acknowledged=True` (explicit opt-in)
- Partition key ensures message ordering per key
- Kafka produce is non-idempotent unless using idempotent producer config

---

### Example 4: Mixed Operations with Retry and Circuit Breaker

Process data through multiple external systems with resilience patterns.

```python
from omnibase_core.models.contracts.subcontracts import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelHttpIOConfig,
    ModelDbIOConfig,
    ModelKafkaIOConfig,
    ModelFilesystemIOConfig,
    ModelEffectRetryPolicy,
    ModelEffectCircuitBreaker,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


def create_data_ingestion_subcontract() -> ModelEffectSubcontract:
    """
    Create a subcontract for data ingestion pipeline.

    Flow:
    1. Fetch data from external API (HTTP GET - idempotent)
    2. Write raw data to archive (Filesystem - non-idempotent)
    3. Store processed data in database (DB INSERT - non-idempotent)
    4. Publish event notification (Kafka - non-idempotent)

    Note: Transaction NOT enabled because operations span multiple handler types.
    """

    return ModelEffectSubcontract(
        subcontract_name="data_ingestion_pipeline",
        description="Ingest data from external source, store, and notify",

        # Global defaults for retry and circuit breaker
        default_retry_policy=ModelEffectRetryPolicy(
            enabled=True,
            max_retries=3,
            backoff_strategy="exponential",
            base_delay_ms=1000,
        ),
        default_circuit_breaker=ModelEffectCircuitBreaker(
            enabled=True,
            failure_threshold=5,
            timeout_ms=60000,
        ),

        operations=[
            # Step 1: Fetch external data (idempotent GET)
            ModelEffectOperation(
                operation_name="fetch_external_data",
                description="Fetch data from external data provider",
                # GET is idempotent - default retry applies
                io_config=ModelHttpIOConfig(
                    handler_type=EnumEffectHandlerType.HTTP,
                    url_template="https://data-provider.com/api/v2/data/${input.data_id}",
                    method="GET",
                    headers={
                        "Authorization": "Bearer ${env.DATA_PROVIDER_TOKEN}",
                        "Accept": "application/json",
                    },
                    timeout_ms=10000,
                ),
                # Uses default retry policy (inherited from subcontract)
                # Uses default circuit breaker (inherited from subcontract)
            ),

            # Step 2: Archive raw data (non-idempotent write)
            ModelEffectOperation(
                operation_name="archive_raw_data",
                description="Write raw data to archive filesystem",
                idempotent=False,  # Write may corrupt on retry with different content
                io_config=ModelFilesystemIOConfig(
                    handler_type=EnumEffectHandlerType.FILESYSTEM,
                    file_path_template="/data/archive/${input.date}/${input.data_id}.json",
                    operation="write",
                    atomic=True,  # Write to temp, then rename
                    create_dirs=True,
                    encoding="utf-8",
                    timeout_ms=5000,
                ),
                # Override: No retry for non-idempotent filesystem write
                retry_policy=ModelEffectRetryPolicy(enabled=False),
                # No circuit breaker for local filesystem
                circuit_breaker=ModelEffectCircuitBreaker(enabled=False),
            ),

            # Step 3: Store in database (non-idempotent insert)
            ModelEffectOperation(
                operation_name="store_processed_data",
                description="Insert processed data into database",
                idempotent=False,  # INSERT creates new row
                io_config=ModelDbIOConfig(
                    handler_type=EnumEffectHandlerType.DB,
                    operation="insert",
                    connection_name="analytics_db",
                    query_template="""
                        INSERT INTO ingested_data
                        (data_id, source, content, ingested_at)
                        VALUES ($1, $2, $3, NOW())
                    """,
                    query_params=[
                        "${input.data_id}",
                        "${input.source}",
                        "${output.fetch_external_data.body}",  # Reference previous step
                    ],
                    timeout_ms=5000,
                ),
                # Override: No retry for INSERT
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),

            # Step 4: Publish notification (non-idempotent produce)
            ModelEffectOperation(
                operation_name="publish_ingestion_event",
                description="Notify downstream systems of new data",
                idempotent=False,
                io_config=ModelKafkaIOConfig(
                    handler_type=EnumEffectHandlerType.KAFKA,
                    topic="data-ingestion-events",
                    payload_template="""{
                        "event_type": "data_ingested",
                        "data_id": "${input.data_id}",
                        "source": "${input.source}",
                        "timestamp": "${input.timestamp}"
                    }""",
                    partition_key_template="${input.source}",
                    acks="all",
                    timeout_ms=5000,
                ),
                # Override: No retry for Kafka produce
                retry_policy=ModelEffectRetryPolicy(enabled=False),
            ),
        ],

        # Abort on first failure - partial ingestion is incomplete
        execution_mode="sequential_abort",

        # Transaction NOT enabled - mixed handler types
        # transaction=ModelEffectTransactionConfig(enabled=False),  # Default
    )
```

**Key Points**:
- Default retry/circuit breaker inherited by operations unless overridden
- Only HTTP GET uses retry (idempotent)
- Non-idempotent operations (write, insert, produce) have retry disabled
- `sequential_abort` ensures no partial state on failure
- Transaction disabled because operations span HTTP, filesystem, DB, and Kafka

---

## Validation Rules

Effect subcontracts enforce several validation rules at construction time. Understanding these rules helps avoid runtime errors.

### Rule 1: Transaction Scope Validation

**Rule**: Transactions are only valid for DB operations using the same connection.

```python
# INVALID - Mixed handler types in transaction
ModelEffectSubcontract(
    subcontract_name="invalid_mixed_transaction",
    operations=[
        ModelEffectOperation(
            operation_name="http_call",
            io_config=ModelHttpIOConfig(method="GET", url_template="..."),
        ),
        ModelEffectOperation(
            operation_name="db_query",
            io_config=ModelDbIOConfig(operation="select", connection_name="db1", ...),
        ),
    ],
    transaction=ModelEffectTransactionConfig(enabled=True),  # FAILS
)
# Error: "Transaction enabled but found non-DB operations: ['http_call']"
```

```python
# INVALID - Different connections in transaction
ModelEffectSubcontract(
    subcontract_name="invalid_multi_connection",
    operations=[
        ModelEffectOperation(
            operation_name="query_db1",
            io_config=ModelDbIOConfig(operation="select", connection_name="primary_db", ...),
        ),
        ModelEffectOperation(
            operation_name="query_db2",
            io_config=ModelDbIOConfig(operation="select", connection_name="replica_db", ...),
        ),
    ],
    transaction=ModelEffectTransactionConfig(enabled=True),  # FAILS
)
# Error: "Transaction enabled but operations use different connections: {'primary_db', 'replica_db'}"
```

**Rationale**: Database transactions are connection-scoped. Cross-connection or cross-system transactions require distributed transaction protocols (2PC) which are not supported in v1.0.

### Rule 2: Idempotency + Retry Validation

**Rule**: Cannot retry non-idempotent operations.

```python
# INVALID - Retry enabled for non-idempotent POST
ModelEffectOperation(
    operation_name="create_resource",
    io_config=ModelHttpIOConfig(method="POST", url_template="...", body_template="{}"),
    retry_policy=ModelEffectRetryPolicy(enabled=True, max_retries=3),  # FAILS
)
# Error: "Operation 'create_resource' is not idempotent but has retry enabled"
```

```python
# VALID - Explicitly mark as idempotent if you know it is
ModelEffectOperation(
    operation_name="upsert_resource",
    idempotent=True,  # Override: this POST is actually idempotent (upsert)
    io_config=ModelHttpIOConfig(method="POST", url_template="...", body_template="{}"),
    retry_policy=ModelEffectRetryPolicy(enabled=True, max_retries=3),  # OK
)
```

**Rationale**: Retrying non-idempotent operations can cause duplicate side effects (duplicate orders, duplicate messages, etc.).

### Rule 3: SELECT Retry in Transaction Validation

**Rule**: Cannot retry SELECT inside repeatable_read or serializable transactions.

```python
# INVALID - Retry SELECT in repeatable_read transaction
ModelEffectSubcontract(
    subcontract_name="invalid_select_retry",
    operations=[
        ModelEffectOperation(
            operation_name="select_data",
            io_config=ModelDbIOConfig(operation="select", connection_name="db", ...),
            retry_policy=ModelEffectRetryPolicy(enabled=True),  # FAILS
        ),
    ],
    transaction=ModelEffectTransactionConfig(
        enabled=True,
        isolation_level="repeatable_read",  # Snapshot-sensitive
    ),
)
# Error: "Operation 'select_data' is a SELECT with retry enabled inside a repeatable_read transaction"
```

**Rationale**: In repeatable_read/serializable, the first SELECT establishes the transaction snapshot. Retrying SELECTs can cause subtle consistency bugs because retry resets internal state but doesn't reset the snapshot.

**Solution**: Use `read_committed` isolation (where each query sees fresh data) or disable retry for SELECT operations.

### Rule 4: No Raw Operations in Transaction

**Rule**: Raw DB operations are forbidden in transactions.

```python
# INVALID - Raw operation in transaction
ModelEffectSubcontract(
    subcontract_name="invalid_raw_in_transaction",
    operations=[
        ModelEffectOperation(
            operation_name="call_stored_proc",
            io_config=ModelDbIOConfig(
                operation="raw",  # FAILS in transaction
                connection_name="db",
                query_template="CALL process_data($1)",
                query_params=["${input.data_id}"],
            ),
        ),
    ],
    transaction=ModelEffectTransactionConfig(enabled=True),  # FAILS
)
# Error: "Raw DB operations not allowed inside transactions: ['call_stored_proc']"
```

**Rationale**: Raw operations (stored procedures, multi-statement batches) may issue their own COMMIT/ROLLBACK or have unpredictable side effects that break transactional semantics.

### Rule 5: Kafka acks=0 Opt-in

**Rule**: Fire-and-forget Kafka mode requires explicit acknowledgment.

```python
# INVALID - acks=0 without acknowledgment
ModelKafkaIOConfig(
    topic="events",
    payload_template="{}",
    acks="0",  # Fire-and-forget
    # Missing: acks_zero_acknowledged=True  # FAILS
)
# Error: "Kafka acks=0 requires explicit opt-in. Set acks_zero_acknowledged=True"
```

**Rationale**: `acks=0` provides no delivery guarantee and messages may be silently lost. Explicit opt-in ensures awareness of this risk.

---

## Migration Path

### Migrating from Manual Effect Node Implementation

#### Before (Manual Implementation)

```python
from omnibase_core.nodes import NodeEffect, ModelEffectInput, ModelEffectOutput
import httpx


class NodeUserServiceEffect(NodeEffect):
    """Effect node with manual HTTP implementation."""

    def __init__(self, container):
        super().__init__(container)
        self.http_client = httpx.AsyncClient()

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """Manual HTTP call with retry logic."""
        user_id = input_data.operation_data["user_id"]
        url = f"https://api.userservice.com/v1/users/{user_id}"

        # Manual retry loop
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = await self.http_client.get(
                    url,
                    headers={"Authorization": f"Bearer {os.environ['API_TOKEN']}"},
                    timeout=5.0,
                )
                response.raise_for_status()
                return ModelEffectOutput(
                    success=True,
                    result=response.json(),
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                raise
            except httpx.RequestError:
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

        return ModelEffectOutput(success=False, error="Max retries exceeded")
```

**Problems**:
- Manual retry logic scattered in code
- No idempotency validation
- No circuit breaker protection
- Hard to test resilience patterns
- Configuration buried in code

#### After (Effect Subcontract)

```python
from omnibase_core.nodes import NodeEffect, ModelEffectInput, ModelEffectOutput
from omnibase_core.models.contracts.subcontracts import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelHttpIOConfig,
    ModelEffectRetryPolicy,
    ModelEffectCircuitBreaker,
)


class NodeUserServiceEffect(NodeEffect):
    """Effect node with declarative subcontract."""

    @property
    def effect_subcontract(self) -> ModelEffectSubcontract:
        """Define effect operations declaratively."""
        return ModelEffectSubcontract(
            subcontract_name="user_service_operations",
            operations=[
                ModelEffectOperation(
                    operation_name="get_user",
                    io_config=ModelHttpIOConfig(
                        url_template="https://api.userservice.com/v1/users/${input.user_id}",
                        method="GET",
                        headers={"Authorization": "Bearer ${env.API_TOKEN}"},
                        timeout_ms=5000,
                    ),
                    retry_policy=ModelEffectRetryPolicy(
                        enabled=True,
                        max_retries=3,
                        backoff_strategy="exponential",
                        base_delay_ms=1000,
                    ),
                    circuit_breaker=ModelEffectCircuitBreaker(
                        enabled=True,
                        failure_threshold=5,
                    ),
                ),
            ],
        )

    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        """Execute subcontract - runtime handles retry/circuit breaker."""
        return await self.execute_subcontract(input_data)
```

**Benefits**:
- Declarative retry configuration
- Automatic idempotency validation
- Built-in circuit breaker support
- Testable configuration
- Clear separation of concerns

### Migration Checklist

1. **Identify effect operations** in existing node
2. **Determine handler types** (HTTP, DB, Kafka, Filesystem)
3. **Assess idempotency** for each operation
4. **Configure retry policies** only for idempotent operations
5. **Add circuit breakers** for external service calls
6. **Define transaction boundaries** for DB-only workflows
7. **Write tests** validating subcontract behavior
8. **Gradually migrate** operations to subcontract

---

## Best Practices

### 1. Always Assess Idempotency First

Before enabling retry, ask: "Is this operation safe to repeat?"

```python
# Ask these questions:
# - Will retrying create duplicates? (INSERT, POST, Kafka produce)
# - Will retrying corrupt state? (Filesystem write with different content)
# - Will retrying cause inconsistency? (Non-atomic operations)
```

### 2. Use Appropriate Execution Mode

```python
# Use sequential_abort when:
# - Operations are dependent (step 2 needs step 1 result)
# - Partial completion is invalid (order processing)
# - Atomicity matters
execution_mode="sequential_abort"

# Use sequential_continue when:
# - Operations are independent (batch notifications)
# - Partial completion is acceptable (metrics collection)
# - Need to know all failures
execution_mode="sequential_continue"
```

### 3. Scope Transactions Narrowly

```python
# GOOD - Narrow transaction scope
operations=[
    ModelEffectOperation(operation_name="non_transactional_read", ...),  # Outside transaction
]
# Create separate subcontract for transactional operations

# AVOID - Large transaction scope
# Don't wrap many operations in one transaction if they don't need atomicity
```

### 4. Configure Circuit Breakers for External Services

```python
# Always enable circuit breakers for:
# - External APIs (third-party services)
# - Remote databases (cross-datacenter)
# - Shared infrastructure (message queues)

# Consider disabling for:
# - Local filesystem operations
# - In-process computations
circuit_breaker=ModelEffectCircuitBreaker(
    enabled=True,  # Enable for external services
    failure_threshold=5,
    timeout_ms=60000,
)
```

### 5. Use Parameterized Queries

```python
# GOOD - Parameterized query (SQL injection safe)
query_template="SELECT * FROM users WHERE id = $1 AND status = $2"
query_params=["${input.user_id}", "${input.status}"]

# BAD - String interpolation in query (SQL injection risk)
query_template="SELECT * FROM users WHERE id = '${input.user_id}'"  # VULNERABLE
```

---

## Troubleshooting

### Error: "Operation 'X' is not idempotent but has retry enabled"

**Cause**: Attempting to retry a non-idempotent operation.

**Solution**:
1. Disable retry: `retry_policy=ModelEffectRetryPolicy(enabled=False)`
2. OR mark operation as idempotent if it truly is: `idempotent=True`

### Error: "Transaction enabled but found non-DB operations"

**Cause**: Transaction spans multiple handler types.

**Solution**: Move non-DB operations to separate subcontract, or disable transaction.

### Error: "query_params has N items but query_template requires M"

**Cause**: Mismatch between `$N` placeholders and `query_params` count.

**Solution**: Ensure `query_params` list length matches highest placeholder number.

```python
# Placeholders: $1, $2, $3 → need 3 params
query_template="SELECT * FROM t WHERE a = $1 AND b = $2 AND c = $3"
query_params=["value1", "value2", "value3"]  # Must have exactly 3
```

### Warning: "verify_ssl=False disables SSL certificate validation"

**Cause**: SSL verification disabled (security risk).

**Solution**: Only disable for development/testing. Always enable in production.

### Error: "Kafka acks=0 requires explicit opt-in"

**Cause**: Using fire-and-forget mode without acknowledgment.

**Solution**: Add `acks_zero_acknowledged=True` if you accept message loss risk.

---

## API Reference

### Primary Models

| Model | Purpose | Import |
|-------|---------|--------|
| `ModelEffectSubcontract` | Root container for effect operations | `from omnibase_core.models.contracts.subcontracts import ModelEffectSubcontract` |
| `ModelEffectOperation` | Single effect operation definition | `from omnibase_core.models.contracts.subcontracts import ModelEffectOperation` |

### IO Config Models

| Model | Handler Type | Import |
|-------|-------------|--------|
| `ModelHttpIOConfig` | HTTP API calls | `from omnibase_core.models.contracts.subcontracts import ModelHttpIOConfig` |
| `ModelDbIOConfig` | Database operations | `from omnibase_core.models.contracts.subcontracts import ModelDbIOConfig` |
| `ModelKafkaIOConfig` | Kafka message production | `from omnibase_core.models.contracts.subcontracts import ModelKafkaIOConfig` |
| `ModelFilesystemIOConfig` | Filesystem operations | `from omnibase_core.models.contracts.subcontracts import ModelFilesystemIOConfig` |

### Resilience Models

| Model | Purpose | Import |
|-------|---------|--------|
| `ModelEffectRetryPolicy` | Retry configuration | `from omnibase_core.models.contracts.subcontracts import ModelEffectRetryPolicy` |
| `ModelEffectCircuitBreaker` | Circuit breaker configuration | `from omnibase_core.models.contracts.subcontracts import ModelEffectCircuitBreaker` |
| `ModelEffectTransactionConfig` | DB transaction settings | `from omnibase_core.models.contracts.subcontracts import ModelEffectTransactionConfig` |

### Constants

| Constant | Purpose | Import |
|----------|---------|--------|
| `IDEMPOTENCY_DEFAULTS` | Default idempotency by handler/operation | `from omnibase_core.constants.constants_effect_idempotency import IDEMPOTENCY_DEFAULTS` |

---

## Additional Resources

- **Node Building Guide**: [`docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md`](node-building/04_EFFECT_NODE_TUTORIAL.md)
- **ONEX Four-Node Architecture**: [`docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md`](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- **Migration to Declarative Nodes**: [`docs/guides/MIGRATING_TO_DECLARATIVE_NODES.md`](MIGRATING_TO_DECLARATIVE_NODES.md)
- **Error Handling Best Practices**: [`docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)

---

**Last Updated**: 2025-12-09
**Version**: 1.0.0
**Maintainer**: ONEX Framework Team
