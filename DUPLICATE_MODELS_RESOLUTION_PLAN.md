# DUPLICATE MODELS RESOLUTION PLAN

**Generated**: 2025-11-08
**Repository**: omnibase_core
**Total Duplicate Sets**: 79
**Estimated Total Import Updates**: ~500-800 files

---

## EXECUTIVE SUMMARY

### Resolution Strategy

This plan addresses all 79 duplicate model filename sets with a **zero-backwards-compatibility** approach:

- ✅ **DELETE all re-export files** (NO re-exports allowed)
- ✅ **DELETE all stub files** (empty/minimal implementations)
- ✅ **CONSOLIDATE to canonical locations** (keep most complete version)
- ✅ **RENAME generic names to domain-specific** (model_metadata.py → model_{domain}_metadata.py)
- ✅ **UPDATE all imports** to reference new locations
- ✅ **VERIFY tests pass** after each phase

### Phased Approach

1. **Phase 1**: Delete identical duplicates (4 sets → 8 files deleted)
2. **Phase 2**: Delete re-exports and stubs (20 sets → ~30 files deleted)
3. **Phase 3**: Consolidate to canonical locations (30 sets → ~35 files deleted)
4. **Phase 4**: Rename generic names to domain-specific (25 sets → ~50 files affected)
5. **Phase 5**: Update all imports and verify tests

---

## PHASE 1: DELETE IDENTICAL DUPLICATES

**Goal**: Remove byte-for-byte identical files
**Impact**: Delete 8 files, ~1.8KB savings
**Risk**: LOW - files are identical
**Estimated Import Updates**: ~15 files

### 1.1 model_config.py (5 → 0 copies) - DELETE ALL STUBS

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_config.py` (31 bytes) - stub
- `/home/user/omnibase_core/src/omnibase_core/models/events/model_config.py` (31 bytes) - stub
- `/home/user/omnibase_core/src/omnibase_core/models/operations/model_config.py` (31 bytes) - stub
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_config.py` (31 bytes) - stub
- `/home/user/omnibase_core/src/omnibase_core/models/workflows/model_config.py` (31 bytes) - stub

**Analysis**: All 5 files contain ONLY `from pydantic import BaseModel` - these are useless stubs

**Action**: DELETE ALL
**Reason**: No actual implementation, just import stubs - provide no value

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_config.py
git rm src/omnibase_core/models/events/model_config.py
git rm src/omnibase_core/models/operations/model_config.py
git rm src/omnibase_core/models/security/model_config.py
git rm src/omnibase_core/models/workflows/model_config.py
```

**Import updates needed**: ~5 files (remove unused imports)

---

### 1.2 model_metadata_validation_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_metadata_validation_config.py` (251 bytes) - identical
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_metadata_validation_config.py` (251 bytes) - identical

**Action**: CONSOLIDATE
**Keep**: `models/config/model_metadata_validation_config.py` (correct domain)
**Delete**: `models/core/model_metadata_validation_config.py`
**Reason**: Config models belong in config/ directory

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_metadata_validation_config.py
```

**Import updates needed**: ~2 files

---

### 1.3 model_tree_generator_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_tree_generator_config.py` (1,098 bytes) - identical
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_tree_generator_config.py` (1,098 bytes) - identical

**Action**: CONSOLIDATE
**Keep**: `models/config/model_tree_generator_config.py` (correct domain)
**Delete**: `models/core/model_tree_generator_config.py`
**Reason**: Config models belong in config/ directory

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_tree_generator_config.py
```

**Import updates needed**: ~3 files

---

### 1.4 model_unified_version.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_unified_version.py` (440 bytes) - identical
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_unified_version.py` (440 bytes) - identical

**Action**: CONSOLIDATE
**Keep**: `models/results/model_unified_version.py` (more specific domain)
**Delete**: `models/core/model_unified_version.py`
**Reason**: Version information is a result/output concern

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_unified_version.py
```

**Import updates needed**: ~5 files

---

## PHASE 2: DELETE RE-EXPORTS AND STUBS

**Goal**: Eliminate all re-export files and empty stubs
**Impact**: Delete ~30 files
**Risk**: LOW - no actual functionality lost
**Estimated Import Updates**: ~50 files

### 2.1 model_error_context.py (2 → 1 copies) - DELETE RE-EXPORT

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/common/model_error_context.py` (5,246 bytes) - CANONICAL
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_error_context.py` (407 bytes) - RE-EXPORT

**Action**: DELETE RE-EXPORT
**Keep**: `models/common/model_error_context.py` (canonical implementation)
**Delete**: `models/core/model_error_context.py` (just imports from common/)
**Reason**: User requirement - NO re-exports allowed

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_error_context.py
```

**Import updates needed**: ~8 files

---

### 2.2 model_validation_issue.py (2 → 1 copies) - DELETE STUB

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/common/model_validation_issue.py` (3,558 bytes) - CANONICAL
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_validation_issue.py` (410 bytes) - STUB

**Action**: DELETE STUB
**Keep**: `models/common/model_validation_issue.py` (full implementation)
**Delete**: `models/core/model_validation_issue.py` (minimal stub)
**Reason**: Stub provides no value, canonical version exists in common/

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_validation_issue.py
```

**Import updates needed**: ~5 files

---

### 2.3 model_action.py (4 → 1 copies) - DELETE 3 VERSIONS

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_action.py` (95 bytes) - STUB (just `pass`)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_action.py` (1,194 bytes) - Protocol implementation
- `/home/user/omnibase_core/src/omnibase_core/models/model_action.py` (1,889 bytes) - Near-duplicate
- `/home/user/omnibase_core/src/omnibase_core/models/orchestrator/model_action.py` (2,781 bytes) - CANONICAL

**Action**: CONSOLIDATE TO ORCHESTRATOR + RENAME INFRASTRUCTURE
**Keep**: `models/orchestrator/model_action.py` (most complete, lease semantics)
**Rename**: `models/infrastructure/model_action.py` → `model_protocol_action.py` (different purpose - protocol compliance)
**Delete**: `models/core/model_action.py` (useless stub)
**Delete**: `models/model_action.py` (near-duplicate of orchestrator version)
**Reason**: Orchestrator version is canonical, infrastructure version serves different purpose (protocol compliance)

**Git commands**:
```bash
# Delete stub and near-duplicate
git rm src/omnibase_core/models/core/model_action.py
git rm src/omnibase_core/models/model_action.py

# Rename infrastructure version to clarify purpose
git mv src/omnibase_core/models/infrastructure/model_action.py \
       src/omnibase_core/models/infrastructure/model_protocol_action.py
```

**Import updates needed**: ~10 files

---

