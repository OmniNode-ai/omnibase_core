# Contract-Driven NodeEffect Specification v1.0

> **Version**: 1.0.0
> **Status**: PROTOCOL FROZEN - Implementation Ready
> **Scope**: omnibase_core
> **Last Updated**: 2025-12-07
> **Revision**: R17 - Architectural audit complete (Core/SPI separation, registry pattern, execution semantics)
> **See Also**: [ONEX Terminology Guide](../standards/onex_terminology.md) for canonical definitions of Effect, Handler, and other ONEX concepts.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Principles](#architectural-principles)
3. [v1.0 Scope](#v10-scope)
4. [Component Specifications](#component-specifications)
5. [Contract Schema](#contract-schema)
6. [Validation Rules](#validation-rules)
7. [Execution Flow](#execution-flow)
8. [Resilience Patterns](#resilience-patterns)
9. [Migration Strategy](#migration-strategy)
10. [Testing Strategy](#testing-strategy)
11. [Version Roadmap](#version-roadmap)

---

## Executive Summary

This document specifies the contract-driven `NodeEffect` implementation for ONEX v1.0. The design follows the pattern established by `NodeCompute` (PR #115), enabling **zero custom Python code** effect nodes driven entirely by declarative YAML contracts.

### Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Contract-Driven** | All I/O logic defined in YAML, no custom Python required |
| **Handler Dispatch** | Effects dispatch to typed handlers (HTTP, DB, Kafka, Filesystem) |
| **Resilience First** | Built-in retry policies, circuit breakers, transaction management |
| **Abort-on-First-Failure** | Sequential operations abort on first error (matching NodeCompute v1.0) |
| **Zero Any Types** | Full type safety throughout implementation |
| **Discriminated Unions** | Handler-specific IO configs validated at contract load time |
| **Idempotency-Aware Retries** | Retry policies respect operation idempotency |
| **Enum-Based Handler Types** | Handler types use `EnumEffectHandlerType`, not raw strings |
| **Typed Circuit Breaker State** | Uses existing `ModelCircuitBreaker` infrastructure (typed, no `dict[str, Any]`) |
| **Resolved IO Context** | Templates resolved inside retry loop via `ModelResolvedIOContext` |
| **Handler Contract** | Handlers receive fully-resolved context, never raw templates |
| **Operation-Level Timeout** | `operation_timeout_ms` prevents retry stacking from exceeding intended limits |

### Pattern Alignment

```
NodeCompute v1.0 Pattern          NodeEffect v1.0 Pattern
─────────────────────────         ─────────────────────────
ModelComputeSubcontract    →      ModelEffectSubcontract
MixinComputeExecution      →      MixinEffectExecution
compute_executor.py        →      effect_executor.py
Sequential Pipelines       →      Sequential I/O Operations
```

---

## Architectural Principles

### Core/SPI Layering

**Critical Rule**: Core defines vocabulary; SPI implements execution. Dependencies flow downward only.

```
┌─────────────────────────────────────────────────────────────┐
│                         SPI Layer                           │
│  (Implements protocols, execution glue, adapters)           │
│  - ProtocolEffectHandler implementations                    │
│  - HttpRestAdapter, DbAdapter, KafkaAdapter                 │
│                           │                                 │
│                           │ consumes (never defines)        │
│                           ▼                                 │
├─────────────────────────────────────────────────────────────┤
│                        Core Layer                           │
│  (Defines models, types, vocabularies)                      │
│  - EnumEffectHandlerType                                    │
│  - ModelEffectSubcontract                                   │
│  - ModelHttpIOConfig, ModelDbIOConfig, etc.                 │
│  - ModelEffectRetryPolicy, ModelCircuitBreakerConfig        │
│  - ProtocolEffectHandler (protocol definition)              │
└─────────────────────────────────────────────────────────────┘
```

**Ownership Rules**:
- **Core owns**: Effect identifiers, handler enumerations, all contract models, protocol definitions
- **SPI owns**: Protocol implementations, adapters, execution glue
- **Never**: SPI defines types that Core depends upon
- **Never**: Core imports from SPI

### Four-Node Context

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   EFFECT    │───▶│   COMPUTE   │───▶│   REDUCER   │───▶│ORCHESTRATOR │
│   (I/O)     │    │ (Process)   │    │(Aggregate)  │    │(Coordinate) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      ▲
      │
      └── THIS DOCUMENT: Contract-driven external interactions
```

### NodeEffect Role

**Purpose**: Manage side effects and external interactions with:
- I/O operations (file, database, API calls, message queues)
- Transaction management with rollback support
- Retry policies and circuit breaker patterns
- Event emission for state changes

### Class Hierarchy

```python
# Current Implementation (to be moved to legacy)
class NodeEffect(NodeCoreBase):
    """Code-driven implementation with inline handlers."""
    pass

# Target Implementation (v1.0)
class NodeEffect(NodeCoreBase, MixinEffectExecution):
    """
    Contract-driven effect node.
    Zero custom Python code - driven by effect subcontract.
    Dispatches to handlers in omnibase_infra.
    """
    pass  # All logic from contract via mixin
```

---

## v1.0 Scope

### In Scope (v1.0)

| Feature | Description |
|---------|-------------|
| Sequential I/O Operations | Execute operations in order, abort on first failure |
| 4 Handler Types | HTTP, Database, Kafka, Filesystem |
| Discriminated Union IO Config | Type-safe, handler-specific configuration |
| Idempotency-Aware Retries | Retry only idempotent operations |
| Circuit Breaker (Process-Local) | Basic open/closed/half-open state management |
| Transaction Boundaries | DB-only, same-connection transactions |
| Response Extraction | JSONPath extraction from responses |
| Template Variables | `${input.field}`, `${env.VAR}`, `${secret.KEY}` substitution |
| Execution Mode | Explicit `sequential_abort` semantics |
| Operation-Level Timeout | `operation_timeout_ms` prevents retry stacking |

### Out of Scope (Deferred)

| Feature | Target Version | Rationale |
|---------|----------------|-----------|
| Parallel I/O Operations | v1.1 | Requires semaphore coordination |
| Conditional Operations | v1.2 | Requires expression language |
| Streaming Responses | v1.2 | Requires async iterator support |
| Custom Handlers | v1.1 | Handler registry pattern needed |
| Rate Limiting | v1.1 | Requires rate limiter integration |
| Bulkhead Pattern | v1.2 | Requires thread pool management |
| Distributed Circuit Breaker | v1.2 | Requires shared state (Redis) |
| Saga/Compensation Handlers | v1.2 | Requires multi-service coordination |

---

## Component Specifications

### 0. Handler Type Enumeration

**Location**: `src/omnibase_core/enums/enum_effect_handler_type.py`

```python
"""
Effect Handler Type Enumeration.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Eliminates raw string handler types to prevent typo bugs and enable IDE completion.
"""

from enum import Enum


class EnumEffectHandlerType(str, Enum):
    """
    Enumeration of supported effect handler types.

    SINGLE SOURCE OF TRUTH for handler type values.
    IO config models use this enum directly as the discriminator field type.

    Using an enum instead of raw strings:
    - Prevents typos ("filesystem" vs "file_system")
    - Enables IDE autocompletion
    - Provides exhaustiveness checking
    - Centralizes handler type definitions
    - Preserves full type safety (no .value string extraction)

    Pydantic Serialization Note:
        Because EnumEffectHandlerType inherits from (str, Enum), Pydantic
        automatically serializes to the string value ("http", "db", etc.)
        when dumping to JSON/YAML. The discriminated union works because
        Pydantic compares the serialized string values during validation.
    """

    HTTP = "http"
    DB = "db"
    KAFKA = "kafka"
    FILESYSTEM = "filesystem"

    @classmethod
    def values(cls) -> list[str]:
        """Return all handler type values."""
        return [member.value for member in cls]
```

### 1. Handler-Specific IO Config Models

**Location**: `src/omnibase_core/models/contracts/subcontracts/effect_io_configs.py`

```python
"""
Effect IO Configuration Models - Discriminated Union Pattern.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Each handler type has its own strongly-typed IO config model.
The discriminator field `handler_type` uses EnumEffectHandlerType directly
for full type safety (no .value string extraction needed).

Pydantic Serialization Note:
    Because EnumEffectHandlerType inherits from (str, Enum), Pydantic
    automatically serializes to the string value ("http", "db", etc.)
    when dumping to JSON/YAML. The discriminated union works because
    Pydantic compares the serialized string values during validation.
"""

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelHttpIOConfig(BaseModel):
    """HTTP-specific IO configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Uses enum directly - SINGLE SOURCE OF TRUTH with full type safety
    handler_type: EnumEffectHandlerType = Field(default=EnumEffectHandlerType.HTTP)

    url_template: str = Field(..., description="URL with ${} placeholders")
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(...)
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: str | None = Field(default=None, description="Request body template")
    query_params: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int = Field(default=30000, ge=100, le=300000)

    # HTTP-specific defaults
    follow_redirects: bool = Field(default=True)
    verify_ssl: bool = Field(default=True)

    @model_validator(mode="after")
    def validate_body_for_mutating_methods(self) -> "ModelHttpIOConfig":
        """
        Require body_template for mutating HTTP methods.

        POST/PUT/PATCH without a body is almost always a user mistake.
        """
        if self.method in ["POST", "PUT", "PATCH"] and self.body_template is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"HTTP {self.method} requires body_template. "
                        f"If empty body is intentional, set body_template to empty string."
            )
        return self


class ModelDbIOConfig(BaseModel):
    """Database-specific IO configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Uses enum directly - SINGLE SOURCE OF TRUTH with full type safety
    handler_type: EnumEffectHandlerType = Field(default=EnumEffectHandlerType.DB)

    # Explicit operation type - eliminates brittle query string parsing
    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(
        ...,
        description="Explicit DB operation type. Use 'raw' for complex queries (requires idempotent=false unless explicitly set)."
    )

    connection_name: str = Field(..., description="Named connection reference")
    query_template: str = Field(..., description="SQL/query template with $1, $2 params")
    query_params: list[str] = Field(default_factory=list, description="Parameter references")
    timeout_ms: int = Field(default=30000, ge=100, le=300000)

    # DB-specific settings
    fetch_size: int | None = Field(default=None, description="Cursor fetch size")
    read_only: bool = Field(default=False, description="Read-only transaction hint")

    @field_validator("operation", mode="before")
    @classmethod
    def normalize_operation_case(cls, v: str) -> str:
        """
        Normalize operation to lowercase to prevent silent idempotency bypasses.

        Without this validator, 'SELECT' vs 'select' could cause the idempotency
        lookup to fail silently (IDEMPOTENCY_DEFAULTS uses uppercase keys like
        'SELECT', but the Literal type requires lowercase). This mismatch could
        allow retries on operations that should not be retried.

        Example of the bug this prevents:
            operation: "SELECT"  # User provides uppercase in YAML
            # Without normalization: Pydantic rejects (not in Literal["select",...])
            # OR if accepted: idempotency lookup may behave unexpectedly
        """
        return v.lower() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_raw_query_safety(self) -> "ModelDbIOConfig":
        """
        Prevent SQL injection via ${input.*} in raw queries.

        Raw queries must use parameterized values ($1, $2) not direct input interpolation.
        Direct interpolation of user input into raw SQL queries creates SQL injection
        vulnerabilities that bypass prepared statement protections.

        SAFE pattern:
            query_template: "SELECT * FROM users WHERE id = $1"
            query_params: ["${input.user_id}"]
            # Template resolution happens in query_params, value is passed as parameter

        UNSAFE pattern (rejected by this validator):
            query_template: "SELECT * FROM users WHERE id = ${input.user_id}"
            # User input directly interpolated into SQL string = SQL injection risk

        This validation only applies to 'raw' operations because:
        - Standard operations (select/insert/update/delete/upsert) have predictable
          query structures that are validated at contract load time
        - Raw operations allow arbitrary SQL, requiring stricter input sanitization
        """
        if self.operation != "raw":
            return self

        import re
        if re.search(r'\$\{input\.', self.query_template):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Raw DB queries must not embed ${input.*} templates directly in query_template. "
                        "Use query_params with $1, $2 placeholders instead to prevent SQL injection. "
                        f"Found direct input interpolation in: {self.query_template[:100]}..."
            )
        return self

    @model_validator(mode="after")
    def validate_param_count_matches_placeholders(self) -> "ModelDbIOConfig":
        """
        Ensure query_params count matches $N placeholders in query_template.

        Prevents runtime errors by catching mismatches at contract load time.

        Examples:
            - query_template="SELECT * FROM users WHERE id = $1" with query_params=["${input.id}"] -> VALID
            - query_template="SELECT * FROM users WHERE id = $1 AND name = $2" with query_params=["${input.id}"] -> INVALID (missing $2 param)
            - query_template="SELECT * FROM users" with query_params=["${input.id}"] -> INVALID (no placeholders but params provided)
        """
        import re

        # Find all $N placeholders (PostgreSQL-style positional parameters)
        placeholders = re.findall(r'\$(\d+)', self.query_template)

        if not placeholders:
            if self.query_params:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"query_params provided ({len(self.query_params)} items) but no $N placeholders found in query_template. "
                            f"Either add placeholders or remove query_params."
                )
            return self

        # Find the maximum placeholder number (e.g., $1, $2, $3 means max=3)
        max_placeholder = max(int(p) for p in placeholders)
        expected_count = max_placeholder  # $1, $2, $3 means 3 params expected
        actual_count = len(self.query_params)

        if actual_count != expected_count:
            unique_placeholders = sorted(set(int(p) for p in placeholders))
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"query_params count ({actual_count}) does not match "
                        f"placeholder count ({expected_count}). "
                        f"Found placeholders: ${', $'.join(str(p) for p in unique_placeholders)}. "
                        f"Ensure query_params has exactly {expected_count} entries."
            )

        return self


class ModelKafkaIOConfig(BaseModel):
    """Kafka-specific IO configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Uses enum directly - SINGLE SOURCE OF TRUTH with full type safety
    handler_type: EnumEffectHandlerType = Field(default=EnumEffectHandlerType.KAFKA)

    topic: str = Field(..., description="Target Kafka topic")
    payload_template: str = Field(
        ...,  # REQUIRED - no silent empty payload defaults
        description="Template for message payload. Use ${input.field} references."
    )
    partition_key_template: str | None = Field(default=None, description="Partition key template")
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_ms: int = Field(default=30000, ge=100, le=300000)

    # Kafka-specific settings
    acks: Literal["0", "1", "all"] = Field(default="all", description="Producer acks setting")
    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(default="none")


class ModelFilesystemIOConfig(BaseModel):
    """
    Filesystem-specific IO configuration.

    > **Filesystem Atomicity**: When `atomic=true` for `move` operations,
    > cross-device moves (different filesystems) will **fail fast** rather than
    > falling back to non-atomic copy+delete. This ensures atomicity guarantees
    > are explicit, not silently degraded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Uses enum directly - SINGLE SOURCE OF TRUTH with full type safety
    handler_type: EnumEffectHandlerType = Field(default=EnumEffectHandlerType.FILESYSTEM)

    file_path_template: str = Field(..., description="File path with ${} placeholders")
    operation: Literal["read", "write", "delete", "move", "copy"] = Field(...)
    timeout_ms: int = Field(default=30000, ge=100, le=300000)

    # Filesystem-specific settings
    atomic: bool = Field(default=True, description="Use atomic write (write to temp, then rename)")
    create_dirs: bool = Field(default=True, description="Create parent directories if missing")
    encoding: str = Field(default="utf-8", description="File encoding for text operations")
    mode: str | None = Field(default=None, description="File permissions (e.g., '0644')")

    @model_validator(mode="after")
    def validate_atomicity_semantics(self) -> "ModelFilesystemIOConfig":
        """
        Validate atomic flag is only set for operations that support it.

        Atomicity Semantics:
        - delete: Cannot be atomic (file gone = done)
        - copy: Cannot be atomic (no rename-based atomicity)
        - move: Atomic only within same filesystem (cross-device moves fail fast)
        - write: Atomic via temp file + rename
        - read: N/A (no writes)

        When atomic=true for 'move' operations, cross-device moves (different
        filesystems) will FAIL FAST rather than falling back to non-atomic
        copy+delete. This ensures atomicity guarantees are explicit, not
        silently degraded.
        """
        if not self.atomic:
            return self

        if self.operation in ["delete", "copy", "read"]:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"atomic=true not supported for '{self.operation}' operation. "
                        f"Atomic writes only apply to 'write' and 'move' (same-filesystem) operations."
            )
        return self


# Type alias for discriminated union
EffectIOConfig = ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig
```

### 1.1 Resolved IO Context (Handler Input)

**Location**: `src/omnibase_core/models/contracts/subcontracts/effect_resolved_context.py`

```python
"""
Resolved IO Context - Template-free handler input.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Handlers receive ModelResolvedIOContext, NOT raw io_config with templates.
All ${...} placeholders are resolved before handler invocation.

HANDLER CONTRACT:
- Handlers MUST NOT perform template resolution
- Handlers receive concrete values only
- Handlers MUST NOT import or depend on effect_executor.py

Type Safety Note:
    handler_type uses EnumEffectHandlerType directly for consistency with
    IO config models. Pydantic serializes (str, Enum) to string values
    automatically, maintaining discriminated union functionality.
"""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class ModelResolvedHttpContext(BaseModel):
    """Resolved HTTP context - all templates substituted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_type: EnumEffectHandlerType = EnumEffectHandlerType.HTTP

    # Resolved values (no ${...} placeholders)
    url: str = Field(..., description="Fully resolved URL")
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(...)
    headers: dict[str, str] = Field(default_factory=dict, description="Resolved headers")
    body: str | None = Field(default=None, description="Resolved request body")
    query_params: dict[str, str] = Field(default_factory=dict, description="Resolved query params")
    timeout_ms: int = Field(...)

    # Pass-through from io_config
    follow_redirects: bool = Field(default=True)
    verify_ssl: bool = Field(default=True)


class ModelResolvedDbContext(BaseModel):
    """Resolved DB context - all templates substituted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_type: EnumEffectHandlerType = EnumEffectHandlerType.DB

    operation: Literal["select", "insert", "update", "delete", "upsert", "raw"] = Field(...)
    connection_name: str = Field(...)
    query: str = Field(..., description="Resolved SQL query")
    params: list[str | int | float | bool | None] = Field(
        default_factory=list,
        description="Resolved parameter values (not templates)"
    )
    timeout_ms: int = Field(...)
    fetch_size: int | None = Field(default=None)
    read_only: bool = Field(default=False)


class ModelResolvedKafkaContext(BaseModel):
    """Resolved Kafka context - all templates substituted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_type: EnumEffectHandlerType = EnumEffectHandlerType.KAFKA

    topic: str = Field(...)
    partition_key: str | None = Field(default=None, description="Resolved partition key")
    headers: dict[str, str] = Field(default_factory=dict)
    payload: str = Field(..., description="Resolved message payload")
    timeout_ms: int = Field(...)
    acks: Literal["0", "1", "all"] = Field(default="all")
    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(default="none")


class ModelResolvedFilesystemContext(BaseModel):
    """Resolved filesystem context - all templates substituted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_type: EnumEffectHandlerType = EnumEffectHandlerType.FILESYSTEM

    file_path: str = Field(..., description="Fully resolved file path")
    operation: Literal["read", "write", "delete", "move", "copy"] = Field(...)
    content: str | None = Field(default=None, description="Resolved content for write operations")
    timeout_ms: int = Field(...)
    atomic: bool = Field(default=True)
    create_dirs: bool = Field(default=True)
    encoding: str = Field(default="utf-8")
    mode: str | None = Field(default=None)


# Type alias for handler input
ResolvedIOContext = (
    ModelResolvedHttpContext
    | ModelResolvedDbContext
    | ModelResolvedKafkaContext
    | ModelResolvedFilesystemContext
)
```

### 2. Idempotency and Retry Configuration

**Location**: `src/omnibase_core/models/contracts/subcontracts/effect_retry_config.py`

```python
"""
Effect Retry and Idempotency Configuration.

VERSION: 1.0.0

Idempotency-aware retry policies that prevent duplicate side effects.
"""

from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ModelEffectRetryPolicy(BaseModel):
    """Retry policy with idempotency awareness."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=10)
    backoff_strategy: Literal["fixed", "exponential", "linear"] = Field(default="exponential")
    base_delay_ms: int = Field(default=1000, ge=100, le=60000)
    max_delay_ms: int = Field(default=30000, ge=1000, le=300000)
    jitter_factor: float = Field(default=0.1, ge=0.0, le=0.5, description="Jitter as fraction of delay")
    retryable_status_codes: list[int] = Field(default_factory=lambda: [429, 500, 502, 503, 504])
    retryable_errors: list[str] = Field(default_factory=lambda: ["ECONNRESET", "ETIMEDOUT", "ECONNREFUSED"])


# Default idempotency by handler type and operation
IDEMPOTENCY_DEFAULTS: dict[str, dict[str, bool]] = {
    "http": {
        "GET": True,
        "HEAD": True,
        "OPTIONS": True,
        "PUT": True,      # PUT is idempotent by HTTP spec
        "DELETE": True,   # DELETE is idempotent by HTTP spec
        "POST": False,    # POST is NOT idempotent
        "PATCH": False,   # PATCH is NOT idempotent
    },
    "db": {
        "SELECT": True,
        "INSERT": False,  # May create duplicates
        "UPDATE": True,   # Same update = same result
        "DELETE": True,   # Deleting deleted = no-op
        "UPSERT": True,   # Idempotent by design
    },
    "kafka": {
        "produce": False,  # Produces duplicate messages (unless idempotent producer)
    },
    "filesystem": {
        "read": True,
        "write": False,   # CORRECTED: Overwrites may corrupt data on retry with different content
        "delete": True,   # Deleting deleted = no-op
        "move": False,    # Source may not exist after first move
        "copy": False,    # CORRECTED: Dest may exist after first attempt, causing failure
    },
}
```

### 3. ModelEffectSubcontract (~250 lines)

**Location**: `src/omnibase_core/models/contracts/subcontracts/model_effect_subcontract.py`

```python
"""
Effect Subcontract Model.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Defines declarative effect operations with:
- Discriminated union IO configs (type-safe per handler)
- Idempotency-aware retry policies
- Process-local circuit breaker configuration
- DB-only transaction boundaries
"""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


# NOTE: Circuit breaker runtime state is NOT defined here.
# USE EXISTING: from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
# USE EXISTING: from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
#
# The existing ModelCircuitBreaker provides comprehensive circuit breaker functionality:
# - state: str (closed/open/half_open) with EnumCircuitBreakerState
# - failure_count, success_count, total_requests, half_open_requests
# - last_failure_time, last_state_change (datetime)
# - Sliding window support (window_size_seconds)
# - Failure rate detection (failure_rate_threshold, minimum_request_threshold)
# - Slow call detection (slow_call_duration_threshold_ms, slow_call_rate_threshold)
# - Methods: should_allow_request(), record_success(), record_failure(), record_slow_call()
# - Factory methods: create_fast_fail(), create_resilient(), create_disabled()
#
# For advanced subcontract composition, see: ModelCircuitBreakerSubcontract
# Location: omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract


class ModelEffectCircuitBreaker(BaseModel):
    """
    Effect-specific circuit breaker configuration (simplified view).

    Note: For full circuit breaker configuration with advanced features (sliding windows,
    failure rates, slow call detection), use ModelCircuitBreakerSubcontract from:
        omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract

    This simplified version provides effect-specific defaults optimized for
    common I/O operation patterns. For runtime state management, compose with
    the existing ModelCircuitBreaker infrastructure.

    SCOPE: Process-local only in v1.0.
    Keyed by operation correlation_id (stable identity).
    NOT shared across threads - NodeEffect instances must be isolated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=False)
    failure_threshold: int = Field(default=5, ge=1, le=100)
    success_threshold: int = Field(default=2, ge=1, le=10)
    timeout_ms: int = Field(default=60000, ge=1000, le=600000)
    half_open_requests: int = Field(default=3, ge=1, le=10)


class ModelEffectTransaction(BaseModel):
    """
    Transaction boundary configuration.

    SCOPE: DB operations only, same connection only.
    HTTP, Kafka, and Filesystem do not support transactions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(default=False)  # Default false - must explicitly enable
    isolation_level: Literal["read_uncommitted", "read_committed", "repeatable_read", "serializable"] = Field(
        default="read_committed"
    )
    rollback_on_error: bool = Field(default=True)
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)


#### Nested Transaction Behavior

When a NodeEffect with `transaction.enabled=true` is invoked within an existing
ambient transaction (e.g., called from an outer NodeEffect or application code
with active transaction):

| Scenario | Behavior |
|----------|----------|
| **No ambient transaction** | NodeEffect issues `BEGIN`, manages full transaction lifecycle |
| **Ambient transaction exists** | NodeEffect creates a `SAVEPOINT` instead of `BEGIN` |
| **Rollback on error** | `ROLLBACK TO SAVEPOINT` (doesn't abort outer transaction) |
| **Success** | `RELEASE SAVEPOINT` |

This follows PostgreSQL savepoint semantics and allows composition of transactional
effects without breaking outer transaction boundaries.

> **Implementation Note**: The SPI adapter (DbAdapter) is responsible for detecting
> ambient transactions and converting `BEGIN`/`COMMIT`/`ROLLBACK` to savepoint equivalents.


class ModelEffectResponseHandling(BaseModel):
    """Response extraction and validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success_codes: list[int] = Field(default_factory=lambda: [200, 201, 202, 204])
    extract_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Map of output_name -> JSONPath expression"
    )
    fail_on_empty: bool = Field(default=False, description="Fail if extraction returns empty")

    # Explicit extraction engine - prevents silent fallback behavior
    extraction_engine: Literal["jsonpath", "dotpath"] = Field(
        default="jsonpath",
        description="Extraction engine. 'jsonpath' requires jsonpath-ng (fails at load if missing), "
                    "'dotpath' uses simple $.field.subfield semantics."
    )


> **Extraction Engine Behavior**: The `extraction_engine` field explicitly controls
> response field extraction. There is NO silent fallback between engines:
> - `jsonpath`: Requires `jsonpath_ng` package. Fails fast if not installed.
> - `dotpath`: Simple `$.field.subfield` syntax. No external dependencies.
> Both engines reject non-primitive extraction results (lists, dicts). Only
> `str`, `int`, `float`, `bool`, and `None` are allowed. Attempting to extract
> a complex type will raise `ModelOnexError` with `EXTRACTION_ERROR`.


class ModelEffectObservability(BaseModel):
    """Observability configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    log_request: bool = Field(default=True)
    log_response: bool = Field(default=False, description="May contain sensitive data")
    emit_metrics: bool = Field(default=True)
    trace_propagation: bool = Field(default=True)


class ModelEffectOperation(BaseModel):
    """
    Single effect operation definition with discriminated union IO config.

    The `io_config` field uses a discriminated union based on `handler_type`.
    This ensures type-safe validation at contract load time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    operation_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    # Idempotency - CRITICAL for retry safety
    idempotent: bool | None = Field(
        default=None,
        description="Override default idempotency. If None, uses handler/operation defaults."
    )

    # Discriminated union IO config
    io_config: Annotated[
        ModelHttpIOConfig | ModelDbIOConfig | ModelKafkaIOConfig | ModelFilesystemIOConfig,
        Field(discriminator="handler_type")
    ]

    # Response handling
    response_handling: ModelEffectResponseHandling = Field(default_factory=ModelEffectResponseHandling)

    # Resilience (can be overridden per-operation)
    retry_policy: ModelEffectRetryPolicy | None = Field(default=None)
    circuit_breaker: ModelEffectCircuitBreaker | None = Field(default=None)

    # Correlation
    correlation_id: UUID = Field(default_factory=uuid4)

    # Operation-level timeout (guards against retry stacking)
    operation_timeout_ms: int | None = Field(
        default=None,
        ge=1000,
        le=600000,
        description="Overall operation timeout including all retries. "
                    "If None, defaults to 60000ms (60s). "
                    "Prevents retry stacking from exceeding intended limits."
    )

    @property
    def handler_type(self) -> str:
        """Extract handler type from IO config."""
        return self.io_config.handler_type

    def get_effective_idempotency(self) -> bool:
        """
        Determine effective idempotency for this operation.

        Priority:
        1. Explicit `idempotent` field if set
        2. Default based on handler_type and operation
        """
        if self.idempotent is not None:
            return self.idempotent

        handler = self.io_config.handler_type
        defaults = IDEMPOTENCY_DEFAULTS.get(handler, {})

        # Extract operation type for lookup
        if handler == "http":
            op_type = self.io_config.method
        elif handler == "filesystem":
            op_type = self.io_config.operation
        elif handler == "kafka":
            op_type = "produce"
        elif handler == "db":
            # Use explicit operation type (no more query string parsing)
            op_type = self.io_config.operation.upper()
            # 'raw' operations default to non-idempotent for safety
            if op_type == "RAW":
                return False
        else:
            return True  # Conservative default

        return defaults.get(op_type, True)


class ModelEffectOperationResult(BaseModel):
    """
    Strongly-typed result for a single effect operation.

    Eliminates dict[str, Any] in favor of explicit fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    operation_name: str
    success: bool
    retries: int = Field(default=0, ge=0)
    duration_ms: float = Field(ge=0)
    extracted_fields: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    error_message: str | None = Field(default=None)
    error_code: str | None = Field(default=None)


class ModelEffectContractMetadata(BaseModel):
    """
    Contract-level metadata for tooling, versioning, and RSD compatibility.

    Enables:
    - Contract diffing and migration tracking
    - ONEX introspection and code generation
    - Audit trails and change history
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_id: UUID = Field(default_factory=uuid4, description="Stable contract identity")
    revision: int = Field(default=1, ge=1, description="Monotonic revision number")
    created_at: str | None = Field(default=None, description="ISO-8601 creation timestamp")
    updated_at: str | None = Field(default=None, description="ISO-8601 last update timestamp")
    author: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, description="Searchable tags")

    # Contract hash for tooling and RSD
    contract_hash: str | None = Field(
        default=None,
        description=(
            "SHA256 hash of canonicalized contract for tooling support.\n\n"
            "Enables:\n"
            "- Contract diffing and migration detection\n"
            "- Audit trail verification\n"
            "- RSD experiment reproducibility\n"
            "- Cache invalidation\n\n"
            "Computed from sorted keys, normalized whitespace. "
            "If not provided, tooling may compute on load."
        )
    )


class ModelEffectInputSchema(BaseModel):
    """
    Optional input schema for pre-execution validation.

    RESERVED FOR v1.1: Minimal implementation in v1.0 (structure only, no validation).

    When fully implemented:
    - Effect inputs are validated against this schema before execution
    - Required fields must be present in ModelEffectInput.operation_data
    - Optional fields may be present or absent

    This enables:
    - Early failure on malformed inputs
    - Contract introspection for code generation
    - IDE autocompletion for input fields
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    required_fields: list[str] = Field(
        default_factory=list,
        description="Field names that must be present in input. Format: 'field_name' or 'nested.field'"
    )
    optional_fields: list[str] = Field(
        default_factory=list,
        description="Field names that may be present in input"
    )


class ModelEffectSubcontract(BaseModel):
    """
    Effect Subcontract - defines all I/O operations declaratively.

    VERSION: 1.0.0 - Sequential operations, abort-on-first-failure

    CRITICAL VALIDATIONS:
    1. Transaction enabled only for DB-only operations with same connection
    2. Retry enabled only for idempotent operations
    3. All IO configs validated against handler type
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Interface version for code generation stability
    INTERFACE_VERSION: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0)

    # Contract metadata for tooling and RSD compatibility
    metadata: ModelEffectContractMetadata = Field(default_factory=ModelEffectContractMetadata)

    # Identity
    subcontract_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    description: str | None = Field(default=None, max_length=1000)

    # Execution semantics - EXPLICIT in contract
    execution_mode: Literal["sequential_abort", "sequential_continue"] = Field(
        default="sequential_abort",
        description=(
            "Controls failure handling behavior:\n\n"
            "**sequential_abort** (default):\n"
            "- Stop on first operation failure\n"
            "- RAISES ModelOnexError immediately\n"
            "- Partial ModelEffectOutput available in exception context\n"
            "- Use when atomicity matters: 'all succeed or fail fast'\n\n"
            "**sequential_continue**:\n"
            "- Run all operations regardless of failures\n"
            "- NEVER raises for operation failures\n"
            "- Returns complete ModelEffectOutput with all results\n"
            "- failed_operation and operation success flags indicate failures\n"
            "- Use for best-effort: 'run everything, report all outcomes'"
        )
    )

    # Operations (sequential execution per execution_mode)
    operations: list[ModelEffectOperation] = Field(..., min_length=1, max_length=50)

    # Global resilience defaults
    default_retry_policy: ModelEffectRetryPolicy = Field(default_factory=ModelEffectRetryPolicy)
    default_circuit_breaker: ModelEffectCircuitBreaker = Field(default_factory=ModelEffectCircuitBreaker)
    transaction: ModelEffectTransaction = Field(default_factory=ModelEffectTransaction)

    # Observability
    observability: ModelEffectObservability = Field(default_factory=ModelEffectObservability)

    # Correlation
    correlation_id: UUID = Field(default_factory=uuid4)

    # Reserved: Input schema (v1.1 - validation not enforced in v1.0)
    input_schema: ModelEffectInputSchema | None = Field(
        default=None,
        description="Optional input schema. Reserved for v1.1 - structure only in v1.0."
    )

    # Reserved: Determinism flag (important for RSD replay)
    deterministic: bool = Field(
        default=False,
        description=(
            "Indicates if effect is deterministic for same input. "
            "Non-deterministic effects (HTTP, time-sensitive queries) may not be safely replayable.\n\n"
            "**Runtime Consequences**:\n"
            "- deterministic=true: Effect results may be cached and replayed by ONEX infrastructure\n"
            "- deterministic=false: Effect is excluded from replay, snapshotting, and caching systems\n"
            "- Default false is conservative (safe)\n\n"
            "**Examples**:\n"
            "- HTTP GET with stable response: deterministic=true\n"
            "- HTTP POST creating resource: deterministic=false\n"
            "- DB SELECT on immutable table: deterministic=true\n"
            "- DB SELECT with NOW(): deterministic=false"
        )
    )

    # Reserved for forward compatibility (v1.1+)
    future: dict[str, object] = Field(
        default_factory=dict,
        description=(
            "Reserved for ONEX-provided extensions. "
            "User-defined keys not supported in v1.0.\n\n"
            "**Namespace Rules**:\n"
            "- ONEX-owned keys MUST use `ONEX_` prefix\n"
            "- User-defined keys (v1.1+) will use no prefix or custom prefix\n"
            "- Collision prevention: ONEX will never use un-prefixed keys\n\n"
            "**Expected ONEX Extensions**:\n"
            "- `ONEX_response_cache_ttl_ms`: Response caching configuration\n"
            "- `ONEX_callgraph_annotation`: Dependency tracking metadata\n"
            "- `ONEX_replay_policy`: Replay and snapshot behavior hints"
        )
    )

    @model_validator(mode="after")
    def validate_transaction_scope(self) -> "ModelEffectSubcontract":
        """
        Validate transaction is only enabled for DB operations with same connection.

        RULE: Transactions only make sense for:
        1. All operations are DB operations
        2. All operations use the same connection_name
        """
        if not self.transaction.enabled:
            return self

        # Check all operations are DB
        non_db_ops = [op for op in self.operations if op.handler_type != "db"]
        if non_db_ops:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transaction enabled but found non-DB operations: {[op.operation_name for op in non_db_ops]}. "
                        f"Transactions only supported for DB handler type.",
            )

        # Check all use same connection
        connection_names = {op.io_config.connection_name for op in self.operations}
        if len(connection_names) > 1:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Transaction enabled but operations use different connections: {connection_names}. "
                        f"All DB operations in a transaction must use the same connection.",
            )

        return self

    @model_validator(mode="after")
    def validate_idempotency_retry_interaction(self) -> "ModelEffectSubcontract":
        """
        Validate retry policies respect idempotency.

        RULE: Cannot retry non-idempotent operations.
        """
        for op in self.operations:
            # Get effective retry policy
            retry_policy = op.retry_policy or self.default_retry_policy

            if retry_policy.enabled and retry_policy.max_retries > 0:
                if not op.get_effective_idempotency():
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Operation '{op.operation_name}' is not idempotent but has retry enabled. "
                                f"Set idempotent=true or disable retries to prevent duplicate side effects.",
                    )

        return self

    @model_validator(mode="after")
    def validate_select_retry_in_transaction(self) -> "ModelEffectSubcontract":
        """
        Prevent retrying SELECT inside transaction with snapshot-sensitive isolation.

        In PostgreSQL repeatable_read/serializable, the first SELECT defines the
        transaction's snapshot. Retrying a SELECT would NOT see changes made by
        concurrent transactions (expected in repeatable_read), but the retry loop
        resets internal state, potentially causing the application to behave as if
        the snapshot changed. This creates subtle consistency bugs.

        RULE: Cannot retry SELECT operations inside repeatable_read or serializable
        transactions. Either use read_committed (where retries are safe) or disable
        retry for SELECT operations.

        Why this matters:
        - SELECT in read_committed: Each query sees latest committed data (retry OK)
        - SELECT in repeatable_read: First query defines snapshot (retry breaks semantics)
        - SELECT in serializable: Strict ordering enforced (retry may cause serialization failures)
        """
        if not self.transaction.enabled:
            return self

        isolation = self.transaction.isolation_level
        if isolation in ["read_uncommitted", "read_committed"]:
            return self  # Safe to retry - each query sees fresh data

        # Check for SELECT operations with retry enabled in strict isolation
        for op in self.operations:
            if op.io_config.handler_type == "db":
                if op.io_config.operation == "select":
                    retry = op.retry_policy or self.default_retry_policy
                    if retry.enabled and retry.max_retries > 0:
                        raise ModelOnexError(
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                            message=f"Operation '{op.operation_name}' is a SELECT with retry enabled "
                                    f"inside a {isolation} transaction. This violates snapshot semantics. "
                                    f"Either disable retry for this operation or use read_committed isolation."
                        )

        return self

    @model_validator(mode="after")
    def validate_no_raw_in_transaction(self) -> "ModelEffectSubcontract":
        """
        Disallow raw DB operations inside transactions.

        Raw operations (stored procedures, multi-statement batches) may have
        unpredictable side effects that break transactional semantics:
        - Stored procedures may issue their own COMMIT/ROLLBACK
        - Multi-statement batches may have partial failure modes
        - Side effects (temp tables, session variables) may leak across transaction boundaries

        Route complex transactional logic through dedicated patterns:
        - Use individual operations (select/insert/update/delete/upsert) instead
        - Decompose stored procedures into discrete, observable steps
        - Use application-level orchestration for complex multi-step logic
        """
        if not self.transaction.enabled:
            return self

        raw_ops = [
            op for op in self.operations
            if op.io_config.handler_type == "db"
            and op.io_config.operation == "raw"
        ]

        if raw_ops:
            raw_names = [op.operation_name for op in raw_ops]
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Raw DB operations not allowed inside transactions: {raw_names}. "
                        f"Raw operations (stored procedures, multi-statement batches) may have "
                        f"side effects that break transactional semantics. "
                        f"Use dedicated subcontracts or explicit application logic instead."
            )

        return self
