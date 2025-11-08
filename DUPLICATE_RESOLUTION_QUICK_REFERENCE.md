# DUPLICATE MODELS RESOLUTION - QUICK REFERENCE

**Generated**: 2025-11-08
**Status**: READY TO EXECUTE

---

## EXECUTIVE SUMMARY

This resolution plan eliminates all 79 duplicate model filename sets in omnibase_core with zero backwards compatibility.

### Key Numbers
- **Files to delete**: ~88 (stubs, re-exports, superseded versions)
- **Files to rename**: ~17 (domain-specific naming)
- **Import updates**: ~500-800 files
- **Tests to verify**: 12,000+ tests must pass

### Key Documents
1. **DUPLICATE_MODELS_RESOLUTION_PLAN.md** - Complete detailed plan (all 79 duplicates)
2. **scripts/execute_duplicate_resolution.sh** - Master execution script
3. **scripts/update_all_imports.sh** - Import update script
4. **DUPLICATE_MODELS_AUDIT_REPORT.md** - Original audit findings

---

## EXECUTION WORKFLOW

### Option 1: Automated Execution (Recommended for Consistency)

```bash
# 1. Review the plan
less DUPLICATE_MODELS_RESOLUTION_PLAN.md

# 2. Execute all phases automatically
bash scripts/execute_duplicate_resolution.sh
```

**What it does**:
- Creates backup branch automatically
- Executes all 5 phases sequentially
- Commits after each phase
- Runs verification tests
- Reports summary at end

**Runtime**: ~15-30 minutes (mostly test execution)

---

### Option 2: Manual Phase-by-Phase Execution

If you prefer more control, execute each phase manually:

#### Phase 1: Delete Identical Duplicates

```bash
# Delete model_config.py stubs (5 files)
git rm src/omnibase_core/models/core/model_config.py
git rm src/omnibase_core/models/events/model_config.py
git rm src/omnibase_core/models/operations/model_config.py
git rm src/omnibase_core/models/security/model_config.py
git rm src/omnibase_core/models/workflows/model_config.py

# Consolidate other identical files
git rm src/omnibase_core/models/core/model_metadata_validation_config.py
git rm src/omnibase_core/models/core/model_tree_generator_config.py
git rm src/omnibase_core/models/core/model_unified_version.py

# Commit
git commit -m "Phase 1: Delete identical duplicate model files"
```

**Result**: 8 files deleted

---

#### Phase 2: Delete Re-exports and Stubs

```bash
# Delete re-exports (user requirement: NO re-exports allowed)
git rm src/omnibase_core/models/core/model_error_context.py
git rm src/omnibase_core/models/core/model_validation_issue.py

# Delete stubs and consolidate model_action.py
git rm src/omnibase_core/models/core/model_action.py
git rm src/omnibase_core/models/model_action.py
git mv src/omnibase_core/models/infrastructure/model_action.py \
       src/omnibase_core/models/infrastructure/model_protocol_action.py

# CRITICAL: Consolidate model_validation_result.py (5 → 2 copies)
git rm src/omnibase_core/models/core/model_validation_result.py
git rm src/omnibase_core/models/security/model_validation_result.py
git rm src/omnibase_core/models/validation/model_validation_result.py
git mv src/omnibase_core/models/model_validation_result.py \
       src/omnibase_core/models/model_import_validation_result.py

# CRITICAL: Fix model_registry_error.py conflict (different base classes!)
git rm src/omnibase_core/models/core/model_registry_error.py

# Delete all CLI/connection/node/health stubs from core/
git rm src/omnibase_core/models/core/model_cli_*.py
git rm src/omnibase_core/models/core/model_connection_*.py
git rm src/omnibase_core/models/core/model_custom_connection_properties.py
git rm src/omnibase_core/models/core/model_node_*.py
git rm src/omnibase_core/models/core/model_health_*.py

# Delete misc stubs
git rm src/omnibase_core/models/core/model_data_handling_declaration.py
git rm src/omnibase_core/models/core/model_environment_properties.py
git rm src/omnibase_core/models/core/model_contract_data.py
git rm src/omnibase_core/models/core/model_custom_fields.py
git rm src/omnibase_core/models/core/model_execution_metadata.py

# Commit
git commit -m "Phase 2: Delete re-exports and stubs"
```

**Result**: ~30 files deleted, 2 files renamed

---

#### Phase 3: Consolidate to Canonical Locations

