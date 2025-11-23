# Version Field Requirement - Test Failure Report

**Generated**: 2025-11-22
**Branch**: chore/validation
**Change**: Removed `default_factory` from `version` fields in `ModelBaseSubcontract` and subcontract models
**Impact**: Version field is now REQUIRED for all subcontract instantiations

---

## Executive Summary

### Total Test Failures: **~796 tests across 4 test categories**

| Category | Failed | Passed | Total | Pass Rate |
|----------|--------|--------|-------|-----------|
| **Subcontracts** | 754 | 173 | 927 | 18.7% |
| **Declarative Nodes** | 13 | 7 | 20 | 35.0% |
| **FSM Mixin** | 8 | 1 | 9 | 11.1% |
| **FSM Executor Utils** | 21 | 1 | 22 | 4.5% |
| **TOTAL** | **~796** | **~182** | **~978** | **18.6%** |

---

## Error Pattern

All failures follow the same pattern:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for ModelXxxSubcontract
version
  Field required [type=missing, input_value={...}, input_type=dict]
```

**Root Cause**: Tests create subcontract instances without providing the required `version` field.

---

## Failures by Test File (Top 20)

### Subcontracts Directory: 754 failures across 27 files

| Rank | Test File | Failures | Model |
|------|-----------|----------|-------|
| 1 | `test_model_action_config_parameter.py` | 71 | ModelActionConfigParameter |
| 2 | `test_model_event_mapping_rule.py` | 70 | ModelEventMappingRule |
| 3 | `test_model_logging_subcontract.py` | 53 | ModelLoggingSubcontract |
| 4 | `test_model_environment_validation_rule.py` | 49 | ModelEnvironmentValidationRule |
| 5 | `test_model_observability_subcontract.py` | 44 | ModelObservabilitySubcontract |
| 6 | `test_model_security_subcontract.py` | 43 | ModelSecuritySubcontract |
| 7 | `test_model_event_handling_subcontract.py` | 43 | ModelEventHandlingSubcontract |
| 8 | `test_model_event_bus_subcontract.py` | 42 | ModelEventBusSubcontract |
| 9 | `test_model_component_health_detail.py` | 41 | ModelComponentHealthDetail |
| 10 | `test_model_metrics_subcontract.py` | 38 | ModelMetricsSubcontract |
| 11 | `test_model_log_level_override.py` | 38 | ModelLogLevelOverride |
| 12 | `test_model_response_header_rule.py` | 37 | ModelResponseHeaderRule |
| 13 | `test_model_environment_validation_rules.py` | 37 | ModelEnvironmentValidationRules |
| 14 | `test_model_query_parameter_rule.py` | 34 | ModelQueryParameterRule |
| 15 | `test_model_circuit_breaker_subcontract.py` | 33 | ModelCircuitBreakerSubcontract |
| 16 | `test_model_health_check_subcontract.py` | 30 | ModelHealthCheckSubcontract |
| 17 | `test_model_header_transformation.py` | 30 | ModelHeaderTransformation |
| 18 | `test_model_validation_schema_rule.py` | 28 | ModelValidationSchemaRule |
| 19 | `test_model_retry_subcontract.py` | 28 | ModelRetrySubcontract |
| 20 | `test_model_serialization_subcontract.py` | 23 | ModelSerializationSubcontract |

### Other Test Files: 42+ failures

| Test File | Failures | Model |
|-----------|----------|-------|
| `test_declarative_nodes.py` | 13 errors | ModelWorkflowDefinitionMetadata |
| `test_mixin_fsm_execution.py` | 8 errors | ModelFSMStateDefinition |
| `test_fsm_executor.py` | 21 errors | ModelFSMStateDefinition |

---

## Affected Model Categories

### 1. Primary Subcontracts (High Impact)
These are the 6 main subcontract types in `ModelContract`:

- **ModelFSMSubcontract** (via ModelFSMStateDefinition)
- **ModelEventTypeSubcontract** - 16 failures
- **ModelAggregationSubcontract** - 23 failures
- **ModelStateMachineSubcontract** - Not directly tested
- **ModelRoutingSubcontract** - 10 failures
- **ModelCachingSubcontract** - Not directly tested

### 2. Extended Subcontracts (Medium Impact)
Additional subcontract models:

- **ModelLoggingSubcontract** - 53 failures (highest in category)
- **ModelMetricsSubcontract** - 38 failures
- **ModelSecuritySubcontract** - 43 failures
- **ModelObservabilitySubcontract** - 44 failures
- **ModelEventHandlingSubcontract** - 43 failures
- **ModelEventBusSubcontract** - 42 failures
- **ModelCircuitBreakerSubcontract** - 33 failures
- **ModelRetrySubcontract** - 28 failures
- **ModelHealthCheckSubcontract** - 30 failures
- **ModelValidationSubcontract** - 18 failures
- **ModelSerializationSubcontract** - 23 failures

### 3. Support Models (Low Impact)
Models used by subcontracts:

- **ModelEventMappingRule** - 70 failures (2nd highest overall!)
- **ModelActionConfigParameter** - 71 failures (HIGHEST OVERALL!)
- **ModelEnvironmentValidationRule** - 49 failures
- **ModelComponentHealthDetail** - 41 failures
- **ModelLogLevelOverride** - 38 failures
- **ModelResponseHeaderRule** - 37 failures
- **ModelQueryParameterRule** - 34 failures
- **ModelHeaderTransformation** - 30 failures
- **ModelValidationSchemaRule** - 28 failures
- **ModelAggregationParameter** - 23 failures
- **ModelResourceUsageMetric** - 16 failures
- **ModelFSMTransitionAction** - 10 failures

### 4. Workflow/FSM Models (Critical Impact)
Used in declarative nodes and FSM execution:

- **ModelWorkflowDefinitionMetadata** - 13 errors in declarative nodes
- **ModelFSMStateDefinition** - 29 errors across FSM tests

---

## Test Failure Examples

### Example 1: Basic Instantiation Without Version

**File**: `test_model_routing_subcontract.py`
**Test**: `test_valid_routing_subcontract_default`

```python
# BEFORE (worked)
subcontract = ModelRoutingSubcontract()