```

### 4. Strongly-Typed Output Model

**Location**: `src/omnibase_core/models/model_effect_output.py` (updated)

```python
"""
ModelEffectOutput - Strongly-typed output model for NodeEffect operations.

VERSION: 2.0.0 - Zero Any types, explicit result structure

"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectOperationResult,
)

__all__ = ["ModelEffectOutput"]


class ModelEffectOutput(BaseModel):
    """
    Strongly-typed output model for NodeEffect operations.

    Zero Any types - all fields explicitly typed.
    """

    # Operation results - strongly typed
    operations: list[ModelEffectOperationResult] = Field(
        ...,
        description="Results from each operation in execution order"
    )

    # Failure tracking
    failed_operation: str | None = Field(
        default=None,
        description="Name of first failed operation (if any)"
    )

    # Aggregate metrics
    total_retry_count: int = Field(default=0, ge=0)
    total_duration_ms: float = Field(ge=0)

    # Transaction state
    transaction_state: EnumTransactionState = Field(...)

    # Execution metadata
    execution_mode: Literal["sequential_abort", "sequential_continue"] = Field(...)
    subcontract_name: str = Field(...)
    subcontract_version: str = Field(...)

    # Identifiers
    operation_id: UUID = Field(...)
    correlation_id: UUID = Field(...)

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)
```

### 4.1 Protocol Definition (Core Layer)

**Location**: `src/omnibase_core/protocols/protocol_effect_handler.py`

```python
"""
Effect Handler Protocol - Core Layer.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Defines the interface for effect handlers. Implemented in SPI.
Core defines; SPI implements.