```bash
# Service/Container (4 files)
git rm src/omnibase_core/models/core/model_service.py
git rm src/omnibase_core/models/core/model_service_registration.py
git rm src/omnibase_core/models/service/model_security_config.py
git rm src/omnibase_core/models/contracts/model_external_service_config.py

# Results/Outputs (8 files)
git rm src/omnibase_core/models/core/model_onex_result.py
git rm src/omnibase_core/models/core/model_onex_message.py
git rm src/omnibase_core/models/core/model_onex_message_context.py
git rm src/omnibase_core/models/core/model_orchestrator_metrics.py
git rm src/omnibase_core/models/results/model_orchestrator_info.py
git rm src/omnibase_core/models/model_orchestrator_output.py
git rm src/omnibase_core/models/core/model_unified_summary.py
git rm src/omnibase_core/models/core/model_unified_summary_details.py

# Infrastructure/Config (7 files)
git rm src/omnibase_core/models/core/model_duration.py
git rm src/omnibase_core/models/core/model_state.py
git rm src/omnibase_core/models/infrastructure/model_circuit_breaker.py
git rm src/omnibase_core/models/contracts/subcontracts/model_circuit_breaker.py
git rm src/omnibase_core/models/infrastructure/model_retry_config.py
git rm src/omnibase_core/models/configuration/model_retry_policy.py
git rm src/omnibase_core/models/infrastructure/model_action_payload.py

# Config/Core (7 files)
git rm src/omnibase_core/models/core/model_namespace_config.py
git rm src/omnibase_core/models/core/model_uri.py
git rm src/omnibase_core/models/core/model_example.py
git rm src/omnibase_core/models/core/model_example_metadata.py
git rm src/omnibase_core/models/config/model_examples_collection.py
git rm src/omnibase_core/models/core/model_fallback_metadata.py
git rm src/omnibase_core/models/core/model_fallback_strategy.py

# Workflows (6 files)
git rm src/omnibase_core/models/operations/model_workflow_configuration.py
git rm src/omnibase_core/models/service/model_workflow_execution_result.py
git rm src/omnibase_core/models/contracts/subcontracts/model_workflow_metrics.py
git rm src/omnibase_core/models/service/model_workflow_parameters.py
git rm src/omnibase_core/models/model_workflow_step.py
git rm src/omnibase_core/models/model_dependency_graph.py

# Events/Config (3 files)
git rm src/omnibase_core/models/core/model_event_envelope.py
git rm src/omnibase_core/models/service/model_event_bus_config.py
git rm src/omnibase_core/models/contracts/model_event_descriptor.py

# Monitoring/Resources (4 files)
git rm src/omnibase_core/models/service/model_monitoring_config.py
git rm src/omnibase_core/models/core/model_resource_allocation.py
git rm src/omnibase_core/models/service/model_resource_limits.py
git rm src/omnibase_core/models/core/model_metric_value.py

# Schema/Validation (1 file)
git rm src/omnibase_core/models/validation/model_schema.py

# Health (3 files)
git rm src/omnibase_core/models/configuration/model_health_check_config.py
git rm src/omnibase_core/models/service/model_health_check_config.py
git rm src/omnibase_core/models/contracts/subcontracts/model_health_check_result.py

# Miscellaneous (4 files)
git rm src/omnibase_core/models/contracts/model_condition_value.py
git rm src/omnibase_core/models/core/model_security_context.py
git rm src/omnibase_core/models/security/model_trust_level.py
git rm src/omnibase_core/models/nodes/model_node_info.py

# Commit
git commit -m "Phase 3: Consolidate to canonical locations"
```

**Result**: ~50 files deleted

---

#### Phase 4: Rename Generic Names to Domain-Specific

