# Mixin Contract Gaps - Action Plan

**Generated**: 2025-10-15
**Requirement**: "there should be a contract model and yaml contract/subcontract for every mixin type"

---

## Executive Summary

**Current State**:
- **10 mixins** documented in `mixin_metadata.yaml`
- **1 mixin** has complete coverage (metadata + subcontract)
- **9 mixins** are missing subcontract models
- **34 mixin implementations** exist in codebase but lack metadata

**Critical Finding**: `model_circuit_breaker.py` is NOT a proper subcontract model:
- Missing `_subcontract` suffix
- Missing `INTERFACE_VERSION` ClassVar
- It's a component model used by routing subcontract, not a standalone mixin subcontract

---

## PRIORITY 1: Create Missing Subcontract Models

These 9 mixins in metadata REQUIRE subcontract models following the `ModelCachingSubcontract` pattern:

### 1. model_retry_subcontract.py (for MixinRetry)

**Status**: ❌ MISSING
**Template**: Use `model_caching_subcontract.py` as reference
**Required Fields** (from mixin_metadata.yaml config_schema):
```python
class ModelRetrySubcontract(BaseModel):
    """Retry subcontract model for automatic retry logic."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Core retry configuration
    max_retries: int = Field(default=3, ge=0, le=100)
    base_delay_seconds: float = Field(default=1.0, ge=0.1, le=3600.0)

    # Backoff strategy
    backoff_strategy: str = Field(default="exponential")  # enum: fixed, linear, exponential, random, fibonacci
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    max_delay_seconds: float = Field(default=300.0, ge=1.0, le=3600.0)

    # Jitter configuration
    jitter_enabled: bool = Field(default=True)
    jitter_max_seconds: float = Field(default=1.0, ge=0.0, le=60.0)

    # Retry conditions
    retry_on_exceptions: list[str] = Field(default_factory=lambda: ["ConnectionError", "TimeoutError", "HTTPError"])
    retry_on_status_codes: list[int] = Field(default_factory=lambda: [429, 500, 502, 503, 504])
    stop_on_success: bool = Field(default=True)

    # Circuit breaker integration
    circuit_breaker_enabled: bool = Field(default=False)
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=100)
    circuit_reset_timeout_seconds: float = Field(default=60.0, ge=1.0, le=3600.0)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
```

---

### 2. model_health_check_subcontract.py (for MixinHealthCheck)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelHealthCheckSubcontract(BaseModel):
    """Health check subcontract model for health monitoring."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    health_check_interval_ms: int = Field(default=30000, ge=1000, le=300000)
    health_check_timeout_ms: int = Field(default=5000, ge=100, le=30000)
    failure_threshold: int = Field(default=3, ge=1, le=10)
    recovery_threshold: int = Field(default=2, ge=1, le=10)
    include_dependency_checks: bool = Field(default=True)
    include_component_checks: bool = Field(default=True)
    enable_async_checks: bool = Field(default=True)
    aggregate_check_results: bool = Field(default=True)
    emit_health_events: bool = Field(default=True)
    health_status_ttl_seconds: int = Field(default=30, ge=5, le=3600)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 3. model_event_bus_subcontract.py (for MixinEventBus)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelEventBusSubcontract(BaseModel):
    """Event bus subcontract model for event-driven communication."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Core event bus configuration
    event_bus_enabled: bool = Field(default=True)
    event_bus_type: str = Field(default="hybrid")  # enum: redis, kafka, memory, hybrid

    # Event emission configuration
    enable_event_logging: bool = Field(default=True)
    correlation_tracking: bool = Field(default=True)
    event_retention_seconds: int = Field(default=3600, ge=0, le=86400)

    # Reliability and retry
    max_retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_ms: int = Field(default=1000, ge=0, le=10000)
    enable_event_validation: bool = Field(default=True)
    graceful_degradation: bool = Field(default=True)

    # Event routing
    routing_key_strategy: str = Field(default="type_based")  # enum: type_based, priority_based, broadcast, topic_based
    enable_dead_letter_queue: bool = Field(default=True)

    # Performance tuning
    event_batch_size: int = Field(default=1, ge=1, le=1000)
    event_buffer_size: int = Field(default=100, ge=10, le=10000)
    publish_timeout_ms: int = Field(default=5000, ge=100, le=30000)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 4. model_circuit_breaker_subcontract.py (for MixinCircuitBreaker)

**Status**: ⚠️ **RENAME REQUIRED**
**Action**: The existing `model_circuit_breaker.py` needs to be:
1. Renamed to `model_circuit_breaker_subcontract.py`
2. Enhanced with:
   - `INTERFACE_VERSION: ClassVar[ModelSemVer]`
   - Comprehensive docstring with VERSION and STABILITY GUARANTEE
   - Field validators for business rules
   - ConfigDict instead of dict

**Current model_circuit_breaker.py is a COMPONENT** (used by routing subcontract), not a mixin subcontract!

