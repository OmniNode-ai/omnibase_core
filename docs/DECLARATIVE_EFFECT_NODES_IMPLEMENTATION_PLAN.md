# Effect Nodes Implementation Plan

**Version**: 1.3.0
**Status**: Approved
**Created**: 2025-12-02
**Updated**: 2025-12-03

> **v1.3.0 Correction**: Handler implementations moved to `omnibase_infra`. Core contains only models, resilience algorithms, and runtime orchestration. See [Core I/O Invariant](#core-io-invariant).

**Repository**: omnibase_core

### Related Documents

- [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) - How mixins dissolve into handlers, runtime, and domain libraries
- [ONEX Four-Node Architecture](./architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) - Overall node architecture

---

## Naming Convention

**IMPORTANT**: As of v1.1.0, declarative nodes are the DEFAULT implementation pattern and no longer require a "Declarative" suffix:

| Old Name (Deprecated) | New Name (Default) | Description |
|----------------------|-------------------|-------------|
| `NodeEffect` | `NodeEffect` | Effect node runtime |
| `NodeComputeDeclarative` | `NodeCompute` | Compute node runtime |
| `NodeReducerDeclarative` | `NodeReducer` | Reducer node runtime |
| `NodeOrchestratorDeclarative` | `NodeOrchestrator` | Orchestrator node runtime |

Legacy imperative nodes (if still needed) use the `Legacy` suffix:

| Legacy Name | Description |
|-------------|-------------|
| `NodeEffectLegacy` | Old imperative effect base class |
| `NodeComputeLegacy` | Old imperative compute base class |
| `NodeReducerLegacy` | Old imperative reducer base class |
| `NodeOrchestratorLegacy` | Old imperative orchestrator base class |

**Deprecation Timeline**:
- **v0.4.0**: Legacy nodes marked deprecated with warnings
- **v0.5.0**: Legacy nodes moved to `omnibase_core.legacy` namespace
- **v1.0.0**: Legacy nodes removed

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Package Structure](#2-package-structure)
3. [Pydantic Models](#3-pydantic-models)
4. [Protocol Handlers](#4-protocol-handlers)
5. [Resilience Components](#5-resilience-components)
6. [Runtime Class](#6-runtime-class)
7. [Implementation Phases](#7-implementation-phases)
8. [Testing Strategy](#8-testing-strategy)
9. [Dependencies](#9-dependencies)
10. [Public API](#10-public-api)
11. [Migration Guide](#11-migration-guide)

---

## 1. Executive Summary

### 1.1 Goal

Provide reusable effect infrastructure for all ONEX repositories (omniintelligence, omnibase_infra, omnibuild) by implementing:

- **Pydantic models** for YAML contract validation
- **Protocol handlers** for HTTP REST, Bolt (Neo4j/Memgraph), PostgreSQL, and Kafka
- **Resilience components** (circuit breaker, retry policy, rate limiter)
- **NodeEffect runtime** that executes YAML contracts

### 1.2 Scope

**In Scope (omnibase_core)**:
- Pydantic contract models (ModelEffectContract, ModelProtocolConfig, etc.)
- Abstract base classes and protocol handlers
- Resilience components (RetryPolicy, CircuitBreaker, RateLimiter)
- NodeEffect runtime class
- Comprehensive test suite

**Out of Scope (consuming repos)**:
- YAML contract files (go in omniintelligence, omnibase_infra, omnibuild)
- Domain-specific effect implementations
- Kafka consumer/producer integration at application level

### 1.3 Benefits

| Benefit | Description |
|---------|-------------|
| Reduce boilerplate | Eliminate 80%+ of repetitive Python code per adapter |
| Increase consistency | Same resilience, metrics, error handling across all effects |
| Simplify testing | Mock at protocol handler level |
| Enable runtime config | Change endpoints without code deployment |
| Maintain type safety | Full Pydantic validation of contracts |

### 1.4 Architecture Overview

```
                    +---------------------------+
                    |    Kafka Event Bus        |
                    | (Request/Response Topics) |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |       NodeEffect          |
                    |      (Base Runtime)       |
                    +-------------+-------------+
                                  |
         +------------------------+------------------------+
         |                        |                        |
+--------v--------+    +----------v----------+    +--------v--------+
|  Contract YAML  |    |  Protocol Handlers  |    |   Resilience    |
|  (consuming     |    |  - HttpRestHandler  |    |  - RetryPolicy  |
|   repos only)   |    |  - BoltHandler      |    |  - CircuitBreaker|
+--------+--------+    |  - PostgresHandler  |    |  - RateLimiter  |
         |             |  - KafkaHandler     |    +-----------------+
         |             +----------+----------+
         +------------------------+
                                  |
                    +-------------v-------------+
                    |   External Systems        |
                    | (Qdrant, Memgraph, etc.)  |
                    +---------------------------+
```

---

## 2. Package Structure

> **IMPORTANT**: Handler implementations live in `omnibase_infra`, NOT in `omnibase_core`. Core contains only pure Pydantic models, pure algorithms (resilience), and the runtime orchestration class. This maintains the invariant that Core contains no I/O code.

### omnibase_core (Pure Code - No I/O)

```
omnibase_core/
└── src/omnibase_core/
    └── nodes/
        └── effect/
            ├── __init__.py                        # Public API exports
            ├── models/                            # Pure Pydantic models (stays in core)
            │   ├── __init__.py
            │   ├── model_effect_contract.py       # Root contract model
            │   ├── model_protocol_config.py       # Protocol configuration
            │   ├── model_connection_config.py     # Connection settings
            │   ├── model_auth_config.py           # Authentication settings
            │   ├── model_operation_config.py      # Operation definitions
            │   ├── model_request_config.py        # Request configuration
            │   ├── model_response_config.py       # Response mapping
            │   ├── model_resilience_config.py     # Resilience policies
            │   ├── model_events_config.py         # Kafka event config
            │   └── model_observability_config.py  # Metrics/tracing
            ├── resilience/                        # Pure algorithms (stays in core)
            │   ├── __init__.py
            │   ├── retry_policy.py                # Exponential backoff
            │   ├── circuit_breaker.py             # Fault tolerance
            │   └── rate_limiter.py                # Token bucket
            ├── runtime.py                         # NodeEffect runtime (stays in core)
            └── legacy/                            # Deprecated imperative nodes
                ├── __init__.py
                └── node_effect_legacy.py          # NodeEffectLegacy (deprecated)
```

### omnibase_spi (Protocol Interfaces)

```
omnibase_spi/
└── src/omnibase_spi/
    └── protocols/
        └── handlers/
            └── protocol_handler.py                # Abstract ProtocolHandler interface
```

### omnibase_infra (I/O Implementations)

```
omnibase_infra/
└── src/omnibase_infra/
    └── handlers/
        ├── __init__.py
        ├── handler_http_rest.py                   # HTTP REST handler (uses aiohttp)
        ├── handler_bolt.py                        # Neo4j/Memgraph Bolt handler (uses neo4j)
        ├── handler_postgres.py                    # PostgreSQL handler (uses asyncpg)
        ├── handler_kafka.py                       # Kafka handler (uses confluent-kafka)
        └── handler_registry.py                    # Handler factory/registry
```

---

## 3. Pydantic Models

### 3.1 ModelEffectContract (Root Model)

**File**: `src/omnibase_core/nodes/effect/models/model_effect_contract.py`

```python
"""Root contract model for declarative effect nodes."""

from typing import Any
from pydantic import BaseModel, Field
from datetime import date


class ModelVersion(BaseModel):
    """Semantic version model."""
    major: int = Field(ge=0, description="Major version")
    minor: int = Field(ge=0, description="Minor version")
    patch: int = Field(ge=0, description="Patch version")

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class ModelMetadata(BaseModel):
    """Contract metadata."""
    author: str | None = Field(default=None, description="Contract author")
    created_at: date | None = Field(default=None, description="Creation date")
    updated_at: date | None = Field(default=None, description="Last update date")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    documentation: str | None = Field(default=None, description="Documentation URL")
    dependencies: list[str] = Field(default_factory=list, description="Contract dependencies")


class ModelEffectContract(BaseModel):
    """
    Root model for declarative effect node contracts.

    Validates YAML contracts that define:
    - Protocol type and connection settings
    - Available operations with request/response mapping
    - Resilience policies (retry, circuit breaker, rate limit)
    - Observability configuration (metrics, tracing, logging)
    - Kafka event topics for consuming/producing

    Example:
        >>> contract = ModelEffectContract.model_validate(yaml.safe_load(contract_file))
        >>> node = NodeEffect(contract)
        >>> await node.initialize()
    """

    # Required fields
    name: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique effect name (snake_case)",
        examples=["qdrant_vector_effect", "mlx_embedding_adapter"]
    )
    version: ModelVersion = Field(..., description="Contract semantic version")
    protocol: "ModelProtocolConfig" = Field(..., description="Protocol configuration")
    connection: "ModelConnectionConfig" = Field(..., description="Connection settings")
    operations: dict[str, "ModelOperationConfig"] = Field(
        ...,
        min_length=1,
        description="Available operations"
    )

    # Optional fields
    description: str | None = Field(default=None, description="Human-readable description")
    authentication: "ModelAuthConfig | None" = Field(
        default=None,
        description="Authentication configuration"
    )
    resilience: "ModelResilienceConfig | None" = Field(
        default=None,
        description="Resilience policies"
    )
    events: "ModelEventsConfig | None" = Field(
        default=None,
        description="Kafka event configuration"
    )
    observability: "ModelObservabilityConfig | None" = Field(
        default=None,
        description="Observability settings"
    )
    metadata: ModelMetadata | None = Field(
        default=None,
        description="Contract metadata"
    )

    model_config = {
        "extra": "forbid",
        "frozen": False,
        "validate_assignment": True
    }


# Forward references resolved at module load
from omnibase_core.nodes.effect.models.model_protocol_config import ModelProtocolConfig
from omnibase_core.nodes.effect.models.model_connection_config import ModelConnectionConfig
from omnibase_core.nodes.effect.models.model_auth_config import ModelAuthConfig
from omnibase_core.nodes.effect.models.model_operation_config import ModelOperationConfig
from omnibase_core.nodes.effect.models.model_resilience_config import ModelResilienceConfig
from omnibase_core.nodes.effect.models.model_events_config import ModelEventsConfig
from omnibase_core.nodes.effect.models.model_observability_config import ModelObservabilityConfig

ModelEffectContract.model_rebuild()
```

### 3.2 ModelProtocolConfig

**File**: `src/omnibase_core/nodes/effect/models/model_protocol_config.py`

```python
"""Protocol configuration model."""

from enum import Enum
from pydantic import BaseModel, Field


class EnumProtocolType(str, Enum):
    """Supported protocol types."""
    HTTP_REST = "http_rest"
    BOLT = "bolt"
    POSTGRES = "postgres"
    KAFKA = "kafka"


class ModelProtocolConfig(BaseModel):
    """Protocol handler configuration."""

    type: EnumProtocolType = Field(..., description="Protocol handler to use")
    version: str | None = Field(
        default=None,
        description="Protocol version (e.g., HTTP/1.1, Bolt/4.4)"
    )
    content_type: str = Field(
        default="application/json",
        description="Default content type for requests"
    )

    model_config = {"extra": "forbid"}
```

### 3.3 ModelConnectionConfig

**File**: `src/omnibase_core/nodes/effect/models/model_connection_config.py`

```python
"""Connection configuration model."""

from pydantic import BaseModel, Field


class ModelPoolConfig(BaseModel):
    """Connection pool configuration."""
    min_size: int = Field(default=1, ge=1, description="Minimum pool size")
    max_size: int = Field(default=10, ge=1, description="Maximum pool size")
    max_idle_time_ms: int = Field(default=300000, ge=0, description="Max idle time in ms")


class ModelTlsConfig(BaseModel):
    """TLS/SSL configuration."""
    enabled: bool = Field(default=False, description="Enable TLS")
    verify: bool = Field(default=True, description="Verify certificates")
    ca_cert_path: str | None = Field(default=None, description="CA certificate path")
    client_cert_path: str | None = Field(default=None, description="Client certificate path")
    client_key_path: str | None = Field(default=None, description="Client key path")


class ModelConnectionConfig(BaseModel):
    """Connection settings for effect nodes."""

    # URL-based connection (preferred for HTTP, Bolt)
    url: str | None = Field(
        default=None,
        description="Connection URL with ${ENV_VAR} substitution support",
        examples=["http://${QDRANT_HOST}:${QDRANT_PORT}"]
    )

    # Component-based connection (alternative for databases)
    host: str | None = Field(default=None, description="Host address")
    port: int | None = Field(default=None, ge=1, le=65535, description="Port number")
    database: str | None = Field(default=None, description="Database name")

    # Connection behavior
    timeout_ms: int = Field(default=30000, ge=0, description="Connection timeout in ms")
    pool: ModelPoolConfig = Field(default_factory=ModelPoolConfig, description="Pool settings")
    tls: ModelTlsConfig = Field(default_factory=ModelTlsConfig, description="TLS settings")

    model_config = {"extra": "forbid"}
```

### 3.4 ModelAuthConfig

**File**: `src/omnibase_core/nodes/effect/models/model_auth_config.py`

```python
"""Authentication configuration model."""

from enum import Enum
from pydantic import BaseModel, Field


class EnumAuthType(str, Enum):
    """Authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH2 = "oauth2"


class ModelApiKeyAuth(BaseModel):
    """API key authentication."""
    header: str = Field(default="Authorization", description="Header name")
    prefix: str = Field(default="Bearer", description="Value prefix")
    value: str = Field(..., description="API key value (supports ${ENV_VAR})")


class ModelBasicAuth(BaseModel):
    """HTTP Basic authentication."""
    username: str = Field(..., description="Username (supports ${ENV_VAR})")
    password: str = Field(..., description="Password (supports ${ENV_VAR})")


class ModelBearerAuth(BaseModel):
    """Bearer token authentication."""
    token: str = Field(..., description="Bearer token (supports ${ENV_VAR})")


class ModelOAuth2Auth(BaseModel):
    """OAuth2 authentication."""
    token_url: str = Field(..., description="Token endpoint URL")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    scopes: list[str] = Field(default_factory=list, description="OAuth2 scopes")


class ModelAuthConfig(BaseModel):
    """Authentication configuration."""

    type: EnumAuthType = Field(default=EnumAuthType.NONE, description="Auth type")
    api_key: ModelApiKeyAuth | None = Field(default=None, description="API key config")
    basic: ModelBasicAuth | None = Field(default=None, description="Basic auth config")
    bearer: ModelBearerAuth | None = Field(default=None, description="Bearer token config")
    oauth2: ModelOAuth2Auth | None = Field(default=None, description="OAuth2 config")

    model_config = {"extra": "forbid"}
```

### 3.5 ModelOperationConfig

**File**: `src/omnibase_core/nodes/effect/models/model_operation_config.py`

```python
"""Operation configuration model."""

from pydantic import BaseModel, Field
from typing import Any


class ModelOperationConfig(BaseModel):
    """Single operation definition within a contract."""

    description: str = Field(..., description="Operation description")
    request: "ModelRequestConfig | None" = Field(
        default=None,
        description="Request configuration"
    )
    response: "ModelResponseConfig | None" = Field(
        default=None,
        description="Response mapping"
    )
    validation: "ModelValidationConfig | None" = Field(
        default=None,
        description="Input validation rules"
    )
    error_handling: "ModelOperationErrorConfig | None" = Field(
        default=None,
        description="Error handling rules"
    )

    model_config = {"extra": "forbid"}


class ModelValidationConfig(BaseModel):
    """Input validation configuration."""

    required_fields: list[str] = Field(
        default_factory=list,
        description="Required input fields"
    )
    field_types: dict[str, str] = Field(
        default_factory=dict,
        description="Expected field types"
    )
    custom_validators: list[str] = Field(
        default_factory=list,
        description="Custom validator function names"
    )

    model_config = {"extra": "forbid"}


class ModelOperationErrorConfig(BaseModel):
    """Operation-specific error handling."""

    retryable_errors: list[str] = Field(
        default_factory=list,
        description="Error types that trigger retry"
    )
    non_retryable_errors: list[str] = Field(
        default_factory=list,
        description="Error types that go directly to DLQ"
    )
    error_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map error codes to error types"
    )

    model_config = {"extra": "forbid"}


# Forward references
from omnibase_core.nodes.effect.models.model_request_config import ModelRequestConfig
from omnibase_core.nodes.effect.models.model_response_config import ModelResponseConfig

ModelOperationConfig.model_rebuild()
```

### 3.6 ModelRequestConfig

**File**: `src/omnibase_core/nodes/effect/models/model_request_config.py`

```python
"""Request configuration model."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EnumHttpMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ModelRequestConfig(BaseModel):
    """
    Request configuration for operations.

    Supports multiple protocols:
    - HTTP REST: method, path, query, headers, body
    - Bolt: cypher, cypher_params
    - PostgreSQL: sql, sql_params
    - Kafka: topic, message

    Template variables use ${variable} syntax:
    - ${ENV_VAR} - Environment variable
    - ${input.field} - Input field value
    - ${context.field} - Context value
    - ${config.field} - Config value
    """

    # HTTP REST fields
    method: EnumHttpMethod | None = Field(default=None, description="HTTP method")
    path: str | None = Field(
        default=None,
        description="URL path template",
        examples=["/collections/${input.collection}/points"]
    )
    query: dict[str, str] | None = Field(default=None, description="Query parameters")
    headers: dict[str, str] | None = Field(default=None, description="Additional headers")
    body: dict[str, Any] | str | None = Field(default=None, description="Request body template")
    body_template: str | None = Field(default=None, description="External template file path")

    # Bolt (Neo4j/Memgraph) fields
    cypher: str | None = Field(default=None, description="Cypher query")
    cypher_params: dict[str, str] | None = Field(
        default=None,
        description="Cypher parameter mapping"
    )

    # PostgreSQL fields
    sql: str | None = Field(default=None, description="SQL query")
    sql_params: list[str] | None = Field(
        default=None,
        description="SQL parameters (positional)"
    )

    # Kafka fields
    topic: str | None = Field(default=None, description="Kafka topic")

    model_config = {"extra": "forbid"}
```

### 3.7 ModelResponseConfig

**File**: `src/omnibase_core/nodes/effect/models/model_response_config.py`

```python
"""Response configuration model."""

from pydantic import BaseModel, Field


class ModelResponseConfig(BaseModel):
    """
    Response mapping configuration.

    Uses JSONPath expressions to extract values from responses:
    - Simple path: $.id
    - Nested path: $.result.score
    - Array access: $.results[0]
    - All items: $.results[*].score
    - With default: $.count ?? 0
    """

    success_codes: list[int] = Field(
        default=[200, 201, 202, 204],
        description="HTTP status codes considered successful"
    )
    mapping: dict[str, str] = Field(
        default_factory=dict,
        description="JSONPath mapping from response to output fields",
        examples=[{
            "vector_id": "$.result.id",
            "score": "$.result.score",
            "metadata": "$.result.payload"
        }]
    )
    transform: str | None = Field(
        default=None,
        description="Optional transformation function name"
    )

    model_config = {"extra": "forbid"}
```

### 3.8 ModelResilienceConfig

**File**: `src/omnibase_core/nodes/effect/models/model_resilience_config.py`

```python
"""Resilience configuration model."""

from pydantic import BaseModel, Field


class ModelRetryConfig(BaseModel):
    """Retry policy configuration."""
    enabled: bool = Field(default=True, description="Enable retry")
    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    initial_delay_ms: int = Field(default=1000, ge=0, description="Initial delay in ms")
    max_delay_ms: int = Field(default=30000, ge=0, description="Maximum delay in ms")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, description="Backoff multiplier")
    jitter: bool = Field(default=True, description="Add random jitter to delays")


class ModelCircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    enabled: bool = Field(default=True, description="Enable circuit breaker")
    failure_threshold: int = Field(default=5, ge=1, description="Failures before opening")
    success_threshold: int = Field(default=2, ge=1, description="Successes to close")
    timeout_ms: int = Field(default=60000, ge=0, description="Reset timeout in ms")
    half_open_max_calls: int = Field(default=3, ge=1, description="Max calls in half-open")


class ModelRateLimitConfig(BaseModel):
    """Rate limiter configuration."""
    enabled: bool = Field(default=False, description="Enable rate limiting")
    requests_per_second: float = Field(default=100.0, gt=0, description="Request rate")
    burst_size: int = Field(default=10, ge=1, description="Burst capacity")


class ModelTimeoutConfig(BaseModel):
    """Timeout configuration."""
    request_ms: int = Field(default=30000, ge=0, description="Per-request timeout")
    operation_ms: int = Field(default=120000, ge=0, description="Total operation timeout")


class ModelBulkheadConfig(BaseModel):
    """Bulkhead configuration for isolation."""
    enabled: bool = Field(default=False, description="Enable bulkhead")
    max_concurrent: int = Field(default=10, ge=1, description="Max concurrent calls")
    max_wait_ms: int = Field(default=5000, ge=0, description="Max wait time")


class ModelResilienceConfig(BaseModel):
    """Complete resilience configuration."""

    retry: ModelRetryConfig = Field(
        default_factory=ModelRetryConfig,
        description="Retry policy"
    )
    circuit_breaker: ModelCircuitBreakerConfig = Field(
        default_factory=ModelCircuitBreakerConfig,
        description="Circuit breaker"
    )
    rate_limit: ModelRateLimitConfig = Field(
        default_factory=ModelRateLimitConfig,
        description="Rate limiter"
    )
    timeout: ModelTimeoutConfig = Field(
        default_factory=ModelTimeoutConfig,
        description="Timeouts"
    )
    bulkhead: ModelBulkheadConfig = Field(
        default_factory=ModelBulkheadConfig,
        description="Bulkhead isolation"
    )

    model_config = {"extra": "forbid"}
```

### 3.9 ModelEventsConfig

**File**: `src/omnibase_core/nodes/effect/models/model_events_config.py`

```python
"""Kafka events configuration model."""

from enum import Enum
from pydantic import BaseModel, Field


class EnumAutoOffsetReset(str, Enum):
    """Kafka offset reset behavior."""
    EARLIEST = "earliest"
    LATEST = "latest"


class EnumAcks(str, Enum):
    """Kafka producer acknowledgment."""
    NONE = "0"
    LEADER = "1"
    ALL = "all"


class ModelConsumeConfig(BaseModel):
    """Kafka consumer configuration."""
    topic: str = Field(..., description="Topic to consume from")
    group_id: str = Field(..., description="Consumer group ID")
    auto_offset_reset: EnumAutoOffsetReset = Field(
        default=EnumAutoOffsetReset.EARLIEST,
        description="Offset reset behavior"
    )
    enable_auto_commit: bool = Field(default=False, description="Enable auto commit")
    batch_size: int = Field(default=1, ge=1, description="Messages per batch")


class ModelProduceConfig(BaseModel):
    """Kafka producer configuration."""
    success_topic: str = Field(..., description="Topic for successful responses")
    failure_topic: str | None = Field(
        default=None,
        description="Topic for failures (before DLQ)"
    )
    dlq_topic: str = Field(..., description="Dead letter queue topic")
    acks: EnumAcks = Field(default=EnumAcks.ALL, description="Acknowledgment level")


class ModelEnvelopeConfig(BaseModel):
    """Event envelope configuration."""
    include_metadata: bool = Field(default=True, description="Include metadata in envelope")
    include_timing: bool = Field(default=True, description="Include timing info")
    correlation_id_path: str = Field(
        default="$.correlation_id",
        description="JSONPath to correlation ID"
    )


class ModelEventsConfig(BaseModel):
    """Kafka events configuration."""

    consume: ModelConsumeConfig | None = Field(
        default=None,
        description="Consumer settings"
    )
    produce: ModelProduceConfig | None = Field(
        default=None,
        description="Producer settings"
    )
    envelope: ModelEnvelopeConfig = Field(
        default_factory=ModelEnvelopeConfig,
        description="Envelope settings"
    )

    model_config = {"extra": "forbid"}
```

### 3.10 ModelObservabilityConfig

**File**: `src/omnibase_core/nodes/effect/models/model_observability_config.py`

```python
"""Observability configuration model."""

from enum import Enum
from pydantic import BaseModel, Field


class EnumLogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ModelHistogramConfig(BaseModel):
    """Histogram bucket configuration."""
    buckets: list[float] = Field(
        default=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        description="Histogram bucket boundaries"
    )


class ModelMetricsConfig(BaseModel):
    """Metrics configuration."""
    enabled: bool = Field(default=True, description="Enable metrics collection")
    prefix: str = Field(
        default="omniintelligence_effect",
        description="Metric name prefix"
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Additional labels"
    )
    histograms: ModelHistogramConfig = Field(
        default_factory=ModelHistogramConfig,
        description="Histogram settings"
    )


class ModelTracingConfig(BaseModel):
    """Distributed tracing configuration."""
    enabled: bool = Field(default=True, description="Enable tracing")
    service_name: str | None = Field(default=None, description="Service name for traces")
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Sampling rate")


class ModelLoggingConfig(BaseModel):
    """Logging configuration."""
    level: EnumLogLevel = Field(default=EnumLogLevel.INFO, description="Log level")
    include_request_body: bool = Field(
        default=False,
        description="Log request bodies (debug only)"
    )
    include_response_body: bool = Field(
        default=False,
        description="Log response bodies (debug only)"
    )
    sanitize_secrets: bool = Field(default=True, description="Sanitize sensitive data")
    secret_patterns: list[str] = Field(
        default=["password", "secret", "token", "api_key", "authorization"],
        description="Patterns to sanitize"
    )


class ModelObservabilityConfig(BaseModel):
    """Complete observability configuration."""

    metrics: ModelMetricsConfig = Field(
        default_factory=ModelMetricsConfig,
        description="Metrics settings"
    )
    tracing: ModelTracingConfig = Field(
        default_factory=ModelTracingConfig,
        description="Tracing settings"
    )
    logging: ModelLoggingConfig = Field(
        default_factory=ModelLoggingConfig,
        description="Logging settings"
    )

    model_config = {"extra": "forbid"}
```

---

## 4. Protocol Handlers

**IMPORTANT**: While the handler *interface* (abstract base class `ProtocolHandler`) is defined in `omnibase_spi`, the concrete implementations (`HttpRestHandler`, `BoltHandler`, `PostgresHandler`, `KafkaHandler`) live in `omnibase_infra`. This maintains the invariant that Core contains no I/O code.

### Core I/O Invariant

No code in `omnibase_core` may initiate network I/O, database I/O, file I/O, or external process execution. Handler implementations that perform I/O must live in `omnibase_infra`.

**Rationale**:
- Core remains pure and testable without external dependencies
- I/O-dependent code is isolated in infrastructure layer
- Dependency injection allows runtime handler resolution
- Testing can use mock handlers without I/O library dependencies

### 4.1 Abstract Base Class

**File**: `src/omnibase_spi/protocols/handlers/protocol_handler.py` (interface in SPI)

```python
"""Abstract protocol handler base class."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class ModelProtocolRequest(BaseModel):
    """Protocol-agnostic request model."""
    operation: str = Field(..., description="Operation name")
    params: dict[str, Any] = Field(default_factory=dict, description="Operation params")
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds")
    correlation_id: str = Field(..., description="Correlation ID for tracing")


class ModelProtocolResponse(BaseModel):
    """Protocol-agnostic response model."""
    success: bool = Field(..., description="Whether operation succeeded")
    status_code: int | None = Field(default=None, description="HTTP status code")
    data: dict[str, Any] | None = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message")
    duration_ms: float = Field(..., description="Operation duration")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class ProtocolHandler(ABC):
    """
    Abstract base class for protocol handlers.

    Implementations handle protocol-specific details while
    exposing a uniform interface to NodeEffect.

    Thread Safety:
        - Handlers should be created per-node instance
        - Connection pools may be shared within a handler
        - State mutations must be synchronized
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize connection pool/client.

        Args:
            config: Connection and authentication configuration

        Raises:
            ConnectionError: If connection cannot be established
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Close connections gracefully.

        Should flush pending operations and release resources.
        """
        pass

    @abstractmethod
    async def execute(
        self,
        request: ModelProtocolRequest,
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:
        """
        Execute protocol-specific operation.

        Args:
            request: Protocol-agnostic request
            operation_config: Operation configuration from contract

        Returns:
            Protocol-agnostic response
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass
```

### 4.2 HttpRestHandler

**File**: `src/omnibase_infra/handlers/handler_http_rest.py` (implementation in Infra)

```python
"""HTTP REST Protocol Handler."""

import json
import os
import re
import ssl
import time
from typing import Any

import aiohttp

from omnibase_core.nodes.effect.handlers.protocol_handler import (
    ModelProtocolRequest,
    ModelProtocolResponse,
    ProtocolHandler,
)


class HttpRestHandler(ProtocolHandler):
    """
    Handler for HTTP REST APIs.

    Features:
    - GET, POST, PUT, PATCH, DELETE methods
    - JSON request/response bodies
    - Header management with auth injection
    - Connection pooling via aiohttp
    - TLS/SSL with certificate verification
    - Environment variable substitution
    """

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        self.base_url: str = ""
        self.default_headers: dict[str, str] = {}

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize HTTP client session with connection pooling."""
        pool_config = config.get("pool", {})

        connector = aiohttp.TCPConnector(
            limit=pool_config.get("max_size", 10),
            limit_per_host=pool_config.get("max_size", 10),
            ttl_dns_cache=300,
            ssl=self._get_ssl_context(config.get("tls", {}))
        )

        timeout = aiohttp.ClientTimeout(
            total=config.get("timeout_ms", 30000) / 1000
        )

        auth_headers = self._build_auth_headers(config.get("authentication", {}))

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=auth_headers
        )

        self.base_url = self._resolve_env_vars(config.get("url", ""))
        self.default_headers = config.get("headers", {})

    async def shutdown(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    async def execute(
        self,
        request: ModelProtocolRequest,
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:
        """Execute HTTP request."""
        start_time = time.perf_counter()

        try:
            req_config = operation_config.get("request", {})
            method = req_config.get("method", "GET")
            path = self._substitute_variables(
                req_config.get("path", ""),
                request.params
            )
            url = f"{self.base_url}{path}"

            # Build headers
            headers = {**self.default_headers, **request.headers}

            # Build body
            body = None
            if req_config.get("body"):
                body = self._substitute_variables(req_config["body"], request.params)
                if isinstance(body, dict):
                    body = json.dumps(body)

            # Build query params
            query = {}
            if req_config.get("query"):
                for k, v in req_config["query"].items():
                    query[k] = self._substitute_variables(v, request.params)

            # Execute request
            if not self.session:
                raise RuntimeError("Session not initialized")

            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                params=query
            ) as response:
                duration_ms = (time.perf_counter() - start_time) * 1000

                response_data = {}
                if response.content_type == "application/json":
                    response_data = await response.json()

                success_codes = operation_config.get("response", {}).get(
                    "success_codes", [200, 201, 202, 204]
                )

                return ModelProtocolResponse(
                    success=response.status in success_codes,
                    status_code=response.status,
                    data=response_data,
                    duration_ms=duration_ms,
                    metadata={"url": url, "method": method}
                )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ModelProtocolResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    async def health_check(self) -> bool:
        """Check HTTP connectivity."""
        if not self.session:
            return False
        try:
            async with self.session.get(self.base_url) as response:
                return response.status < 500
        except Exception:
            return False

    def _substitute_variables(self, template: Any, params: dict[str, Any]) -> Any:
        """Substitute ${variable} patterns in template."""
        if isinstance(template, str):
            def replace(match: re.Match[str]) -> str:
                key = match.group(1)
                parts = key.split(".")
                value: Any = params
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part, match.group(0))
                    else:
                        return match.group(0)
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                return str(value)
            return re.sub(r'\$\{([^}]+)\}', replace, template)
        elif isinstance(template, dict):
            return {k: self._substitute_variables(v, params) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._substitute_variables(item, params) for item in template]
        return template

    def _build_auth_headers(self, auth_config: dict[str, Any]) -> dict[str, str]:
        """Build authentication headers."""
        auth_type = auth_config.get("type", "none")
        headers: dict[str, str] = {}

        if auth_type == "api_key":
            api_key_config = auth_config.get("api_key", {})
            header = api_key_config.get("header", "Authorization")
            prefix = api_key_config.get("prefix", "Bearer")
            value = self._resolve_env_vars(api_key_config.get("value", ""))
            headers[header] = f"{prefix} {value}" if prefix else value

        elif auth_type == "basic":
            import base64
            basic_config = auth_config.get("basic", {})
            username = self._resolve_env_vars(basic_config.get("username", ""))
            password = self._resolve_env_vars(basic_config.get("password", ""))
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        elif auth_type == "bearer":
            token = self._resolve_env_vars(auth_config.get("bearer", {}).get("token", ""))
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _resolve_env_vars(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns."""
        def replace(match: re.Match[str]) -> str:
            env_var = match.group(1)
            # Handle default values: ${VAR:default}
            if ":" in env_var:
                var_name, default = env_var.split(":", 1)
                return os.getenv(var_name, default)
            return os.getenv(env_var, "")
        return re.sub(r'\$\{([^}]+)\}', replace, value)

    def _get_ssl_context(self, tls_config: dict[str, Any]) -> ssl.SSLContext | None:
        """Build SSL context from TLS config."""
        if not tls_config.get("enabled", False):
            return None

        ctx = ssl.create_default_context()

        if not tls_config.get("verify", True):
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        if tls_config.get("ca_cert_path"):
            ctx.load_verify_locations(tls_config["ca_cert_path"])

        if tls_config.get("client_cert_path") and tls_config.get("client_key_path"):
            ctx.load_cert_chain(
                tls_config["client_cert_path"],
                tls_config["client_key_path"]
            )

        return ctx
```

### 4.3 BoltHandler

**File**: `src/omnibase_infra/handlers/handler_bolt.py` (implementation in Infra)

```python
"""Neo4j Bolt Protocol Handler for Memgraph/Neo4j."""

import os
import re
import time
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from omnibase_core.nodes.effect.handlers.protocol_handler import (
    ModelProtocolRequest,
    ModelProtocolResponse,
    ProtocolHandler,
)


class BoltHandler(ProtocolHandler):
    """
    Handler for Neo4j Bolt protocol (Memgraph, Neo4j).

    Features:
    - Cypher query execution
    - Parameterized queries for security
    - Transaction management
    - Connection pooling
    """

    def __init__(self) -> None:
        self.driver: AsyncDriver | None = None
        self.database: str | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize Bolt driver with connection pooling."""
        url = self._resolve_env_vars(config.get("url", "bolt://localhost:7687"))
        auth = None

        auth_config = config.get("authentication", {})
        if auth_config.get("type") == "basic":
            auth = (
                self._resolve_env_vars(auth_config.get("basic", {}).get("username", "")),
                self._resolve_env_vars(auth_config.get("basic", {}).get("password", ""))
            )

        pool_config = config.get("pool", {})

        self.driver = AsyncGraphDatabase.driver(
            url,
            auth=auth,
            max_connection_pool_size=pool_config.get("max_size", 50),
            connection_timeout=config.get("timeout_ms", 30000) / 1000
        )

        self.database = config.get("database")

    async def shutdown(self) -> None:
        """Close Bolt driver."""
        if self.driver:
            await self.driver.close()

    async def execute(
        self,
        request: ModelProtocolRequest,
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:
        """Execute Cypher query."""
        start_time = time.perf_counter()

        try:
            req_config = operation_config.get("request", {})
            cypher = self._substitute_variables(
                req_config.get("cypher", ""),
                request.params
            )

            # Build Cypher parameters
            cypher_params: dict[str, Any] = {}
            param_mapping = req_config.get("cypher_params", {})
            for param_name, param_source in param_mapping.items():
                if param_source.startswith("${input."):
                    path = param_source[8:-1]  # Remove ${input. and }
                    cypher_params[param_name] = self._get_nested_value(
                        request.params.get("input", {}),
                        path
                    )

            if not self.driver:
                raise RuntimeError("Driver not initialized")

            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, cypher_params)
                records = await result.data()
                summary = await result.consume()

                duration_ms = (time.perf_counter() - start_time) * 1000

                return ModelProtocolResponse(
                    success=True,
                    data={
                        "records": records,
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set
                        }
                    },
                    duration_ms=duration_ms,
                    metadata={"database": self.database}
                )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ModelProtocolResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    async def health_check(self) -> bool:
        """Check Bolt connectivity."""
        if not self.driver:
            return False
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS test")
                await result.single()
                return True
        except Exception:
            return False

    def _substitute_variables(self, template: str, params: dict[str, Any]) -> str:
        """Substitute ${variable} patterns in Cypher template."""
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key.startswith("input."):
                path = key[6:]
                value = self._get_nested_value(params.get("input", {}), path)
                return str(value) if value is not None else match.group(0)
            return match.group(0)
        return re.sub(r'\$\{([^}]+)\}', replace, template)

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation."""
        parts = path.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _resolve_env_vars(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns."""
        def replace(match: re.Match[str]) -> str:
            env_var = match.group(1)
            if ":" in env_var:
                var_name, default = env_var.split(":", 1)
                return os.getenv(var_name, default)
            return os.getenv(env_var, "")
        return re.sub(r'\$\{([^}]+)\}', replace, value)
```

### 4.4 PostgresHandler

**File**: `src/omnibase_infra/handlers/handler_postgres.py` (implementation in Infra)

```python
"""PostgreSQL Protocol Handler."""

import os
import re
import time
from typing import Any

import asyncpg

from omnibase_core.nodes.effect.handlers.protocol_handler import (
    ModelProtocolRequest,
    ModelProtocolResponse,
    ProtocolHandler,
)


class PostgresHandler(ProtocolHandler):
    """
    Handler for PostgreSQL databases.

    Features:
    - SQL query execution
    - Parameterized queries ($1, $2, etc.)
    - Connection pooling via asyncpg
    - Transaction management
    """

    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize asyncpg connection pool."""
        pool_config = config.get("pool", {})

        dsn = config.get("url")
        if not dsn:
            host = self._resolve_env_vars(config.get("host", "localhost"))
            port = config.get("port", 5432)
            database = self._resolve_env_vars(config.get("database", "postgres"))

            auth_config = config.get("authentication", {})
            user = ""
            password = ""
            if auth_config.get("type") == "basic":
                user = self._resolve_env_vars(auth_config.get("basic", {}).get("username", ""))
                password = self._resolve_env_vars(auth_config.get("basic", {}).get("password", ""))

            dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=pool_config.get("min_size", 1),
            max_size=pool_config.get("max_size", 10),
            command_timeout=config.get("timeout_ms", 30000) / 1000
        )

    async def shutdown(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()

    async def execute(
        self,
        request: ModelProtocolRequest,
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:
        """Execute SQL query."""
        start_time = time.perf_counter()

        try:
            req_config = operation_config.get("request", {})
            sql = req_config.get("sql", "")

            # Build SQL parameters from mapping
            sql_params: list[Any] = []
            param_mapping = req_config.get("sql_params", [])
            for param_source in param_mapping:
                if param_source.startswith("${input."):
                    path = param_source[8:-1]
                    value = self._get_nested_value(request.params.get("input", {}), path)
                    sql_params.append(value)
                else:
                    sql_params.append(param_source)

            if not self.pool:
                raise RuntimeError("Pool not initialized")

            async with self.pool.acquire() as conn:
                sql_lower = sql.strip().lower()

                if sql_lower.startswith("select"):
                    rows = await conn.fetch(sql, *sql_params)
                    data = {
                        "rows": [dict(row) for row in rows],
                        "row_count": len(rows)
                    }
                else:
                    result = await conn.execute(sql, *sql_params)
                    parts = result.split()
                    affected = int(parts[-1]) if parts else 0
                    data = {"affected_rows": affected, "result": result}

                duration_ms = (time.perf_counter() - start_time) * 1000

                return ModelProtocolResponse(
                    success=True,
                    data=data,
                    duration_ms=duration_ms
                )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ModelProtocolResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    async def health_check(self) -> bool:
        """Check PostgreSQL connectivity."""
        if not self.pool:
            return False
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception:
            return False

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dict."""
        parts = path.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _resolve_env_vars(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns."""
        def replace(match: re.Match[str]) -> str:
            env_var = match.group(1)
            if ":" in env_var:
                var_name, default = env_var.split(":", 1)
                return os.getenv(var_name, default)
            return os.getenv(env_var, "")
        return re.sub(r'\$\{([^}]+)\}', replace, value)
```

### 4.5 KafkaHandler

**File**: `src/omnibase_infra/handlers/handler_kafka.py` (implementation in Infra)

```python
"""Kafka Protocol Handler for event publishing."""

import asyncio
import json
import os
import re
import time
from typing import Any
from uuid import uuid4

from confluent_kafka import Producer

from omnibase_core.nodes.effect.handlers.protocol_handler import (
    ModelProtocolRequest,
    ModelProtocolResponse,
    ProtocolHandler,
)


class KafkaHandler(ProtocolHandler):
    """
    Handler for Kafka message production.

    Features:
    - Message publishing with delivery confirmation
    - Idempotent producer
    - Batch publishing support
    - Compression (LZ4)
    """

    def __init__(self) -> None:
        self.producer: Producer | None = None
        self.config: dict[str, Any] = {}

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize Kafka producer."""
        bootstrap_servers = self._resolve_env_vars(
            config.get("url", "localhost:9092")
        )

        producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "enable.idempotence": config.get("idempotence", True),
            "acks": config.get("acks", "all"),
            "compression.type": "lz4",
            "linger.ms": 10,
            "batch.size": 32768,
            "request.timeout.ms": config.get("timeout_ms", 30000),
            "delivery.timeout.ms": 120000,
        }

        self.producer = Producer(producer_config)
        self.config = config

    async def shutdown(self) -> None:
        """Flush and close producer."""
        if self.producer:
            self.producer.flush(timeout=10.0)

    async def execute(
        self,
        request: ModelProtocolRequest,
        operation_config: dict[str, Any]
    ) -> ModelProtocolResponse:
        """Publish message to Kafka topic."""
        start_time = time.perf_counter()

        try:
            req_config = operation_config.get("request", {})
            topic = self._substitute_variables(
                req_config.get("topic", ""),
                request.params
            )

            # Build message
            message = {
                "event_id": request.params.get("event_id", str(uuid4())),
                "event_type": request.params.get("event_type", request.operation),
                "correlation_id": request.correlation_id,
                "timestamp": time.time(),
                "payload": request.params.get("payload", {})
            }

            message_bytes = json.dumps(message, default=str).encode("utf-8")
            key = request.params.get("key", request.correlation_id)
            key_bytes = key.encode("utf-8") if isinstance(key, str) else key

            # Create delivery future
            loop = asyncio.get_event_loop()
            future: asyncio.Future[dict[str, Any]] = loop.create_future()

            def delivery_callback(err: Any, msg: Any) -> None:
                if err:
                    if not future.done():
                        future.set_exception(Exception(f"Kafka delivery failed: {err}"))
                else:
                    if not future.done():
                        future.set_result({
                            "partition": msg.partition(),
                            "offset": msg.offset()
                        })

            if not self.producer:
                raise RuntimeError("Producer not initialized")

            self.producer.produce(
                topic=topic,
                value=message_bytes,
                key=key_bytes,
                callback=delivery_callback
            )

            self.producer.poll(0)
            result = await future

            duration_ms = (time.perf_counter() - start_time) * 1000

            return ModelProtocolResponse(
                success=True,
                data={
                    "topic": topic,
                    "partition": result["partition"],
                    "offset": result["offset"]
                },
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ModelProtocolResponse(
                success=False,
                error=str(e),
                duration_ms=duration_ms
            )

    async def health_check(self) -> bool:
        """Check Kafka connectivity."""
        if not self.producer:
            return False
        try:
            metadata = self.producer.list_topics(timeout=5.0)
            return metadata is not None
        except Exception:
            return False

    def _substitute_variables(self, template: str, params: dict[str, Any]) -> str:
        """Substitute ${variable} patterns."""
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if key.startswith("input."):
                path = key[6:]
                value = self._get_nested_value(params.get("input", {}), path)
                return str(value) if value is not None else match.group(0)
            return match.group(0)
        return re.sub(r'\$\{([^}]+)\}', replace, template)

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from dict."""
        parts = path.split(".")
        value: Any = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    def _resolve_env_vars(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns."""
        def replace(match: re.Match[str]) -> str:
            env_var = match.group(1)
            if ":" in env_var:
                var_name, default = env_var.split(":", 1)
                return os.getenv(var_name, default)
            return os.getenv(env_var, "")
        return re.sub(r'\$\{([^}]+)\}', replace, value)
```

### 4.6 Handler Registry

**File**: `src/omnibase_infra/handlers/handler_registry.py` (implementation in Infra)

```python
"""Protocol handler registry."""

from typing import Type

from omnibase_spi.protocols.handlers.protocol_handler import ProtocolHandler
from omnibase_infra.handlers.handler_http_rest import HttpRestHandler
from omnibase_infra.handlers.handler_bolt import BoltHandler
from omnibase_infra.handlers.handler_postgres import PostgresHandler
from omnibase_infra.handlers.handler_kafka import KafkaHandler


class ProtocolHandlerRegistry:
    """
    Registry for protocol handlers.

    Provides a central location to register and retrieve
    protocol handlers by their type identifier.

    Built-in handlers:
    - http_rest: HTTP REST APIs
    - bolt: Neo4j/Memgraph Bolt protocol
    - postgres: PostgreSQL databases
    - kafka: Apache Kafka message bus
    """

    _handlers: dict[str, Type[ProtocolHandler]] = {}

    @classmethod
    def register(cls, protocol_type: str, handler_class: Type[ProtocolHandler]) -> None:
        """
        Register a protocol handler.

        Args:
            protocol_type: Unique identifier for the protocol
            handler_class: Handler class implementing ProtocolHandler
        """
        cls._handlers[protocol_type] = handler_class

    @classmethod
    def get(cls, protocol_type: str) -> Type[ProtocolHandler]:
        """
        Get handler class for protocol type.

        Args:
            protocol_type: Protocol identifier

        Returns:
            Handler class for the protocol

        Raises:
            ValueError: If protocol type is not registered
        """
        handler = cls._handlers.get(protocol_type)
        if not handler:
            available = list(cls._handlers.keys())
            raise ValueError(
                f"Unknown protocol type: {protocol_type}. Available: {available}"
            )
        return handler

    @classmethod
    def list_protocols(cls) -> list[str]:
        """
        List registered protocol types.

        Returns:
            List of registered protocol type identifiers
        """
        return list(cls._handlers.keys())

    @classmethod
    def is_registered(cls, protocol_type: str) -> bool:
        """
        Check if a protocol type is registered.

        Args:
            protocol_type: Protocol identifier to check

        Returns:
            True if registered, False otherwise
        """
        return protocol_type in cls._handlers


# Register built-in handlers
ProtocolHandlerRegistry.register("http_rest", HttpRestHandler)
ProtocolHandlerRegistry.register("bolt", BoltHandler)
ProtocolHandlerRegistry.register("postgres", PostgresHandler)
ProtocolHandlerRegistry.register("kafka", KafkaHandler)
```

### 4.7 Handler-Mixin Integration

As part of the broader mixin dissolution strategy (see [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md)), protocol handlers absorb functionality that was previously implemented via mixins. Each handler becomes a self-contained unit with all necessary cross-cutting concerns built in.

**Handler Absorption Matrix**:

| Handler | Absorbed Mixin Logic | Implementation Notes |
|---------|---------------------|---------------------|
| **HttpRestHandler** | `MixinHttpClient` logic | HTTP client session management, request/response handling, TLS configuration |
| **BoltHandler** | Connection/retry logic from mixins | Driver lifecycle, connection pooling, transaction management |
| **PostgresHandler** | `MixinDatabaseConnection` patterns | asyncpg pool management, connection lifecycle, query execution |
| **KafkaHandler** | `MixinEventBus` patterns | Producer/consumer lifecycle, delivery confirmation, message serialization |

**Cross-Cutting Concerns in Handlers**:

Each handler implements its own:

1. **Health Checks** (absorbs `MixinHealthCheck`):
   - `health_check()` method validates connectivity
   - Protocol-specific health validation (ping, heartbeat, query)
   - Integrated into NodeEffect health aggregation

2. **Metrics Collection** (absorbs `MixinMetrics`):
   - Duration tracking per operation
   - Success/failure counters
   - Protocol-specific metrics (latency, pool utilization)

3. **Retry/Resilience** (absorbs `MixinRetry` patterns):
   - Connection retry logic built into handlers
   - Handlers work with external RetryPolicy for operation-level retries
   - Graceful degradation on connection failures

**Benefits of Handler-Based Approach**:

- **Cohesion**: All protocol-specific logic in one place
- **Testability**: Mock handlers rather than multiple mixins
- **Type Safety**: Protocol-specific configurations validated at handler level
- **Reduced Complexity**: No mixin composition order issues

---

## 5. Resilience Components

### 5.1 RetryPolicy

**File**: `src/omnibase_core/nodes/effect/resilience/retry_policy.py`

```python
"""Retry policy with exponential backoff and jitter."""

import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class RetryPolicy:
    """
    Retry policy with exponential backoff and optional jitter.

    Features:
    - Configurable max attempts
    - Exponential backoff with multiplier
    - Optional jitter to prevent thundering herd
    - Callback on retry for logging/metrics

    Example:
        >>> policy = RetryPolicy(max_attempts=3, initial_delay_ms=1000)
        >>> result = await policy.execute(async_func, arg1, arg2)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ) -> None:
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of attempts (including initial)
            initial_delay_ms: Initial delay between retries in milliseconds
            max_delay_ms: Maximum delay cap in milliseconds
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_attempts = max_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        on_retry: Callable[[int, Exception], None] | None = None,
        **kwargs: Any
    ) -> T:
        """
        Execute function with retry policy.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            on_retry: Optional callback on retry (attempt_number, exception)
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Exception: The last exception if all retries fail
        """
        last_error: Exception = Exception("No attempts executed")

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)

                    if on_retry:
                        on_retry(attempt + 1, e)

                    await asyncio.sleep(delay / 1000)

        raise last_error

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and optional jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in milliseconds
        """
        delay = self.initial_delay_ms * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay_ms)

        if self.jitter:
            # Add 0-50% jitter
            delay = delay * (0.5 + random.random() * 0.5)

        return delay
```

### 5.2 CircuitBreaker

**File**: `src/omnibase_core/nodes/effect/resilience/circuit_breaker.py`

```python
"""Circuit breaker for fault tolerance."""

import time
from enum import Enum


class EnumCircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests blocked
    - HALF_OPEN: Testing recovery, limited requests allowed

    Example:
        >>> cb = CircuitBreaker(failure_threshold=5)
        >>> if cb.is_open():
        ...     raise Exception("Circuit breaker open")
        >>> try:
        ...     result = await make_request()
        ...     cb.record_success()
        ... except:
        ...     cb.record_failure()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_ms: int = 60000,
        half_open_max_calls: int = 3
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures to open circuit
            success_threshold: Consecutive successes to close from half-open
            timeout_ms: Time in ms before transitioning from open to half-open
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_ms = timeout_ms
        self.half_open_max_calls = half_open_max_calls

        self._state = EnumCircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> str:
        """Get current state as string."""
        return self._state.value

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def is_open(self) -> bool:
        """
        Check if circuit breaker is open (blocking requests).

        Also handles automatic transition from OPEN to HALF_OPEN
        after timeout.

        Returns:
            True if requests should be blocked
        """
        if self._state == EnumCircuitBreakerState.OPEN:
            if self._last_failure_time:
                elapsed = (time.time() - self._last_failure_time) * 1000
                if elapsed >= self.timeout_ms:
                    self._state = EnumCircuitBreakerState.HALF_OPEN
                    self._half_open_calls = 0
                    return False
            return True

        if self._state == EnumCircuitBreakerState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                return True
            self._half_open_calls += 1
            return False

        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == EnumCircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._reset()
        else:
            # In CLOSED state, reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == EnumCircuitBreakerState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._state = EnumCircuitBreakerState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.failure_threshold:
            self._state = EnumCircuitBreakerState.OPEN

    def _reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = EnumCircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    def force_open(self) -> None:
        """Force circuit breaker to open state (for testing/admin)."""
        self._state = EnumCircuitBreakerState.OPEN
        self._last_failure_time = time.time()

    def force_close(self) -> None:
        """Force circuit breaker to closed state (for testing/admin)."""
        self._reset()
```

### 5.3 RateLimiter

**File**: `src/omnibase_core/nodes/effect/resilience/rate_limiter.py`

```python
"""Token bucket rate limiter."""

import asyncio
import time


class RateLimiter:
    """
    Token bucket rate limiter.

    Features:
    - Configurable requests per second
    - Burst capacity for handling spikes
    - Non-blocking check or blocking acquire

    Example:
        >>> limiter = RateLimiter(requests_per_second=100, burst_size=10)
        >>> await limiter.acquire()  # Blocks if rate exceeded
        >>> await make_request()
    """

    def __init__(
        self,
        requests_per_second: float = 100.0,
        burst_size: int = 10
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Sustained request rate
            burst_size: Maximum burst capacity (token bucket size)
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size

        self._tokens = float(burst_size)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Note:
            This method blocks until tokens are available.
        """
        async with self._lock:
            await self._refill()

            while self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)
                await self._refill()

            self._tokens -= tokens

    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False if rate limited
        """
        async with self._lock:
            await self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            float(self.burst_size),
            self._tokens + elapsed * self.requests_per_second
        )
        self._last_update = now

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        elapsed = time.time() - self._last_update
        return min(
            float(self.burst_size),
            self._tokens + elapsed * self.requests_per_second
        )
```

### 5.4 Mixin Replacement Note

The resilience components in this section (RetryPolicy, CircuitBreaker, RateLimiter) replace mixin-based resilience patterns that were previously scattered across the codebase. See [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) for the complete dissolution strategy.

**Migration from Mixins**:

| Old Mixin Pattern | New Resilience Component |
|-------------------|-------------------------|
| `MixinRetry.retry_with_backoff()` | `RetryPolicy.execute()` |
| Custom circuit breaker mixins | `CircuitBreaker` with configurable thresholds |
| Ad-hoc rate limiting in mixins | `RateLimiter` with token bucket algorithm |

**Benefits**:
- Centralized, testable resilience logic
- Configurable via YAML contracts (ModelResilienceConfig)
- Consistent behavior across all effect handlers
- Clear separation from business logic

---

## 6. Runtime Class

### 6.1 NodeEffect

**File**: `src/omnibase_core/nodes/effect/runtime.py`

```python
"""
Effect Node Runtime.

This is the base runtime that loads YAML contracts and executes them
using the appropriate protocol handlers.
"""

import logging
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml
from jsonpath_ng import parse as jsonpath_parse
from pydantic import BaseModel, Field

from omnibase_core.nodes.effect.handlers.handler_registry import (
    ProtocolHandlerRegistry,
)
from omnibase_core.nodes.effect.handlers.protocol_handler import (
    ModelProtocolRequest,
    ProtocolHandler,
)
from omnibase_core.nodes.effect.models.model_effect_contract import (
    ModelEffectContract,
)
from omnibase_core.nodes.effect.resilience.circuit_breaker import (
    CircuitBreaker,
)
from omnibase_core.nodes.effect.resilience.rate_limiter import RateLimiter
from omnibase_core.nodes.effect.resilience.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)


class ModelEffectInput(BaseModel):
    """Input model for declarative effect execution."""
    operation: str = Field(..., description="Operation to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    correlation_id: UUID = Field(default_factory=uuid4, description="Correlation ID")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ModelEffectOutput(BaseModel):
    """Output model for declarative effect execution."""
    success: bool = Field(..., description="Whether operation succeeded")
    operation: str = Field(..., description="Operation that was executed")
    data: dict[str, Any] = Field(default_factory=dict, description="Response data")
    error: str | None = Field(default=None, description="Error message if failed")
    correlation_id: UUID = Field(..., description="Correlation ID")
    duration_ms: float = Field(default=0.0, description="Operation duration in ms")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Operation metadata")


class NodeEffect:
    """
    Declarative Effect Node Runtime.

    This class:
    1. Loads and validates YAML contracts using Pydantic models
    2. Initializes the appropriate protocol handler
    3. Routes operations to the handler based on contract
    4. Applies response mapping via JSONPath
    5. Handles resilience (retry, circuit breaker, rate limiter)
    6. Collects metrics and provides health checks

    Example:
        >>> node = NodeEffect(
        ...     contract_path="/path/to/qdrant_vector_effect.yaml"
        ... )
        >>> await node.initialize()
        >>> result = await node.execute_effect(ModelEffectInput(
        ...     operation="upsert",
        ...     params={"collection": "vectors", "embeddings": [...]}
        ... ))
        >>> await node.shutdown()

    Thread Safety:
        - This class is NOT thread-safe
        - Create one instance per async context
        - Protocol handlers manage their own connection pools
    """

    def __init__(
        self,
        contract_path: str | Path | None = None,
        contract: ModelEffectContract | None = None,
        config_overrides: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize declarative effect node.

        Args:
            contract_path: Path to YAML contract file (mutually exclusive with contract)
            contract: Pre-loaded contract model (mutually exclusive with contract_path)
            config_overrides: Optional config overrides (e.g., from environment)

        Raises:
            ValueError: If neither or both contract_path and contract are provided
        """
        if contract_path is None and contract is None:
            raise ValueError("Either contract_path or contract must be provided")
        if contract_path is not None and contract is not None:
            raise ValueError("Only one of contract_path or contract should be provided")

        self.contract_path = Path(contract_path) if contract_path else None
        self.config_overrides = config_overrides or {}

        self.node_id = uuid4()
        self.contract: ModelEffectContract | None = contract
        self.handler: ProtocolHandler | None = None

        # Resilience components
        self.retry_policy: RetryPolicy | None = None
        self.circuit_breaker: CircuitBreaker | None = None
        self.rate_limiter: RateLimiter | None = None

        # Metrics
        self.metrics: dict[str, Any] = {
            "operations_executed": 0,
            "operations_succeeded": 0,
            "operations_failed": 0,
            "total_duration_ms": 0.0,
            "retries_attempted": 0,
            "circuit_breaker_opens": 0,
        }

        # Per-operation metrics
        self.operation_metrics: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        """
        Initialize the effect node.

        This method:
        1. Loads and validates the YAML contract (if not pre-loaded)
        2. Resolves environment variables in configuration
        3. Initializes the protocol handler
        4. Sets up resilience policies

        Raises:
            ValueError: If contract is invalid
            ConnectionError: If handler initialization fails
        """
        # Load contract if path provided
        if self.contract is None and self.contract_path:
            self.contract = self._load_contract()

        if self.contract is None:
            raise ValueError("No contract loaded")

        # Initialize protocol handler
        protocol_type = self.contract.protocol.type.value
        handler_class = ProtocolHandlerRegistry.get(protocol_type)
        self.handler = handler_class()

        # Build connection config
        connection_config = self.contract.connection.model_dump()
        if self.contract.authentication:
            connection_config["authentication"] = self.contract.authentication.model_dump()

        # Resolve environment variables
        connection_config = self._resolve_env_vars_in_config(connection_config)

        await self.handler.initialize(connection_config)

        # Initialize resilience components
        resilience = self.contract.resilience
        if resilience:
            if resilience.retry.enabled:
                self.retry_policy = RetryPolicy(
                    max_attempts=resilience.retry.max_attempts,
                    initial_delay_ms=resilience.retry.initial_delay_ms,
                    max_delay_ms=resilience.retry.max_delay_ms,
                    backoff_multiplier=resilience.retry.backoff_multiplier,
                    jitter=resilience.retry.jitter
                )

            if resilience.circuit_breaker.enabled:
                self.circuit_breaker = CircuitBreaker(
                    failure_threshold=resilience.circuit_breaker.failure_threshold,
                    success_threshold=resilience.circuit_breaker.success_threshold,
                    timeout_ms=resilience.circuit_breaker.timeout_ms
                )

            if resilience.rate_limit.enabled:
                self.rate_limiter = RateLimiter(
                    requests_per_second=resilience.rate_limit.requests_per_second,
                    burst_size=resilience.rate_limit.burst_size
                )

        logger.info(
            f"NodeEffect initialized | "
            f"node_id={self.node_id} | "
            f"contract={self.contract.name} | "
            f"protocol={protocol_type}"
        )

    async def shutdown(self) -> None:
        """Shutdown the effect node gracefully."""
        if self.handler:
            await self.handler.shutdown()

        logger.info(
            f"NodeEffect shutdown | "
            f"node_id={self.node_id} | "
            f"final_metrics={self.metrics}"
        )

    async def execute_effect(
        self,
        input_data: ModelEffectInput
    ) -> ModelEffectOutput:
        """
        Execute an effect operation.

        This method:
        1. Validates the operation exists in contract
        2. Validates input against operation requirements
        3. Applies rate limiting if enabled
        4. Checks circuit breaker state
        5. Executes with retry policy
        6. Maps response via JSONPath
        7. Updates metrics

        Args:
            input_data: Effect input with operation and params

        Returns:
            ModelEffectOutput with result or error
        """
        if self.contract is None:
            return ModelEffectOutput(
                success=False,
                operation=input_data.operation,
                error="Contract not loaded",
                correlation_id=input_data.correlation_id
            )

        start_time = time.perf_counter()
        operation = input_data.operation

        # Validate operation exists
        if operation not in self.contract.operations:
            available = list(self.contract.operations.keys())
            return ModelEffectOutput(
                success=False,
                operation=operation,
                error=f"Unknown operation: {operation}. Available: {available}",
                correlation_id=input_data.correlation_id
            )

        operation_config = self.contract.operations[operation]

        # Validate required fields
        if operation_config.validation:
            validation_error = self._validate_input(
                input_data.params,
                operation_config.validation
            )
            if validation_error:
                return ModelEffectOutput(
                    success=False,
                    operation=operation,
                    error=validation_error,
                    correlation_id=input_data.correlation_id
                )

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Circuit breaker check
        if self.circuit_breaker and self.circuit_breaker.is_open():
            return ModelEffectOutput(
                success=False,
                operation=operation,
                error="Circuit breaker is open",
                correlation_id=input_data.correlation_id,
                metadata={"circuit_breaker_state": "open"}
            )

        # Build protocol request
        protocol_request = ModelProtocolRequest(
            operation=operation,
            params={
                "input": input_data.params,
                "context": input_data.context,
            },
            correlation_id=str(input_data.correlation_id),
            timeout_ms=(
                self.contract.resilience.timeout.request_ms
                if self.contract.resilience
                else 30000
            )
        )

        # Execute with retry
        try:
            if self.handler is None:
                raise RuntimeError("Handler not initialized")

            operation_config_dict = operation_config.model_dump()

            if self.retry_policy:
                response = await self.retry_policy.execute(
                    self.handler.execute,
                    protocol_request,
                    operation_config_dict,
                    on_retry=lambda attempt, error: self._on_retry(attempt, error, operation)
                )
            else:
                response = await self.handler.execute(
                    protocol_request,
                    operation_config_dict
                )

            # Map response
            mapped_data = self._map_response(
                response.data,
                operation_config.response
            )

            # Update circuit breaker
            if self.circuit_breaker:
                if response.success:
                    self.circuit_breaker.record_success()
                else:
                    self.circuit_breaker.record_failure()

            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(operation, response.success, duration_ms)

            return ModelEffectOutput(
                success=response.success,
                operation=operation,
                data=mapped_data,
                error=response.error,
                correlation_id=input_data.correlation_id,
                duration_ms=duration_ms,
                metadata={
                    "protocol_status_code": response.status_code,
                    **response.metadata
                }
            )

        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()

            duration_ms = (time.perf_counter() - start_time) * 1000
            self._update_metrics(operation, False, duration_ms)

            logger.error(
                f"Effect execution failed | "
                f"operation={operation} | "
                f"correlation_id={input_data.correlation_id} | "
                f"error={e}",
                exc_info=True
            )

            return ModelEffectOutput(
                success=False,
                operation=operation,
                error=str(e),
                correlation_id=input_data.correlation_id,
                duration_ms=duration_ms
            )

    async def health_check(self) -> dict[str, Any]:
        """Check health of the effect node and its connection."""
        health: dict[str, Any] = {
            "node_id": str(self.node_id),
            "contract": self.contract.name if self.contract else None,
            "protocol": (
                self.contract.protocol.type.value if self.contract else None
            ),
            "status": "unhealthy",
            "handler_healthy": False,
            "circuit_breaker_state": None,
            "metrics": self.metrics
        }

        if self.handler:
            health["handler_healthy"] = await self.handler.health_check()

        if self.circuit_breaker:
            health["circuit_breaker_state"] = self.circuit_breaker.state

        health["status"] = "healthy" if health["handler_healthy"] else "unhealthy"

        return health

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        ops_executed = self.metrics["operations_executed"]
        avg_duration = (
            self.metrics["total_duration_ms"] / ops_executed
            if ops_executed > 0
            else 0.0
        )

        return {
            **self.metrics,
            "avg_duration_ms": avg_duration,
            "success_rate": (
                self.metrics["operations_succeeded"] / ops_executed
                if ops_executed > 0
                else 0.0
            ),
            "by_operation": self.operation_metrics,
            "node_id": str(self.node_id),
            "contract": self.contract.name if self.contract else None
        }

    def _load_contract(self) -> ModelEffectContract:
        """Load and validate YAML contract from file."""
        if not self.contract_path:
            raise ValueError("No contract path provided")

        with open(self.contract_path) as f:
            raw_contract = yaml.safe_load(f)

        return ModelEffectContract.model_validate(raw_contract)

    def _resolve_env_vars_in_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve environment variables in configuration."""
        import os
        import re

        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                def replace(match: re.Match[str]) -> str:
                    env_var = match.group(1)
                    # Handle defaults: ${VAR:default}
                    if ":" in env_var:
                        var_name, default = env_var.split(":", 1)
                        return self.config_overrides.get(
                            var_name,
                            os.getenv(var_name, default)
                        )
                    return self.config_overrides.get(
                        env_var,
                        os.getenv(env_var, "")
                    )
                return re.sub(r'\$\{([^}]+)\}', replace, value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value

        return resolve_value(config)

    def _validate_input(
        self,
        params: dict[str, Any],
        validation: Any  # ModelValidationConfig
    ) -> str | None:
        """Validate input against operation requirements."""
        if not validation:
            return None

        # Check required fields
        for field in validation.required_fields:
            if field not in params:
                return f"Missing required field: {field}"
            if params[field] is None:
                return f"Required field cannot be null: {field}"

        # Check field types
        for field, expected_type in validation.field_types.items():
            if field in params:
                actual_type = type(params[field]).__name__
                if actual_type != expected_type and expected_type not in ["any", "Any"]:
                    return f"Field {field} expected type {expected_type}, got {actual_type}"

        return None

    def _map_response(
        self,
        response_data: dict[str, Any] | None,
        response_config: Any  # ModelResponseConfig | None
    ) -> dict[str, Any]:
        """Map response data using JSONPath expressions."""
        if not response_data:
            return {}

        if not response_config or not response_config.mapping:
            return response_data

        result: dict[str, Any] = {}
        for output_field, jsonpath_expr in response_config.mapping.items():
            try:
                # Handle default syntax: $.field ?? default
                default_value: Any = None
                if " ?? " in jsonpath_expr:
                    path, default = jsonpath_expr.split(" ?? ", 1)
                    jsonpath_expr = path.strip()
                    default_value = default.strip()

                # Parse and execute JSONPath
                jsonpath_parser = jsonpath_parse(jsonpath_expr)
                matches = jsonpath_parser.find(response_data)

                if matches:
                    if len(matches) == 1:
                        result[output_field] = matches[0].value
                    else:
                        result[output_field] = [m.value for m in matches]
                elif default_value is not None:
                    try:
                        import json
                        result[output_field] = json.loads(default_value)
                    except json.JSONDecodeError:
                        result[output_field] = default_value

            except Exception as e:
                logger.warning(
                    f"JSONPath mapping failed | "
                    f"field={output_field} | "
                    f"expr={jsonpath_expr} | "
                    f"error={e}"
                )

        return result

    def _on_retry(self, attempt: int, error: Exception, operation: str) -> None:
        """Callback when retry is attempted."""
        self.metrics["retries_attempted"] += 1
        logger.warning(
            f"Retrying operation | "
            f"operation={operation} | "
            f"attempt={attempt} | "
            f"error={error}"
        )

    def _update_metrics(
        self,
        operation: str,
        success: bool,
        duration_ms: float
    ) -> None:
        """Update operation metrics."""
        self.metrics["operations_executed"] += 1
        self.metrics["total_duration_ms"] += duration_ms

        if success:
            self.metrics["operations_succeeded"] += 1
        else:
            self.metrics["operations_failed"] += 1

        # Per-operation metrics
        if operation not in self.operation_metrics:
            self.operation_metrics[operation] = {
                "executed": 0,
                "succeeded": 0,
                "failed": 0,
                "total_duration_ms": 0.0
            }

        op_metrics = self.operation_metrics[operation]
        op_metrics["executed"] += 1
        op_metrics["total_duration_ms"] += duration_ms

        if success:
            op_metrics["succeeded"] += 1
        else:
            op_metrics["failed"] += 1
```

---

## 7. Implementation Phases

### Phase 1: Pydantic Models (Day 1)

**Tasks**:
1. Create package structure: `src/omnibase_core/nodes/effect/models/`
2. Implement all model files:
   - `model_effect_contract.py` (root contract)
   - `model_protocol_config.py`
   - `model_connection_config.py`
   - `model_auth_config.py`
   - `model_operation_config.py`
   - `model_request_config.py`
   - `model_response_config.py`
   - `model_resilience_config.py`
   - `model_events_config.py`
   - `model_observability_config.py`
3. Add `__init__.py` with exports
4. Write unit tests for model validation

**Deliverables**:
- All model files created
- 100% test coverage on model validation
- JSON schema generation working

### Phase 2: Protocol Handlers (Days 2-3)

**Tasks**:
1. Create handlers package: `src/omnibase_core/nodes/effect/handlers/`
2. Implement base class: `protocol_handler.py`
3. Implement handlers:
   - Day 2: `handler_http_rest.py`, `handler_bolt.py`
   - Day 3: `handler_postgres.py`, `handler_kafka.py`
4. Implement registry: `handler_registry.py`
5. Write unit tests with mocks

**Deliverables**:
- All handler files created
- Mock-based unit tests passing
- Handler registry working

### Phase 3: Resilience Components (Day 4)

**Tasks**:
1. Create resilience package: `src/omnibase_core/nodes/effect/resilience/`
2. Implement components:
   - `retry_policy.py`
   - `circuit_breaker.py`
   - `rate_limiter.py`
3. Add `__init__.py` with exports
4. Write comprehensive unit tests

**Deliverables**:
- All resilience components created
- Unit tests for edge cases (timing, state transitions)
- Documentation for each component

### Phase 4: Runtime Integration (Day 5)

**Tasks**:
1. Implement `runtime.py` (NodeEffect)
2. Wire up all components:
   - Contract loading and validation
   - Handler initialization
   - Resilience policy application
   - JSONPath response mapping
   - Metrics collection
3. Add `__init__.py` for package root
4. Write integration tests

**Deliverables**:
- NodeEffect fully functional
- Integration tests with mocked handlers
- Example usage documentation

### Phase 5: Testing & Documentation (Days 6-7)

**Tasks**:
1. Day 6: Additional tests
   - Handler integration tests (requires test containers)
   - Performance benchmarks
   - Edge case testing
2. Day 7: Documentation
   - API reference documentation
   - Usage examples
   - Migration guide for existing effects
   - Update CHANGELOG.md

**Deliverables**:
- >90% test coverage
- Complete API documentation
- Migration guide

---

## 8. Testing Strategy

### 8.1 Unit Tests

**Location**: `tests/unit/nodes/effect/`

**Structure**:
```
tests/unit/nodes/effect/
├── models/
│   ├── test_model_effect_contract.py
│   ├── test_model_protocol_config.py
│   ├── test_model_connection_config.py
│   ├── test_model_auth_config.py
│   ├── test_model_operation_config.py
│   ├── test_model_resilience_config.py
│   └── test_model_observability_config.py
├── handlers/
│   ├── test_handler_http_rest.py
│   ├── test_handler_bolt.py
│   ├── test_handler_postgres.py
│   ├── test_handler_kafka.py
│   └── test_handler_registry.py
├── resilience/
│   ├── test_retry_policy.py
│   ├── test_circuit_breaker.py
│   └── test_rate_limiter.py
└── test_runtime.py
```

**Key Test Cases**:

1. **Model Validation**:
   - Valid contract parsing
   - Invalid contract rejection (missing fields, wrong types)
   - Default value application
   - Enum validation
   - Nested model validation

2. **Handler Tests**:
   - Initialization with various configs
   - Request execution (mocked responses)
   - Variable substitution
   - Authentication header building
   - Error handling

3. **Resilience Tests**:
   - Retry with exponential backoff
   - Circuit breaker state transitions
   - Rate limiter token bucket behavior
   - Concurrency handling

4. **Runtime Tests**:
   - Contract loading from YAML
   - Operation routing
   - Response mapping with JSONPath
   - Metrics collection
   - Health check behavior

### 8.2 Integration Tests

**Location**: `tests/integration/nodes/effect/`

**Prerequisites**:
- Docker for test containers
- Test fixtures for each protocol

**Test Scenarios**:
1. HTTP REST handler against mock server
2. PostgreSQL handler against test database
3. Kafka handler against Redpanda container
4. Full end-to-end contract execution

### 8.3 Contract Validation Tests

**Location**: `tests/unit/nodes/effect/contracts/`

**Sample Contracts**:
- Valid minimal contract
- Full-featured contract with all options
- Invalid contracts (various failure modes)
- Edge cases (empty operations, complex JSONPath)

---

## 9. Dependencies

> **IMPORTANT**: I/O-related dependencies (`aiohttp`, `asyncpg`, `neo4j`, `confluent-kafka`) belong to `omnibase_infra`, NOT `omnibase_core`. Core only depends on pure libraries like Pydantic, PyYAML, and jsonpath-ng.

### 9.1 omnibase_core Dependencies (Pure Code)

```toml
# omnibase_core/pyproject.toml
[tool.poetry.dependencies]
pyyaml = "^6.0.2"        # YAML parsing (file I/O done by runtime caller)
pydantic = "^2.12.5"     # Model validation
jsonpath-ng = "^1.6.0"   # JSONPath parsing (pure string processing)
```

### 9.2 omnibase_infra Dependencies (I/O Code)

```toml
# omnibase_infra/pyproject.toml
[tool.poetry.dependencies]
omnibase_core = "^0.2.0"     # Core models and resilience
omnibase_spi = "^0.2.0"      # Protocol interfaces

# Handler I/O dependencies
aiohttp = "^3.9.0"           # HTTP client (HttpRestHandler)
asyncpg = "^0.29.0"          # PostgreSQL async driver (PostgresHandler)
neo4j = "^5.15.0"            # Neo4j/Memgraph Bolt driver (BoltHandler)
confluent-kafka = "^2.3.0"   # Kafka client (KafkaHandler)
```

### 9.3 Development Dependencies

```toml
[tool.poetry.group.dev.dependencies]
# Already present
pytest = "^8.4.0"
pytest-asyncio = "^0.25.0"
aioresponses = "^0.7.6"  # Mocking aiohttp

# Consider adding
testcontainers = "^3.7.0"  # Docker test containers
```

### 9.4 Version Constraints

| Package | Min Version | Max Version | Repository | Notes |
|---------|-------------|-------------|------------|-------|
| neo4j | 5.15.0 | <6.0.0 | omnibase_infra | Async driver required |
| confluent-kafka | 2.3.0 | <3.0.0 | omnibase_infra | Production-grade Kafka |
| aiohttp | 3.9.0 | <4.0.0 | omnibase_infra | HTTP client |
| asyncpg | 0.29.0 | <1.0.0 | omnibase_infra | PostgreSQL async |
| jsonpath-ng | 1.6.0 | <2.0.0 | omnibase_core | JSONPath parsing |
| pydantic | 2.12.5 | <3.0.0 | omnibase_core | Model validation |

---

## 10. Public API

### 10.1 Package Exports

> **NOTE**: Handlers are exported from `omnibase_infra`, not `omnibase_core`. The core package exports only models, resilience, and runtime.

**File**: `src/omnibase_core/nodes/effect/__init__.py`

```python
"""
Effect Node Infrastructure (Core).

This package provides the PURE CODE components for effect nodes:
- Models: Contract validation models (Pydantic)
- Resilience: Retry, circuit breaker, rate limiter (pure algorithms)
- Runtime: NodeEffect execution engine (orchestration only)

NOTE: Protocol handlers (HTTP, Bolt, PostgreSQL, Kafka) are in omnibase_infra.
Import handlers from omnibase_infra.handlers for I/O operations.
"""

# Models
from omnibase_core.nodes.effect.models import (
    ModelEffectContract,
    ModelProtocolConfig,
    ModelConnectionConfig,
    ModelAuthConfig,
    ModelOperationConfig,
    ModelRequestConfig,
    ModelResponseConfig,
    ModelResilienceConfig,
    ModelEventsConfig,
    ModelObservabilityConfig,
    EnumProtocolType,
    EnumAuthType,
)

# Resilience
from omnibase_core.nodes.effect.resilience import (
    RetryPolicy,
    CircuitBreaker,
    EnumCircuitBreakerState,
    RateLimiter,
)

# Runtime
from omnibase_core.nodes.effect.runtime import (
    NodeEffect,
    ModelEffectInput,
    ModelEffectOutput,
)

__all__ = [
    # Models
    "ModelEffectContract",
    "ModelProtocolConfig",
    "ModelConnectionConfig",
    "ModelAuthConfig",
    "ModelOperationConfig",
    "ModelRequestConfig",
    "ModelResponseConfig",
    "ModelResilienceConfig",
    "ModelEventsConfig",
    "ModelObservabilityConfig",
    "EnumProtocolType",
    "EnumAuthType",
    # Resilience
    "RetryPolicy",
    "CircuitBreaker",
    "EnumCircuitBreakerState",
    "RateLimiter",
    # Runtime
    "NodeEffect",
    "ModelEffectInput",
    "ModelEffectOutput",
]
```

**File**: `src/omnibase_infra/handlers/__init__.py`

```python
"""
Protocol Handlers (Infrastructure).

This package provides the I/O implementations for effect nodes:
- HttpRestHandler: HTTP REST API interactions
- BoltHandler: Neo4j/Memgraph Bolt protocol
- PostgresHandler: PostgreSQL database operations
- KafkaHandler: Apache Kafka message publishing

These handlers implement the ProtocolHandler interface from omnibase_spi.
"""

from omnibase_spi.protocols.handlers.protocol_handler import (
    ProtocolHandler,
    ModelProtocolRequest,
    ModelProtocolResponse,
)
from omnibase_infra.handlers.handler_http_rest import HttpRestHandler
from omnibase_infra.handlers.handler_bolt import BoltHandler
from omnibase_infra.handlers.handler_postgres import PostgresHandler
from omnibase_infra.handlers.handler_kafka import KafkaHandler
from omnibase_infra.handlers.handler_registry import ProtocolHandlerRegistry

__all__ = [
    # Interface (re-exported from SPI)
    "ProtocolHandler",
    "ModelProtocolRequest",
    "ModelProtocolResponse",
    # Implementations
    "HttpRestHandler",
    "BoltHandler",
    "PostgresHandler",
    "KafkaHandler",
    "ProtocolHandlerRegistry",
]
```

### 10.2 Backward Compatibility

This update transitions to the new naming convention where declarative nodes become the default:

1. **`NodeEffect`**: Now refers to the declarative runtime (formerly `NodeEffectDeclarative`)
2. **`NodeEffectLegacy`**: Old imperative base class (deprecated, see [Naming Convention](#naming-convention))
3. **Main namespace**: All effect code now in `nodes/effect/` package directly
4. **Legacy namespace**: Deprecated imperative nodes in `nodes/effect/legacy/`

**Migration**: Import `NodeEffect` from `omnibase_core.nodes.effect` for the new declarative runtime.

### 10.3 Integration with Existing Code

The effect node runtime integrates with existing infrastructure:

```python
# Example: Using effect node in consuming repo
from omnibase_core.nodes.effect import (
    NodeEffect,
    ModelEffectInput,
)

# Import handlers from omnibase_infra (I/O implementations)
from omnibase_infra.handlers import (
    ProtocolHandlerRegistry,
    HttpRestHandler,
)

# Ensure handlers are registered (typically done at app startup)
# ProtocolHandlerRegistry auto-registers built-in handlers on import

# Load contract from YAML
node = NodeEffect(
    contract_path="contracts/effects/qdrant_vector_effect.yaml"
)
await node.initialize()

# Execute operation
result = await node.execute_effect(
    ModelEffectInput(
        operation="upsert",
        params={"collection": "vectors", "embeddings": [...]}
    )
)

# Shutdown
await node.shutdown()
```

> **NOTE**: The `NodeEffect` runtime in core resolves handlers via `ProtocolHandlerRegistry`. Ensure `omnibase_infra.handlers` is imported at application startup to register the built-in handlers.

---

## 11. Migration Guide

### 11.1 Migrating from Legacy Imperative Nodes

For consuming repositories (omniintelligence, etc.) to migrate from `NodeEffectLegacy` (formerly `NodeEffect`) to the new `NodeEffect` (declarative runtime):

**Step 1: Create YAML Contract**

Convert the Python configuration to YAML:

```yaml
# contracts/effects/qdrant_vector_effect.yaml
name: qdrant_vector_effect
version: {major: 1, minor: 0, patch: 0}
protocol:
  type: http_rest
connection:
  url: http://${QDRANT_HOST}:${QDRANT_PORT}
operations:
  upsert:
    description: Upsert vector to collection
    request:
      method: PUT
      path: /collections/${input.collection}/points
      body:
        points:
          - id: ${input.vector_id}
            vector: ${input.embeddings}
```

**Step 2: Replace Legacy Node**

```python
# Before: Legacy Imperative (DEPRECATED)
from omnibase_core.nodes.effect.legacy import NodeEffectLegacy

class NodeQdrantVectorEffect(NodeEffectLegacy):
    async def process(self, input_data):
        # 100+ lines of boilerplate
        ...

# After: New NodeEffect (Declarative Runtime)
from omnibase_core.nodes.effect import NodeEffect

node = NodeEffect(
    contract_path="contracts/effects/qdrant_vector_effect.yaml"
)
```

**Step 3: Test Migration**

1. Run existing integration tests against new node
2. Verify metrics collection matches
3. Test error handling and resilience

### 11.2 Custom Protocol Handlers

For protocols not covered by built-in handlers:

```python
# Import interface from SPI, registry from Infra
from omnibase_spi.protocols.handlers.protocol_handler import ProtocolHandler
from omnibase_infra.handlers import ProtocolHandlerRegistry

class CustomHandler(ProtocolHandler):
    """Custom handler - place in omnibase_infra/handlers/ or your own infra package."""

    async def initialize(self, config):
        ...

    async def execute(self, request, operation_config):
        ...

    async def health_check(self):
        ...

    async def shutdown(self):
        ...

# Register custom handler (typically at app startup)
ProtocolHandlerRegistry.register("custom_protocol", CustomHandler)
```

> **NOTE**: Custom handlers that perform I/O should live in an infrastructure package (e.g., `omnibase_infra` or your application's infra layer), not in core.

### 11.3 Migrating from Mixin-Based Effects

Effects that were previously built using mixins like `MixinEventBus`, `MixinHealthCheck`, `MixinHttpClient`, or `MixinRetry` should migrate to the handler-based approach. See [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) for the complete dissolution strategy.

**Before (Mixin-Based)**:

```python
from omnibase_core.mixins import (
    MixinEventBus,
    MixinHealthCheck,
    MixinHttpClient,
    MixinRetry,
)

class NodeOldStyleEffect(
    NodeEffectLegacy,
    MixinEventBus,
    MixinHealthCheck,
    MixinHttpClient,
    MixinRetry,
):
    """Effect with scattered cross-cutting concerns via mixins."""

    async def process(self, input_data):
        # Manually coordinate between mixins
        if not await self.health_check():
            raise Exception("Unhealthy")

        response = await self.retry_with_backoff(
            lambda: self.http_client.post(...)
        )

        await self.publish_event(...)
        return response
```

**After (Handler-Based)**:

```python
from omnibase_core.nodes.effect import NodeEffect, ModelEffectInput

# All cross-cutting concerns are handled by:
# 1. Protocol handlers (HTTP, Kafka, etc.)
# 2. Resilience components (retry, circuit breaker)
# 3. NodeEffect runtime (health checks, metrics)

node = NodeEffect(
    contract_path="contracts/effects/my_effect.yaml"
)
await node.initialize()

# Clean, simple execution - no mixin coordination needed
result = await node.execute_effect(
    ModelEffectInput(operation="process", params={...})
)
```

**Key Migration Points**:

1. **Health Checks**: Handled automatically by handlers (`health_check()` method) and aggregated by NodeEffect runtime
2. **HTTP Clients**: Replaced by `HttpRestHandler` with built-in connection pooling and TLS
3. **Event Bus**: Replaced by `KafkaHandler` for Kafka effects, or use events config in contract
4. **Retry Logic**: Replaced by `RetryPolicy` configured via contract YAML
5. **Metrics**: Collected automatically by NodeEffect runtime

**Migration Checklist**:

- [ ] Create YAML contract defining protocol, connection, and operations
- [ ] Remove mixin inheritance from effect class
- [ ] Replace custom HTTP/DB clients with appropriate handler
- [ ] Move retry configuration to contract's `resilience` section
- [ ] Verify health checks work via `node.health_check()`
- [ ] Validate metrics are being collected via `node.get_metrics()`

---

## Appendix A: Example Contract

Full example of a Qdrant Vector Effect contract:

```yaml
name: qdrant_vector_effect
version:
  major: 1
  minor: 0
  patch: 0

description: |
  Effect node for vector storage operations in Qdrant.
  Supports upsert, search, delete, and collection management.

protocol:
  type: http_rest
  content_type: application/json

connection:
  url: http://${QDRANT_HOST:localhost}:${QDRANT_PORT:6333}
  timeout_ms: 30000
  pool:
    min_size: 2
    max_size: 10

authentication:
  type: api_key
  api_key:
    header: api-key
    prefix: ""
    value: ${QDRANT_API_KEY:}

operations:
  upsert:
    description: Upsert vector to collection
    request:
      method: PUT
      path: /collections/${input.collection}/points
      query:
        wait: "true"
      body:
        points:
          - id: ${input.vector_id}
            vector: ${input.embeddings}
            payload: ${input.metadata}
    response:
      success_codes: [200]
      mapping:
        operation_id: "$.result.operation_id"
        status: "$.result.status"
    validation:
      required_fields:
        - collection
        - vector_id
        - embeddings

  search:
    description: Search for similar vectors
    request:
      method: POST
      path: /collections/${input.collection}/points/search
      body:
        vector: ${input.query_vector}
        limit: ${input.top_k:10}
        with_payload: true
    response:
      success_codes: [200]
      mapping:
        results: "$.result[*]"

resilience:
  retry:
    enabled: true
    max_attempts: 3
    initial_delay_ms: 1000
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout_ms: 60000

events:
  consume:
    topic: dev.archon-intelligence.effect.qdrant-vector.request.v1
    group_id: qdrant-vector-effect
  produce:
    success_topic: dev.archon-intelligence.effect.qdrant-vector.response.v1
    dlq_topic: dev.archon-intelligence.effect.qdrant-vector.request.v1.dlq

observability:
  metrics:
    enabled: true
    prefix: omniintelligence_qdrant
  logging:
    level: INFO

metadata:
  author: omniintelligence
  created_at: "2025-12-02"
  tags:
    - vector
    - qdrant
    - storage
```

---

## Appendix B: Reference Links

| Document | Description |
|----------|-------------|
| [Mixin Migration Plan](./MIXIN_MIGRATION_PLAN.md) | Complete strategy for dissolving mixins into handlers, runtime, and domain libraries |
| [ONEX Four-Node Architecture](./architecture/ONEX_FOUR_NODE_ARCHITECTURE.md) | Overall ONEX node architecture documentation |
| [Node Building Guide](./guides/node-building/README.md) | Step-by-step guide for building ONEX nodes |

---

## Appendix C: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-02 | OmniIntelligence Team | Initial specification |
| 1.1.0 | 2025-12-02 | OmniIntelligence Team | Updated naming conventions: declarative nodes are now default (no suffix), legacy imperative nodes use `Legacy` suffix |
| 1.2.0 | 2025-12-03 | OmniIntelligence Team | Added mixin migration references (Section 4.7, 5.4, 11.3) and cross-references to MIXIN_MIGRATION_PLAN.md |

---

*Document generated from EFFECT_NODES_SPEC.md specification*