```bash
# Metadata renames (6 files)
git mv src/omnibase_core/models/configuration/model_metadata.py \
       src/omnibase_core/models/configuration/model_configuration_metadata.py

git mv src/omnibase_core/models/core/model_metadata.py \
       src/omnibase_core/models/core/model_core_metadata.py

git mv src/omnibase_core/models/security/model_metadata.py \
       src/omnibase_core/models/security/model_security_metadata.py

git mv src/omnibase_core/models/core/model_generic_metadata.py \
       src/omnibase_core/models/core/model_protocol_metadata.py

git mv src/omnibase_core/models/results/model_generic_metadata.py \
       src/omnibase_core/models/results/model_simple_metadata.py

git rm src/omnibase_core/models/core/model_metadata_field_info.py

# Performance metrics renames (3 files)
git mv src/omnibase_core/models/cli/model_performance_metrics.py \
       src/omnibase_core/models/cli/model_cli_performance_metrics.py

git mv src/omnibase_core/models/core/model_performance_metrics.py \
       src/omnibase_core/models/core/model_core_performance_metrics.py

git mv src/omnibase_core/models/discovery/model_performance_metrics.py \
       src/omnibase_core/models/discovery/model_discovery_performance_metrics.py

# CLI consolidations (2 files moved + 2 deleted)
git rm src/omnibase_core/models/cli/model_cli_output_data.py
git mv src/omnibase_core/models/core/model_cli_output_data.py \
       src/omnibase_core/models/cli/model_cli_output_data.py

git rm src/omnibase_core/models/cli/model_cli_execution_result.py
git mv src/omnibase_core/models/core/model_cli_execution_result.py \
       src/omnibase_core/models/cli/model_cli_execution_result.py

# Node configuration (1 file)
git rm src/omnibase_core/models/config/model_node_configuration.py

# Commit
git commit -m "Phase 4: Rename generic names to domain-specific"
```

**Result**: 15 files renamed/moved

---

#### Phase 5: Update All Imports

```bash
# Run import update script
bash scripts/update_all_imports.sh

# Review changes
git diff

# Commit
git add -A
git commit -m "Phase 5: Update all imports after duplicate resolution"
```

**Result**: ~500-800 import statements updated

---

#### Verification

```bash
# Run tests
poetry run pytest tests/ -x

# Type checking
poetry run mypy src/omnibase_core/

# Linting
poetry run ruff check src/ tests/

# Formatting
poetry run black --check src/ tests/
poetry run isort --check src/ tests/
```

---

## CRITICAL ISSUES RESOLVED

### 1. model_registry_error.py - CONFLICTING BASE CLASSES ⚠️

**Problem**: Same class name extended different base classes
- `core/model_registry_error.py` → extends **ModelOnexWarning**
- `common/model_registry_error.py` → extends **ModelOnexError**

**Resolution**: Delete `core/` version, keep `common/` (canonical error type)

**Impact**: Type confusion eliminated, consistent error handling

---

### 2. model_validation_result.py - 5 DIFFERENT VERSIONS ⚠️

**Problem**: 5 completely different implementations
- `common/` → Canonical (10,721 bytes) - documented as replacement
- `core/` → Stub (187 bytes)
- `security/` → Security validation (1,878 bytes)
- `validation/` → General validation (862 bytes)
- `models/` → Import validation (3,007 bytes)

**Resolution**:
- Keep `common/` (canonical)
- Rename `models/` → `model_import_validation_result.py` (different purpose)
- Delete `core/`, `security/`, `validation/` (superseded)

**Impact**: Single source of truth, import validation kept separate

---

### 3. model_action.py - 4 DIFFERENT IMPLEMENTATIONS ⚠️

**Problem**: 4 versions with different purposes
- `orchestrator/` → Full action with lease semantics (2,781 bytes) - CANONICAL
- `infrastructure/` → Protocol implementation (1,194 bytes) - DIFFERENT PURPOSE
- `core/` → Empty stub (95 bytes)
- `models/` → Near-duplicate (1,889 bytes)

**Resolution**:
- Keep `orchestrator/` (canonical)
- Rename `infrastructure/` → `model_protocol_action.py` (clarify purpose)
- Delete `core/` and `models/` (stub and duplicate)

**Impact**: Clear separation between orchestrator actions and protocol actions

---

## RE-EXPORTS ELIMINATION

**User Requirement**: NO re-exports allowed

All re-export files deleted:
- ❌ `core/model_error_context.py` → Use `common/model_error_context.py` directly
- ❌ `core/model_validation_issue.py` → Use `common/model_validation_issue.py` directly

**Benefit**: Single canonical import path, no confusion

---

## DOMAIN-SPECIFIC NAMING

All generic names renamed with domain prefixes:

### Before (Generic - Confusing)
```python
from omnibase_core.models.configuration.model_metadata import ModelMetadata
from omnibase_core.models.security.model_metadata import ModelMetadata  # Same name!
from omnibase_core.models.core.model_metadata import ModelMetadata       # Same name!
```

### After (Domain-Specific - Clear)
```python
from omnibase_core.models.configuration.model_configuration_metadata import ModelConfigurationMetadata
from omnibase_core.models.security.model_security_metadata import ModelSecurityMetadata
from omnibase_core.models.core.model_core_metadata import ModelCoreMetadata
```

