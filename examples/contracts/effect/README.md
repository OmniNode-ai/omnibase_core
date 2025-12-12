# NodeEffect Contract Examples

This directory contains comprehensive example YAML contracts for NodeEffect operations in the ONEX framework. These examples demonstrate how to define external I/O operations declaratively using the v1.1.0 contract schema.

## Overview

NodeEffect is the ONEX node type responsible for **external interactions** (I/O operations):
- HTTP REST API calls
- Database queries (SQL)
- Message queue operations (Kafka)
- Filesystem operations
- External service integrations

All examples follow the **contract-driven pattern**, where the YAML contract defines the complete operation logic, eliminating boilerplate code from node implementations.

## Examples

### 1. HTTP API Calls (`http_api_call.yaml`)

**Use Case**: User Management API Integration

**Demonstrates**:
- HTTP POST/GET/PATCH methods
- Request body templating with variable substitution
- Response field extraction using JSONPath
- Retry policy with exponential backoff and jitter
- Success code validation
- Request/response observability
- Idempotency headers

**Operations**:
1. `create_user` - POST to create user resource
2. `get_user` - GET to retrieve user data
3. `update_user_status` - PATCH to update user fields

**Key Features**:
```yaml
# NOTE: io_config uses flat structure (no http_config wrapper)
io_config:
  handler_type: http
  method: POST
  url_template: "https://api.example.com/v1/users"
  body_template: |
    {
      "email": "${input.email}",
      "display_name": "${input.display_name}"
    }

# Retry policy matching ModelEffectRetryPolicy schema
retry_policy:
  max_retries: 3
  backoff_strategy: exponential
  base_delay_ms: 1000
  max_delay_ms: 10000
  jitter_factor: 0.1

response_handling:
  extract_fields:
    user_id: "$.id"
    email: "$.email"
```

---

### 2. Database Queries (`db_query.yaml`)

**Use Case**: User Profile Database Operations

**Demonstrates**:
- Parameterized SELECT queries (SQL injection prevention)
- INSERT with transaction support and RETURNING clause
- UPDATE with optimistic locking (version-based)
- Query parameter binding from input data
- Transaction isolation levels
- Deadlock retry handling
- Connection pooling configuration

**Operations**:
1. `select_user_by_email` - Parameterized SELECT with safe binding
2. `insert_user` - Transactional INSERT with RETURNING
3. `update_user_status` - UPDATE with version checking
4. `soft_delete_user` - Soft delete using UPDATE

**Key Features**:
```yaml
# NOTE: io_config uses flat structure (no db_config wrapper)
io_config:
  handler_type: db
  operation: select
  connection_name: "user_db_pool"
  query_template: |
    SELECT id, email, display_name
    FROM users
    WHERE email = $1
    LIMIT 1

  # Query params bind to $1, $2, etc. in order
  query_params:
    - "${input.email}"

  timeout_ms: 5000
  read_only: true

# Retry policy matching ModelEffectRetryPolicy schema
# NOTE: retryable_error_codes is not part of ModelEffectRetryPolicy
# but can be extended by handlers
retry_policy:
  max_retries: 4
  backoff_strategy: exponential
  base_delay_ms: 100
  max_delay_ms: 2000
  jitter_factor: 0.1
```

---

### 3. Kafka Message Production (`kafka_produce.yaml`)

**Use Case**: Event-Driven User Activity Tracking

**Demonstrates**:
- Message production to multiple topics
- Partition key templating for consistent hashing
- Message headers for tracing and correlation
- Delivery guarantees (acks=all, acks=1, acks=0)
- Compression (snappy, lz4, gzip, zstd)
- Idempotent producer configuration
- Batching for throughput optimization
- Security configuration (SASL_SSL)

**Operations**:
1. `publish_user_registration` - User registration events with acks=all
2. `publish_user_activity` - High-throughput activity events with acks=1
3. `publish_audit_log` - Audit logs with maximum durability

**Key Features**:
```yaml
# NOTE: io_config uses flat structure (no kafka_config wrapper)
io_config:
  handler_type: kafka
  topic: "user.events.registration"
  partition_key_template: "${input.user_id}"
  payload_template: |
    {
      "event_type": "user.registered",
      "user_id": "${input.user_id}",
      "timestamp": "${input.timestamp}"
    }
  headers:
    X-Correlation-ID: "${input.correlation_id}"

  # Acknowledgment level: "0", "1", or "all"
  acks: "all"

  # Compression: none, gzip, snappy, lz4, zstd
  compression: snappy

  timeout_ms: 30000
```

---

### 4. Filesystem Operations (`filesystem_operations.yaml`)

**Use Case**: Document Management System

