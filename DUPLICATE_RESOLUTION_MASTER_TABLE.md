# DUPLICATE MODELS RESOLUTION - MASTER TABLE

**Generated**: 2025-11-08
**All 79 Duplicate Sets - Action Plan**

---

## LEGEND

- **DELETE**: Remove file (stub, re-export, or superseded)
- **KEEP**: Canonical version to retain
- **RENAME**: Change filename to domain-specific name
- **MOVE**: Relocate to correct domain directory

---

## TABLE OF ALL 79 DUPLICATE SETS

| # | Filename | Copies | Action | Keep/Rename To | Delete Locations | Phase |
|---|----------|--------|--------|----------------|------------------|-------|
| 1 | model_config.py | 5 | DELETE ALL | N/A - stubs only | core/, events/, operations/, security/, workflows/ | 1 |
| 2 | model_metadata_validation_config.py | 2 | CONSOLIDATE | config/ | core/ | 1 |
| 3 | model_tree_generator_config.py | 2 | CONSOLIDATE | config/ | core/ | 1 |
| 4 | model_unified_version.py | 2 | CONSOLIDATE | results/ | core/ | 1 |
| 5 | model_error_context.py | 2 | DELETE RE-EXPORT | common/ (canonical) | core/ (re-export) | 2 |
| 6 | model_validation_issue.py | 2 | DELETE STUB | common/ (canonical) | core/ (stub) | 2 |
| 7 | model_action.py | 4 | CONSOLIDATE + RENAME | orchestrator/ (canonical) + infrastructure/model_protocol_action.py (rename) | core/ (stub), models/ (dup) | 2 |
| 8 | model_validation_result.py | 5 | CONSOLIDATE + RENAME | common/ (canonical) + models/model_import_validation_result.py (rename) | core/, security/, validation/ | 2 |
| 9 | model_registry_error.py | 2 | DELETE CONFLICT | common/ (extends ModelOnexError) | core/ (extends ModelOnexWarning) | 2 |
| 10 | model_cli_action.py | 2 | CONSOLIDATE | cli/ | core/ | 2 |
| 11 | model_cli_execution.py | 2 | CONSOLIDATE | cli/ | core/ | 2 |
| 12 | model_cli_execution_metadata.py | 2 | CONSOLIDATE | cli/ | core/ | 2 |
| 13 | model_cli_result.py | 2 | CONSOLIDATE | cli/ | core/ | 2 |
| 14 | model_connection_info.py | 2 | CONSOLIDATE | connections/ | core/ | 2 |
| 15 | model_connection_metrics.py | 2 | CONSOLIDATE | connections/ | core/ | 2 |
| 16 | model_custom_connection_properties.py | 2 | CONSOLIDATE | connections/ | core/ | 2 |
| 17 | model_node_capability.py | 2 | CONSOLIDATE | nodes/ | core/ | 2 |
| 18 | model_node_information.py | 2 | CONSOLIDATE | nodes/ | core/ | 2 |
| 19 | model_node_metadata_info.py | 2 | CONSOLIDATE | nodes/ | core/ | 2 |
| 20 | model_node_type.py | 2 | CONSOLIDATE | nodes/ | core/ | 2 |
| 21 | model_health_check.py | 2 | CONSOLIDATE | health/ | core/ | 2 |
| 22 | model_health_status.py | 2 | CONSOLIDATE | health/ | core/ | 2 |
| 23 | model_data_handling_declaration.py | 2 | CONSOLIDATE | config/ | core/ | 2 |
| 24 | model_environment_properties.py | 2 | CONSOLIDATE | config/ | core/ | 2 |
| 25 | model_contract_data.py | 2 | CONSOLIDATE | utils/ | core/ | 2 |
| 26 | model_custom_fields.py | 2 | CONSOLIDATE | service/ | core/ | 2 |
| 27 | model_execution_metadata.py | 2 | CONSOLIDATE | operations/ | core/ | 2 |
| 28 | model_service.py | 2 | CONSOLIDATE | container/ | core/ | 3 |
| 29 | model_service_registration.py | 2 | CONSOLIDATE | container/ | core/ | 3 |
| 30 | model_security_config.py | 2 | CONSOLIDATE | config/ | service/ | 3 |
| 31 | model_external_service_config.py | 2 | CONSOLIDATE | service/ | contracts/ | 3 |
| 32 | model_onex_result.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 33 | model_onex_message.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 34 | model_onex_message_context.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 35 | model_orchestrator_metrics.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 36 | model_orchestrator_info.py | 2 | CONSOLIDATE | core/ | results/ | 3 |
| 37 | model_orchestrator_output.py | 2 | CONSOLIDATE | service/ | models/ | 3 |
| 38 | model_unified_summary.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 39 | model_unified_summary_details.py | 2 | CONSOLIDATE | results/ | core/ | 3 |
| 40 | model_duration.py | 2 | CONSOLIDATE | infrastructure/ | core/ | 3 |
| 41 | model_state.py | 2 | CONSOLIDATE | infrastructure/ | core/ | 3 |
| 42 | model_circuit_breaker.py | 3 | CONSOLIDATE | configuration/ (most complete) | infrastructure/, contracts/subcontracts/ | 3 |
| 43 | model_retry_config.py | 2 | CONSOLIDATE | core/ (more complete) | infrastructure/ | 3 |
| 44 | model_retry_policy.py | 2 | CONSOLIDATE | infrastructure/ (more complete) | configuration/ | 3 |
| 45 | model_action_payload.py | 2 | CONSOLIDATE | core/ | infrastructure/ | 3 |
| 46 | model_namespace_config.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 47 | model_uri.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 48 | model_example.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 49 | model_example_metadata.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 50 | model_examples_collection.py | 2 | CONSOLIDATE | core/ (more complete) | config/ | 3 |
| 51 | model_fallback_metadata.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 52 | model_fallback_strategy.py | 2 | CONSOLIDATE | config/ | core/ | 3 |
| 53 | model_workflow_configuration.py | 2 | CONSOLIDATE | configuration/ | operations/ | 3 |
| 54 | model_workflow_execution_result.py | 2 | CONSOLIDATE | workflows/ | service/ | 3 |
| 55 | model_workflow_metrics.py | 2 | CONSOLIDATE | core/ | contracts/subcontracts/ | 3 |
| 56 | model_workflow_parameters.py | 2 | CONSOLIDATE | operations/ (most complete) | service/ | 3 |
| 57 | model_workflow_step.py | 2 | CONSOLIDATE | contracts/ | models/ | 3 |
| 58 | model_dependency_graph.py | 2 | CONSOLIDATE | workflows/ | models/ | 3 |
| 59 | model_event_envelope.py | 2 | CONSOLIDATE | events/ (most complete) | core/ | 3 |
| 60 | model_event_bus_config.py | 2 | CONSOLIDATE | configuration/ | service/ | 3 |
| 61 | model_event_descriptor.py | 2 | CONSOLIDATE | discovery/ (most complete) | contracts/ | 3 |
| 62 | model_monitoring_config.py | 2 | CONSOLIDATE | configuration/ | service/ | 3 |
| 63 | model_resource_allocation.py | 2 | CONSOLIDATE | configuration/ | core/ | 3 |
| 64 | model_resource_limits.py | 2 | CONSOLIDATE | configuration/ | service/ | 3 |
| 65 | model_metric_value.py | 2 | CONSOLIDATE | discovery/ | core/ | 3 |
| 66 | model_schema.py | 2 | CONSOLIDATE | core/ (most complete) | validation/ | 3 |
| 67 | model_health_check_config.py | 3 | CONSOLIDATE | health/ (most complete) | configuration/, service/ | 3 |
| 68 | model_health_check_result.py | 2 | CONSOLIDATE | core/ | contracts/subcontracts/ | 3 |
| 69 | model_condition_value.py | 2 | CONSOLIDATE | security/ | contracts/ | 3 |
| 70 | model_security_context.py | 2 | CONSOLIDATE | security/ | core/ | 3 |
| 71 | model_trust_level.py | 2 | CONSOLIDATE | core/ (more complete) | security/ | 3 |
| 72 | model_node_info.py | 2 | CONSOLIDATE | core/ | nodes/ (stub) | 3 |
| 73 | model_metadata.py | 3 | RENAME ALL | configuration/model_configuration_metadata.py, core/model_core_metadata.py, security/model_security_metadata.py | N/A - renamed | 4 |
| 74 | model_generic_metadata.py | 3 | RENAME NON-CANONICAL | metadata/ (keep canonical), core/model_protocol_metadata.py, results/model_simple_metadata.py | N/A - renamed | 4 |
| 75 | model_metadata_field_info.py | 2 | CONSOLIDATE | metadata/ | core/ | 4 |
| 76 | model_performance_metrics.py | 3 | RENAME ALL | cli/model_cli_performance_metrics.py, core/model_core_performance_metrics.py, discovery/model_discovery_performance_metrics.py | N/A - renamed | 4 |
| 77 | model_cli_output_data.py | 2 | MOVE + DELETE | cli/ (moved from core/) | cli/ (old stub) | 4 |
| 78 | model_cli_execution_result.py | 2 | MOVE + DELETE | cli/ (moved from core/) | cli/ (old stub) | 4 |
| 79 | model_node_configuration.py | 3 | CONSOLIDATE | nodes/ (most complete) | core/ (Phase 2), config/ (Phase 4) | 2, 4 |