LAYER SEPARATION:
- Core defines this protocol (vocabulary)
- SPI implements concrete handlers (HttpRestAdapter, DbAdapter, etc.)
- Core NEVER imports SPI implementations

This protocol was previously embedded in MixinEffectExecution.
Moving it to a dedicated module enforces proper Core/SPI separation.
"""

from typing import Protocol, Any
from uuid import UUID

from omnibase_core.models.contracts.subcontracts.effect_resolved_context import ResolvedIOContext


class ProtocolEffectHandler(Protocol):
    """
    Core protocol for effect handlers.

    LAYER: Core (vocabulary definition)
    IMPLEMENTATION: SPI (HttpRestAdapter, DbAdapter, etc.)

    Handlers receive fully-resolved context (no templates).

    HANDLER CONTRACT (R4):
    - Handlers receive ResolvedIOContext with ALL templates already resolved
    - Handlers MUST NOT perform template resolution
    - Handlers MUST NOT import resolve_template or effect_executor.py
    - Handlers receive concrete values only (no ${...} placeholders)
    """

    async def execute(
        self,
        resolved_context: ResolvedIOContext,
        correlation_id: UUID,
    ) -> dict[str, Any]:
        """
        Execute the effect operation.

        Args:
            resolved_context: Fully resolved IO context (no ${...} templates)
            correlation_id: Operation correlation ID for tracing

        Returns:
            Response dict suitable for field extraction
        """
        ...
```

### 4.2 Effect Handler Registry (Core Layer)

**Location**: `src/omnibase_core/registry/effect_handler_registry.py`

```python
"""
Effect Handler Registry - Core Layer.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Registry abstraction that decouples Core from SPI service names.
SPI populates; Core consumes.

