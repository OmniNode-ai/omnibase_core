# Mixin Contract Restoration & Creation Plan

**Generated**: 2025-10-15
**Branch**: feature/mixin-subcontracts
**Based on**: MIXIN_CONTRACT_GAPS.md audit

---

## Summary

**Found in Archived**:
- ✅ `model_health_check_subcontract.py` - EXISTS (needs modernization)
- ⚠️ Related models available but no exact matches for others

**Need to Create from Scratch**:
- 8 missing subcontract models

---

## Phase 1: Restore & Modernize Archived Subcontract

### model_health_check_subcontract.py ✅

**Location**: `archived/src/omnibase_core/models/subcontracts/model_health_check_subcontract.py`
**Status**: Found, needs modernization
**Action**: Restore and update to current ONEX standards

**Required Modernization**:
1. **Update imports**:
   ```python
   # OLD (archived)
   from omnibase_spi.model.health.model_health_status import ModelHealthStatus
   from omnibase_spi.protocols.types.core_types import HealthStatus, NodeType

   # NEW (current)
   from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
   from omnibase_core.models.core.model_health_status import ModelHealthStatus
   ```

2. **Add INTERFACE_VERSION**:
   ```python
   from typing import ClassVar
   from omnibase_core.primitives.model_semver import ModelSemVer

   class ModelHealthCheckSubcontract(BaseModel):
       INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)
   ```

3. **Replace string version with ModelSemVer**:
   ```python
   # OLD
   subcontract_version: str = Field(default="1.0.0", ...)

   # NEW
   subcontract_version: ModelSemVer = Field(
       default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
       description="Version of the subcontract"
   )
   ```

4. **Update model_config**:
   ```python
   # OLD
   class Config:
       json_schema_extra = {...}

   # NEW
   model_config = ConfigDict(
       extra="ignore",
       use_enum_values=False,
       validate_assignment=True,
   )
   ```

5. **Add docstring header**:
   ```python
   """
   Health Check Subcontract Model - ONEX Standards Compliant.

   VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

   STABILITY GUARANTEE:
   - All fields, methods, and validators are stable interfaces
   - New optional fields may be added in minor versions only
   - Existing fields cannot be removed or have types/constraints changed

   ZERO TOLERANCE: No Any types allowed in implementation.
   """
   ```

**Testing**:
- Restore file to `src/omnibase_core/models/contracts/subcontracts/`
- Apply all modernizations
- Run mypy and pytest to verify
- Update tests if needed

---

## Phase 2: Create Missing Subcontracts (Priority Order)

### 1. model_retry_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/models/configuration/model_retry_policy.py`
- `archived/src/omnibase_core/models/configuration/model_request_retry_config.py`
- `archived/src/omnibase_core/models/core/model_retry_config.py`
- `archived/src/omnibase_core/models/retry/model_retry_policy.py`

**Strategy**: Use mixin_metadata.yaml spec + adapt patterns from archived retry models

**Key Fields** (from mixin_metadata.yaml):
```python
class ModelRetrySubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    max_retries: int = Field(default=3, ge=0, le=100)
    base_delay_seconds: float = Field(default=1.0, ge=0.1, le=3600.0)
    backoff_strategy: str = Field(default="exponential")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    # ... (see MIXIN_CONTRACT_GAPS.md for complete spec)
```

**Estimated Time**: 1-2 hours

---

### 2. model_circuit_breaker_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/models/configuration/model_circuit_breaker.py`
- `archived/src/omnibase_core/models/configuration/model_circuit_breaker_metadata.py`
- `archived/src/omnibase_core/models/agent/model_circuit_breaker_map.py`
- `archived/src/omnibase_core/models/resilience/model_circuit_breaker_state.py`

**Current File**: `src/omnibase_core/models/contracts/subcontracts/model_circuit_breaker.py`
**Status**: EXISTS but is a COMPONENT model, not a proper subcontract

**Action**:
1. Rename existing to `model_circuit_breaker_component.py`
2. Create proper `model_circuit_breaker_subcontract.py` with:
   - INTERFACE_VERSION ClassVar
   - Complete config from mixin_metadata.yaml
   - Proper docstring header