# NOW (fails with "Field required: version")
```

**Fix Required**:
```python
subcontract = ModelRoutingSubcontract(
    version="1.0.0"  # or ModelContractVersion(major=1, minor=0, patch=0)
)
```

### Example 2: Parameterized Instantiation

**File**: `test_model_event_mapping_rule.py`
**Test**: `test_default_value_float`

```python
# BEFORE (worked)
rule = ModelEventMappingRule(
    source_path="amount",
    target_path="total",
    default_value=0.0
)

# NOW (fails with "Field required: version")
```

**Fix Required**:
```python
rule = ModelEventMappingRule(
    source_path="amount",
    target_path="total",
    default_value=0.0,
    version="1.0.0"  # Add version
)
```

### Example 3: FSM State Definition

**File**: `test_mixin_fsm_execution.py`
**Test**: `test_mixin_validate_contract`

```python
# BEFORE (worked)
state = ModelFSMStateDefinition(
    state_name="idle",
    state_type="initial",
    description="Initial idle state"
)

# NOW (fails with "Field required: version")
```

**Fix Required**:
```python
state = ModelFSMStateDefinition(
    state_name="idle",
    state_type="initial",
    description="Initial idle state",
    version="1.0.0"  # Add version
)
```

---

## Categorization of Fix Strategies

### Strategy 1: Direct Instantiation Fixes (Easy)
**Scope**: ~650 tests
**Effort**: 5 minutes per file (mass find-replace)
**Risk**: Low

**Pattern**:
```python
# Add version="1.0.0" to all instantiations
ModelXxxSubcontract(..., version="1.0.0")
```

**Affected Test Files** (27 files in subcontracts/):
- All files in `tests/unit/models/contracts/subcontracts/`

### Strategy 2: Fixture Updates (Medium)
**Scope**: ~100 tests
**Effort**: 15 minutes per fixture
**Risk**: Medium (affects multiple tests)

**Pattern**:
```python
@pytest.fixture
def sample_subcontract():
    return ModelXxxSubcontract(
        version="1.0.0",  # Add this
        # ... other params
    )