**Files renamed**:
1. `model_metadata.py` → `model_configuration_metadata.py`, `model_security_metadata.py`, `model_core_metadata.py`
2. `model_generic_metadata.py` → `model_protocol_metadata.py`, `model_simple_metadata.py` (+ canonical kept)
3. `model_performance_metrics.py` → `model_cli_performance_metrics.py`, `model_core_performance_metrics.py`, `model_discovery_performance_metrics.py`

---

## MODELS/COMMON/ - TRULY COMMON MODELS

All 20 files in `models/common/` are confirmed as truly common and remain unchanged:

✅ **Error Handling** (4 files):
- model_error_context.py
- model_onex_error_data.py
- model_onex_warning.py
- model_registry_error.py

✅ **Validation** (4 files):
- model_validation_result.py (CANONICAL)
- model_validation_issue.py
- model_validation_metadata.py

✅ **Type Utilities** (12 files):
- model_typed_mapping.py
- model_typed_value.py
- model_value_container.py
- model_value_union.py
- model_flexible_value.py
- model_multi_type_value.py
- model_numeric_value.py
- model_numeric_string_value.py
- model_schema_value.py
- model_discriminated_value.py
- model_dict_value_union.py
- model_optional_int.py
- model_coercion_mode.py

**Rationale**: These models are used across ALL domains (security, CLI, workflows, nodes, etc.)

---

## ROLLBACK PROCEDURE

If anything goes wrong:

```bash
# Option 1: Reset to backup branch
git checkout backup/pre-duplicate-resolution-YYYYMMDD-HHMMSS

# Option 2: Revert specific phase
git revert <commit-hash>

# Option 3: Interactive rebase to undo phases
git rebase -i HEAD~5  # Adjust number based on phases completed
```

**CRITICAL**: Backup branch is created automatically by master script

---

## TESTING STRATEGY

### Before Execution
```bash
# Baseline - ensure tests pass
poetry run pytest tests/ -x
```

### After Each Phase (Manual Execution)
```bash
# Quick smoke test (fast)
poetry run pytest tests/unit/models/ -x

# Full validation (slow but comprehensive)
poetry run pytest tests/ -x
```

### Final Verification (Automated in Script)
```bash
# Full test suite
poetry run pytest tests/

# Type checking (must be zero errors)
poetry run mypy src/omnibase_core/

# Code quality
poetry run ruff check src/ tests/
poetry run black --check src/ tests/
poetry run isort --check src/ tests/
```

---

## EXPECTED OUTCOMES

### Before Resolution
- **79 duplicate filename sets**
- **~170 files** with duplicate names
- **Multiple import paths** for same model
- **Type confusion** (e.g., model_registry_error.py with different base classes)
- **Generic names** without domain context

### After Resolution
- **0 duplicate filename sets**
- **~88 fewer files** (deleted duplicates)
- **Single canonical import path** per model
- **No type confusion** - consistent implementations
- **Domain-specific names** - clear purpose

---

## SUCCESS CRITERIA

- [ ] All 79 duplicate sets resolved
- [ ] All tests pass (12,000+ tests)
- [ ] Zero mypy errors
- [ ] All imports use canonical locations
- [ ] No re-exports remain
- [ ] All generic names renamed to domain-specific
- [ ] models/common/ contains only truly common models
- [ ] Documentation updated

---

## TIMELINE

### Automated Execution
- **Setup**: 5 minutes
- **Execution**: 15-30 minutes
- **Total**: ~35 minutes

### Manual Execution
- **Phase 1**: 30 minutes
- **Phase 2**: 1-2 hours
- **Phase 3**: 2-3 hours
- **Phase 4**: 1-2 hours
- **Phase 5**: 2-3 hours
- **Verification**: 1 hour
- **Total**: 8-12 hours

**Recommendation**: Use automated script for consistency and speed

---

## CONTACT & SUPPORT

**Questions?** Refer to:
1. DUPLICATE_MODELS_RESOLUTION_PLAN.md - Complete details
2. DUPLICATE_MODELS_AUDIT_REPORT.md - Original findings
3. CLAUDE.md - Project conventions

**Issues during execution?**
1. Check backup branch exists
2. Review git diff for unexpected changes
3. Run pytest with -x to stop at first failure
4. Review import errors carefully

---

**Generated**: 2025-11-08
**Ready to Execute**: YES
**Backup Required**: YES (created automatically by script)
**Estimated Runtime**: 15-30 minutes (automated) or 8-12 hours (manual)
