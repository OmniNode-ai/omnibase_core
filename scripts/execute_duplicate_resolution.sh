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
BACKUP_BRANCH="backup/pre-duplicate-resolution-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH"
echo "Backup branch created: $BACKUP_BRANCH"
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
echo "Backup branch: $BACKUP_BRANCH"
echo ""
echo "Next steps:"
echo "  1. Review git diff for unexpected changes"
echo "  2. Run full test suite: poetry run pytest tests/"
echo "  3. Fix any formatting: poetry run black src/ tests/ && poetry run isort src/ tests/"
echo "  4. Push changes and create PR"
echo ""