```

**Affected Areas**:
- FSM test fixtures
- Declarative node test fixtures
- Integration test fixtures

### Strategy 3: Factory Function Updates (Hard)
**Scope**: ~40 tests
**Effort**: 30 minutes per factory
**Risk**: High (complex test helpers)

**Pattern**:
```python
def create_event_mapping(source, target, **kwargs):
    kwargs.setdefault("version", "1.0.0")  # Add default version
    return ModelEventMappingRule(
        source_path=source,
        target_path=target,
        **kwargs
    )
```

**Affected Areas**:
- FSM executor utilities
- Event handling test helpers
- Workflow coordination helpers

### Strategy 4: YAML Fixture Updates (Low Priority)
**Scope**: 2 files
**Effort**: 5 minutes
**Risk**: Very Low

**Files**:
- `tests/fixtures/validation/valid/sample_contract.yaml` (already has version)
- `tests/fixtures/validation/invalid/malformed_contract.yaml` (check if version should be missing)

---

## Recommended Fix Order (Priority)

### Phase 1: High-Impact Models (1-2 hours)
Fix the top 10 most-affected test files:

1. **ModelActionConfigParameter** (71 failures) - 15 min
2. **ModelEventMappingRule** (70 failures) - 15 min
3. **ModelLoggingSubcontract** (53 failures) - 15 min
4. **ModelEnvironmentValidationRule** (49 failures) - 10 min
5. **ModelObservabilitySubcontract** (44 failures) - 10 min
6. **ModelSecuritySubcontract** (43 failures) - 10 min
7. **ModelEventHandlingSubcontract** (43 failures) - 10 min
8. **ModelEventBusSubcontract** (42 failures) - 10 min
9. **ModelComponentHealthDetail** (41 failures) - 10 min
10. **ModelMetricsSubcontract** (38 failures) - 10 min

**Total Impact**: 544 failures fixed (68% of total)

### Phase 2: Medium-Impact Models (1 hour)
Fix the next 10 files:

11. **ModelLogLevelOverride** (38 failures) - 8 min
12. **ModelResponseHeaderRule** (37 failures) - 8 min
13. **ModelEnvironmentValidationRules** (37 failures) - 8 min
14. **ModelQueryParameterRule** (34 failures) - 8 min
15. **ModelCircuitBreakerSubcontract** (33 failures) - 8 min
16. **ModelHealthCheckSubcontract** (30 failures) - 8 min
17. **ModelHeaderTransformation** (30 failures) - 8 min
18. **ModelValidationSchemaRule** (28 failures) - 8 min
19. **ModelRetrySubcontract** (28 failures) - 8 min
20. **ModelSerializationSubcontract** (23 failures) - 8 min

**Total Impact**: 318 failures fixed (40% of total)

### Phase 3: Low-Impact Models (30 min)
Fix remaining subcontract files:

21-27. Remaining 7 files with <23 failures each

**Total Impact**: 92 failures fixed (12% of total)

### Phase 4: FSM and Workflow Models (1 hour)
Fix integration and workflow tests:

- **test_declarative_nodes.py** (13 errors) - 20 min
- **test_mixin_fsm_execution.py** (8 errors) - 20 min
- **test_fsm_executor.py** (21 errors) - 20 min

**Total Impact**: 42 failures fixed (5% of total)

---

## Automation Potential

### Mass Find-Replace Candidates (Can use sed/awk)

**Pattern 1**: Default instantiation
```bash
# Find all instances of ModelXxxSubcontract()
# Replace with ModelXxxSubcontract(version="1.0.0")