DEPENDENCY INVERSION PATTERN:
- Core defines the registry interface and consumes it
- SPI populates the registry at composition time
- Core never knows concrete SPI class names (HttpRestAdapter, etc.)

This replaces the hard-coded handler_map in MixinEffectExecution,
which violated dependency inversion by embedding SPI service names in Core.
"""

from pydantic import BaseModel, Field, ConfigDict

from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class EffectHandlerRegistry(BaseModel):
    """
    Registry mapping handler types to service names.

    POPULATION: SPI modules register handlers at composition time
    CONSUMPTION: Core mixin resolves handlers via registry

    This maintains dependency inversion - Core never knows SPI class names.

    Thread Safety:
        This registry is NOT thread-safe. For multi-threaded applications,
        populate the registry during single-threaded initialization phase
        before any concurrent access.

    Example:
        # SPI initialization (single-threaded startup)
        registry = EffectHandlerRegistry()
        registry.register(EnumEffectHandlerType.HTTP, "HttpRestAdapter")
        registry.register(EnumEffectHandlerType.DB, "DbAdapter")
        container.register_service("EffectHandlerRegistry", registry)

        # Core consumption (may be multi-threaded)
        registry = container.get_service("EffectHandlerRegistry")
        service_name = registry.resolve(EnumEffectHandlerType.HTTP)
    """

    model_config = ConfigDict(extra="forbid")

    handlers: dict[EnumEffectHandlerType, str] = Field(default_factory=dict)

    def register(self, handler_type: EnumEffectHandlerType, service_name: str) -> None:
        """
        Register a handler implementation for a handler type.

        Args:
            handler_type: The effect handler type (HTTP, DB, KAFKA, FILESYSTEM)
            service_name: The service name to resolve from container

        Raises:
            ModelOnexError: If handler_type is already registered (prevents silent overwrites)
        """
        if handler_type in self.handlers:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Handler already registered for handler_type={handler_type.value}. "
                        f"Existing: {self.handlers[handler_type]}, Attempted: {service_name}",
            )
        self.handlers[handler_type] = service_name

    def resolve(self, handler_type: EnumEffectHandlerType) -> str:
        """
        Resolve service name for handler type.

        Args:
            handler_type: The effect handler type to resolve

        Returns:
            The registered service name for this handler type

        Raises:
            ModelOnexError: If no handler is registered for the type
        """
        if handler_type not in self.handlers:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                message=f"No handler registered for handler_type={handler_type.value}. "
                        f"Available handlers: {list(self.handlers.keys())}",
            )
        return self.handlers[handler_type]

    def is_registered(self, handler_type: EnumEffectHandlerType) -> bool:
        """Check if a handler type has a registered implementation."""
        return handler_type in self.handlers

    def list_registered(self) -> list[EnumEffectHandlerType]:
        """List all registered handler types."""
        return list(self.handlers.keys())
```

> **SPI Registration Example**: The SPI layer registers handlers at application startup:
> ```python
> # In SPI initialization (e.g., omnibase_spi/bootstrap.py)
> from omnibase_core.registry.effect_handler_registry import EffectHandlerRegistry
> from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
> def register_effect_handlers(container: ModelONEXContainer) -> None:
>     """Register all effect handlers with the registry."""
>     registry = EffectHandlerRegistry()
>     # Register SPI implementations
>     registry.register(EnumEffectHandlerType.HTTP, "HttpRestAdapter")
>     registry.register(EnumEffectHandlerType.DB, "DbAdapter")
>     registry.register(EnumEffectHandlerType.KAFKA, "KafkaAdapter")
>     registry.register(EnumEffectHandlerType.FILESYSTEM, "FilesystemHandler")
>     # Register the registry itself for Core consumption
>     container.register_service("EffectHandlerRegistry", registry)
> ```

### 5. MixinEffectExecution (~400 lines)

**Location**: `src/omnibase_core/mixins/mixin_effect_execution.py`

```python
"""
Effect Execution Mixin - Contract-Driven I/O Operations.

VERSION: 1.0.0 - Sequential execution with abort-on-first-failure

Provides execute_effect() method that reads from ModelEffectSubcontract
and dispatches to appropriate handlers with resilience patterns.

All pure functions (template resolution, backoff calculation, retryability)
are delegated to effect_executor.py for testability and future portability.