**Key Fields**:
```python
class ModelCircuitBreakerSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    failure_threshold: int = Field(default=5, ge=1, le=100)
    success_threshold: int = Field(default=2, ge=1, le=20)
    timeout_seconds: int = Field(default=60, ge=1, le=300)
    # ... (see metadata)
```

**Estimated Time**: 1 hour

---

### 3. model_event_bus_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/core/services/event_bus_service/v1_0_0/models/model_event_bus_config.py`
- `archived/src/omnibase_core/models/configuration/model_event_bus_config.py`
- `archived/src/omnibase_core/models/service/model_event_bus_config.py`

**Strategy**: Use mixin_metadata.yaml spec + adapt config patterns from archived

**Key Fields**:
```python
class ModelEventBusSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    event_bus_enabled: bool = Field(default=True)
    event_bus_type: str = Field(default="hybrid")
    enable_event_logging: bool = Field(default=True)
    correlation_tracking: bool = Field(default=True)
    # ... (see metadata)
```

**Estimated Time**: 1-2 hours

---

### 4. model_logging_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/models/core/model_logging_config.py`
- `archived/src/omnibase_core/models/policy/model_logging_policy.py`
- `archived/src/omnibase_core/models/policy/model_debug_logging_policy.py`

**Strategy**: Use mixin_metadata.yaml spec + adapt from archived logging configs

**Key Fields**:
```python
class ModelLoggingSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    log_level: str = Field(default="INFO")
    enable_context_logging: bool = Field(default=True)
    enable_correlation_tracking: bool = Field(default=True)
    # ... (see metadata)
```

**Estimated Time**: 1 hour

---

### 5. model_metrics_subcontract.py

**References Available in Archived**:
- Many metrics models in archived (performance_metrics, monitoring_metrics, etc.)
- No direct metrics_subcontract found

**Strategy**: Create from mixin_metadata.yaml spec

**Key Fields**:
```python
class ModelMetricsSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    metrics_backend: str = Field(default="prometheus")
    enable_histograms: bool = Field(default=True)
    enable_counters: bool = Field(default=True)
    # ... (see metadata)
```

**Estimated Time**: 1 hour

---

### 6. model_security_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/models/security/` (many security models)
- `archived/src/omnibase_core/models/service/model_security_config.py`
- No direct security_subcontract found

**Strategy**: Create from mixin_metadata.yaml spec + adapt security patterns

**Key Fields**:
```python
class ModelSecuritySubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_redaction: bool = Field(default=True)
    sensitive_field_patterns: list[str] = Field(default_factory=lambda: ["password", "secret", "token", "key"])
    # ... (see metadata)
```

**Estimated Time**: 1-2 hours

---

### 7. model_validation_subcontract.py

**References Available in Archived**:
- `archived/src/omnibase_core/models/validation/` (many validation models)
- `archived/src/omnibase_core/models/core/model_validation_config.py`

**Strategy**: Create from mixin_metadata.yaml spec + adapt validation patterns

**Key Fields**:
```python
class ModelValidationSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    enable_fail_fast: bool = Field(default=True)
    strict_type_checking: bool = Field(default=True)
    # ... (see metadata)
```

**Estimated Time**: 1 hour

---

### 8. model_serialization_subcontract.py

**References Available in Archived**:
- No direct serialization_subcontract found
- Pattern available in mixin_canonical_serialization.py

**Strategy**: Create from mixin_metadata.yaml spec

**Key Fields**:
```python
class ModelSerializationSubcontract(BaseModel):
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    serialization_format: str = Field(default="yaml")
    enable_canonical_mode: bool = Field(default=True)
    # ... (see metadata)
```

**Estimated Time**: 1 hour

---

## Implementation Workflow

### Step 1: Setup Branch
```bash
git checkout -b feature/mixin-subcontracts
```

### Step 2: Phase 1 - Restore Health Check
1. Copy archived health_check_subcontract to current location
2. Apply all modernizations listed above
3. Run tests: `poetry run pytest tests/unit/models/contracts/subcontracts/ -v`
4. Run mypy: `poetry run mypy src/omnibase_core/models/contracts/subcontracts/model_health_check_subcontract.py`
5. Commit: `feat(subcontracts): restore and modernize model_health_check_subcontract`