**New fields to add** (from metadata):
```python
class ModelCircuitBreakerSubcontract(BaseModel):
    """Circuit breaker subcontract model for fault tolerance."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Keep existing fields from model_circuit_breaker.py:
    enabled: bool = Field(default=True)
    failure_threshold: int = Field(default=5, ge=1, le=100)  # Updated max from metadata
    success_threshold: int = Field(default=2, ge=1, le=20)   # Updated default/max from metadata
    timeout_seconds: int = Field(default=60, ge=1, le=300)   # Renamed from timeout_ms, updated from metadata

    # Keep other existing fields...

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 5. model_logging_subcontract.py (for MixinLogging)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelLoggingSubcontract(BaseModel):
    """Logging subcontract model for structured logging."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    log_level: str = Field(default="INFO")  # enum: DEBUG, INFO, WARNING, ERROR, CRITICAL
    enable_context_logging: bool = Field(default=True)
    enable_correlation_tracking: bool = Field(default=True)
    log_format: str = Field(default="json")  # enum: json, text, structured
    enable_log_redaction: bool = Field(default=True)
    sensitive_field_patterns: list[str] = Field(default_factory=lambda: ["password", "secret", "token", "key"])
    log_buffer_size: int = Field(default=100, ge=10, le=10000)
    enable_async_logging: bool = Field(default=True)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 6. model_metrics_subcontract.py (for MixinMetrics)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelMetricsSubcontract(BaseModel):
    """Metrics subcontract model for performance metrics collection."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    metrics_backend: str = Field(default="prometheus")  # enum: prometheus, opentelemetry, statsd
    enable_histograms: bool = Field(default=True)
    enable_counters: bool = Field(default=True)
    enable_gauges: bool = Field(default=True)
    enable_timers: bool = Field(default=True)
    metrics_prefix: str = Field(default="onex")
    metrics_port: int = Field(default=9090, ge=1024, le=65535)
    enable_detailed_metrics: bool = Field(default=False)
    aggregation_interval_ms: int = Field(default=60000, ge=1000, le=300000)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 7. model_security_subcontract.py (for MixinSecurity)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelSecuritySubcontract(BaseModel):
    """Security subcontract model for security features."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_redaction: bool = Field(default=True)
    sensitive_field_patterns: list[str] = Field(default_factory=lambda: ["password", "secret", "token", "key"])
    enable_input_sanitization: bool = Field(default=True)
    enable_output_sanitization: bool = Field(default=True)
    enable_sql_injection_protection: bool = Field(default=True)
    enable_xss_protection: bool = Field(default=True)
    enable_csrf_protection: bool = Field(default=True)
    max_input_length: int = Field(default=1048576, ge=1024)  # 1MB default

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 8. model_validation_subcontract.py (for MixinValidation)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelValidationSubcontract(BaseModel):
    """Validation subcontract model for input validation."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_fail_fast: bool = Field(default=True)
    strict_type_checking: bool = Field(default=True)
    enable_schema_validation: bool = Field(default=True)
    enable_constraint_validation: bool = Field(default=True)
    max_validation_errors: int = Field(default=10, ge=1, le=100)
    enable_validation_caching: bool = Field(default=True)
    validation_cache_ttl_seconds: int = Field(default=300, ge=10, le=3600)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 9. model_serialization_subcontract.py (for MixinSerialization)

**Status**: ❌ MISSING
**Required Fields**:
```python
class ModelSerializationSubcontract(BaseModel):
    """Serialization subcontract model for canonical serialization."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    serialization_format: str = Field(default="yaml")  # enum: yaml, json
    enable_canonical_mode: bool = Field(default=True)
    enable_deterministic_output: bool = Field(default=True)
    sort_keys: bool = Field(default=True)
    indent_size: int = Field(default=2, ge=1, le=8)
    line_width: int = Field(default=120, ge=80, le=200)
    enable_unicode: bool = Field(default=True)
    enable_compression: bool = Field(default=False)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

## PRIORITY 2: Extract NodeEffect Patterns

These patterns are currently in `node_effect.py` (~1400 lines) and should become mixins:

### 1. MixinContractLoader + model_contract_loader_subcontract.py

**Pattern**: Contract loading from YAML, contract validation, contract caching
**Current Location**: `node_effect.py` lines ~100-300 (estimated)
**New Files**:
- `src/omnibase_core/mixins/mixin_contract_loader.py`
- `src/omnibase_core/models/contracts/subcontracts/model_contract_loader_subcontract.py`

**Subcontract Fields**:
```python
class ModelContractLoaderSubcontract(BaseModel):
    """Contract loader subcontract model for YAML contract loading."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_contract_validation: bool = Field(default=True)
    enable_contract_caching: bool = Field(default=True)
    contract_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    strict_schema_validation: bool = Field(default=True)
    enable_subcontract_composition: bool = Field(default=True)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 2. MixinTransactions + model_transaction_subcontract.py

