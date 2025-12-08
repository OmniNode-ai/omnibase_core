# NodeEffect Contract Examples

This directory contains comprehensive example YAML contracts for NodeEffect operations in the ONEX framework. These examples demonstrate how to define external I/O operations declaratively using the v1.0 contract schema.

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
http_config:
  method: POST
  url: "https://api.example.com/v1/users"
  body_template: |
    {
      "email": "${email}",
      "display_name": "${display_name}"
    }

retry_policy:
  backoff_strategy: exponential
  jitter: true

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
db_config:
  query: |
    SELECT id, email, display_name
    FROM users
    WHERE email = $1
    LIMIT 1

  query_params:
    - param_name: "email"
      source: "operation_data"
      field: "email"
      type: "string"

  transaction:
    enabled: true
    isolation_level: READ_COMMITTED

retry_policy:
  retryable_error_codes:
    - "40001"  # Serialization failure
    - "40P01"  # Deadlock detected
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
kafka_config:
  producer:
    acks: all
    enable_idempotence: true
    compression_type: snappy

  message:
    topic: "user.events.registration"
    partition_key: "${user_id}"
    value_template: |
      {
        "event_type": "user.registered",
        "user_id": "${user_id}",
        "timestamp": "${timestamp}"
      }
    headers:
      X-Correlation-ID: "${correlation_id}"
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
filesystem_config:
  operation_type: WRITE
  path: "/data/documents/${tenant_id}/users/${user_id}/${document_id}.json"

  atomic_write:
    enabled: true
    verify_checksum: true
    checksum_algorithm: "sha256"

  backup:
    enabled: true
    max_backups: 3
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
global_circuit_breaker:
  enabled: true
  failure_threshold: 5
  timeout_ms: 30000
  half_open_max_requests: 2

circuit_breaker:  # Per-operation
  enabled: true
  failure_threshold: 3
  on_state_change:
    emit_event: true
    notify:
      channels: [pagerduty, slack]

retry_policy:
  backoff_strategy: exponential
  jitter: true
  jitter_factor: 0.2

observability:
  log_timing: true
  tracing:
    enabled: true
    service_name: "payment-service"
  events:
    on_start: {enabled: true}
    on_success: {enabled: true}
    on_failure: {enabled: true}
    on_retry: {enabled: true}
```

---

## Contract Structure

All effect contracts follow this structure:

```yaml
effect_operations:
  version: "1.0.0"

  # How operations are executed
  execution_mode: sequential_abort  # or sequential_continue, concurrent

  # Global timeout for all operations
  operation_timeout_ms: 30000

  operations:
    - operation_name: example_operation
      description: "What this operation does"

      # Handler configuration (HTTP, DB, Kafka, Filesystem)
      io_config:
        handler_type: http  # or db, kafka, filesystem
        http_config:
          # Handler-specific configuration

      # Retry configuration
      retry_policy:
        enabled: true
        max_retries: 3
        backoff_strategy: exponential

      # Circuit breaker (optional)
      circuit_breaker:
        enabled: true
        failure_threshold: 5

      # Response handling
      response_handling:
        success_codes: [200, 201]
        extract_fields:
          result_id: "$.id"

      # Observability
      observability:
        log_requests: true
        emit_metrics: true

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
from omnibase_core.models import ModelEffectInput

input_data = ModelEffectInput(
    operation_data={
        "email": "john.smith@example.com",
        "display_name": "John Smith",
        "auth_token": "eyJhbGci..."
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
  failure_threshold: 5      # Open after 5 failures
  success_threshold: 2      # Close after 2 successes
  timeout_ms: 30000         # Wait 30s before retry
  half_open_max_requests: 2 # Allow 2 requests in half-open state
```

**States**: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing) → CLOSED

### Retry Policy

Automatic retries with configurable backoff strategies:

```yaml
retry_policy:
  max_retries: 3
  backoff_strategy: exponential  # or linear, constant
  initial_delay_ms: 1000
  max_delay_ms: 10000
  backoff_multiplier: 2.0
  jitter: true                   # Prevent thundering herd
  jitter_factor: 0.1             # ±10% randomization
```

**Backoff Strategies**:
- **Exponential**: delay = initial_delay × (multiplier ^ attempt)
- **Linear**: delay = initial_delay + (multiplier × attempt)
- **Constant**: delay = initial_delay (fixed)

### Timeouts

Multiple levels of timeout protection:

```yaml
operation_timeout_ms: 60000      # Total for all operations
query_timeout_ms: 5000           # Database query timeout
timeout_ms: 15000                # HTTP request timeout
connect_timeout_ms: 5000         # Connection establishment timeout
read_timeout_ms: 10000           # Response read timeout
```

### Observability

Comprehensive monitoring and tracing:

```yaml
observability:
  log_requests: true
  log_responses: true
  log_timing: true
  emit_metrics: true

  tracing:
    enabled: true
    service_name: "payment-service"
    span_name: "process_payment"

  events:
    on_start: {enabled: true}
    on_success: {enabled: true}
    on_failure: {enabled: true}
    on_retry: {enabled: true}
```

## Best Practices

### 1. Use Idempotency for Mutations

Always include idempotency keys for POST/PUT/PATCH/DELETE operations:

```yaml
headers:
  X-Idempotency-Key: "${idempotency_key}"
```

### 2. Set Appropriate Timeouts

Follow the timeout hierarchy:
- `operation_timeout_ms` > sum of individual operation timeouts
- `request_timeout_ms` > `connect_timeout_ms` + `read_timeout_ms`

### 3. Choose Correct Execution Mode

- **sequential_abort**: Payment processing (stop on failure)
- **sequential_continue**: Batch operations (continue on failures)
- **concurrent**: Independent operations (parallel execution)

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
  log_parameters: false        # Don't log password_hash, tokens
  log_response_body: false     # May contain PII
  log_message_body: false      # May contain sensitive data
```

### 8. Use Transactions for Consistency

Enable transactions for operations that must be atomic:

```yaml
transaction:
  enabled: true
  isolation_level: READ_COMMITTED
  auto_commit: true
```

### 9. Validate Responses

Use schema validation to catch issues early:

```yaml
response_handling:
  validate_response:
    enabled: true
    schema_ref: "schemas/payment_response.json"
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
**Last Updated**: 2024-12-08
**Maintained By**: ONEX Framework Team