### Step 3: Phase 2 - Create Missing Subcontracts
For each subcontract (in priority order):
1. Create file in `src/omnibase_core/models/contracts/subcontracts/`
2. Implement model following template in MIXIN_CONTRACT_GAPS.md
3. Add comprehensive docstring with VERSION and STABILITY GUARANTEE
4. Add INTERFACE_VERSION ClassVar
5. Implement all fields from mixin_metadata.yaml
6. Add field validators for business rules
7. Use ConfigDict (not dict) for model_config
8. Create unit test file in `tests/unit/models/contracts/subcontracts/`
9. Run tests and mypy
10. Commit: `feat(subcontracts): add model_{name}_subcontract`

### Step 4: Update __init__.py
Update `src/omnibase_core/models/contracts/subcontracts/__init__.py` to export all new models:
```python
from .model_health_check_subcontract import ModelHealthCheckSubcontract
from .model_retry_subcontract import ModelRetrySubcontract
from .model_circuit_breaker_subcontract import ModelCircuitBreakerSubcontract
from .model_event_bus_subcontract import ModelEventBusSubcontract
from .model_logging_subcontract import ModelLoggingSubcontract
from .model_metrics_subcontract import ModelMetricsSubcontract
from .model_security_subcontract import ModelSecuritySubcontract
from .model_validation_subcontract import ModelValidationSubcontract
from .model_serialization_subcontract import ModelSerializationSubcontract

__all__ = [
    "ModelHealthCheckSubcontract",
    "ModelRetrySubcontract",
    "ModelCircuitBreakerSubcontract",
    "ModelEventBusSubcontract",
    "ModelLoggingSubcontract",
    "ModelMetricsSubcontract",
    "ModelSecuritySubcontract",
    "ModelValidationSubcontract",
    "ModelSerializationSubcontract",
]
```

### Step 5: Create PR
```bash
git add src/omnibase_core/models/contracts/subcontracts/
git add tests/unit/models/contracts/subcontracts/
git commit -m "feat(subcontracts): add 9 missing mixin subcontract models

- Restore and modernize model_health_check_subcontract from archived
- Create 8 new subcontract models following ONEX standards
- All models include INTERFACE_VERSION ClassVar
- All models use ModelSemVer for version fields
- Comprehensive docstrings with stability guarantees
- Field validators for business rules
- Complete test coverage

Implements requirements from MIXIN_CONTRACT_AUDIT.md and MIXIN_CONTRACT_GAPS.md"

git push origin feature/mixin-subcontracts
gh pr create --title "feat: Add 9 missing mixin subcontract models" --body "$(cat PR_BODY.md)"
```

---

## Estimated Timeline

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| 1 | Restore health_check_subcontract | 2 hours | 2 hours |
| 2.1 | Create retry_subcontract | 2 hours | 4 hours |
| 2.2 | Create circuit_breaker_subcontract | 1 hour | 5 hours |
| 2.3 | Create event_bus_subcontract | 2 hours | 7 hours |
| 2.4 | Create logging_subcontract | 1 hour | 8 hours |
| 2.5 | Create metrics_subcontract | 1 hour | 9 hours |
| 2.6 | Create security_subcontract | 2 hours | 11 hours |
| 2.7 | Create validation_subcontract | 1 hour | 12 hours |
| 2.8 | Create serialization_subcontract | 1 hour | 13 hours |
| 3 | Testing and refinement | 2 hours | 15 hours |
| 4 | Documentation and PR | 1 hour | 16 hours |

**Total Estimated Time**: 16 hours (2 work days)

---

## Success Criteria

✅ All 9 subcontract models created and passing tests
✅ Zero mypy errors
✅ All tests passing (unit + integration)
✅ Proper INTERFACE_VERSION on all models
✅ No string versions (only ModelSemVer)
✅ Comprehensive docstrings with stability guarantees
✅ ConfigDict used (not dict)
✅ Field validators for business rules
✅ All models exported in __init__.py
✅ PR approved and merged

---

## Next Steps After This PR

1. **Update mixin implementations** to use new subcontract models
2. **Create YAML subcontract examples** for testing/reference
3. **Extract NodeEffect patterns** into new mixins (Priority 2 from MIXIN_CONTRACT_GAPS.md)
4. **Delete archetype files** (NodeEffect, NodeCompute, etc.) once mixins are complete
