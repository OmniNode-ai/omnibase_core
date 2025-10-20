# Mixin YAML Schema Reference

**Status**: Active
**Type**: Reference Documentation
**Prerequisites**: Basic YAML syntax
**Related**: [Creating Mixins](01_CREATING_MIXINS.md), [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md)

## Overview

This document provides a complete reference for the ONEX mixin YAML schema. Use this as a quick reference when creating or modifying mixin contracts.

## Complete Schema Template

```yaml
# ====================
# REQUIRED FIELDS
# ====================

mixin_name: "mixin_capability_name"           # String: Unique mixin identifier
mixin_version:                                # Object: Semantic versioning
  major: 1                                    # Integer: Major version
  minor: 0                                    # Integer: Minor version
  patch: 0                                    # Integer: Patch version
description: "Comprehensive mixin description"  # String: What this mixin provides
applicable_node_types:                        # Array: Valid node types
  - "COMPUTE"
  - "EFFECT"
  - "REDUCER"
  - "ORCHESTRATOR"

# ====================
# ACTIONS DEFINITION
# ====================

actions:                                      # Array: Mixin capabilities
  - name: "action_name"                       # String: Action identifier
    description: "Action description"         # String: What action does
    inputs:                                   # Array: Required input parameters
      - "input_param1"
      - "input_param2"
    outputs:                                  # Array: Output parameters
      - "output_param1"
      - "output_param2"
    required: true                            # Boolean: Is action mandatory
    timeout_ms: 5000                          # Integer: Action timeout

# ====================
# CONFIGURATION SECTION
# ====================

capability_name_config:                       # Object: Mixin configuration
  config_param1: default_value                # Any: Configuration parameters
  config_param2: default_value
  nested_config:                              # Object: Nested configuration
    nested_param1: value
    nested_param2: value

# ====================
# OUTPUT MODELS (OPTIONAL)
# ====================

output_models:                                # Object: Output structure definitions
  model_name:                                 # Object: Model definition
    field1: "type_definition"                 # String: Field type
    field2: "type_definition"
    nested_object:                            # Object: Nested structure
      type: "object"
      properties:
        sub_field: "type"

# ====================
# DEPENDENCIES (OPTIONAL)
# ====================

dependencies:                                 # Array: Provided capabilities
  - name: "capability_name"                   # String: Capability identifier
    type: "capability"                        # String: Dependency type
    description: "What this provides"         # String: Capability description

requires_dependencies:                        # Array: Required capabilities
  - name: "protocol_name"                     # String: Required capability
    type: "protocol"                          # String: Dependency type
    description: "What this needs"            # String: Requirement description
    optional: false                           # Boolean: Is it optional

# ====================
# METRICS (OPTIONAL)
# ====================

metrics:                                      # Array: Metric definitions
  - name: "metric_name"                       # String: Metric identifier
    type: "counter"                           # String: counter|gauge|histogram
    description: "Metric description"         # String: What metric tracks
    labels:                                   # Array: Metric labels
      - "label1"
      - "label2"
    buckets: [1, 10, 100, 1000]              # Array: Histogram buckets (if type=histogram)
```

## Field Definitions

### Required Fields

#### mixin_name

**Type**: `string`
**Required**: Yes
**Pattern**: `mixin_[capability_name]`

**Description**: Unique identifier for the mixin. Must be globally unique within the project.

**Examples**:
```yaml
mixin_name: "mixin_health_check"          # ✓ Good
mixin_name: "mixin_error_handling"        # ✓ Good
mixin_name: "health_check"                # ✗ Bad: Missing 'mixin_' prefix
mixin_name: "mixin-health-check"          # ✗ Bad: Use underscores, not hyphens
```

#### mixin_version

**Type**: `object`
**Required**: Yes
**Schema**:
```yaml
mixin_version:
  major: integer  # Breaking changes
  minor: integer  # New features, backward compatible
  patch: integer  # Bug fixes
```