CORE/SPI SEPARATION:
- ProtocolEffectHandler: Imported from omnibase_core.protocols (Core layer)
- EffectHandlerRegistry: Imported from omnibase_core.registry (Core layer)
- Handler implementations: Resolved via registry, never imported directly
"""

from typing import Any
from uuid import UUID
import time

from omnibase_core.protocols.protocol_effect_handler import ProtocolEffectHandler
from omnibase_core.registry.effect_handler_registry import EffectHandlerRegistry
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
    ModelEffectOperation,
    ModelEffectOperationResult,
    ModelEffectRetryPolicy,
    ModelEffectCircuitBreaker,
)
# Use existing circuit breaker infrastructure for runtime state management
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.models.contracts.subcontracts.effect_resolved_context import (
    ResolvedIOContext,
    ModelResolvedHttpContext,
    ModelResolvedDbContext,
    ModelResolvedKafkaContext,
    ModelResolvedFilesystemContext,
)
from omnibase_core.models.model_effect_input import ModelEffectInput
from omnibase_core.models.model_effect_output import ModelEffectOutput
from omnibase_core.enums.enum_effect_types import EnumTransactionState
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.effect_executor import (
    resolve_template,
    resolve_io_config,  # New: resolves entire io_config to ResolvedIOContext
    calculate_backoff,
    is_retryable_error,
    extract_response_fields,
)


class MixinEffectExecution:
    """
    Mixin providing contract-driven effect execution.

    Requires:
        - self.effect_subcontract: ModelEffectSubcontract (from contract)
        - self.container: ModelONEXContainer (for handler resolution)

    Circuit Breaker Integration:
        Uses existing ModelCircuitBreaker infrastructure from:
            omnibase_core.models.configuration.model_circuit_breaker

        This provides:
        - Typed state management (no dict[str, Any])
        - Sliding window failure tracking
        - Failure rate detection
        - Slow call detection (optional)
        - Factory methods for common configurations

    Circuit Breaker Scope:
        - Process-local only (v1.0)
        - Keyed by operation correlation_id (stable, rename-safe identity)
        - NOT thread-safe - create separate NodeEffect instances per thread
    """

    effect_subcontract: ModelEffectSubcontract
    # Use existing ModelCircuitBreaker for typed state management
    _circuit_breaker_state: dict[str, ModelCircuitBreaker]

    def __init_effect_execution__(self) -> None:
        """Initialize effect execution state. Call from __init__."""
        object.__setattr__(self, "_circuit_breaker_state", {})

    async def execute_effect(
        self,
        input_data: ModelEffectInput,
    ) -> ModelEffectOutput:
        """
        Execute effect operations defined in subcontract.

        Behavior depends on execution_mode:

        sequential_abort:
            - Stops on first failure
            - RAISES ModelOnexError with partial results in context
            - Caller must handle exception
            - Partial output available via exception.context["partial_output"]

        sequential_continue:
            - Runs all operations
            - RETURNS ModelEffectOutput (never raises for op failures)
            - Check failed_operation and operation.success for failures

        Args:
            input_data: Input data with operation context

        Returns:
            ModelEffectOutput with operation results

        Raises:
            ModelOnexError: On operation failure (sequential_abort mode only).
                            Exception context contains partial_output dict.
        """
        start_time = time.perf_counter()
        operation_results: list[ModelEffectOperationResult] = []
        failed_operation: str | None = None
        total_retries = 0

        # Resolve transaction state
        transaction = self.effect_subcontract.transaction
        transaction_state = EnumTransactionState.ACTIVE if transaction.enabled else EnumTransactionState.COMMITTED

        try:
            for operation in self.effect_subcontract.operations:
                op_start = time.perf_counter()

                try:
                    # Resolve handler for operation type
                    handler = self._resolve_handler(operation.io_config.handler_type)

                    # Get effective policies
                    retry_policy = operation.retry_policy or self.effect_subcontract.default_retry_policy
                    circuit_breaker = operation.circuit_breaker or self.effect_subcontract.default_circuit_breaker

                    # Execute with resilience
                    result, retries = await self._execute_with_resilience(
                        handler=handler,
                        operation=operation,
                        input_data=input_data.operation_data,
                        retry_policy=retry_policy,
                        circuit_breaker=circuit_breaker,
                    )

                    # Extract response fields using explicit extraction engine
                    extracted = extract_response_fields(
                        result,
                        operation.response_handling.extract_fields,
                        operation.response_handling.extraction_engine,
                    )

                    op_duration = (time.perf_counter() - op_start) * 1000
                    total_retries += retries

                    operation_results.append(ModelEffectOperationResult(
                        operation_name=operation.operation_name,
                        success=True,
                        retries=retries,
                        duration_ms=op_duration,
                        extracted_fields=extracted,
                    ))

                except ModelOnexError as e:
                    op_duration = (time.perf_counter() - op_start) * 1000

                    operation_results.append(ModelEffectOperationResult(
                        operation_name=operation.operation_name,
                        success=False,
                        retries=0,
                        duration_ms=op_duration,
                        error_message=str(e.message),
                        error_code=str(e.error_code),
                    ))

                    failed_operation = operation.operation_name

                    if self.effect_subcontract.execution_mode == "sequential_abort":
                        # Abort on first failure
                        transaction_state = (
                            EnumTransactionState.ROLLED_BACK
                            if transaction.rollback_on_error
                            else EnumTransactionState.FAILED
                        )

                        # Attach partial output to exception for inspection
                        # This enables callers to see what completed before failure
                        partial_duration = (time.perf_counter() - start_time) * 1000
                        partial_output = ModelEffectOutput(
                            operations=operation_results,
                            failed_operation=failed_operation,
                            total_retry_count=total_retries,
                            total_duration_ms=partial_duration,
                            transaction_state=transaction_state,
                            execution_mode=self.effect_subcontract.execution_mode,
                            subcontract_name=self.effect_subcontract.subcontract_name,
                            subcontract_version=self.effect_subcontract.version,
                            operation_id=input_data.operation_id,
                            correlation_id=self.effect_subcontract.correlation_id,
                        )
                        e.context = e.context or {}
                        e.context["partial_output"] = partial_output.model_dump()
                        raise

                    # sequential_continue: keep going

            # All operations complete
            if transaction.enabled and failed_operation is None:
                transaction_state = EnumTransactionState.COMMITTED

        except ModelOnexError:
            # Re-raise in sequential_abort mode
            if self.effect_subcontract.execution_mode == "sequential_abort":
                raise

        total_duration = (time.perf_counter() - start_time) * 1000

        return ModelEffectOutput(
            operations=operation_results,
            failed_operation=failed_operation,
            total_retry_count=total_retries,
            total_duration_ms=total_duration,
            transaction_state=transaction_state,
            execution_mode=self.effect_subcontract.execution_mode,
            subcontract_name=self.effect_subcontract.subcontract_name,
            subcontract_version=self.effect_subcontract.version,
            operation_id=input_data.operation_id,
            correlation_id=self.effect_subcontract.correlation_id,
        )

    def _resolve_handler(self, handler_type: EnumEffectHandlerType) -> ProtocolEffectHandler:
        """
        Resolve handler by type via registry.

        Core uses registry abstraction; SPI populates with concrete service names.
        This maintains dependency inversion - Core never knows SPI class names.

        DEPENDENCY INVERSION:
        - Registry populated by SPI at composition time
        - Core resolves via registry, never hard-codes service names
        - Enables testing with mock registrations
        """
        registry: EffectHandlerRegistry = self.container.get_service("EffectHandlerRegistry")
        handler_service_name = registry.resolve(handler_type)

        handler = self.container.get_service_optional(handler_service_name)
        if handler is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.RESOURCE_UNAVAILABLE,
                message=f"Handler not available: {handler_service_name}",
            )

        return handler

    async def _execute_with_resilience(
        self,
        handler: ProtocolEffectHandler,
        operation: ModelEffectOperation,
        input_data: dict[str, Any],
        retry_policy: ModelEffectRetryPolicy,
        circuit_breaker: ModelEffectCircuitBreaker,
    ) -> tuple[dict[str, Any], int]:
        """
        Execute operation with retry, circuit breaker, and overall timeout.

        Template resolution is INSIDE the retry loop so transient resolution
        failures (e.g., secrets store temporarily unavailable, env not loaded)
        can be retried when allowed by the retry policy.

        Returns:
            Tuple of (result, retry_count)
        """
        # Use correlation_id for stable identity (survives operation renames)
        cb_key = str(operation.correlation_id)

        # Check circuit breaker first
        if circuit_breaker.enabled:
            if not self._circuit_breaker_allows(cb_key, circuit_breaker):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.CIRCUIT_BREAKER_OPEN,
                    message=f"Circuit breaker open for {operation.operation_name}",
                )

        # Operation-level deadline prevents retry stacking from exceeding intended limits
        operation_timeout_ms = operation.operation_timeout_ms or 60000  # Default 60s
        deadline_time = time.perf_counter() + (operation_timeout_ms / 1000.0)

        last_exception: Exception | None = None
        retry_count = 0

        while retry_count <= retry_policy.max_retries:
            # Check overall operation deadline at start of each iteration
            if time.perf_counter() > deadline_time:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.TIMEOUT,
                    message=f"Operation '{operation.operation_name}' exceeded "
                            f"operation_timeout_ms={operation_timeout_ms}",
                )

            try:
                # Template resolution INSIDE retry loop - transient failures can be retried
                # This is the ONLY place templates are resolved - handlers receive concrete values
                context = {"input": input_data, "env": dict(os.environ)}
                resolved_context: ResolvedIOContext = resolve_io_config(
                    operation.io_config, context
                )

                # Execute handler with resolved context (no templates)
                # Handler contract: receives ResolvedIOContext, never raw io_config
                result = await handler.execute(
                    resolved_context=resolved_context,
                    correlation_id=operation.correlation_id,
                )

                # Record success
                if circuit_breaker.enabled:
                    self._circuit_breaker_record_success(cb_key, circuit_breaker)

                return result, retry_count

            except Exception as e:
                last_exception = e
                retry_count += 1

                # Check retryability
                if not retry_policy.enabled:
                    break

                if not is_retryable_error(e, retry_policy):
                    break

                if retry_count > retry_policy.max_retries:
                    break

                # Calculate backoff
                delay_ms = calculate_backoff(retry_count, retry_policy)
                await asyncio.sleep(delay_ms / 1000.0)

        # Record failure
        if circuit_breaker.enabled:
            self._circuit_breaker_record_failure(cb_key, circuit_breaker)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            message=f"Effect operation failed after {retry_count} retries: {operation.operation_name}",
        ) from last_exception

    # Circuit breaker methods (process-local, not thread-safe)
    # Leverages existing ModelCircuitBreaker infrastructure for typed state management
    # See: omnibase_core.models.configuration.model_circuit_breaker

    def _get_or_create_circuit_breaker(self, key: str, config: ModelEffectCircuitBreaker) -> ModelCircuitBreaker:
        """Get or create a ModelCircuitBreaker instance for the given key."""
        if key not in self._circuit_breaker_state:
            # Create new circuit breaker using existing infrastructure
            # Map effect config to ModelCircuitBreaker configuration
            self._circuit_breaker_state[key] = ModelCircuitBreaker(
                enabled=config.enabled,
                failure_threshold=config.failure_threshold,
                success_threshold=config.success_threshold,
                timeout_seconds=config.timeout_ms // 1000,  # Convert ms to seconds
                half_open_max_requests=config.half_open_requests,
            )
        return self._circuit_breaker_state[key]

    def _circuit_breaker_allows(self, key: str, config: ModelEffectCircuitBreaker) -> bool:
        """Check if circuit breaker allows request using existing infrastructure."""
        cb = self._get_or_create_circuit_breaker(key, config)
        # Delegate to existing ModelCircuitBreaker.should_allow_request()
        return cb.should_allow_request()

    def _circuit_breaker_record_success(self, key: str, config: ModelEffectCircuitBreaker) -> None:
        """Record successful request using existing infrastructure."""
        cb = self._get_or_create_circuit_breaker(key, config)
        # Delegate to existing ModelCircuitBreaker.record_success()
        cb.record_success()

    def _circuit_breaker_record_failure(self, key: str, config: ModelEffectCircuitBreaker) -> None:
        """Record failed request using existing infrastructure."""
        cb = self._get_or_create_circuit_breaker(key, config)
        # Delegate to existing ModelCircuitBreaker.record_failure()
        cb.record_failure()
```

### 6. Effect Executor - Pure Functions (~250 lines)

**Location**: `src/omnibase_core/utils/effect_executor.py`

```python
"""
Effect Executor - Stateless pure functions for effect operations.

VERSION: 1.0.0

All functions are pure (no side effects, no state) for:
- Unit testability without mocking
- Future portability to other runtimes (WASM, etc.)
- Clear separation from orchestration logic