---

## SUMMARY BY ACTION TYPE

### DELETE (Stubs, Re-exports, Superseded)
**Total files deleted**: ~88

| Category | Count |
|----------|-------|
| Stubs (empty/minimal) | ~35 |
| Re-exports (import-only) | ~5 |
| Superseded by canonical | ~48 |

### RENAME (Domain-Specific)
**Total files renamed**: ~12

| Original Name | New Name | Reason |
|---------------|----------|--------|
| model_metadata.py (configuration/) | model_configuration_metadata.py | Domain specificity |
| model_metadata.py (core/) | model_core_metadata.py | Domain specificity |
| model_metadata.py (security/) | model_security_metadata.py | Domain specificity |
| model_generic_metadata.py (core/) | model_protocol_metadata.py | Clarify purpose |
| model_generic_metadata.py (results/) | model_simple_metadata.py | Clarify purpose |
| model_performance_metrics.py (cli/) | model_cli_performance_metrics.py | Domain specificity |
| model_performance_metrics.py (core/) | model_core_performance_metrics.py | Domain specificity |
| model_performance_metrics.py (discovery/) | model_discovery_performance_metrics.py | Domain specificity |
| model_action.py (infrastructure/) | model_protocol_action.py | Clarify purpose (protocol vs orchestrator) |
| model_validation_result.py (models/) | model_import_validation_result.py | Clarify purpose (import validation) |

