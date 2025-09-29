# Union Compliance Recovery Plan

## Current Status Assessment

### Critical Issues Identified
- **Invalid Unions**: 24 found (target: ≤8) - **16 unions over limit**
- **Backwards Compatibility**: 5 violations detected
- **MyPy Type Errors**: Multiple type checking failures
- **Code Formatting**: Black/isort modifications pending

### Root Cause Analysis
The previous agent rounds that should have reduced unions to ~5 appear to have been lost during the merge resolution process. We need to systematically re-apply the fixes.

## Systematic Recovery Strategy

### Phase 1: Critical Union Violations (Priority 1)
**Target**: Reduce 24 → ≤8 invalid unions (need to eliminate 16+ violations)

#### 1.1 Contract Models (High Impact)
```bash
src/omnibase_core/models/contracts/model_contract_effect.py
```
**Issues**:
- `Union[ModelValidationRules, ModelValidationRulesInputValue, None, dict, str]` - **5 types primitive soup**
- `Union[ModelValidationRules, ModelValidationRulesInputValue, None, dict]` - **4 types**
- `Union[ModelValidationRulesInputValue, None, dict]` - **3 types**

**Fix Strategy**:
- Replace with discriminated union using Literal discriminators
- Create `ValidationRuleUnion = Annotated[Union[...], Discriminator(...)]`
- Use ModelSchemaValue for dict/str fallbacks

#### 1.2 Metadata Models
```bash
src/omnibase_core/models/metadata/model_input_state.py
```
**Issues**:
- `Union[ModelSemVer, None, dict]` patterns

**Fix Strategy**:
- Create SemVerInput discriminated union
- Remove dict fallback, use proper ModelSemVer constructor

#### 1.3 Operations Models
```bash
src/omnibase_core/models/operations/model_computation_input_data.py
```
**Status**: Fixed by Agent 2 but may need re-application

#### 1.4 Additional Union Hotspots
- Check all models/ subdirectories for remaining primitive soup patterns
- Focus on `Union[..., dict, str, object]` patterns

### Phase 2: Backwards Compatibility Cleanup (Priority 2)

#### 2.1 Remove Legacy Patterns
```bash
src/omnibase_core/models/nodes/model_node_configuration_value.py
```
**Remove**:
- `# Backwards compatibility for existing code` comments
- Legacy factory class wrapper methods

```bash
src/omnibase_core/models/utils/model_subcontract_constraint_validator.py
src/omnibase_core/models/utils/model_validation_rules_converter.py
```
**Remove**:
- `# Legacy type alias for backward compatibility` comments
- `# Handle legacy formats for backward compatibility` logic

### Phase 3: MyPy Type Errors (Priority 3)

#### 3.1 ModelSemVer Issues
**Status**: Fixed by Agent 4 - verify application

#### 3.2 ModelContractData Type Issues
**Status**: Fixed by Agent 5 - verify application

#### 3.3 Workflow Condition Errors
```bash
src/omnibase_core/models/contracts/model_workflow_condition.py
```
**Issues**:
- `"object" has no attribute "value"` errors
- Impossible subclass combinations (str & int & float & bool)

**Fix Strategy**:
- Replace object usage with proper discriminated unions
- Fix impossible TypeVar bounds

#### 3.4 Exception Type in Pydantic
**Issue**: `Unable to generate pydantic-core schema for <class 'Exception'>`
**Fix**: Add `arbitrary_types_allowed=True` to model_config or replace with proper model

### Phase 4: Code Quality & Formatting (Priority 4)

#### 4.1 Import Organization
**Status**: isort made changes - need to re-add

#### 4.2 Code Formatting
**Status**: Black made changes - need to re-add

#### 4.3 End-of-File Fixes
**Status**: Hook made changes - need to re-add

## Execution Plan

### Step 1: Deploy Targeted Agent Teams (Parallel)
```bash
# 8 parallel agents with specific focus areas:

Agent 1: Contract effect union violations (model_contract_effect.py)
Agent 2: Metadata union violations (model_input_state.py, model_metadata_node_collection.py)
Agent 3: Operations union verification (ensure previous fixes applied)
Agent 4: Backwards compatibility removal (all 5 violation files)
Agent 5: MyPy workflow condition fixes (model_workflow_condition.py)
Agent 6: Exception type fixes (find and fix Pydantic schema errors)
Agent 7: Remaining union hotspot scan (any missed primitive soup)
Agent 8: Type annotation consistency (ensure all fixes are compatible)
```

### Step 2: Validation Checkpoint
```bash
# After agent completion:
poetry run python scripts/validation/validate-union-usage.py --allow-invalid 8
```
**Success Criteria**: ≤8 invalid unions

### Step 3: Re-add Hook Changes
```bash
git add -A  # Include all formatting fixes from hooks
```

### Step 4: Final Validation
```bash
# Full pre-commit validation:
pre-commit run --all-files
```

### Step 5: Commit & Push
```bash
git commit -m "fix: comprehensive union compliance recovery

- Reduced invalid unions from 24 → ≤8 (67% reduction)
- Eliminated all primitive soup patterns (Union[..., dict, str])
- Removed 5 backwards compatibility violations
- Fixed all MyPy type checking errors
- Applied discriminated union patterns throughout
- Preserved 76+ OnexError fixes from main branch"

git push origin terragon/check-duplicate-models-enums-ojnbem
```

## Success Metrics

### Validation Targets
- ✅ **Union Violations**: ≤8 invalid unions (currently 24)
- ✅ **Backwards Compatibility**: 0 violations (currently 5)
- ✅ **MyPy Errors**: 0 type checking failures
- ✅ **Code Quality**: All hooks pass
- ✅ **Primitive Soup**: 100% elimination

### Quality Assurance
- All discriminated unions use proper Literal discriminators
- No Any types in new code
- All models use Pydantic's model_dump() instead of custom serialize()
- ONEX naming conventions maintained throughout

## Risk Mitigation

### If Agent Fixes Don't Apply
- **Fallback**: Manual fix of top 5 highest-impact union violations
- **Focus**: Contract models first (biggest violation count)

### If MyPy Errors Persist
- **Strategy**: Isolate and fix one file at a time
- **Priority**: Files blocking the union validation

### If Hooks Continue Failing
- **Approach**: Fix validation errors first, then re-run hooks
- **Sequence**: Union → Backwards Compatibility → MyPy → Formatting

## Timeline Estimate
- **Phase 1-3 (Parallel Agents)**: 10-15 minutes
- **Validation & Re-commit**: 5 minutes
- **Total**: ~20 minutes to full compliance

---

**Document Created**: 2025-09-28
**Current Invalid Unions**: 24/8 (300% over limit)
**Target**: ≤8 invalid unions (≥67% reduction required)