Functions:
- resolve_template: Template variable substitution
- resolve_io_config: Converts EffectIOConfig to ResolvedIOContext (NEW in R4)
- calculate_backoff: Retry delay calculation
- is_retryable_error: Retryability predicate
- extract_response_fields: JSONPath extraction
"""

import os
import re
import random
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.effect_io_configs import (
    EffectIOConfig,
    ModelHttpIOConfig,
    ModelDbIOConfig,
    ModelKafkaIOConfig,
    ModelFilesystemIOConfig,
)
from omnibase_core.models.contracts.subcontracts.effect_resolved_context import (
    ResolvedIOContext,
    ModelResolvedHttpContext,
    ModelResolvedDbContext,
    ModelResolvedKafkaContext,
    ModelResolvedFilesystemContext,
)


def resolve_template(template: str, context: dict[str, Any]) -> str:
    """
    Resolve ${...} placeholders in template string.

    Supports:
        - ${input.field} - From context["input"]
        - ${env.VAR} - From environment variables
        - ${secret.KEY} - From context["secrets"] (future: secret manager)
        - ${output.field} - From context["output"] (previous step, v1.1)

    Args:
        template: String with ${...} placeholders
        context: Resolution context dict

    Returns:
        Resolved string with placeholders substituted

    Raises:
        ModelOnexError: If required placeholder cannot be resolved
    """
    pattern = r'\$\{([^}]+)\}'

    def replace(match: re.Match[str]) -> str:
        path = match.group(1)
        parts = path.split(".")

        if len(parts) < 2:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid template path: {path}. Expected format: ${{prefix.field}}",
            )

        prefix = parts[0]
        field_path = parts[1:]

        if prefix == "env":
            var_name = field_path[0] if field_path else ""
            value = os.environ.get(var_name)
            if value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Environment variable not found: {var_name}",
                )
            return value

        elif prefix == "secret":
            # v1.0: Fall back to env vars. v1.1+: Secret manager integration
            secret_name = field_path[0] if field_path else ""
            secrets = context.get("secrets", {})
            if secret_name in secrets:
                return str(secrets[secret_name])
            # Fallback to env
            value = os.environ.get(secret_name)
            if value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Secret not found: {secret_name}",
                )
            return value

        elif prefix == "input":
            return str(_resolve_nested_path(context.get("input", {}), field_path))

        elif prefix == "output":
            return str(_resolve_nested_path(context.get("output", {}), field_path))

        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown template prefix: {prefix}. Valid: input, env, secret, output",
            )

    return re.sub(pattern, replace, template)


def _resolve_nested_path(data: dict[str, Any], path: list[str]) -> Any:
    """Resolve nested path in dict."""
    current = data
    for part in path:
        if isinstance(current, dict):
            if part not in current:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Path not found: {'.'.join(path)}",
                )
            current = current[part]
        else:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Cannot traverse path {'.'.join(path)}: intermediate value is not a dict",
            )
    return current


def resolve_io_config(io_config: EffectIOConfig, context: dict[str, Any]) -> ResolvedIOContext:
    """
    Convert EffectIOConfig (with templates) to ResolvedIOContext (concrete values).

    NEW IN R4: This is the SINGLE POINT of template resolution for IO configs.
    Handlers receive the returned ResolvedIOContext, never raw io_config.

    Args:
        io_config: IO config with ${...} templates
        context: Resolution context with "input", "env", "secrets" keys

    Returns:
        ResolvedIOContext with all templates substituted

    Raises:
        ModelOnexError: If template resolution fails
    """
    handler_type = io_config.handler_type

    if handler_type == "http":
        assert isinstance(io_config, ModelHttpIOConfig)
        return ModelResolvedHttpContext(
            url=resolve_template(io_config.url_template, context),
            method=io_config.method,
            headers={k: resolve_template(v, context) for k, v in io_config.headers.items()},
            body=resolve_template(io_config.body_template, context) if io_config.body_template else None,
            query_params={k: resolve_template(v, context) for k, v in io_config.query_params.items()},
            timeout_ms=io_config.timeout_ms,
            follow_redirects=io_config.follow_redirects,
            verify_ssl=io_config.verify_ssl,
        )

    elif handler_type == "db":
        assert isinstance(io_config, ModelDbIOConfig)
        return ModelResolvedDbContext(
            operation=io_config.operation,
            connection_name=io_config.connection_name,
            query=resolve_template(io_config.query_template, context),
            params=[resolve_template(p, context) for p in io_config.query_params],
            timeout_ms=io_config.timeout_ms,
            fetch_size=io_config.fetch_size,
            read_only=io_config.read_only,
        )

    elif handler_type == "kafka":
        assert isinstance(io_config, ModelKafkaIOConfig)
        # Payload uses explicit payload_template from io_config (no silent empty defaults)
        return ModelResolvedKafkaContext(
            topic=io_config.topic,
            partition_key=resolve_template(io_config.partition_key_template, context) if io_config.partition_key_template else None,
            headers={k: resolve_template(v, context) for k, v in io_config.headers.items()},
            payload=resolve_template(io_config.payload_template, context),  # Explicit template
            timeout_ms=io_config.timeout_ms,
            acks=io_config.acks,
            compression=io_config.compression,
        )

    elif handler_type == "filesystem":
        assert isinstance(io_config, ModelFilesystemIOConfig)
        return ModelResolvedFilesystemContext(
            file_path=resolve_template(io_config.file_path_template, context),
            operation=io_config.operation,
            content=context.get("input", {}).get("content"),  # Content from input for writes
            timeout_ms=io_config.timeout_ms,
            atomic=io_config.atomic,
            create_dirs=io_config.create_dirs,
            encoding=io_config.encoding,
            mode=io_config.mode,
        )

    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown handler type: {handler_type}",
        )


def calculate_backoff(retry_count: int, policy: ModelEffectRetryPolicy) -> int:
    """
    Calculate backoff delay with jitter.

    Args:
        retry_count: Current retry attempt (1-based)
        policy: Retry policy configuration

    Returns:
        Delay in milliseconds
    """
    if policy.backoff_strategy == "fixed":
        delay = policy.base_delay_ms
    elif policy.backoff_strategy == "linear":
        delay = policy.base_delay_ms * retry_count
    else:  # exponential
        delay = policy.base_delay_ms * (2 ** (retry_count - 1))

    # Apply max cap
    delay = min(delay, policy.max_delay_ms)

    # Add jitter
    jitter = delay * policy.jitter_factor * (random.random() * 2 - 1)
    delay = int(delay + jitter)

    # Ensure non-negative
    return max(0, delay)


def is_retryable_error(error: Exception, policy: ModelEffectRetryPolicy) -> bool:
    """
    Determine if error is retryable based on policy.

    Args:
        error: The exception that occurred
        policy: Retry policy configuration

    Returns:
        True if error should be retried
    """
    error_str = str(error)

    # Check retryable error strings
    for retryable in policy.retryable_errors:
        if retryable in error_str:
            return True

    # Check HTTP status codes if available
    if hasattr(error, "status_code"):
        if error.status_code in policy.retryable_status_codes:
            return True

    # Check nested cause
    if error.__cause__ is not None:
        return is_retryable_error(error.__cause__, policy)

    return False


def extract_response_fields(
    response: dict[str, Any],
    extract_fields: dict[str, str],
    extraction_engine: Literal["jsonpath", "dotpath"] = "jsonpath",
) -> dict[str, str | int | float | bool | None]:
    """
    Extract fields from response using specified engine.

    FAIL-FAST BEHAVIOR:
    - If extraction_engine="jsonpath" but jsonpath_ng is not installed,
      raises ConfigurationError at extraction time.
    - No silent fallback to dotpath - explicit engine selection required.

    Args:
        response: Response dict to extract from
        extract_fields: Map of output_name -> path expression
        extraction_engine: "jsonpath" or "dotpath" (default: "jsonpath")

    Returns:
        Dict of extracted values (primitive types only: str, int, float, bool, None)

    Raises:
        ModelOnexError: If jsonpath_ng missing, extraction fails, or non-primitive result
    """
    result: dict[str, str | int | float | bool | None] = {}

    if not extract_fields:
        return result

    if extraction_engine == "jsonpath":
        try:
            from jsonpath_ng import parse as jsonpath_parse
        except ImportError:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                message="extraction_engine='jsonpath' requires jsonpath_ng package. "
                        "Install with: pip install jsonpath-ng "
                        "Or set extraction_engine='dotpath' for simple $.field.subfield syntax."
            )

        for field_name, jsonpath_expr in extract_fields.items():
            try:
                parsed = jsonpath_parse(jsonpath_expr)
                matches = parsed.find(response)
                if matches:
                    value = matches[0].value
                    result[field_name] = _coerce_to_primitive(value)
                else:
                    result[field_name] = None
            except Exception as e:
                # JSONPath parse or evaluation error
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.EXTRACTION_ERROR,
                    message=f"JSONPath extraction failed for '{field_name}': {e}",
                )

    elif extraction_engine == "dotpath":
        for field_name, dotpath_expr in extract_fields.items():
            value = _extract_dotpath(response, dotpath_expr)
            result[field_name] = _coerce_to_primitive(value)

    else:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown extraction_engine: {extraction_engine}. Use 'jsonpath' or 'dotpath'.",
        )

    return result


def _coerce_to_primitive(value: Any) -> str | int | float | bool | None:
    """
    Coerce value to primitive type, rejecting complex types.

    Args:
        value: Any value from extraction

    Returns:
        Primitive value (str, int, float, bool, None)

    Raises:
        ModelOnexError: If value is a complex type (list, dict, etc.)
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    # Reject lists, dicts, and other complex types
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.EXTRACTION_ERROR,
        message=f"Extraction returned non-primitive type: {type(value).__name__}. "
                f"Only str, int, float, bool, None are allowed.",
    )


def _extract_dotpath(data: dict[str, Any], path: str) -> Any:
    """
    Extract value using simple dotpath ($.field.subfield).

    Args:
        data: Dict to extract from
        path: Dotpath expression (must start with "$.")

    Returns:
        Extracted value (may be None if path not found)

    Raises:
        ModelOnexError: If path doesn't start with "$."
    """
    if not path.startswith("$."):
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Dotpath must start with '$.' - got: {path}",
        )

    parts = path[2:].split(".")  # Remove "$." prefix
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current

```

---

## Contract Schema

### Complete YAML Example (Revised)

```yaml
# examples/contracts/effect/slack_notification.yaml
effect_subcontract:
  # Contract metadata for tooling and RSD compatibility
  metadata:
    revision: 1
    author: "onex-team"
    tags: ["notification", "slack", "http"]

  subcontract_name: slack_notification_sender
  version: "1.0.0"
  description: "Send notifications to Slack channels with retry and circuit breaker"

  # EXPLICIT execution semantics
  execution_mode: sequential_abort

  # Sequential operations - abort on first failure
  operations:
    - operation_name: send_slack_message
      description: "Post message to Slack channel"

      # Explicit idempotency (POST is not idempotent by default)
      idempotent: false  # Prevents retry

      # Discriminated union IO config
      io_config:
        handler_type: http
        url_template: "https://slack.com/api/chat.postMessage"
        method: POST
        headers:
          Content-Type: "application/json"
          Authorization: "Bearer ${secret.SLACK_TOKEN}"
        body_template: |
          {
            "channel": "${input.channel}",
            "text": "${input.message}",
            "username": "${input.username}"
          }
        timeout_ms: 10000

      response_handling:
        success_codes: [200]
        extract_fields:
          message_ts: "$.ts"
          channel_id: "$.channel"
        fail_on_empty: false

      # NO retry - operation is not idempotent
      retry_policy:
        enabled: false

  # Global defaults
  default_retry_policy:
    enabled: true
    max_retries: 3
    backoff_strategy: exponential
    base_delay_ms: 1000
    max_delay_ms: 30000
    jitter_factor: 0.1
    retryable_status_codes: [429, 500, 502, 503, 504]

  default_circuit_breaker:
    enabled: true
    failure_threshold: 5
    success_threshold: 2
    timeout_ms: 60000
    half_open_requests: 3

  # NO transaction - HTTP is not transactional
  transaction:
    enabled: false

  observability:
    log_request: true
    log_response: false  # May contain sensitive tokens
    emit_metrics: true
    trace_propagation: true
```

### Database Transaction Example (Revised)

```yaml
# examples/contracts/effect/user_update_transaction.yaml
effect_subcontract:
  # Contract metadata
  metadata:
    revision: 1
    author: "onex-team"
    tags: ["database", "transaction", "user-profile"]

  subcontract_name: user_profile_transaction
  version: "1.0.0"
  description: "Update user profile with transaction support"

  execution_mode: sequential_abort

  operations:
    # All operations MUST be DB and use SAME connection for transaction
    - operation_name: update_user_profile
      idempotent: true  # UPDATE is idempotent

      io_config:
        handler_type: db
        operation: update  # EXPLICIT - no query string parsing
        connection_name: "primary_postgres"  # MUST match across all ops
        query_template: |
          UPDATE users
          SET display_name = $1, email = $2, updated_at = NOW()
          WHERE user_id = $3
        query_params: ["${input.display_name}", "${input.email}", "${input.user_id}"]
        timeout_ms: 5000

      response_handling:
        extract_fields:
          rows_affected: "$.rowCount"

      retry_policy:
        enabled: true
        max_retries: 2

    - operation_name: log_profile_change
      idempotent: true  # INSERT with ON CONFLICT is idempotent (upsert semantics)

      io_config:
        handler_type: db
        operation: upsert  # EXPLICIT - ON CONFLICT makes it idempotent
        connection_name: "primary_postgres"  # SAME connection
        query_template: |
          INSERT INTO audit_log (user_id, action, timestamp)
          VALUES ($1, 'profile_update', NOW())
          ON CONFLICT (user_id, action, timestamp) DO NOTHING
        query_params: ["${input.user_id}"]
        timeout_ms: 5000

  # Transaction ENABLED - valid because all ops are DB with same connection
  transaction:
    enabled: true
    isolation_level: read_committed
    rollback_on_error: true
    timeout_ms: 30000
```

### Invalid Contract Examples (For Documentation)

```yaml
# INVALID: Transaction with mixed handler types
effect_subcontract:
  subcontract_name: invalid_mixed_transaction
  operations:
    - operation_name: db_op
      io_config:
        handler_type: db
        operation: select  # Explicit operation type
        connection_name: "postgres"
        query_template: "SELECT 1"
    - operation_name: http_op
      io_config:
        handler_type: http  # ERROR: Can't mix with transaction
        url_template: "https://api.example.com"
        method: GET

  transaction:
    enabled: true  # VALIDATION ERROR: Non-DB operations found

---

# INVALID: Retry on non-idempotent operation
effect_subcontract:
  subcontract_name: invalid_retry_idempotency
  operations:
    - operation_name: kafka_produce
      idempotent: false  # Kafka produce is not idempotent
      io_config:
        handler_type: kafka
        topic: "events"
      retry_policy:
        enabled: true
        max_retries: 3  # VALIDATION ERROR: Cannot retry non-idempotent