### KEEP (Canonical Versions)
**Files to keep**: ~90 canonical locations

---

## PHASE BREAKDOWN

### Phase 1: Identical Duplicates (4 sets, 8 files deleted)
- model_config.py (5 → 0)
- model_metadata_validation_config.py (2 → 1)
- model_tree_generator_config.py (2 → 1)
- model_unified_version.py (2 → 1)

### Phase 2: Re-exports and Stubs (27 sets, ~30 files deleted)
- Delete re-exports: 2 files
- Delete stubs: ~28 files
- Rename: 2 files

### Phase 3: Consolidate to Canonical (45 sets, ~50 files deleted)
- Service/Container: 4 files
- Results/Outputs: 8 files
- Infrastructure/Config: 7 files
- Config/Core: 7 files
- Workflows: 6 files
- Events/Config: 3 files
- Monitoring/Resources: 4 files
- Schema/Validation: 1 file
- Health: 3 files
- Miscellaneous: 4 files

### Phase 4: Rename to Domain-Specific (5 sets, 15 files affected)
- Metadata renames: 6 files
- Performance metrics renames: 3 files
- CLI consolidations: 4 files
- Node configuration: 2 files

### Phase 5: Update Imports (~500-800 files)
- Automated via scripts/update_all_imports.sh

---

## CRITICAL DUPLICATES (Top 5)

### 1. model_validation_result.py (5 copies) ⚠️ **HIGHEST PRIORITY**
- **Problem**: 5 completely different implementations
- **Resolution**: Keep common/ (canonical), rename models/ to model_import_validation_result.py, delete 3 others
- **Impact**: Eliminates confusion, single source of truth

### 2. model_registry_error.py (2 copies) ⚠️ **CONFLICTING BASE CLASSES**
- **Problem**: Same name, different base classes (ModelOnexWarning vs ModelOnexError)
- **Resolution**: Delete core/ (wrong base class), keep common/
- **Impact**: Prevents type confusion bugs

### 3. model_action.py (4 copies) ⚠️ **DIFFERENT PURPOSES**
- **Problem**: 4 versions (orchestrator, infrastructure, stub, duplicate)
- **Resolution**: Keep orchestrator/, rename infrastructure/ to model_protocol_action.py, delete 2 others
- **Impact**: Clear separation of concerns

### 4. model_metadata.py (3 copies) ⚠️ **GENERIC NAME**
- **Problem**: Same name in 3 domains (configuration, core, security)
- **Resolution**: Rename all to model_{domain}_metadata.py
- **Impact**: Domain-specific clarity

### 5. model_generic_metadata.py (3 copies) ⚠️ **GENERIC NAME**
- **Problem**: Generic name used in multiple contexts
- **Resolution**: Keep metadata/ (canonical), rename core/ to model_protocol_metadata.py, results/ to model_simple_metadata.py
- **Impact**: Purpose clarity

---

## VERIFICATION CHECKLIST

After execution:

- [ ] **File counts**:
  - Total model files: ~1,140 (was 1,316)
  - Files deleted: ~88
  - Files renamed: ~12
  - Duplicate sets remaining: 0

- [ ] **Import validation**:
  - No broken imports
  - All imports use canonical locations
  - No re-exports remain

- [ ] **Testing**:
  - All 12,000+ tests pass
  - Zero mypy errors
  - Ruff/black/isort clean

- [ ] **Documentation**:
  - CLAUDE.md updated if needed
  - No references to deleted files

---

## QUICK EXECUTION

```bash
# One command to execute all phases
bash scripts/execute_duplicate_resolution.sh
```

**Estimated runtime**: 15-30 minutes

---

**Generated**: 2025-11-08
**Total Duplicate Sets**: 79
**Files to Delete**: ~88
**Files to Rename**: ~12
**Import Updates**: ~500-800