find tests/ -name "*.py" -exec sed -i '' \
  's/ModelRoutingSubcontract()/ModelRoutingSubcontract(version="1.0.0")/g' {} \;
```

**Pattern 2**: Single-parameter instantiation
```bash
# ModelXxxSubcontract(param=value)
# → ModelXxxSubcontract(param=value, version="1.0.0")

# This requires more sophisticated regex
```

### Manual Fixes Required

1. **Multi-line instantiations** - Need to identify where to add version
2. **Factory functions** - Need to understand test helper logic
3. **Fixtures with kwargs** - Need to understand parameter passing
4. **YAML loading tests** - May need version in YAML or parsing logic

---

## Estimated Total Effort

| Phase | Tasks | Effort | Failures Fixed |
|-------|-------|--------|----------------|
| **Phase 1** | Top 10 models | 2 hours | 544 (68%) |
| **Phase 2** | Next 10 models | 1 hour | 318 (40%) |
| **Phase 3** | Remaining subcontracts | 30 min | 92 (12%) |
| **Phase 4** | FSM/Workflow | 1 hour | 42 (5%) |
| **TOTAL** | 27+ files | **4.5 hours** | **~996 tests** |

**With Automation**: Could reduce to **2-3 hours** using find-replace for simple cases.

---

## Risk Assessment

### Low Risk Changes (80% of fixes)
- Direct instantiation with version parameter
- Simple factory function defaults
- Fixture updates

### Medium Risk Changes (15% of fixes)
- Complex factory functions with logic
- Parameterized tests with multiple scenarios
- Integration tests with external dependencies

### High Risk Changes (5% of fixes)
- FSM executor logic (complex state machines)
- Workflow coordination tests (multi-step)
- YAML parsing with schema validation

---

## Verification Strategy

### Step 1: Run Subcontracts Tests After Each File
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_action_config_parameter.py -xvs
```

### Step 2: Run Full Subcontracts Suite After Phase Completion
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=short
```

### Step 3: Run Full Test Suite After All Phases
```bash
poetry run pytest tests/ --tb=short
```

### Step 4: Verify CI Splits (20 splits)
```bash
# Run subset to verify distribution
for i in {1..5}; do
  poetry run pytest tests/ --splits 20 --group $i --tb=short
done
```

---

## Alternative Solution: Restore default_factory

**If changes are too extensive**, consider restoring `default_factory`:

```python
class ModelBaseSubcontract(BaseModel):
    version: str = Field(
        default_factory=lambda: "1.0.0",  # Restore this
        description="Subcontract schema version"
    )
```

**Pros**:
- Zero test changes required
- Backward compatible
- Immediate CI pass

**Cons**:
- Loses explicit version tracking
- Tests don't verify version handling
- May hide version mismatches in production

**Recommendation**: Proceed with test fixes to maintain explicit version requirements.

---

## Next Steps

1. **Decision**: Confirm proceeding with test fixes vs. restoring default_factory
2. **Start Phase 1**: Fix top 10 high-impact models (2 hours, 68% of failures)
3. **Verify**: Run tests after each file
4. **Iterate**: Continue with Phase 2-4
5. **Final Verification**: Run full CI suite

---

## Appendix: Command Reference

### Run Single Test File
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_routing_subcontract.py -xvs
```

### Run All Subcontract Tests
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=short
```

### Count Failures Per File
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -v 2>&1 | \
  grep -E "FAILED|PASSED" | awk '{print $1}' | sed 's/::.*//' | \
  sort | uniq -c | sort -rn
```

### Get Failure Summary
```bash
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -q 2>&1 | \
  grep -E "failed|passed" | tail -1
```

---

**Report Generated By**: Polymorphic Agent
**Correlation ID**: N/A
**Branch**: chore/validation
**Last Updated**: 2025-11-22