---

# INVALID: Transaction with different connections
effect_subcontract:
  subcontract_name: invalid_multi_connection
  operations:
    - operation_name: read_user
      io_config:
        handler_type: db
        operation: select  # Explicit operation type
        connection_name: "postgres_read"  # Different connection
        query_template: "SELECT * FROM users"
    - operation_name: write_user
      io_config:
        handler_type: db
        operation: update  # Explicit operation type
        connection_name: "postgres_write"  # Different connection
        query_template: "UPDATE users SET ..."

  transaction:
    enabled: true  # VALIDATION ERROR: Multiple connections

---

# INVALID: Raw DB operation with retry (unsafe)
effect_subcontract:
  subcontract_name: invalid_raw_retry
  operations:
    - operation_name: complex_query
      io_config:
        handler_type: db
        operation: raw  # Raw operations default to non-idempotent
        connection_name: "postgres"
        query_template: "CALL some_procedure($1)"
        query_params: ["${input.param}"]
      retry_policy:
        enabled: true
        max_retries: 3  # VALIDATION ERROR: 'raw' operations are non-idempotent by default
```

---

## Validation Rules

### Contract Load-Time Validations

| Rule | Error Message | Severity |
|------|---------------|----------|
| Transaction requires all DB ops | "Transaction enabled but found non-DB operations: [names]" | REJECT |
| Transaction requires same connection | "All DB operations in a transaction must use the same connection" | REJECT |
| No retry on non-idempotent | "Operation 'X' is not idempotent but has retry enabled" | REJECT |
| IO config matches handler type | Pydantic discriminated union validation | REJECT |
| At least one operation | "Subcontract must have at least one operation" | REJECT |
| DB operation type required | "DB io_config must specify operation type (select/insert/update/delete/upsert/raw)" | REJECT |
| DB operation case normalization | Operation normalized to lowercase; "SELECT" becomes "select" | AUTO-FIX |
| Raw query injection prevention | "Raw DB queries must not embed ${input.*} templates directly in query_template" | REJECT |
| SELECT retry in strict isolation | "SELECT with retry enabled inside repeatable_read/serializable transaction violates snapshot semantics" | REJECT |
| Raw DB ops non-idempotent | "'raw' DB operations default to non-idempotent unless explicitly set" | WARN |
| Handler type is valid enum | "Invalid handler_type. Must be one of: http, db, kafka, filesystem" | REJECT |
| No raw DB in transactions | "Raw DB operations not allowed inside transactions: [names]" | REJECT |
| JSONPath requires jsonpath_ng | "extraction_engine='jsonpath' requires jsonpath_ng package" | REJECT |
| Extraction returns non-primitive | "Extraction returned non-primitive type: {type}" | REJECT |
| Invalid extraction engine | "Unknown extraction_engine: {value}. Use 'jsonpath' or 'dotpath'" | REJECT |
| Dotpath requires $. prefix | "Dotpath must start with '$.' - got: {path}" | REJECT |

### Runtime Validations

| Rule | Behavior | Recovery |
|------|----------|----------|
| Circuit breaker open | Fail fast without calling handler | Wait for timeout |
| Handler not available | ModelOnexError with RESOURCE_UNAVAILABLE | Manual intervention |
| Template resolution failure | ModelOnexError with VALIDATION_ERROR | Fix input data |
| JSONPath package missing | ModelOnexError with CONFIGURATION_ERROR | Install jsonpath-ng or use dotpath |
| JSONPath extraction error | ModelOnexError with EXTRACTION_ERROR | Fix JSONPath expression |
| Non-primitive extraction result | ModelOnexError with EXTRACTION_ERROR | Adjust extraction path to return primitive |
| Response field not found | Return None for missing fields | Graceful degradation |

---

## Execution Flow

### Sequence Diagram (Revised)

```
┌─────────┐    ┌──────────────┐    ┌─────────────────────┐    ┌─────────────┐
│  Caller │    │  NodeEffect  │    │ MixinEffectExecution│    │   Handler   │
└────┬────┘    └──────┬───────┘    └──────────┬──────────┘    └──────┬──────┘
     │                │                       │                      │
     │  process()     │                       │                      │
     │───────────────>│                       │                      │
     │                │   execute_effect()    │                      │
     │                │──────────────────────>│                      │
     │                │                       │                      │
     │                │                       │ foreach operation:   │
     │                │                       │                      │
     │                │                       │ 1. Check idempotency │
     │                │                       │ 2. Check circuit breaker
     │                │                       │ 3. Resolve templates │
     │                │                       │                      │
     │                │                       │  execute_with_resilience()
     │                │                       │─────────────────────>│
     │                │                       │                      │
     │                │                       │     [retry loop if   │
     │                │                       │      idempotent]     │
     │                │                       │                      │
     │                │                       │<─────────────────────│
     │                │                       │  ModelEffectOperationResult
     │                │                       │                      │
     │                │                       │ 4. Extract response  │
     │                │                       │ 5. Update circuit breaker
     │                │                       │                      │
     │                │   ModelEffectOutput   │                      │
     │                │<──────────────────────│                      │
     │  output        │                       │                      │
     │<───────────────│                       │                      │
```

### Execution Mode Behavior

#### Behavior Matrix

| Mode | On Success | On Failure | Returns | Raises |
|------|------------|------------|---------|--------|
| `sequential_abort` | Continue to next | Stop immediately | Partial results in exception | `ModelOnexError` |
| `sequential_continue` | Continue to next | Continue to next | Complete results | Never (for op failures) |

#### When to Use Each Mode

**sequential_abort** is appropriate when:
- Operations have dependencies (later ops need earlier results)
- Partial completion is worse than complete failure
- You want fail-fast semantics
- Atomicity matters: "all succeed or fail fast"

**sequential_continue** is appropriate when:
- Operations are independent
- You need to know which operations succeeded/failed
- Best-effort execution is acceptable
- Reporting all outcomes matters: "run everything, report all outcomes"

#### Visual Examples

**sequential_abort (default)**:
```
Operation 1: send_slack_message  ─────▶ SUCCESS ─────▶ Continue
Operation 2: update_database     ─────▶ FAILURE ─────▶ ABORT
Operation 3: emit_event          ─────▶ (not executed)

Result:
  - transaction_state: ROLLED_BACK
  - failed_operation: "update_database"
  - RAISES ModelOnexError
  - Partial output in exception.context["partial_output"]
```

**sequential_continue**:
```
Operation 1: send_slack_message  ─────▶ SUCCESS ─────▶ Continue
Operation 2: update_database     ─────▶ FAILURE ─────▶ Continue (record error)
Operation 3: emit_event          ─────▶ SUCCESS ─────▶ Done

Result:
  - transaction_state: FAILED (has failures)
  - failed_operation: "update_database"
  - RETURNS ModelEffectOutput normally
  - Check operations[1].success == False for failure details
```

#### Accessing Partial Results (sequential_abort)

When `sequential_abort` raises, the partial output is attached to the exception:

```python
try:
    output = await node.execute_effect(input_data)
except ModelOnexError as e:
    # Access partial results
    partial = e.context.get("partial_output", {})
    completed_ops = partial.get("operations", [])
    failed_op = partial.get("failed_operation")

    # Log what completed before failure
    for op in completed_ops:
        logger.info(f"Operation {op['operation_name']}: success={op['success']}")
```

---

## Resilience Patterns

> **Integration Note**: NodeEffect's circuit breaker leverages the existing
> `ModelCircuitBreaker` and `ModelCircuitBreakerSubcontract` infrastructure
> defined in `omnibase_core.models.configuration`. For advanced features
> (sliding windows, failure rates, slow call detection), compose with the
> full `ModelCircuitBreakerSubcontract` from
> `omnibase_core.models.contracts.subcontracts.model_circuit_breaker_subcontract`.


### Circuit Breaker (Process-Local)

**Scope**: v1.0 circuit breaker is **process-local only**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Process Boundary                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ NodeEffect 1 │  │ NodeEffect 2 │  │ NodeEffect 3 │          │
│  │              │  │              │  │              │          │
│  │ CB State A   │  │ CB State B   │  │ CB State C   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│        │                 │                 │                    │
│        └─────────────────┴─────────────────┘                    │
│                    NOT SHARED                                   │
│        Each instance has independent circuit breaker state      │
└─────────────────────────────────────────────────────────────────┘
```

**Key Characteristics**:
- Uses existing `ModelCircuitBreaker` infrastructure (typed model, no `dict[str, Any]`)
- Leverages `should_allow_request()`, `record_success()`, `record_failure()` methods
- NOT thread-safe - create separate NodeEffect instances per thread
- Provides local protection against cascading failures
- Does NOT provide cluster-wide coordination (use v1.2+ for that)

#### Circuit Breaker Keying Strategy

**Keyed by**: `operation.correlation_id` (UUID)

Each `ModelEffectOperation` has a `correlation_id` field (auto-generated UUID if not specified). The circuit breaker uses this as the state lookup key:

```python
# In MixinEffectExecution._execute_with_resilience():
cb_key = str(operation.correlation_id)  # Stable identity
```

**Why `correlation_id` instead of operation name or handler type?**

| Keying Strategy | Pros | Cons |
|-----------------|------|------|
| **`correlation_id` (chosen)** | Stable identity; survives operation renames; each operation definition has isolated state | Requires explicit correlation_id for cross-contract coordination |
| `operation_name` | Human-readable keys | Renaming operation resets circuit breaker state; name collisions across subcontracts |
| `handler_type + resource` | Aggregates failures across operations hitting same resource | Unrelated operations could trip each other's breakers; loses operation-level granularity |

**Implications**:

1. **Rename Safety**: Renaming `operation_name` from `"send_notification"` to `"notify_user"` does NOT reset circuit breaker state - the `correlation_id` remains constant.

2. **Per-Operation Isolation**: Each operation definition maintains independent circuit breaker state. Two operations calling the same HTTP endpoint have separate breaker states (unless they share the same `correlation_id`).

3. **Cross-Contract Coordination**: If you need multiple operations (across subcontracts) to share circuit breaker state, explicitly set the same `correlation_id` on each:
   ```yaml
   # subcontract_a.yaml
   operations:
     - operation_name: call_payment_api
       correlation_id: "550e8400-e29b-41d4-a716-446655440000"  # Shared
       io_config: ...

   # subcontract_b.yaml
   operations:
     - operation_name: retry_payment
       correlation_id: "550e8400-e29b-41d4-a716-446655440000"  # Same ID = shared state
       io_config: ...
   ```

4. **State Persistence**: In v1.0, circuit breaker state is process-local and ephemeral. Process restart clears all state. For persistent/distributed state, see v1.2 roadmap.

> **Note**: This differs from alternative designs that key by "handler type + resource URL" which would aggregate circuit breaker state across all operations hitting the same endpoint. The `correlation_id` approach provides finer-grained control at the cost of requiring explicit coordination when aggregation is desired.

### Idempotency-Aware Retry

```
┌─────────────────────────────────────────────────────────────────┐
│ Operation: HTTP POST to /users                                   │
│ idempotent: false (default for POST)                            │
│                                                                  │
│ Attempt 1: Execute ─────▶ FAILURE (timeout)                     │
│                                                                  │
│ STOP - Cannot retry non-idempotent operation                    │
│ Reason: May have created user before timeout                    │
│                                                                  │
│ Result: ModelOnexError (no retry attempted)                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ Operation: HTTP PUT to /users/123                               │
│ idempotent: true (default for PUT)                              │
│                                                                  │
│ Attempt 1: Execute ─────▶ FAILURE (502)                         │
│            Wait: 1000ms                                          │
│                                                                  │
│ Attempt 2: Execute ─────▶ FAILURE (503)                         │
│            Wait: 2000ms                                          │
│                                                                  │
│ Attempt 3: Execute ─────▶ SUCCESS                               │
│                                                                  │
│ Result: Success with retries=2                                   │
└─────────────────────────────────────────────────────────────────┘
```

> **Template Resolution in Retry Loop**: Template resolution (including secret
> lookups and environment variable access) occurs INSIDE the retry loop. This
> means transient resolution failures (e.g., secrets store temporarily unavailable,
> environment not fully loaded) can be retried when allowed by the retry policy.
> If resolution consistently fails, it will exhaust retries like any other failure.
>
> **Operation-Level Timeout**: Each operation has an `operation_timeout_ms` field
> (default 60 seconds) that acts as a deadline for the entire operation including
> all retries. This prevents retry stacking from exceeding intended time limits.
> The deadline is checked at the start of each retry iteration - if the deadline
> has passed, the operation fails with `EnumCoreErrorCode.TIMEOUT`.