**Pattern**: Transaction management, rollback support, transaction state tracking
**Current Location**: `node_effect.py` lines ~500-700 (estimated)
**New Files**:
- `src/omnibase_core/mixins/mixin_transactions.py`
- `src/omnibase_core/models/contracts/subcontracts/model_transaction_subcontract.py`

**Subcontract Fields**:
```python
class ModelTransactionSubcontract(BaseModel):
    """Transaction subcontract model for transaction management."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    transaction_enabled: bool = Field(default=True)
    rollback_support: bool = Field(default=True)
    enable_savepoints: bool = Field(default=True)
    transaction_timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    auto_commit: bool = Field(default=False)
    isolation_level: str = Field(default="READ_COMMITTED")  # enum: READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE
    enable_transaction_logging: bool = Field(default=True)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

### 3. MixinEffectHandlers + model_effect_handler_subcontract.py

**Pattern**: Effect handler registry, effect type dispatch, handler lifecycle
**Current Location**: `node_effect.py` lines ~900-1100 (estimated)
**New Files**:
- `src/omnibase_core/mixins/mixin_effect_handlers.py`
- `src/omnibase_core/models/contracts/subcontracts/model_effect_handler_subcontract.py`

**Subcontract Fields**:
```python
class ModelEffectHandlerSubcontract(BaseModel):
    """Effect handler subcontract model for effect handler registry."""

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_handler_registry: bool = Field(default=True)
    enable_handler_validation: bool = Field(default=True)
    enable_handler_caching: bool = Field(default=True)
    handler_cache_ttl_seconds: int = Field(default=300, ge=10, le=3600)
    enable_handler_lifecycle: bool = Field(default=True)
    max_concurrent_handlers: int = Field(default=100, ge=1, le=1000)
    handler_timeout_ms: int = Field(default=30000, ge=1000, le=300000)

    model_config = ConfigDict(extra="ignore", use_enum_values=False, validate_assignment=True)
```

---

## PRIORITY 3: Categorize Infrastructure Mixins

**Decision Needed**: Should these 32 mixin implementations have metadata + subcontracts?

### Infrastructure Mixins (likely exempt from subcontracts):
- mixin_node_executor.py - Runtime execution framework
- mixin_node_lifecycle.py - Lifecycle management
- mixin_node_setup.py - Node initialization
- mixin_node_id_from_contract.py - ID generation from contract
- mixin_introspect_from_contract.py - Introspection loading
- mixin_introspection_publisher.py - Publishing introspection
- mixin_introspection.py - General introspection
- mixin_node_introspection_data.py - Introspection data management
- mixin_contract_metadata.py - Contract metadata access
- mixin_service_registry.py - Service registration
- mixin_utils.py - Utility functions

### Feature Mixins (SHOULD have metadata + subcontracts):
- mixin_event_handler.py
- mixin_event_listener.py
- mixin_event_driven_node.py
- mixin_workflow_support.py
- mixin_tool_execution.py
- mixin_fail_fast.py (already related to MixinValidation)
- mixin_redaction.py (already related to MixinSecurity)
- mixin_canonical_serialization.py (already related to MixinSerialization)
- mixin_yaml_serialization.py (already related to MixinSerialization)
- mixin_lazy_evaluation.py
- mixin_lazy_value.py
- mixin_hash_computation.py
- mixin_completion_data.py
- mixin_log_data.py (already related to MixinLogging)

---

## Implementation Template

**For each missing subcontract, follow this pattern** (based on `ModelCachingSubcontract`):

```python
"""
{Mixin Name} Subcontract Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import ClassVar
from pydantic import BaseModel, ConfigDict, Field, field_validator
from omnibase_core.primitives.model_semver import ModelSemVer
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class Model{Name}Subcontract(BaseModel):
    """
    {Mixin name} subcontract model for {functionality}.

    Comprehensive {description} providing {features}.
    Designed for composition into node contracts requiring {functionality}.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Fields from mixin_metadata.yaml config_schema
    # ... (copy from metadata)

    @field_validator("{field_name}")
    @classmethod
    def validate_{field_name}(cls, v: {type}) -> {type}:
        """Validate {field_name} business rules."""
        # Add validation logic
        return v

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
```

---

## Next Steps

1. **Create 9 missing subcontract models** (Priority 1)
2. **Extract 3 NodeEffect patterns into mixins** (Priority 2)
3. **Categorize and document infrastructure vs feature mixins** (Priority 3)
4. **Update mixin_metadata.yaml** to include new mixins from Priority 2
5. **Delete NodeEffect, NodeCompute, NodeReducer, NodeOrchestrator archetypes** (~5900 lines)

**Estimated Work**:
- Priority 1: ~8-12 hours (9 subcontract models @ ~1 hour each)
- Priority 2: ~12-16 hours (3 new mixins + subcontracts + extraction from NodeEffect)
- Priority 3: ~4-6 hours (categorization and documentation)
- **Total: ~24-34 hours of development work**