**Demonstrates**:
- Atomic file writes (write-then-move pattern)
- File reading with encoding detection and size limits
- Directory creation with parent support
- File move/rename with conflict handling
- Directory listing with pattern matching and filtering
- Safe file deletion with validation
- Path templating from input data
- Checksum verification
- Backup file management

**Operations**:
1. `create_user_directory` - Create directory structure with permissions
2. `write_document` - Atomic file write with checksum verification
3. `read_document` - File read with encoding detection
4. `archive_document` - Move file to archive location
5. `list_user_documents` - Directory listing with filtering
6. `delete_document` - Safe deletion with metadata validation

**Key Features**:
```yaml
# NOTE: io_config uses flat structure (no filesystem_config wrapper)
io_config:
  handler_type: filesystem
  operation: write
  file_path_template: "/data/documents/${input.tenant_id}/users/${input.user_id}/${input.document_id}.json"

  # Atomic write (write to temp, then rename)
  atomic: true

  # Create parent directories if needed
  create_dirs: true

  # File encoding
  encoding: "utf-8"

  # File permission mode
  mode: "0644"

  timeout_ms: 10000
```

---

### 5. Resilient Effect (`resilient_effect.yaml`)

**Use Case**: Payment Processing with Maximum Resilience

**Demonstrates**:
- **Circuit breaker** with failure threshold and timeout
- **Exponential backoff** with jitter for retries
- **Operation-level and handler-level timeouts**
- **Idempotent operations** with deduplication
- **Request/response tracing** and correlation
- **Comprehensive metrics and logging**
- **Polling for async operations**
- **Rate limiting** and throttling
- **Multi-handler coordination** (HTTP → DB → Kafka)

**Operations**:
1. `process_payment` - HTTP payment with full resilience
2. `verify_payment_status` - HTTP GET with polling
3. `record_payment_transaction` - Database INSERT with transaction
4. `publish_payment_event` - Kafka publish with guaranteed delivery

**Key Features**:
```yaml
# Circuit breaker configuration matching ModelEffectCircuitBreaker schema
circuit_breaker:
  enabled: true
  failure_threshold: 5
  success_threshold: 2
  timeout_ms: 30000
  half_open_requests: 2

# Retry policy matching ModelEffectRetryPolicy schema
retry_policy:
  max_retries: 4
  backoff_strategy: exponential
  base_delay_ms: 1000
  max_delay_ms: 10000
  jitter_factor: 0.1

# Observability configuration matching ModelEffectObservability schema
observability:
  log_request: true
  log_response: true
  emit_metrics: true
  trace_propagation: true
```

---

## Contract Structure

All effect contracts follow this structure:

```yaml
effect_operations:
  # Schema version (ModelSemVer format)
  version: {major: 1, minor: 0, patch: 0}

  # Required: Unique subcontract name (matches ModelEffectSubcontract.subcontract_name)
  subcontract_name: "example_effect"

  # How operations are executed (see execution_mode in ModelEffectSubcontract)
  # "sequential_abort" (default): Stop on first failure, raise error
  # "sequential_continue": Run all operations, report all outcomes
  execution_mode: sequential_abort

  operations:
    - operation_name: example_operation
      description: "What this operation does"

      # Handler configuration (HTTP, DB, Kafka, Filesystem)
      # NOTE: Uses flat structure - fields are direct children of io_config
      # (no http_config, db_config, kafka_config, or filesystem_config wrapper)
      io_config:
        handler_type: http  # or db, kafka, filesystem
        method: POST
        url_template: "https://api.example.com/resource"
        body_template: '{"key": "${input.value}"}'
        timeout_ms: 5000

      # Retry configuration matching ModelEffectRetryPolicy schema
      retry_policy:
        enabled: true                 # Whether retry is enabled (default: true)
        max_retries: 3
        backoff_strategy: exponential
        base_delay_ms: 1000
        max_delay_ms: 10000
        jitter_factor: 0.1

      # Circuit breaker (optional) matching ModelEffectCircuitBreaker schema
      circuit_breaker:
        enabled: true
        failure_threshold: 5
        success_threshold: 2
        timeout_ms: 60000
        half_open_requests: 3         # Default: 3 (range: 1-10)

      # Response handling matching ModelEffectResponseHandling schema
      response_handling:
        success_codes: [200, 201]
        extract_fields:
          result_id: "$.id"
        fail_on_empty: false
        extraction_engine: jsonpath

      # Observability matching ModelEffectObservability schema
      observability:
        log_request: true
        log_response: true
        emit_metrics: true
        trace_propagation: true

metadata:
  version: {major: 1, minor: 0, patch: 0}
  author: "ONEX Framework Team"
  tags: [effect, example]
```

## Variable Templating

All examples use `${variable_name}` syntax for substituting values from `ModelEffectInput.operation_data`:

```yaml
# In contract YAML:
url: "https://api.example.com/users/${user_id}"
body_template: |
  {
    "email": "${email}",
    "name": "${display_name}"
  }

# In Python code:
input_data = ModelEffectInput(
    operation_data={
        "user_id": "usr_12345",
        "email": "john@example.com",
        "display_name": "John Smith"
    }
)
```

## Usage Pattern

### 1. Load Contract

```python
import yaml

with open("examples/contracts/effect/http_api_call.yaml") as f:
    contract_data = yaml.safe_load(f)
```

### 2. Create Node (Minimal Code)

```python
from omnibase_core.nodes import NodeEffect

class NodeUserApiEffect(NodeEffect):
    pass  # All logic driven by contract
```

### 3. Initialize with Container

```python
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

container = ModelONEXContainer()
node = NodeUserApiEffect(container, contract=contract_data)
```

### 4. Execute Operations

```python
import os
from omnibase_core.models import ModelEffectInput

# NOTE: Load sensitive values from environment, never hardcode tokens
input_data = ModelEffectInput(
    operation_data={
        "email": "john.smith@example.com",
        "display_name": "John Smith",
        "auth_token": os.environ.get("API_AUTH_TOKEN"),  # Load from secure env
    }
)

result = await node.process(input_data)
print(result.result_data["operations"]["create_user"]["extracted_fields"]["user_id"])
```

## Handler Types

| Handler | Purpose | Example Use Cases |
|---------|---------|-------------------|
| **HTTP** | REST APIs, webhooks | User management, payment processing, external services |
| **DB** | Database operations | CRUD operations, transactions, queries |
| **Kafka** | Message queuing | Event streaming, audit logs, async notifications |
| **Filesystem** | File operations | Document storage, log files, data exports |

## Resilience Features

### Circuit Breaker

Prevents cascading failures by "opening" when failure threshold is reached:

```yaml
circuit_breaker:
  enabled: true             # Whether circuit breaker is active (default: false)
  failure_threshold: 5      # Open after 5 failures (default: 5)
  success_threshold: 2      # Close after 2 successes (default: 2)
  timeout_ms: 30000         # Wait 30s before retry (default: 60000ms)
  half_open_requests: 3     # Allow 3 requests in half-open state (default: 3)
```

**States**: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED

### Retry Policy

Automatic retries with configurable backoff strategies (matching ModelEffectRetryPolicy schema):

```yaml
retry_policy:
  enabled: true                   # Whether retry is enabled (default: true)
  max_retries: 3                  # Maximum retry attempts (0-10)
  backoff_strategy: exponential   # or linear, fixed
  base_delay_ms: 1000             # Initial delay between retries
  max_delay_ms: 10000             # Maximum delay cap
  jitter_factor: 0.1              # Prevent thundering herd (10% jitter)
```

**Backoff Strategies** (per ModelEffectRetryPolicy schema):
- **exponential**: Delay doubles each retry, e.g., base_delay_ms * 2^attempt (recommended)
- **linear**: Delay increases linearly, e.g., base_delay_ms * attempt
- **fixed**: Constant delay between retries (base_delay_ms)

**Note**: The backoff calculation is handled internally by the retry handler.
The `base_delay_ms` and `max_delay_ms` define the delay bounds.

### Timeouts

Timeout configuration at different levels:

```yaml
operations:
  - operation_name: example_operation
    # Operation-level timeout (in ModelEffectOperation)
    # Guards against retry stacking by setting overall time limit
    operation_timeout_ms: 60000    # Overall timeout including all retries (default: 30000ms)

    # Handler-level timeout (in io_config for each handler type)
    io_config:
      handler_type: http
      timeout_ms: 15000            # Individual request timeout (default: 30000ms)
```

**Note**: Each IO config type (HTTP, DB, Kafka, Filesystem) has its own `timeout_ms` field
that controls the individual request/query timeout. The `operation_timeout_ms` at the operation
level guards against retry stacking by setting an overall time limit including all retries.
The operation_timeout_ms should be greater than io_config.timeout_ms to allow for retries.

### Observability

Comprehensive monitoring and tracing (matching ModelEffectObservability schema):

```yaml
observability:
  log_request: true          # Log outgoing requests (may contain sensitive data)
  log_response: true         # Log responses (may contain sensitive data)
  emit_metrics: true         # Emit performance and success metrics
  trace_propagation: true    # Propagate distributed trace context
```

**Security Warning**: Be careful with `log_request` and `log_response` as they may
log sensitive data like authentication tokens, passwords, or PII.

## Best Practices

### 1. Use Idempotency for Mutations

Always include idempotency keys for POST/PUT/PATCH/DELETE operations:

```yaml
headers:
  X-Idempotency-Key: "${idempotency_key}"
```

### 2. Set Appropriate Timeouts

Follow the timeout hierarchy:
- `operation_timeout_ms` > `io_config.timeout_ms` (to allow for retries)
- Set `operation_timeout_ms` to accommodate retry delays plus operation time

### 3. Choose Correct Execution Mode

- **sequential_abort** (default): Payment processing (stop on first failure, raise error)
- **sequential_continue**: Batch operations (run all operations, report all outcomes)

### 4. Configure Retries Based on Operation Type

- **Read operations (GET)**: More aggressive retries (5+)
- **Write operations (POST/PUT)**: Conservative retries (2-3)
- **Idempotent operations**: Can retry freely
- **Non-idempotent operations**: Minimal retries or none

### 5. Use Circuit Breakers for External Dependencies

Always enable circuit breakers for:
- External APIs (payment gateways, third-party services)
- Databases (prevent connection pool exhaustion)
- Message queues (protect against broker failures)

### 6. Extract Only Needed Fields

Use `extract_fields` to pull only required data:

```yaml
response_handling:
  extract_fields:
    user_id: "$.id"          # Not "$.id.user_id"
    email: "$.email"
  store_full_response: false  # Save memory
```

### 7. Secure Sensitive Data

Never log sensitive information:

```yaml
observability:
  log_request: false           # Don't log password_hash, tokens
  log_response: false          # May contain PII
```

**Note**: The ModelEffectObservability schema uses `log_request` and `log_response`
boolean fields. Set both to `false` when handling sensitive data.

### 8. Use Transactions for Consistency

Enable transactions for DB operations that must be atomic (ModelEffectTransactionConfig):

```yaml
transaction_config:
  enabled: true
  isolation_level: READ_COMMITTED  # or REPEATABLE_READ, SERIALIZABLE, READ_UNCOMMITTED
  rollback_on_error: true
  timeout_ms: 30000
```

**Note**: Transaction configuration only applies to DB handler type.

### 9. Validate Responses

Use response handling configuration to catch issues early (ModelEffectResponseHandling):

```yaml
response_handling:
  success_codes: [200, 201, 204]
  extract_fields:
    user_id: "$.id"
    email: "$.email"
  fail_on_empty: true           # Fail if response is empty/null
  extraction_engine: jsonpath   # or jq, xpath
```

### 10. Add Correlation IDs

Always include correlation IDs for request tracing:

```yaml
headers:
  X-Correlation-ID: "${correlation_id}"
  X-Request-ID: "${request_id}"
```

## Testing Contracts

### Unit Testing

```python
import pytest
from omnibase_core.nodes import NodeEffect
from omnibase_core.models import ModelEffectInput

@pytest.mark.asyncio
async def test_http_api_call_contract(container):
    # Load contract
    contract = load_yaml("examples/contracts/effect/http_api_call.yaml")

    # Create node
    node = NodeUserApiEffect(container, contract=contract)

    # Test input
    input_data = ModelEffectInput(
        operation_data={
            "email": "test@example.com",
            "display_name": "Test User"
        }
    )

    # Execute and verify
    result = await node.process(input_data)
    assert result.result_data["operations"]["create_user"]["success"]
```

### Integration Testing

```python
@pytest.mark.integration
async def test_resilient_payment_flow(container):
    contract = load_yaml("examples/contracts/effect/resilient_effect.yaml")
    node = NodePaymentEffect(container, contract=contract)

    # Test with real payment gateway (staging)
    result = await node.process(payment_input)

    # Verify all operations succeeded
    assert all(op["success"] for op in result.result_data["operations"].values())
```

## Migration from Code-Based Effects

### Before (Code-Based):

```python
class NodeUserApiEffect(NodeEffect):
    def __init__(self, container):
        super().__init__(container)
        self.http_client = container.get_service("ProtocolHttpClient")

    async def process(self, input_data):
        # 50+ lines of HTTP request logic
        # Manual retry handling
        # Manual error handling
        # Manual response extraction
        pass
```

### After (Contract-Driven):

```python
class NodeUserApiEffect(NodeEffect):
    pass  # All logic in YAML contract
```

Just load the contract and execute!

## Further Reading

- **NodeEffect Architecture**: `docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE.md`
- **Contract Schema**: `docs/reference/contracts/EFFECT_CONTRACT_SCHEMA.md`
- **Building Effect Nodes**: `docs/guides/node-building/04_EFFECT_NODE_TUTORIAL.md`
- **Resilience Patterns**: `docs/patterns/RESILIENCE_PATTERNS.md`

---

**Version**: 1.0.0
**Last Updated**: 2025-12-09
**Maintained By**: ONEX Framework Team