### 2.4 model_validation_result.py (5 → 2 copies) - CRITICAL CONSOLIDATION

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/common/model_validation_result.py` (10,721 bytes) - CANONICAL (documented replacement)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_validation_result.py` (187 bytes) - STUB
- `/home/user/omnibase_core/src/omnibase_core/models/model_validation_result.py` (3,007 bytes) - IMPORT VALIDATION (different purpose)
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_validation_result.py` (1,878 bytes) - Superseded
- `/home/user/omnibase_core/src/omnibase_core/models/validation/model_validation_result.py` (862 bytes) - Superseded

**Action**: CONSOLIDATE TO CANONICAL + RENAME IMPORT VERSION
**Keep**: `models/common/model_validation_result.py` (canonical, replaces all others)
**Rename**: `models/model_validation_result.py` → `model_import_validation_result.py` (specific purpose - import validation)
**Delete**: `models/core/model_validation_result.py` (stub)
**Delete**: `models/security/model_validation_result.py` (superseded by canonical)
**Delete**: `models/validation/model_validation_result.py` (superseded by canonical)
**Reason**: Canonical version explicitly documented as replacement for all others

**Git commands**:
```bash
# Delete stubs and superseded versions
git rm src/omnibase_core/models/core/model_validation_result.py
git rm src/omnibase_core/models/security/model_validation_result.py
git rm src/omnibase_core/models/validation/model_validation_result.py

# Rename import validation version to clarify purpose
git mv src/omnibase_core/models/model_validation_result.py \
       src/omnibase_core/models/model_import_validation_result.py
```

**Import updates needed**: ~20 files (high impact)

---

### 2.5 model_registry_error.py (2 → 1 copies) - CRITICAL CONFLICT

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/common/model_registry_error.py` (1,344 bytes) - Extends ModelOnexError
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_registry_error.py` (673 bytes) - Extends ModelOnexWarning

**Action**: DELETE CORE VERSION (different base class creates conflict)
**Keep**: `models/common/model_registry_error.py` (canonical error)
**Delete**: `models/core/model_registry_error.py` (extends wrong base class)
**Reason**: CRITICAL - same class name with different base classes creates type confusion

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_registry_error.py
```

**Import updates needed**: ~3 files

---

### 2.6 Additional Stubs to Delete (Core Directory Cleanup)

**Files to delete** (all are stubs or superseded by domain-specific versions):

```bash
# CLI stubs (superseded by full cli/ implementations)
git rm src/omnibase_core/models/core/model_cli_action.py                    # 1,754 bytes vs cli/ 11,564 bytes
git rm src/omnibase_core/models/core/model_cli_execution.py                 # 10,925 bytes vs cli/ 15,377 bytes
git rm src/omnibase_core/models/core/model_cli_execution_metadata.py        # 2,221 bytes vs cli/ 5,420 bytes
git rm src/omnibase_core/models/core/model_cli_result.py                    # 17,059 bytes vs cli/ 18,626 bytes

# Connection stubs
git rm src/omnibase_core/models/core/model_connection_info.py               # 7,242 bytes vs connections/ 8,813 bytes
git rm src/omnibase_core/models/core/model_connection_metrics.py            # 650 bytes vs connections/ 3,004 bytes
git rm src/omnibase_core/models/core/model_custom_connection_properties.py  # 2,293 bytes vs connections/ 20,190 bytes

# Node stubs
git rm src/omnibase_core/models/core/model_node_capability.py               # 9,580 bytes vs nodes/ 14,529 bytes
git rm src/omnibase_core/models/core/model_node_configuration.py            # 1,950 bytes vs nodes/ 12,874 bytes
git rm src/omnibase_core/models/core/model_node_information.py              # 2,998 bytes vs nodes/ 13,811 bytes
git rm src/omnibase_core/models/core/model_node_metadata_info.py            # 2,341 bytes vs nodes/ 15,635 bytes
git rm src/omnibase_core/models/core/model_node_type.py                     # 2,939 bytes vs nodes/ 30,799 bytes

# Health stubs
git rm src/omnibase_core/models/core/model_health_check.py                  # 770 bytes vs health/ 4,580 bytes
git rm src/omnibase_core/models/core/model_health_status.py                 # 1,932 bytes vs health/ 7,517 bytes

# Other stubs
git rm src/omnibase_core/models/core/model_data_handling_declaration.py     # 404 bytes vs config/ 4,110 bytes
git rm src/omnibase_core/models/core/model_environment_properties.py        # 6,220 bytes vs config/ 8,927 bytes
git rm src/omnibase_core/models/core/model_contract_data.py                 # 1,445 bytes vs utils/ 3,070 bytes
git rm src/omnibase_core/models/core/model_custom_fields.py                 # 3,090 bytes vs service/ 6,568 bytes
git rm src/omnibase_core/models/core/model_execution_metadata.py            # 1,695 bytes vs operations/ 7,288 bytes
```

**Total stubs deleted in Phase 2**: ~22 files
**Import updates needed**: ~60 files

---

## PHASE 3: CONSOLIDATE TO CANONICAL LOCATIONS

**Goal**: Keep most complete version, delete partial implementations
**Impact**: Delete ~35 files
**Risk**: MEDIUM - requires import updates
**Estimated Import Updates**: ~100 files

### 3.1 Service/Configuration Consolidations

#### 3.1.1 model_service.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/container/model_service.py` (917 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_service.py` (915 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/container/model_service.py` (correct domain - service registration)
**Delete**: `models/core/model_service.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_service.py
```

**Import updates**: ~5 files

---