**Description**: Semantic versioning for the mixin. Follow [semver](https://semver.org/) principles.

**Examples**:
```yaml
# Initial release
mixin_version: {major: 1, minor: 0, patch: 0}

# Added new feature (backward compatible)
mixin_version: {major: 1, minor: 1, patch: 0}

# Bug fix
mixin_version: {major: 1, minor: 1, patch: 1}

# Breaking change
mixin_version: {major: 2, minor: 0, patch: 0}
```

#### description

**Type**: `string`
**Required**: Yes
**Min Length**: 20 characters
**Max Length**: 500 characters

**Description**: Comprehensive description of what the mixin provides. Should be clear enough for developers to understand the mixin's purpose without reading the code.

**Examples**:
```yaml
# ✓ Good: Clear, comprehensive
description: "Provides standardized error handling including circuit breakers, retry logic, and error categorization for resilient node operations"

# ✗ Bad: Too vague
description: "Error handling"

# ✗ Bad: Too technical
description: "Implements circuit breaker pattern with exponential backoff retry mechanism and error classification taxonomy"
```

#### applicable_node_types

**Type**: `array<string>`
**Required**: Yes
**Valid Values**: `["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]`

**Description**: List of node types where this mixin can be applied. Enforces architectural constraints.

**Examples**:
```yaml
# Core mixin (all nodes)
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

# EFFECT-specific
applicable_node_types: ["EFFECT"]

# REDUCER and ORCHESTRATOR only
applicable_node_types: ["REDUCER", "ORCHESTRATOR"]

# Multiple specific types
applicable_node_types: ["EFFECT", "REDUCER"]
```

### Actions Section

#### actions

**Type**: `array<action>`
**Required**: Yes (at least one action)

**Description**: List of capabilities provided by the mixin. Each action represents a discrete operation.

**Action Schema**:
```yaml
- name: string                    # Required: Action identifier
  description: string             # Required: What action does
  inputs: array<string>           # Required: Input parameter names
  outputs: array<string>          # Required: Output parameter names
  required: boolean               # Required: Is action mandatory
  timeout_ms: integer             # Required: Action timeout (1-300000)
```

**Examples**:

```yaml
# Simple action
actions:
  - name: "check_health"
    description: "Perform health check of component"
    inputs: ["component_id"]
    outputs: ["health_status"]
    required: true
    timeout_ms: 5000

# Complex action with multiple inputs/outputs
actions:
  - name: "aggregate_data"
    description: "Aggregate data points with specified strategy"
    inputs:
      - "data_points"
      - "aggregation_strategy"
      - "grouping_fields"
    outputs:
      - "aggregated_result"
      - "aggregation_metadata"
      - "quality_score"
    required: true
    timeout_ms: 30000

# Optional action
actions:
  - name: "warm_cache"
    description: "Pre-load frequently accessed data"
    inputs: ["cache_patterns"]
    outputs: ["cache_warming_result"]
    required: false
    timeout_ms: 60000
```

### Configuration Section

#### [mixin_name]_config

**Type**: `object`
**Required**: Recommended
**Naming**: Must match pattern `{mixin_name}_config`

**Description**: Configuration parameters for the mixin. Define all configurable aspects with sensible defaults.

**Structure**:
```yaml
mixin_name_config:
  # Primitive values
  string_param: "default_value"
  integer_param: 42
  boolean_param: true
  float_param: 3.14

  # Arrays
  list_param:
    - "item1"
    - "item2"

  # Nested objects
  nested_config:
    sub_param1: value
    sub_param2: value
```

**Examples**:

```yaml
# Health check configuration
health_check_config:
  interval_seconds: 30
  timeout_ms: 5000
  retry_attempts: 3
  failure_threshold: 5
  healthy_threshold: 2
  check_endpoints:
    - "/health"
    - "/ready"

# Circuit breaker configuration
circuit_breaker_config:
  enabled: true
  failure_threshold: 5
  success_threshold: 2
  timeout_ms: 30000
  half_open_max_calls: 3
  exclude_error_types:
    - "ValidationError"
    - "NotFoundError"

# Caching configuration
caching_config:
  enabled: true
  ttl_seconds: 300
  max_size_mb: 256
  eviction_policy: "LRU"
  cache_levels:
    - level: "L1"
      type: "memory"
      size_mb: 64
    - level: "L2"
      type: "redis"
      connection_string: "redis://localhost:6379"
```

### Output Models Section

#### output_models

**Type**: `object`
**Required**: Optional (recommended for complex outputs)

**Description**: Define the structure of action outputs. Provides documentation and validation schema.

**Schema**:
```yaml
output_models:
  model_name:                     # Output model identifier
    field_name: "type"            # Field with type definition
    nested_object:                # Nested object definition
      type: "object"
      properties:
        sub_field: "type"
```

**Type Definitions**:
- `"string"` - String value
- `"integer"` - Integer number
- `"float"` - Floating point number
- `"boolean"` - Boolean true/false
- `"timestamp"` - ISO 8601 timestamp
- `"array"` - Array of items
- `"object"` - Nested object

**Examples**:

```yaml
output_models:
  health_check_result:
    status: "string"              # healthy/degraded/unhealthy
    checked_at: "timestamp"       # When check occurred
    response_time_ms: "integer"   # Check duration
    components:                   # Nested array
      type: "array"
      items:
        type: "object"
        properties:
          name: "string"
          status: "string"
          message: "string"

  aggregation_result:
    total_count: "integer"
    sum_value: "float"
    average_value: "float"
    min_value: "float"
    max_value: "float"
    grouped_results:
      type: "object"
      properties:
        group_key: "string"
        group_value: "float"

  circuit_breaker_status:
    state: "string"               # open/closed/half_open
    failure_count: "integer"
    success_count: "integer"
    last_failure_time: "timestamp"
    next_retry_time: "timestamp"
```

### Dependencies Section

#### dependencies

**Type**: `array<dependency>`
**Required**: Optional

**Description**: Capabilities that this mixin provides to other mixins or nodes.

**Schema**:
```yaml
dependencies:
  - name: string                  # Capability identifier
    type: string                  # Dependency type
    description: string           # What is provided
```

**Dependency Types**:
- `"capability"` - Functional capability
- `"protocol"` - Communication protocol
- `"service"` - Service interface
- `"resource"` - Shared resource

**Examples**:

```yaml
dependencies:
  - name: "error_handling"
    type: "capability"
    description: "Provides standardized error handling and recovery"

  - name: "circuit_breaker"
    type: "capability"
    description: "Provides circuit breaker pattern implementation"

  - name: "metrics_collection"
    type: "protocol"
    description: "Provides metrics collection interface"
```

#### requires_dependencies

**Type**: `array<dependency>`
**Required**: Optional

**Description**: Capabilities that this mixin requires from other mixins or the system.

**Schema**:
```yaml
requires_dependencies:
  - name: string                  # Required capability
    type: string                  # Dependency type
    description: string           # Why it's needed
    optional: boolean             # Is it optional
```

**Examples**:

```yaml
requires_dependencies:
  - name: "logging_protocol"
    type: "protocol"
    description: "Required for error logging"
    optional: false

  - name: "metrics_protocol"
    type: "protocol"
    description: "Optional metrics collection"
    optional: true

  - name: "service_discovery"
    type: "service"
    description: "Required for finding dependent services"
    optional: false
```

### Metrics Section

#### metrics

**Type**: `array<metric>`
**Required**: Optional (recommended for observability)

**Description**: Metrics that this mixin collects and exposes.

**Metric Schema**:
```yaml
metrics:
  - name: string                  # Metric identifier
    type: string                  # counter|gauge|histogram
    description: string           # What metric measures
    labels: array<string>         # Metric labels
    buckets: array<number>        # Histogram buckets (if type=histogram)
```

**Metric Types**:
- `"counter"` - Monotonically increasing value (e.g., total errors)
- `"gauge"` - Value that can go up or down (e.g., active connections)
- `"histogram"` - Distribution of values (e.g., response times)

**Examples**:

```yaml
metrics:
  # Counter metric
  - name: "errors_total"
    type: "counter"
    description: "Total number of errors encountered"
    labels:
      - "error_category"
      - "node_type"
      - "severity"

  # Gauge metric
  - name: "circuit_breaker_state"
    type: "gauge"
    description: "Current circuit breaker state (0=closed, 1=open, 2=half_open)"
    labels:
      - "operation_key"
      - "node_id"

  # Histogram metric
  - name: "operation_duration_ms"
    type: "histogram"
    description: "Time spent executing operations"
    labels:
      - "operation_name"
      - "success"
    buckets: [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]
```

## Complete Examples

### Example 1: Simple Core Mixin

```yaml
mixin_name: "mixin_logging"
mixin_version: {major: 1, minor: 0, patch: 0}
description: "Provides structured logging capabilities for ONEX nodes"
applicable_node_types: ["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"]

actions:
  - name: "log_message"
    description: "Log a message with specified level"
    inputs: ["message", "level", "context"]
    outputs: ["log_entry_id"]
    required: true
    timeout_ms: 500

logging_config:
  log_level: "INFO"
  structured_logging: true
  include_timestamps: true
  include_correlation_ids: true

metrics:
  - name: "log_messages_total"
    type: "counter"
    description: "Total log messages written"
    labels: ["level", "node_type"]
```

### Example 2: EFFECT-Specific Mixin

```yaml
mixin_name: "mixin_http_client"
mixin_version: {major: 1, minor: 0, patch: 0}
description: "Provides HTTP client capabilities with connection pooling and retry logic for EFFECT nodes"
applicable_node_types: ["EFFECT"]

actions:
  - name: "http_request"
    description: "Execute HTTP request with retry and circuit breaker"
    inputs: ["method", "url", "headers", "body"]
    outputs: ["response", "status_code", "headers"]
    required: true
    timeout_ms: 30000

  - name: "check_connection_health"
    description: "Verify HTTP connection pool health"
    inputs: ["endpoint"]
    outputs: ["health_status", "active_connections"]
    required: false
    timeout_ms: 5000

http_client_config:
  connection_pool_size: 10
  connection_timeout_ms: 5000
  read_timeout_ms: 30000
  retry_attempts: 3
  retry_status_codes: [408, 429, 500, 502, 503, 504]

output_models:
  http_response:
    status_code: "integer"
    body: "string"
    headers:
      type: "object"
    response_time_ms: "integer"

dependencies:
  - name: "http_client"
    type: "capability"
    description: "Provides HTTP client functionality"

requires_dependencies:
  - name: "circuit_breaker"
    type: "capability"
    description: "Required for fault tolerance"
    optional: false

metrics:
  - name: "http_requests_total"
    type: "counter"
    description: "Total HTTP requests made"
    labels: ["method", "status_code", "endpoint"]

  - name: "http_request_duration_ms"
    type: "histogram"
    description: "HTTP request duration"
    labels: ["method", "endpoint"]
    buckets: [10, 50, 100, 500, 1000, 5000, 10000]
```

### Example 3: REDUCER-Specific Mixin

```yaml
mixin_name: "mixin_state_persistence"
mixin_version: {major: 1, minor: 0, patch: 0}
description: "Provides state persistence and recovery capabilities for REDUCER nodes"
applicable_node_types: ["REDUCER"]

actions:
  - name: "save_state"
    description: "Persist current state to storage"
    inputs: ["state_data", "state_version"]
    outputs: ["save_result", "state_id"]
    required: true
    timeout_ms: 10000

  - name: "load_state"
    description: "Restore state from storage"
    inputs: ["state_id"]
    outputs: ["state_data", "state_version"]
    required: true
    timeout_ms: 10000

  - name: "clear_state"
    description: "Remove persisted state"
    inputs: ["state_id"]
    outputs: ["clear_result"]
    required: false
    timeout_ms: 5000

state_persistence_config:
  storage_backend: "redis"
  connection_string: "redis://localhost:6379"
  key_prefix: "onex_state"
  ttl_seconds: 3600
  compression_enabled: true
  encryption_enabled: false

dependencies:
  - name: "state_management"
    type: "capability"
    description: "Provides state persistence and recovery"

metrics:
  - name: "state_operations_total"
    type: "counter"
    description: "Total state operations"
    labels: ["operation", "success"]

  - name: "state_size_bytes"
    type: "histogram"
    description: "Size of persisted state"
    labels: ["node_id"]
    buckets: [1024, 10240, 102400, 1048576, 10485760]
```

## Validation Rules

### Schema Validation

1. **All required fields present**
2. **Field types match schema**
3. **Version follows semantic versioning**
4. **Node types are valid**
5. **Actions have complete definitions**
6. **Metric types are valid**

### Naming Conventions

1. **mixin_name**: `mixin_[capability]` (lowercase, underscores)
2. **action names**: `action_name` (lowercase, underscores)
3. **config section**: `{mixin_name}_config`
4. **metric names**: `metric_name` (lowercase, underscores)

### Best Practices

1. **Provide comprehensive descriptions** (min 20 characters)
2. **Include all actions** the mixin provides
3. **Define sensible defaults** for all config parameters
4. **Add metrics** for observability
5. **Document output models** for complex results
6. **Declare dependencies** explicitly

## Quick Reference

| Section | Required | Purpose |
|---------|----------|---------|
| `mixin_name` | Yes | Unique identifier |
| `mixin_version` | Yes | Semantic version |
| `description` | Yes | Mixin purpose |
| `applicable_node_types` | Yes | Node type constraints |
| `actions` | Yes | Mixin capabilities |
| `[name]_config` | Recommended | Configuration |
| `output_models` | Optional | Output structure |
| `dependencies` | Optional | Provided capabilities |
| `requires_dependencies` | Optional | Required capabilities |
| `metrics` | Optional | Observability |

## Next Steps

- **[Creating Mixins](01_CREATING_MIXINS.md)**: Step-by-step creation guide
- **[Pydantic Models](03_PYDANTIC_MODELS.md)**: Creating backing models
- **[Mixin Integration](04_MIXIN_INTEGRATION.md)**: Integrating into nodes
- **[Best Practices](05_BEST_PRACTICES.md)**: Advanced patterns

---

**Need help?** See [Mixin Architecture](../../architecture/MIXIN_ARCHITECTURE.md) for architectural overview.