### Non-Transactional Multi-DB Operations (Foot-Gun Warning)

> **WARNING**: This section documents a potentially dangerous configuration that is **intentionally allowed** but requires careful consideration.

**The Scenario**:

When a contract has `transaction.enabled=false` (the default) AND contains multiple database operations, those operations execute **WITHOUT transactional guarantees**.

```yaml
# CAUTION: This is valid but potentially dangerous
effect_subcontract:
  subcontract_name: multi_db_no_transaction
  operations:
    - operation_name: update_user_balance
      io_config:
        handler_type: db
        operation: update
        connection_name: "primary_postgres"
        query_template: "UPDATE accounts SET balance = balance - $1 WHERE user_id = $2"
        query_params: ["${input.amount}", "${input.user_id}"]

    - operation_name: insert_transaction_record
      io_config:
        handler_type: db
        operation: insert
        connection_name: "primary_postgres"
        query_template: "INSERT INTO transactions (user_id, amount, type) VALUES ($1, $2, 'debit')"
        query_params: ["${input.user_id}", "${input.amount}"]

  # DEFAULT - no transaction wrapping!
  transaction:
    enabled: false
```

**What Happens on Partial Failure**:

```
Operation 1: update_user_balance   ─────▶ SUCCESS ─────▶ COMMITTED (permanently)
Operation 2: insert_transaction_record ─────▶ FAILURE
                                                        ^
                                                        |
                                         Data is now INCONSISTENT
                                         - Balance was deducted
                                         - No transaction record exists
                                         - Operation 1 CANNOT be rolled back
```

**Key Behaviors**:

| Aspect | Behavior |
|--------|----------|
| **Isolation** | None - each operation commits independently |
| **Atomicity** | None - partial completion is possible |
| **Rollback** | Impossible - committed operations cannot be undone |
| **Visibility** | Intermediate states visible to other transactions |

**Why This Is Allowed**:

This configuration is intentionally permitted because there are legitimate use cases:

1. **Cross-Database Operations**: Reading from one database and writing to another (different `connection_name` values)
2. **Read-Then-Write Patterns**: SELECT from DB A, then INSERT into DB B based on results
3. **Audit Logging**: Primary operation + separate audit log that should persist even if later ops fail
4. **Performance Optimization**: When operations are truly independent and atomicity is not required

**Example: Legitimate Cross-DB Pattern**:

```yaml
# VALID USE CASE: Read from read replica, write to primary
effect_subcontract:
  subcontract_name: cross_db_sync
  operations:
    - operation_name: read_from_replica
      io_config:
        handler_type: db
        operation: select
        connection_name: "read_replica"  # Different connection
        query_template: "SELECT * FROM users WHERE needs_sync = true LIMIT 100"

    - operation_name: write_to_primary
      io_config:
        handler_type: db
        operation: upsert
        connection_name: "primary_db"  # Different connection - transaction impossible anyway
        query_template: "INSERT INTO user_sync_log ..."

  # Transaction cannot span different connections, so this is correct
  transaction:
    enabled: false
```

**Recommendations**:

| Scenario | Recommendation |
|----------|----------------|
| Multiple DB ops, same connection, need atomicity | Set `transaction.enabled=true` |
| Multiple DB ops, different connections | Keep `transaction.enabled=false` (required) |
| Multiple DB ops, same connection, independence is OK | Explicitly document why in `description` field |
| Mixed handler types (DB + HTTP/Kafka) | `transaction.enabled=false` (required) |

**Validation Gap (Known Limitation)**:

The v1.0 validation does NOT warn when:
- Multiple DB operations exist
- All use the same `connection_name`
- `transaction.enabled=false`

This is a known foot-gun. Future versions (v1.1+) may add an **optional** lint warning for this pattern.

**Best Practice**:

Always ask yourself: "If operation N fails, what state will the system be in?"

If the answer is "inconsistent and unrecoverable," you probably need `transaction.enabled=true`.

---

## Migration Strategy

### Coexistence Model

**Contract-driven NodeEffect v1.0 is a subset of legacy NodeEffect.**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Deployment Options                          │
│                                                                  │
│  Option A: Legacy Only                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ NodeEffect (legacy)                                       │   │
│  │ - Full Python flexibility                                 │   │
│  │ - Custom handlers inline                                  │   │
│  │ - Manual resilience implementation                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Option B: Contract-Driven Only                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ NodeEffect (v2.0 contract-driven)                         │   │
│  │ - Zero custom Python                                      │   │
│  │ - YAML contracts only                                     │   │
│  │ - Built-in resilience from contract                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Option C: Mixed Deployment (Recommended for Migration)         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ NodeEffectLegacy (moved to legacy/)                       │   │
│  │ - Existing code continues to work                         │   │
│  │ - Deprecation warnings on import                          │   │
│  │                                                           │   │
│  │ NodeEffect (v2.0 contract-driven)                         │   │
│  │ - New effects use contracts                               │   │
│  │ - Gradual migration of existing effects                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Migration Template

**Before (Legacy)**:
```python
class MyEffectNode(NodeEffect):
    async def process(self, input_data: ModelEffectInput) -> ModelEffectOutput:
        # Custom Python logic
        async with aiohttp.ClientSession() as session:
            for _ in range(3):  # Manual retry
                try:
                    resp = await session.post(
                        "https://api.slack.com/...",
                        headers={"Authorization": f"Bearer {os.environ['SLACK_TOKEN']}"},
                        json={"channel": input_data.operation_data["channel"], ...}
                    )
                    if resp.status == 200:
                        return ModelEffectOutput(...)
                except Exception:
                    await asyncio.sleep(1)
            raise ModelOnexError(...)
```

**After (Contract-Driven)**:
```yaml
# my_effect.yaml
effect_subcontract:
  subcontract_name: my_effect
  operations:
    - operation_name: send_message
      idempotent: false
      io_config:
        handler_type: http
        url_template: "https://api.slack.com/..."
        method: POST
        headers:
          Authorization: "Bearer ${secret.SLACK_TOKEN}"
        body_template: '{"channel": "${input.channel}", ...}'
      retry_policy:
        enabled: false  # POST not idempotent
```

```python
# Usage
node = NodeEffect.from_contract(container, yaml_content)
result = await node.process(input_data)
```

---

## Testing Strategy

### Unit Tests (~200 tests)

| Category | Count | Focus |
|----------|-------|-------|
| Discriminated Union Validation | 30 | IO config type safety |
| Idempotency Validation | 25 | Retry/idempotency interaction |
| Transaction Validation | 20 | DB-only, same-connection rules |
| Template Resolution | 25 | `${input.*}`, `${env.*}`, `${secret.*}` |
| Backoff Calculation | 15 | Fixed, linear, exponential with jitter |
| Circuit Breaker State | 25 | Open/closed/half-open transitions |
| Response Extraction | 20 | JSONPath extraction edge cases |
| Operation Result Typing | 20 | ModelEffectOperationResult validation |
| Execution Mode | 20 | sequential_abort vs sequential_continue |

### Integration Tests (~60 tests)

| Category | Count | Focus |
|----------|-------|-------|
| HTTP Handler | 15 | Real HTTP calls with mock server |
| Database Handler | 15 | PostgreSQL with transaction tests |
| Filesystem Handler | 10 | Atomic writes, directory creation |
| Kafka Handler | 10 | Producer with mock broker |
| Multi-Operation | 10 | Sequential execution, abort semantics |

---

## Version Roadmap

### v1.0 (Current)

- Sequential operations with explicit execution_mode
- 4 handler types with discriminated union IO configs
- Idempotency-aware retry policies
- Process-local circuit breaker
- DB-only, same-connection transactions
- Template substitution with ${secret.*} support
- Strongly-typed ModelEffectOperationResult

### v1.1 (Next)

- Parallel operations with semaphore
- Custom handler registration
- Rate limiting
- Per-step timeouts
- Response caching
- ${output.*} template for previous step results

### v1.2 (Future)

- Conditional operations (`when` clause)
- Streaming responses
- Bulkhead pattern
- Expression language for conditions
- Saga pattern / compensation handlers
- Distributed circuit breaker (Redis-backed)

---

## Files to Create

| File | Lines | Priority |
|------|-------|----------|
| `models/contracts/subcontracts/effect_io_configs.py` | ~150 | P0 |
| `models/contracts/subcontracts/model_effect_subcontract.py` | ~250 | P0 |
| `models/model_effect_output.py` (updated) | ~60 | P0 |
| `mixins/mixin_effect_execution.py` | ~400 | P0 |
| `utils/effect_executor.py` | ~250 | P0 |
| `nodes/node_effect.py` (refactored) | ~80 | P0 |
| `enums/enum_effect_handler_type.py` | ~30 | P0 |
| `handlers/filesystem_handler.py` | ~150 | P1 |
| `legacy/node_effect_v1.py` (moved) | ~1000 | P1 |
| Tests (unit + integration) | ~1500 | P0 |
| Example contracts | ~200 | P1 |

**Total**: ~4,070 lines of new code

---

## Acceptance Criteria (Revised)

From Design Review + R3 Improvements + R4 Protocol-Frozen:

- [ ] **Discriminated union IO configs** - Type-safe per-handler validation
- [ ] **EnumEffectHandlerType** - Handler types use enum, not raw strings
- [ ] **Explicit DB operation type** - ModelDbIOConfig requires `operation` field
- [ ] **Idempotency validation** - Reject retry on non-idempotent operations
- [ ] **Corrected filesystem idempotency** - `write` and `copy` default to non-idempotent
- [ ] **Transaction scope enforcement** - DB-only, same-connection validation
- [ ] **Process-local circuit breaker** - Keyed by correlation_id, typed state
- [ ] **ModelCircuitBreaker Integration** - Uses existing infrastructure, typed state
- [ ] **Strongly-typed output** - ModelEffectOperationResult, zero Any types
- [ ] **Contract metadata** - ModelEffectContractMetadata for tooling/RSD
- [ ] **Future reserved section** - Forward compatibility placeholder
- [ ] **Explicit execution_mode** - sequential_abort/sequential_continue in contract
- [ ] **Secret reference syntax** - ${secret.KEY} with env fallback
- [ ] **Pure functions in effect_executor.py** - Template, backoff, retryability
- [ ] **MixinEffectExecution** - Orchestration only, delegates to pure functions
- [ ] **NodeEffect refactored** - Zero custom logic, contract-driven via mixin
- [ ] **Legacy coexistence** - NodeEffectLegacy in legacy/ with deprecation warnings
- [ ] **ResolvedIOContext** - Templates resolved to typed context before handler invocation
- [ ] **resolve_io_config()** - Pure function converts EffectIOConfig to ResolvedIOContext
- [ ] **Handler contract** - Handlers receive ResolvedIOContext, never raw templates
- [ ] **extraction_engine explicit** - Response extraction engine specified in contract
- [ ] **input_schema reserved** - Field reserved for v1.1 input validation
- [ ] **deterministic flag** - Field reserved for RSD replay safety hints
- [ ] Handler dispatch works for: http, db, kafka, filesystem
- [ ] Unit tests with contract-only node definitions
- [ ] Example contract YAML in `examples/contracts/effect/`
- [ ] Type checking passes (mypy --strict)

---

## References

- [PR #115: NodeCompute v1.0 Implementation](https://github.com/OmniNode-ai/omnibase_core/pull/115)
- [ONEX Four-Node Architecture](./ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Subcontract Architecture](./SUBCONTRACT_ARCHITECTURE.md)

---

**Document Version**: 1.0.0 (R17 - PROTOCOL FROZEN - IMPLEMENTATION READY)
**Revision**: R17 - Architectural audit corrections (Core/SPI separation, registry pattern, execution semantics)
**Revision History**:
- R1-R2: Initial design and architectural hardening
- R3: Type safety (enum handler types, typed circuit breaker state, explicit DB ops)
- R4: Protocol-frozen (resolved IO context, handler contract, reserved fields)
- R5: Non-transactional multi-DB foot-gun warning
- R6-R14: Validators (enum normalization, casing, atomicity, injection prevention, param count)
- R15: Final semantic documentation (deterministic consequences, ONEX namespaces, nested transactions)
- R16: Safety enhancements (no raw DB ops in transactions, explicit extraction engine, non-primitive rejection)
- R17: Architectural audit (Core/SPI separation via EffectHandlerRegistry, template resolution inside retry, operation-level timeout, execution mode clarity, contract_hash)
**Last Updated**: 2025-12-07
**Author**: ONEX Framework Team