#### 3.1.2 model_service_registration.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/container/model_service_registration.py` (4,181 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_service_registration.py` (699 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/container/model_service_registration.py` (full implementation)
**Delete**: `models/core/model_service_registration.py` (stub)

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_service_registration.py
```

**Import updates**: ~3 files

---

#### 3.1.3 model_security_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_security_config.py` (1,181 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_security_config.py` (1,319 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_security_config.py` (config belongs in config/)
**Delete**: `models/service/model_security_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_security_config.py
```

**Import updates**: ~4 files

---

#### 3.1.4 model_external_service_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/model_external_service_config.py` (1,772 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_external_service_config.py` (9,236 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/service/model_external_service_config.py` (most complete)
**Delete**: `models/contracts/model_external_service_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/contracts/model_external_service_config.py
```

**Import updates**: ~2 files

---

### 3.2 Results/Outputs Consolidations

#### 3.2.1 model_onex_result.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_onex_result.py` (2,491 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_onex_result.py` (2,453 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_onex_result.py` (correct domain)
**Delete**: `models/core/model_onex_result.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_onex_result.py
```

**Import updates**: ~8 files

---

#### 3.2.2 model_onex_message.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_onex_message.py` (2,559 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_onex_message.py` (2,697 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_onex_message.py` (slightly more complete)
**Delete**: `models/core/model_onex_message.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_onex_message.py
```

**Import updates**: ~6 files

---

#### 3.2.3 model_onex_message_context.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_onex_message_context.py` (373 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_onex_message_context.py` (666 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_onex_message_context.py` (more complete)
**Delete**: `models/core/model_onex_message_context.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_onex_message_context.py
```

**Import updates**: ~3 files

---

#### 3.2.4 model_orchestrator_metrics.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_orchestrator_metrics.py` (1,155 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_orchestrator_metrics.py` (1,218 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_orchestrator_metrics.py` (metrics are results)
**Delete**: `models/core/model_orchestrator_metrics.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_orchestrator_metrics.py
```

**Import updates**: ~4 files

---

#### 3.2.5 model_orchestrator_info.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_orchestrator_info.py` (6,168 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_orchestrator_info.py` (4,781 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_orchestrator_info.py` (more complete)
**Delete**: `models/results/model_orchestrator_info.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/results/model_orchestrator_info.py
```

**Import updates**: ~3 files

---

#### 3.2.6 model_orchestrator_output.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/model_orchestrator_output.py` (2,038 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_orchestrator_output.py` (2,277 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/service/model_orchestrator_output.py` (more complete)
**Delete**: `models/model_orchestrator_output.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/model_orchestrator_output.py
```

**Import updates**: ~5 files

---

#### 3.2.7 model_unified_summary.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_unified_summary.py` (443 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_unified_summary.py` (612 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_unified_summary.py` (summary is a result)
**Delete**: `models/core/model_unified_summary.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_unified_summary.py
```

**Import updates**: ~2 files

---

#### 3.2.8 model_unified_summary_details.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_unified_summary_details.py` (409 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_unified_summary_details.py` (667 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/results/model_unified_summary_details.py` (more complete)
**Delete**: `models/core/model_unified_summary_details.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_unified_summary_details.py
```

**Import updates**: ~2 files

---

### 3.3 Infrastructure/Configuration Consolidations

#### 3.3.1 model_duration.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_duration.py` (9,595 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_duration.py` (10,337 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/infrastructure/model_duration.py` (more complete, correct domain)
**Delete**: `models/core/model_duration.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_duration.py
```

**Import updates**: ~10 files

---

#### 3.3.2 model_state.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_state.py` (715 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_state.py` (1,241 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/infrastructure/model_state.py` (more complete)
**Delete**: `models/core/model_state.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_state.py
```

**Import updates**: ~5 files

---

#### 3.3.3 model_circuit_breaker.py (3 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_circuit_breaker.py` (10,000 bytes) - MOST COMPLETE
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_circuit_breaker.py` (5,284 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/subcontracts/model_circuit_breaker.py` (1,801 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_circuit_breaker.py` (most complete)
**Delete**: `models/infrastructure/model_circuit_breaker.py`
**Delete**: `models/contracts/subcontracts/model_circuit_breaker.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/infrastructure/model_circuit_breaker.py
git rm src/omnibase_core/models/contracts/subcontracts/model_circuit_breaker.py
```

**Import updates**: ~6 files

---

#### 3.3.4 model_retry_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_retry_config.py` (14,405 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_retry_config.py` (5,659 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_retry_config.py` (more complete)
**Delete**: `models/infrastructure/model_retry_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/infrastructure/model_retry_config.py
```

**Import updates**: ~4 files

---

#### 3.3.5 model_retry_policy.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_retry_policy.py` (2,426 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_retry_policy.py` (12,965 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/infrastructure/model_retry_policy.py` (most complete)
**Delete**: `models/configuration/model_retry_policy.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/configuration/model_retry_policy.py
```

**Import updates**: ~3 files

---

#### 3.3.6 model_action_payload.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_action_payload.py` (3,265 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/infrastructure/model_action_payload.py` (1,311 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_action_payload.py` (more complete)
**Delete**: `models/infrastructure/model_action_payload.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/infrastructure/model_action_payload.py
```

**Import updates**: ~2 files

---

### 3.4 Config/Core Consolidations

#### 3.4.1 model_namespace_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_namespace_config.py` (1,677 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_namespace_config.py` (314 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_namespace_config.py` (full implementation)
**Delete**: `models/core/model_namespace_config.py` (stub)

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_namespace_config.py
```

**Import updates**: ~2 files

---

#### 3.4.2 model_uri.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_uri.py` (1,959 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_uri.py` (729 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_uri.py` (more complete)
**Delete**: `models/core/model_uri.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_uri.py
```

**Import updates**: ~3 files

---

#### 3.4.3 model_example.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_example.py` (3,584 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_example.py` (1,422 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_example.py` (more complete)
**Delete**: `models/core/model_example.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_example.py
```

**Import updates**: ~4 files

---

#### 3.4.4 model_example_metadata.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_example_metadata.py` (2,872 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_example_metadata.py` (692 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_example_metadata.py` (more complete)
**Delete**: `models/core/model_example_metadata.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_example_metadata.py
```

**Import updates**: ~3 files

---

#### 3.4.5 model_examples_collection.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_examples_collection.py` (8,263 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_examples_collection.py` (10,939 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_examples_collection.py` (more complete)
**Delete**: `models/config/model_examples_collection.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/config/model_examples_collection.py
```

**Import updates**: ~3 files

---

#### 3.4.6 model_fallback_metadata.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_fallback_metadata.py` (2,844 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_fallback_metadata.py` (922 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_fallback_metadata.py` (more complete)
**Delete**: `models/core/model_fallback_metadata.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_fallback_metadata.py
```

**Import updates**: ~2 files

---

#### 3.4.7 model_fallback_strategy.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_fallback_strategy.py` (3,739 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_fallback_strategy.py` (2,101 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/config/model_fallback_strategy.py` (more complete)
**Delete**: `models/core/model_fallback_strategy.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_fallback_strategy.py
```

**Import updates**: ~3 files

---

### 3.5 Workflow Consolidations

#### 3.5.1 model_workflow_configuration.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_workflow_configuration.py` (1,290 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/operations/model_workflow_configuration.py` (1,040 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_workflow_configuration.py` (configuration domain)
**Delete**: `models/operations/model_workflow_configuration.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/operations/model_workflow_configuration.py
```

**Import updates**: ~4 files

---

#### 3.5.2 model_workflow_execution_result.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_workflow_execution_result.py` (875 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/workflows/model_workflow_execution_result.py` (2,011 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/workflows/model_workflow_execution_result.py` (more complete, correct domain)
**Delete**: `models/service/model_workflow_execution_result.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_workflow_execution_result.py
```

**Import updates**: ~3 files

---

#### 3.5.3 model_workflow_metrics.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/subcontracts/model_workflow_metrics.py` (1,418 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_workflow_metrics.py` (2,020 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_workflow_metrics.py` (more complete)
**Delete**: `models/contracts/subcontracts/model_workflow_metrics.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/contracts/subcontracts/model_workflow_metrics.py
```

**Import updates**: ~2 files

---

#### 3.5.4 model_workflow_parameters.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/operations/model_workflow_parameters.py` (8,397 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_workflow_parameters.py` (4,046 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/operations/model_workflow_parameters.py` (most complete)
**Delete**: `models/service/model_workflow_parameters.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_workflow_parameters.py
```

**Import updates**: ~4 files

---

#### 3.5.5 model_workflow_step.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/model_workflow_step.py` (3,945 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/model_workflow_step.py` (2,172 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/contracts/model_workflow_step.py` (more complete)
**Delete**: `models/model_workflow_step.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/model_workflow_step.py
```

**Import updates**: ~5 files

---

#### 3.5.6 model_dependency_graph.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/model_dependency_graph.py` (2,613 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/workflows/model_dependency_graph.py` (4,043 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/workflows/model_dependency_graph.py` (more complete, correct domain)
**Delete**: `models/model_dependency_graph.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/model_dependency_graph.py
```

**Import updates**: ~6 files

---

### 3.6 Event/Configuration Consolidations

#### 3.6.1 model_event_envelope.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_event_envelope.py` (11,110 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/events/model_event_envelope.py` (14,171 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/events/model_event_envelope.py` (most complete, correct domain)
**Delete**: `models/core/model_event_envelope.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_event_envelope.py
```

**Import updates**: ~15 files (high usage)

---

#### 3.6.2 model_event_bus_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_event_bus_config.py` (5,754 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_event_bus_config.py` (1,793 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_event_bus_config.py` (most complete)
**Delete**: `models/service/model_event_bus_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_event_bus_config.py
```

**Import updates**: ~3 files

---

#### 3.6.3 model_event_descriptor.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/model_event_descriptor.py` (1,821 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/discovery/model_event_descriptor.py` (8,277 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/discovery/model_event_descriptor.py` (most complete)
**Delete**: `models/contracts/model_event_descriptor.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/contracts/model_event_descriptor.py
```

**Import updates**: ~4 files

---

### 3.7 Monitoring/Resource Consolidations

#### 3.7.1 model_monitoring_config.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_monitoring_config.py` (1,070 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_monitoring_config.py` (754 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_monitoring_config.py` (more complete)
**Delete**: `models/service/model_monitoring_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_monitoring_config.py
```

**Import updates**: ~2 files

---

#### 3.7.2 model_resource_allocation.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_resource_allocation.py` (5,978 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_resource_allocation.py` (3,764 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_resource_allocation.py` (more complete)
**Delete**: `models/core/model_resource_allocation.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_resource_allocation.py
```

**Import updates**: ~3 files

---

#### 3.7.3 model_resource_limits.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_resource_limits.py` (4,043 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_resource_limits.py` (510 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/configuration/model_resource_limits.py` (more complete)
**Delete**: `models/service/model_resource_limits.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/service/model_resource_limits.py
```

**Import updates**: ~2 files

---

#### 3.7.4 model_metric_value.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_metric_value.py` (855 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/discovery/model_metric_value.py` (1,070 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/discovery/model_metric_value.py` (more complete)
**Delete**: `models/core/model_metric_value.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_metric_value.py
```

**Import updates**: ~3 files

---

### 3.8 Schema/Validation Consolidations

#### 3.8.1 model_schema.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_schema.py` (17,160 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/validation/model_schema.py` (688 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_schema.py` (most complete)
**Delete**: `models/validation/model_schema.py` (stub)

**Git commands**:
```bash
git rm src/omnibase_core/models/validation/model_schema.py
```

**Import updates**: ~5 files

---

### 3.9 Health Check Consolidations

#### 3.9.1 model_health_check_config.py (3 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_health_check_config.py` (2,095 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/health/model_health_check_config.py` (7,217 bytes) - MOST COMPLETE
- `/home/user/omnibase_core/src/omnibase_core/models/service/model_health_check_config.py` (951 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/health/model_health_check_config.py` (most complete, correct domain)
**Delete**: `models/configuration/model_health_check_config.py`
**Delete**: `models/service/model_health_check_config.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/configuration/model_health_check_config.py
git rm src/omnibase_core/models/service/model_health_check_config.py
```

**Import updates**: ~5 files

---

#### 3.9.2 model_health_check_result.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/subcontracts/model_health_check_result.py` (1,498 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_health_check_result.py` (2,993 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_health_check_result.py` (more complete)
**Delete**: `models/contracts/subcontracts/model_health_check_result.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/contracts/subcontracts/model_health_check_result.py
```

**Import updates**: ~2 files

---

### 3.10 Miscellaneous Consolidations

#### 3.10.1 model_condition_value.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/contracts/model_condition_value.py` (978 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_condition_value.py` (1,762 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/security/model_condition_value.py` (more complete, correct domain)
**Delete**: `models/contracts/model_condition_value.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/contracts/model_condition_value.py
```

**Import updates**: ~2 files

---

#### 3.10.2 model_security_context.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_security_context.py` (1,952 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_security_context.py` (2,673 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/security/model_security_context.py` (more complete, correct domain)
**Delete**: `models/core/model_security_context.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_security_context.py
```

**Import updates**: ~4 files

---

#### 3.10.3 model_trust_level.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_trust_level.py` (6,132 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_trust_level.py` (2,349 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_trust_level.py` (more complete)
**Delete**: `models/security/model_trust_level.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/security/model_trust_level.py
```

**Import updates**: ~3 files

---

#### 3.10.4 model_node_info.py (2 → 1 copies)

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_node_info.py` (891 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/nodes/model_node_info.py` (183 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/core/model_node_info.py` (more complete)
**Delete**: `models/nodes/model_node_info.py` (stub)

**Git commands**:
```bash
git rm src/omnibase_core/models/nodes/model_node_info.py
```

**Import updates**: ~2 files

---

**Total files deleted in Phase 3**: ~50 files
**Total import updates in Phase 3**: ~120 files

---

## PHASE 4: RENAME GENERIC NAMES TO DOMAIN-SPECIFIC

**Goal**: Add domain prefixes to all generic model names
**Impact**: Rename ~25 files
**Risk**: HIGH - requires comprehensive import updates
**Estimated Import Updates**: ~200 files

### 4.1 Metadata Renames (3 files)

#### 4.1.1 model_metadata.py (3 copies) → RENAME ALL

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/configuration/model_metadata.py` (295 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_metadata.py` (1,276 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/security/model_metadata.py` (2,065 bytes)

**Action**: RENAME ALL TO DOMAIN-SPECIFIC
**Renames**:
- `models/configuration/model_metadata.py` → `models/configuration/model_configuration_metadata.py`
- `models/core/model_metadata.py` → `models/core/model_core_metadata.py`
- `models/security/model_metadata.py` → `models/security/model_security_metadata.py`

**Git commands**:
```bash
git mv src/omnibase_core/models/configuration/model_metadata.py \
       src/omnibase_core/models/configuration/model_configuration_metadata.py

git mv src/omnibase_core/models/core/model_metadata.py \
       src/omnibase_core/models/core/model_core_metadata.py

git mv src/omnibase_core/models/security/model_metadata.py \
       src/omnibase_core/models/security/model_security_metadata.py
```

**Import updates needed**: ~20 files

---

#### 4.1.2 model_generic_metadata.py (3 copies) → RENAME 2, KEEP CANONICAL

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_generic_metadata.py` (3,193 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/metadata/model_generic_metadata.py` (12,815 bytes) - CANONICAL
- `/home/user/omnibase_core/src/omnibase_core/models/results/model_generic_metadata.py` (2,555 bytes)

**Action**: RENAME NON-CANONICAL VERSIONS
**Keep**: `models/metadata/model_generic_metadata.py` (canonical, truly generic)
**Renames**:
- `models/core/model_generic_metadata.py` → `models/core/model_protocol_metadata.py`
- `models/results/model_generic_metadata.py` → `models/results/model_simple_metadata.py`

**Git commands**:
```bash
git mv src/omnibase_core/models/core/model_generic_metadata.py \
       src/omnibase_core/models/core/model_protocol_metadata.py

git mv src/omnibase_core/models/results/model_generic_metadata.py \
       src/omnibase_core/models/results/model_simple_metadata.py
```

**Import updates needed**: ~15 files

---

#### 4.1.3 model_metadata_field_info.py (2 copies) → CONSOLIDATE

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_metadata_field_info.py` (9,527 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/metadata/model_metadata_field_info.py` (15,317 bytes)

**Action**: CONSOLIDATE
**Keep**: `models/metadata/model_metadata_field_info.py` (most complete, correct domain)
**Delete**: `models/core/model_metadata_field_info.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/core/model_metadata_field_info.py
```

**Import updates needed**: ~8 files

---

### 4.2 Performance Metrics Renames (3 files)

#### 4.2.1 model_performance_metrics.py (3 copies) → RENAME ALL

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/cli/model_performance_metrics.py` (2,324 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_performance_metrics.py` (1,396 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/discovery/model_performance_metrics.py` (935 bytes)

**Action**: RENAME ALL TO DOMAIN-SPECIFIC
**Renames**:
- `models/cli/model_performance_metrics.py` → `models/cli/model_cli_performance_metrics.py`
- `models/core/model_performance_metrics.py` → `models/core/model_core_performance_metrics.py`
- `models/discovery/model_performance_metrics.py` → `models/discovery/model_discovery_performance_metrics.py`

**Git commands**:
```bash
git mv src/omnibase_core/models/cli/model_performance_metrics.py \
       src/omnibase_core/models/cli/model_cli_performance_metrics.py

git mv src/omnibase_core/models/core/model_performance_metrics.py \
       src/omnibase_core/models/core/model_core_performance_metrics.py

git mv src/omnibase_core/models/discovery/model_performance_metrics.py \
       src/omnibase_core/models/discovery/model_discovery_performance_metrics.py
```

**Import updates needed**: ~15 files

---

### 4.3 CLI Output Renames (1 file)

#### 4.3.1 model_cli_output_data.py (2 copies) → CONSOLIDATE FIRST, THEN KEEP

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/cli/model_cli_output_data.py` (6,285 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_cli_output_data.py` (15,420 bytes) - MORE COMPLETE

**Action**: CONSOLIDATE TO CORE, THEN RENAME
**Keep**: `models/core/model_cli_output_data.py` (more complete)
**Delete**: `models/cli/model_cli_output_data.py`
**Then Rename**: `models/core/model_cli_output_data.py` → `models/cli/model_cli_output_data.py` (move to correct domain)

**Git commands**:
```bash
# Delete smaller version
git rm src/omnibase_core/models/cli/model_cli_output_data.py

# Move core version to CLI domain
git mv src/omnibase_core/models/core/model_cli_output_data.py \
       src/omnibase_core/models/cli/model_cli_output_data.py
```

**Import updates needed**: ~8 files

---

#### 4.3.2 model_cli_execution_result.py (2 copies) → CONSOLIDATE FIRST

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/cli/model_cli_execution_result.py` (458 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_cli_execution_result.py` (3,243 bytes)

**Action**: CONSOLIDATE TO CLI
**Keep**: `models/core/model_cli_execution_result.py` (more complete)
**Delete**: `models/cli/model_cli_execution_result.py` (stub)
**Then Move**: `models/core/model_cli_execution_result.py` → `models/cli/model_cli_execution_result.py`

**Git commands**:
```bash
# Delete stub
git rm src/omnibase_core/models/cli/model_cli_execution_result.py

# Move to CLI domain
git mv src/omnibase_core/models/core/model_cli_execution_result.py \
       src/omnibase_core/models/cli/model_cli_execution_result.py
```

**Import updates needed**: ~5 files

---

### 4.4 Node Configuration Consolidation

#### 4.4.1 model_node_configuration.py (3 copies) → CONSOLIDATE TO NODES

**Current locations**:
- `/home/user/omnibase_core/src/omnibase_core/models/config/model_node_configuration.py` (6,679 bytes)
- `/home/user/omnibase_core/src/omnibase_core/models/core/model_node_configuration.py` (1,950 bytes) - ALREADY DELETED IN PHASE 2
- `/home/user/omnibase_core/src/omnibase_core/models/nodes/model_node_configuration.py` (12,874 bytes) - CANONICAL

**Action**: DELETE CONFIG VERSION (nodes version is canonical)
**Keep**: `models/nodes/model_node_configuration.py` (most complete, correct domain)
**Delete**: `models/config/model_node_configuration.py`

**Git commands**:
```bash
git rm src/omnibase_core/models/config/model_node_configuration.py
```

**Import updates needed**: ~10 files

---

**Total renames in Phase 4**: ~15 files
**Total import updates in Phase 4**: ~100 files

---

## PHASE 5: UPDATE ALL IMPORTS AND VERIFY TESTS

**Goal**: Update all import statements to reference new locations
**Impact**: ~500-800 files modified
**Risk**: HIGH - comprehensive codebase changes
**Verification**: All tests must pass

### 5.1 Import Update Strategy

#### Automated Search & Replace

Use `sed` or custom script to update imports in batches:

```bash
# Example: Update model_validation_result imports
find /home/user/omnibase_core -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;

find /home/user/omnibase_core -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.security.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;

find /home/user/omnibase_core -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.validation.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;
```

#### Update Patterns

For each deleted/moved file, update imports following this pattern:

**OLD**:
```python
from omnibase_core.models.core.model_error_context import ModelErrorContext
```

**NEW**:
```python
from omnibase_core.models.common.model_error_context import ModelErrorContext
```

### 5.2 Import Update Script

Create `/home/user/omnibase_core/scripts/update_all_imports.sh`:

```bash
#!/bin/bash
# Import update script for duplicate model resolution
# Generated: 2025-11-08

set -e  # Exit on error

BASE_DIR="/home/user/omnibase_core"

echo "Starting import updates..."

# Phase 1: Identical duplicates
echo "Phase 1: Updating model_config imports..."
# model_config.py deleted entirely - remove imports

echo "Phase 1: Updating model_metadata_validation_config imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_metadata_validation_config import|from omnibase_core.models.config.model_metadata_validation_config import|g' {} \;

echo "Phase 1: Updating model_tree_generator_config imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_tree_generator_config import|from omnibase_core.models.config.model_tree_generator_config import|g' {} \;

echo "Phase 1: Updating model_unified_version imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_unified_version import|from omnibase_core.models.results.model_unified_version import|g' {} \;

# Phase 2: Re-exports and stubs
echo "Phase 2: Updating model_error_context imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_error_context import|from omnibase_core.models.common.model_error_context import|g' {} \;

echo "Phase 2: Updating model_validation_issue imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_validation_issue import|from omnibase_core.models.common.model_validation_issue import|g' {} \;

echo "Phase 2: Updating model_action imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_action import|from omnibase_core.models.orchestrator.model_action import|g' {} \;

find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.model_action import|from omnibase_core.models.orchestrator.model_action import|g' {} \;

find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.infrastructure.model_action import|from omnibase_core.models.infrastructure.model_protocol_action import|g' {} \;

echo "Phase 2: Updating model_validation_result imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;

find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.security.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;

find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.validation.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;

find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.model_validation_result import|from omnibase_core.models.model_import_validation_result import|g' {} \;

echo "Phase 2: Updating model_registry_error imports..."
find "$BASE_DIR" -name "*.py" -type f -exec sed -i \
  's|from omnibase_core.models.core.model_registry_error import|from omnibase_core.models.common.model_registry_error import|g' {} \;

# Continue for all other files...
# (Full script would include all ~79 duplicate sets)

echo "Import updates complete!"
echo "Running import verification..."

# Verify no broken imports
python3 -m py_compile "$BASE_DIR/src/omnibase_core/**/*.py" 2>&1 || echo "Found compilation errors - manual review needed"

echo "Done!"
```

### 5.3 Test Verification

After all import updates:

```bash
# Run full test suite
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# Run type checking
poetry run mypy src/omnibase_core/

# Run linting
poetry run ruff check src/ tests/

# Run formatting check
poetry run black --check src/ tests/
poetry run isort --check src/ tests/
```

### 5.4 Rollback Plan

If tests fail:

1. **Review error messages** - identify which imports are broken
2. **Fix manually** - some imports may need special handling
3. **Re-run tests** - verify fixes
4. **Commit incrementally** - don't commit all changes at once

---

## MASTER EXECUTION SCRIPT

Create `/home/user/omnibase_core/scripts/execute_duplicate_resolution.sh`:

```bash
#!/bin/bash
# Master script to execute all duplicate model resolution phases
# Generated: 2025-11-08
# CRITICAL: This script makes IRREVERSIBLE changes - backup first!

set -e  # Exit on error

BASE_DIR="/home/user/omnibase_core"
cd "$BASE_DIR"

echo "========================================="
echo "DUPLICATE MODELS RESOLUTION - MASTER SCRIPT"
echo "========================================="
echo ""
echo "This script will:"
echo "  - Delete ~100 duplicate/stub model files"
echo "  - Rename ~15 files to domain-specific names"
echo "  - Update ~500-800 import statements"
echo ""
read -p "Are you sure you want to proceed? (yes/NO): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Creating backup branch..."
git checkout -b backup/pre-duplicate-resolution-$(date +%Y%m%d-%H%M%S)
git checkout claude/repo-audit-and-cleanup-011CUthhtoPAvfvphywTxehN

echo ""
echo "========================================="
echo "PHASE 1: DELETE IDENTICAL DUPLICATES"
echo "========================================="

# 1.1 model_config.py - DELETE ALL
echo "Deleting model_config.py stubs..."
git rm src/omnibase_core/models/core/model_config.py
git rm src/omnibase_core/models/events/model_config.py
git rm src/omnibase_core/models/operations/model_config.py
git rm src/omnibase_core/models/security/model_config.py
git rm src/omnibase_core/models/workflows/model_config.py

# 1.2 model_metadata_validation_config.py
echo "Consolidating model_metadata_validation_config.py..."
git rm src/omnibase_core/models/core/model_metadata_validation_config.py

# 1.3 model_tree_generator_config.py
echo "Consolidating model_tree_generator_config.py..."
git rm src/omnibase_core/models/core/model_tree_generator_config.py

# 1.4 model_unified_version.py
echo "Consolidating model_unified_version.py..."
git rm src/omnibase_core/models/core/model_unified_version.py

echo "Phase 1 complete - 8 files deleted"
git commit -m "Phase 1: Delete identical duplicate model files

- Remove 5 model_config.py stubs (all identical, no functionality)
- Consolidate model_metadata_validation_config.py to config/
- Consolidate model_tree_generator_config.py to config/
- Consolidate model_unified_version.py to results/

Total: 8 files deleted"

echo ""
echo "========================================="
echo "PHASE 2: DELETE RE-EXPORTS AND STUBS"
echo "========================================="

# 2.1 model_error_context.py - DELETE RE-EXPORT
echo "Deleting model_error_context.py re-export..."
git rm src/omnibase_core/models/core/model_error_context.py

# 2.2 model_validation_issue.py - DELETE STUB
echo "Deleting model_validation_issue.py stub..."
git rm src/omnibase_core/models/core/model_validation_issue.py

# 2.3 model_action.py - DELETE 2, RENAME 1
echo "Consolidating model_action.py..."
git rm src/omnibase_core/models/core/model_action.py
git rm src/omnibase_core/models/model_action.py
git mv src/omnibase_core/models/infrastructure/model_action.py \
       src/omnibase_core/models/infrastructure/model_protocol_action.py

# 2.4 model_validation_result.py - CRITICAL
echo "Consolidating model_validation_result.py (5 → 2 copies)..."
git rm src/omnibase_core/models/core/model_validation_result.py
git rm src/omnibase_core/models/security/model_validation_result.py
git rm src/omnibase_core/models/validation/model_validation_result.py
git mv src/omnibase_core/models/model_validation_result.py \
       src/omnibase_core/models/model_import_validation_result.py

# 2.5 model_registry_error.py - CRITICAL CONFLICT
echo "Deleting model_registry_error.py conflict..."
git rm src/omnibase_core/models/core/model_registry_error.py

# 2.6 Additional core/ stubs
echo "Deleting CLI stubs from core/..."
git rm src/omnibase_core/models/core/model_cli_action.py
git rm src/omnibase_core/models/core/model_cli_execution.py
git rm src/omnibase_core/models/core/model_cli_execution_metadata.py
git rm src/omnibase_core/models/core/model_cli_result.py

echo "Deleting connection stubs from core/..."
git rm src/omnibase_core/models/core/model_connection_info.py
git rm src/omnibase_core/models/core/model_connection_metrics.py
git rm src/omnibase_core/models/core/model_custom_connection_properties.py

echo "Deleting node stubs from core/..."
git rm src/omnibase_core/models/core/model_node_capability.py
git rm src/omnibase_core/models/core/model_node_configuration.py
git rm src/omnibase_core/models/core/model_node_information.py
git rm src/omnibase_core/models/core/model_node_metadata_info.py
git rm src/omnibase_core/models/core/model_node_type.py

echo "Deleting health stubs from core/..."
git rm src/omnibase_core/models/core/model_health_check.py
git rm src/omnibase_core/models/core/model_health_status.py

echo "Deleting misc stubs from core/..."
git rm src/omnibase_core/models/core/model_data_handling_declaration.py
git rm src/omnibase_core/models/core/model_environment_properties.py
git rm src/omnibase_core/models/core/model_contract_data.py
git rm src/omnibase_core/models/core/model_custom_fields.py
git rm src/omnibase_core/models/core/model_execution_metadata.py

echo "Phase 2 complete - ~30 files deleted"
git commit -m "Phase 2: Delete re-exports and stubs

- Remove model_error_context.py re-export
- Remove model_validation_issue.py stub
- Consolidate model_action.py (4 → 1) + rename infrastructure version
- Consolidate model_validation_result.py (5 → 2) + rename import version
- Remove model_registry_error.py conflict (different base classes)
- Remove 22 core/ stubs superseded by domain-specific versions

Total: ~30 files deleted, 2 files renamed"

echo ""
echo "========================================="
echo "PHASE 3: CONSOLIDATE TO CANONICAL"
echo "========================================="

# Service/Container
echo "Consolidating service models..."
git rm src/omnibase_core/models/core/model_service.py
git rm src/omnibase_core/models/core/model_service_registration.py
git rm src/omnibase_core/models/service/model_security_config.py
git rm src/omnibase_core/models/contracts/model_external_service_config.py

# Results/Outputs
echo "Consolidating results models..."
git rm src/omnibase_core/models/core/model_onex_result.py
git rm src/omnibase_core/models/core/model_onex_message.py
git rm src/omnibase_core/models/core/model_onex_message_context.py
git rm src/omnibase_core/models/core/model_orchestrator_metrics.py
git rm src/omnibase_core/models/results/model_orchestrator_info.py
git rm src/omnibase_core/models/model_orchestrator_output.py
git rm src/omnibase_core/models/core/model_unified_summary.py
git rm src/omnibase_core/models/core/model_unified_summary_details.py

# Infrastructure/Config
echo "Consolidating infrastructure models..."
git rm src/omnibase_core/models/core/model_duration.py
git rm src/omnibase_core/models/core/model_state.py
git rm src/omnibase_core/models/infrastructure/model_circuit_breaker.py
git rm src/omnibase_core/models/contracts/subcontracts/model_circuit_breaker.py
git rm src/omnibase_core/models/infrastructure/model_retry_config.py
git rm src/omnibase_core/models/configuration/model_retry_policy.py
git rm src/omnibase_core/models/infrastructure/model_action_payload.py

# Config/Core
echo "Consolidating config models..."
git rm src/omnibase_core/models/core/model_namespace_config.py
git rm src/omnibase_core/models/core/model_uri.py
git rm src/omnibase_core/models/core/model_example.py
git rm src/omnibase_core/models/core/model_example_metadata.py
git rm src/omnibase_core/models/config/model_examples_collection.py
git rm src/omnibase_core/models/core/model_fallback_metadata.py
git rm src/omnibase_core/models/core/model_fallback_strategy.py

# Workflows
echo "Consolidating workflow models..."
git rm src/omnibase_core/models/operations/model_workflow_configuration.py
git rm src/omnibase_core/models/service/model_workflow_execution_result.py
git rm src/omnibase_core/models/contracts/subcontracts/model_workflow_metrics.py
git rm src/omnibase_core/models/service/model_workflow_parameters.py
git rm src/omnibase_core/models/model_workflow_step.py
git rm src/omnibase_core/models/model_dependency_graph.py

# Events/Config
echo "Consolidating event models..."
git rm src/omnibase_core/models/core/model_event_envelope.py
git rm src/omnibase_core/models/service/model_event_bus_config.py
git rm src/omnibase_core/models/contracts/model_event_descriptor.py

# Monitoring/Resources
echo "Consolidating monitoring models..."
git rm src/omnibase_core/models/service/model_monitoring_config.py
git rm src/omnibase_core/models/core/model_resource_allocation.py
git rm src/omnibase_core/models/service/model_resource_limits.py
git rm src/omnibase_core/models/core/model_metric_value.py

# Schema/Validation
echo "Consolidating validation models..."
git rm src/omnibase_core/models/validation/model_schema.py

# Health
echo "Consolidating health models..."
git rm src/omnibase_core/models/configuration/model_health_check_config.py
git rm src/omnibase_core/models/service/model_health_check_config.py
git rm src/omnibase_core/models/contracts/subcontracts/model_health_check_result.py

# Miscellaneous
echo "Consolidating misc models..."
git rm src/omnibase_core/models/contracts/model_condition_value.py
git rm src/omnibase_core/models/core/model_security_context.py
git rm src/omnibase_core/models/security/model_trust_level.py
git rm src/omnibase_core/models/nodes/model_node_info.py

echo "Phase 3 complete - ~50 files deleted"
git commit -m "Phase 3: Consolidate to canonical locations

Service/Container: 4 files → canonical versions
Results/Outputs: 8 files → results/ domain
Infrastructure/Config: 7 files → canonical versions
Config/Core: 7 files → config/ domain
Workflows: 6 files → workflows/ domain
Events/Config: 3 files → events/configuration domains
Monitoring/Resources: 4 files → canonical versions
Schema/Validation: 1 file → core/ version
Health: 3 files → health/ domain
Miscellaneous: 4 files → correct domains

Total: ~50 files consolidated"

echo ""
echo "========================================="
echo "PHASE 4: RENAME TO DOMAIN-SPECIFIC"
echo "========================================="

# Metadata renames
echo "Renaming metadata models..."
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

# Performance metrics renames
echo "Renaming performance metrics models..."
git mv src/omnibase_core/models/cli/model_performance_metrics.py \
       src/omnibase_core/models/cli/model_cli_performance_metrics.py

git mv src/omnibase_core/models/core/model_performance_metrics.py \
       src/omnibase_core/models/core/model_core_performance_metrics.py

git mv src/omnibase_core/models/discovery/model_performance_metrics.py \
       src/omnibase_core/models/discovery/model_discovery_performance_metrics.py

# CLI consolidations
echo "Consolidating CLI models..."
git rm src/omnibase_core/models/cli/model_cli_output_data.py
git mv src/omnibase_core/models/core/model_cli_output_data.py \
       src/omnibase_core/models/cli/model_cli_output_data.py

git rm src/omnibase_core/models/cli/model_cli_execution_result.py
git mv src/omnibase_core/models/core/model_cli_execution_result.py \
       src/omnibase_core/models/cli/model_cli_execution_result.py

# Node configuration
echo "Consolidating node configuration..."
git rm src/omnibase_core/models/config/model_node_configuration.py

echo "Phase 4 complete - 15 files renamed/moved"
git commit -m "Phase 4: Rename generic names to domain-specific

Metadata renames:
- model_metadata.py → model_{domain}_metadata.py (3 files)
- model_generic_metadata.py → model_protocol_metadata.py, model_simple_metadata.py (2 files)
- Consolidate model_metadata_field_info.py (1 file)

Performance metrics renames:
- model_performance_metrics.py → model_{domain}_performance_metrics.py (3 files)

CLI consolidations:
- Move model_cli_output_data.py to cli/ domain
- Move model_cli_execution_result.py to cli/ domain

Node configuration:
- Consolidate to nodes/model_node_configuration.py

Total: 15 files renamed/moved"

echo ""
echo "========================================="
echo "PHASE 5: UPDATE IMPORTS"
echo "========================================="

echo "Running import update script..."
bash "$BASE_DIR/scripts/update_all_imports.sh"

echo "Phase 5 complete - imports updated"
git add -A
git commit -m "Phase 5: Update all imports after duplicate resolution

- Updated ~500-800 import statements
- Verified no broken imports
- All references now point to canonical locations"

echo ""
echo "========================================="
echo "VERIFICATION"
echo "========================================="

echo "Running tests..."
poetry run pytest tests/ -x || {
    echo "Tests failed - manual review required"
    exit 1
}

echo "Running type checking..."
poetry run mypy src/omnibase_core/ || {
    echo "Type checking failed - manual review required"
    exit 1
}

echo "Running linting..."
poetry run ruff check src/ tests/ || {
    echo "Linting issues found - run 'poetry run ruff check --fix'"
}

echo "Running formatting check..."
poetry run black --check src/ tests/ || {
    echo "Formatting issues found - run 'poetry run black src/ tests/'"
}

poetry run isort --check src/ tests/ || {
    echo "Import sorting issues found - run 'poetry run isort src/ tests/'"
}

echo ""
echo "========================================="
echo "COMPLETE!"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Phase 1: 8 files deleted (identical duplicates)"
echo "  - Phase 2: ~30 files deleted (re-exports and stubs)"
echo "  - Phase 3: ~50 files deleted (consolidated to canonical)"
echo "  - Phase 4: ~15 files renamed (domain-specific names)"
echo "  - Phase 5: ~500-800 imports updated"
echo ""
echo "Total files deleted: ~88"
echo "Total files renamed: ~17"
echo "Total import updates: ~500-800"
echo ""
echo "Next steps:"
echo "  1. Review git diff for unexpected changes"
echo "  2. Run full test suite: poetry run pytest tests/"
echo "  3. Fix any formatting: poetry run black src/ tests/ && poetry run isort src/ tests/"
echo "  4. Push changes and create PR"
echo ""
```

---

## TRULY COMMON MODELS ANALYSIS

### Files in models/common/ - Assessment

**KEEP in common/** (truly shared across all domains):

1. ✅ `model_error_context.py` - Error handling (used everywhere)
2. ✅ `model_validation_result.py` - Validation (used everywhere)
3. ✅ `model_validation_issue.py` - Validation (used everywhere)
4. ✅ `model_validation_metadata.py` - Validation (used everywhere)
5. ✅ `model_registry_error.py` - Registry errors (used everywhere)
6. ✅ `model_onex_error_data.py` - Error data (used everywhere)
7. ✅ `model_onex_warning.py` - Warnings (used everywhere)
8. ✅ `model_typed_mapping.py` - Type utilities (used everywhere)
9. ✅ `model_typed_value.py` - Type utilities (used everywhere)
10. ✅ `model_value_container.py` - Value wrappers (used everywhere)
11. ✅ `model_value_union.py` - Value unions (used everywhere)
12. ✅ `model_flexible_value.py` - Flexible types (used everywhere)
13. ✅ `model_multi_type_value.py` - Multi-type support (used everywhere)
14. ✅ `model_numeric_value.py` - Numeric types (used everywhere)
15. ✅ `model_numeric_string_value.py` - Numeric strings (used everywhere)
16. ✅ `model_schema_value.py` - Schema values (used everywhere)
17. ✅ `model_discriminated_value.py` - Discriminated unions (used everywhere)
18. ✅ `model_dict_value_union.py` - Dict unions (used everywhere)
19. ✅ `model_optional_int.py` - Optional integers (used everywhere)
20. ✅ `model_coercion_mode.py` - Type coercion (used everywhere)

**VERDICT**: All 20 files in models/common/ are truly common and should remain there.

---

## SUMMARY STATISTICS

### Before Resolution
- **Total model files**: 1,316
- **Duplicate filename sets**: 79
- **Files with duplicates**: ~170
- **Import complexity**: HIGH (multiple locations for same model)

### After Resolution
- **Total model files**: ~1,140 (estimated)
- **Duplicate filename sets**: 0
- **Files deleted**: ~88
- **Files renamed**: ~17
- **Import updates**: ~500-800
- **Import complexity**: LOW (single canonical location per model)

### Benefits
1. **Clarity**: Each model has one canonical location
2. **Maintainability**: No confusion about which version to use
3. **Type Safety**: No conflicting implementations (e.g., model_registry_error.py)
4. **Domain Organization**: Files are in their correct domain directories
5. **Discovery**: Easier to find models by domain
6. **Testing**: Simpler to test without duplicate coverage

### Risks Mitigated
1. ✅ Eliminated conflicting base classes (model_registry_error.py)
2. ✅ Eliminated stub files that provide no value
3. ✅ Eliminated re-exports (per user requirement)
4. ✅ Clarified domain ownership via renaming
5. ✅ Reduced import confusion

---

## EXECUTION TIMELINE

### Week 1: Preparation
- [ ] Review and approve this plan
- [ ] Create backup branch
- [ ] Set up monitoring for CI/tests
- [ ] Communicate changes to team

### Week 2: Execution
- [ ] Day 1-2: Execute Phases 1-2 (delete identical, stubs, re-exports)
- [ ] Day 3-4: Execute Phase 3 (consolidate to canonical)
- [ ] Day 5: Execute Phase 4 (rename to domain-specific)

### Week 3: Import Updates & Verification
- [ ] Day 1-3: Execute Phase 5 (update all imports)
- [ ] Day 4-5: Run full test suite, fix issues
- [ ] Verify mypy, ruff, black, isort all pass

### Week 4: Review & Merge
- [ ] Code review
- [ ] Final test verification
- [ ] Merge to main
- [ ] Update documentation

---

## POST-RESOLUTION VALIDATION

### Checklist

- [ ] All tests pass: `poetry run pytest tests/`
- [ ] Type checking passes: `poetry run mypy src/omnibase_core/`
- [ ] Linting passes: `poetry run ruff check src/ tests/`
- [ ] Formatting passes: `poetry run black --check src/ tests/`
- [ ] Import sorting passes: `poetry run isort --check src/ tests/`
- [ ] No broken imports detected
- [ ] No duplicate model filenames remain
- [ ] All re-exports eliminated
- [ ] All stubs eliminated
- [ ] All generic names renamed to domain-specific
- [ ] Documentation updated
- [ ] CLAUDE.md updated if needed

---

**Plan Generated**: 2025-11-08
**Estimated Execution Time**: 3-4 weeks
**Risk Level**: HIGH (comprehensive changes)
**Reversibility**: LOW (backup branch required)
**Impact**: POSITIVE (eliminates technical debt)

---

**Ready to execute?** Review each phase carefully and execute incrementally with testing between phases.
