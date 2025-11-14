#!/bin/bash
# Import update script for duplicate model resolution
# Generated: 2025-11-08
# Updates all imports to reference canonical model locations
#
# Usage: ./scripts/update_all_imports.sh [BASE_DIR]
#   BASE_DIR: Path to omnibase_core repository (default: current directory)
#
# Safety:
#   - Creates .bak backup files before modifying each file
#   - Use rollback command below to restore if needed
#
# Rollback (restore from .bak backups):
#   find . -name "*.py.bak" -exec sh -c 'mv "$1" "${1%.bak}"' _ {} \;
#
# Cleanup backups after verification:
#   find . -name "*.py.bak" -delete
#

set -e  # Exit on error

# Accept BASE_DIR as parameter, default to current directory
BASE_DIR="${1:-.}"

# Validate directory exists
if [[ ! -d "$BASE_DIR" ]]; then
  echo "Error: Directory $BASE_DIR does not exist"
  exit 1
fi

# Convert to absolute path for consistency
BASE_DIR="$(cd "$BASE_DIR" && pwd)"

echo "========================================="
echo "IMPORT UPDATE SCRIPT"
echo "========================================="
echo "Updating all imports to canonical locations..."

# ============================================
# PHASE 1: IDENTICAL DUPLICATES
# ============================================

echo ""
echo "Phase 1: Updating imports for identical duplicates..."

# model_config.py - DELETED ALL, remove any imports
# (These were just stubs, no actual imports should exist)

# model_metadata_validation_config.py: core/ → config/
echo "  - model_metadata_validation_config.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_metadata_validation_config import|from omnibase_core.models.examples.model_metadata_validation_config import|g' {} \;

# model_tree_generator_config.py: core/ → config/
echo "  - model_tree_generator_config.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_tree_generator_config import|from omnibase_core.models.examples.model_tree_generator_config import|g' {} \;

# model_unified_version.py: core/ → results/
echo "  - model_unified_version.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_unified_version import|from omnibase_core.models.results.model_unified_version import|g' {} \;

# ============================================
# PHASE 2: RE-EXPORTS AND STUBS
# ============================================

echo ""
echo "Phase 2: Updating imports for re-exports and stubs..."

# model_error_context.py: core/ → common/ (delete re-export)
echo "  - model_error_context.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_error_context import|from omnibase_core.models.common.model_error_context import|g' {} \;

# model_validation_issue.py: core/ → common/
echo "  - model_validation_issue.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_validation_issue import|from omnibase_core.models.common.model_validation_issue import|g' {} \;

# model_action.py: consolidate to orchestrator/, rename infrastructure/
echo "  - model_action.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_action import|from omnibase_core.models.orchestrator.model_action import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.model_action import|from omnibase_core.models.orchestrator.model_action import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.infrastructure\.model_action import|from omnibase_core.models.infrastructure.model_protocol_action import|g' {} \;

# model_validation_result.py: consolidate to common/, rename import version
echo "  - model_validation_result.py (CRITICAL)"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.security\.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.validation\.model_validation_result import|from omnibase_core.models.common.model_validation_result import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.model_validation_result import|from omnibase_core.models.model_import_validation_result import|g' {} \;

# model_registry_error.py: core/ → common/
echo "  - model_registry_error.py"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_registry_error import|from omnibase_core.models.common.model_registry_error import|g' {} \;

# CLI stubs: core/ → cli/
echo "  - CLI models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_action import|from omnibase_core.models.cli.model_cli_action import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_execution import|from omnibase_core.models.cli.model_cli_execution import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_execution_metadata import|from omnibase_core.models.cli.model_cli_execution_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_result import|from omnibase_core.models.cli.model_cli_result import|g' {} \;

# Connection stubs: core/ → connections/
echo "  - Connection models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_connection_info import|from omnibase_core.models.connections.model_connection_info import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_connection_metrics import|from omnibase_core.models.connections.model_connection_metrics import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_custom_connection_properties import|from omnibase_core.models.connections.model_custom_connection_properties import|g' {} \;

# Node stubs: core/ → nodes/
echo "  - Node models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_node_capability import|from omnibase_core.models.nodes.model_node_capability import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_node_configuration import|from omnibase_core.models.nodes.model_node_configuration import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_node_information import|from omnibase_core.models.nodes.model_node_information import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_node_metadata_info import|from omnibase_core.models.nodes.model_node_metadata_info import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_node_type import|from omnibase_core.models.nodes.model_node_type import|g' {} \;

# Health stubs: core/ → health/
echo "  - Health models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_health_check import|from omnibase_core.models.health.model_health_check import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_health_status import|from omnibase_core.models.health.model_health_status import|g' {} \;

# Misc stubs
echo "  - Miscellaneous models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_data_handling_declaration import|from omnibase_core.models.examples.model_data_handling_declaration import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_environment_properties import|from omnibase_core.models.examples.model_environment_properties import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_contract_data import|from omnibase_core.models.utils.model_contract_data import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_custom_fields import|from omnibase_core.models.service.model_custom_fields import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_execution_metadata import|from omnibase_core.models.operations.model_execution_metadata import|g' {} \;

# ============================================
# PHASE 3: CONSOLIDATE TO CANONICAL
# ============================================

echo ""
echo "Phase 3: Updating imports for canonical consolidations..."

# Service/Container
echo "  - Service/Container models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_service import|from omnibase_core.models.container.model_service import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_service_registration import|from omnibase_core.models.container.model_service_registration import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_security_config import|from omnibase_core.models.examples.model_security_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.model_external_service_config import|from omnibase_core.models.service.model_external_service_config import|g' {} \;

# Results/Outputs
echo "  - Results/Outputs models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_onex_result import|from omnibase_core.models.results.model_onex_result import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_onex_message import|from omnibase_core.models.results.model_onex_message import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_onex_message_context import|from omnibase_core.models.results.model_onex_message_context import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_orchestrator_metrics import|from omnibase_core.models.results.model_orchestrator_metrics import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.results\.model_orchestrator_info import|from omnibase_core.models.core.model_orchestrator_info import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.model_orchestrator_output import|from omnibase_core.models.service.model_orchestrator_output import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_unified_summary import|from omnibase_core.models.results.model_unified_summary import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_unified_summary_details import|from omnibase_core.models.results.model_unified_summary_details import|g' {} \;

# Infrastructure/Config
echo "  - Infrastructure/Config models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_duration import|from omnibase_core.models.infrastructure.model_duration import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_state import|from omnibase_core.models.infrastructure.model_state import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.infrastructure\.model_circuit_breaker import|from omnibase_core.models.configuration.model_circuit_breaker import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.subcontracts\.model_circuit_breaker import|from omnibase_core.models.configuration.model_circuit_breaker import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.infrastructure\.model_retry_config import|from omnibase_core.models.core.model_retry_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.configuration\.model_retry_policy import|from omnibase_core.models.infrastructure.model_retry_policy import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.infrastructure\.model_action_payload import|from omnibase_core.models.core.model_action_payload import|g' {} \;

# Config/Core
echo "  - Config/Core models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_namespace_config import|from omnibase_core.models.examples.model_namespace_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_uri import|from omnibase_core.models.examples.model_uri import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_example import|from omnibase_core.models.examples.model_example import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_example_metadata import|from omnibase_core.models.examples.model_example_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.config\.model_examples_collection import|from omnibase_core.models.core.model_examples_collection import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_fallback_metadata import|from omnibase_core.models.examples.model_fallback_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_fallback_strategy import|from omnibase_core.models.examples.model_fallback_strategy import|g' {} \;

# Workflows
echo "  - Workflow models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.operations\.model_workflow_configuration import|from omnibase_core.models.configuration.model_workflow_configuration import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_workflow_execution_result import|from omnibase_core.models.workflow.execution.model_workflow_execution_result import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.subcontracts\.model_workflow_metrics import|from omnibase_core.models.core.model_workflow_metrics import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_workflow_parameters import|from omnibase_core.models.operations.model_workflow_parameters import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.model_workflow_step import|from omnibase_core.models.contracts.model_workflow_step import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.model_dependency_graph import|from omnibase_core.models.workflow.execution.model_dependency_graph import|g' {} \;

# Events/Config
echo "  - Event/Config models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_event_envelope import|from omnibase_core.models.events.model_event_envelope import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_event_bus_config import|from omnibase_core.models.configuration.model_event_bus_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.model_event_descriptor import|from omnibase_core.models.discovery.model_event_descriptor import|g' {} \;

# Monitoring/Resources
echo "  - Monitoring/Resource models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_monitoring_config import|from omnibase_core.models.configuration.model_monitoring_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_resource_allocation import|from omnibase_core.models.configuration.model_resource_allocation import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_resource_limits import|from omnibase_core.models.configuration.model_resource_limits import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_metric_value import|from omnibase_core.models.discovery.model_metric_value import|g' {} \;

# Schema/Validation
echo "  - Schema/Validation models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.validation\.model_schema import|from omnibase_core.models.core.model_schema import|g' {} \;

# Health
echo "  - Health models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.configuration\.model_health_check_config import|from omnibase_core.models.health.model_health_check_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.service\.model_health_check_config import|from omnibase_core.models.health.model_health_check_config import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.subcontracts\.model_health_check_result import|from omnibase_core.models.core.model_health_check_result import|g' {} \;

# Miscellaneous
echo "  - Miscellaneous models"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.contracts\.model_condition_value import|from omnibase_core.models.security.model_condition_value import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_security_context import|from omnibase_core.models.security.model_security_context import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.security\.model_trust_level import|from omnibase_core.models.core.model_trust_level import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.nodes\.model_node_info import|from omnibase_core.models.core.model_node_info import|g' {} \;

# ============================================
# PHASE 4: DOMAIN-SPECIFIC RENAMES
# ============================================

echo ""
echo "Phase 4: Updating imports for domain-specific renames..."

# Metadata renames
echo "  - Metadata renames"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.configuration\.model_metadata import|from omnibase_core.models.configuration.model_configuration_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_metadata import|from omnibase_core.models.core.model_core_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.security\.model_metadata import|from omnibase_core.models.security.model_security_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_generic_metadata import|from omnibase_core.models.core.model_protocol_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.results\.model_generic_metadata import|from omnibase_core.models.results.model_simple_metadata import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_metadata_field_info import|from omnibase_core.models.metadata.model_metadata_field_info import|g' {} \;

# Performance metrics renames
echo "  - Performance metrics renames"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.cli\.model_performance_metrics import|from omnibase_core.models.cli.model_cli_performance_metrics import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_performance_metrics import|from omnibase_core.models.core.model_core_performance_metrics import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.discovery\.model_performance_metrics import|from omnibase_core.models.discovery.model_discovery_performance_metrics import|g' {} \;

# CLI consolidations (already handled in Phase 3 but ensure correct location)
echo "  - CLI consolidations"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_output_data import|from omnibase_core.models.cli.model_cli_output_data import|g' {} \;
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.core\.model_cli_execution_result import|from omnibase_core.models.cli.model_cli_execution_result import|g' {} \;

# Node configuration
echo "  - Node configuration"
find "$BASE_DIR" -name "*.py" -type f -exec sed -i.bak \
  's|from omnibase_core\.models\.config\.model_node_configuration import|from omnibase_core.models.nodes.model_node_configuration import|g' {} \;

echo ""
echo "========================================="
echo "IMPORT UPDATES COMPLETE!"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Phase 1: Identical duplicates updated"
echo "  - Phase 2: Re-exports and stubs updated"
echo "  - Phase 3: Canonical consolidations updated"
echo "  - Phase 4: Domain-specific renames updated"
echo ""
echo "Backup files (.bak) created for all modified files"
echo ""
echo "Next steps:"
echo "  1. Verify no broken imports with:"
echo "     poetry run python -m py_compile src/omnibase_core/**/*.py"
echo ""
echo "  2. If verification succeeds, cleanup backups:"
echo "     find . -name \"*.py.bak\" -delete"
echo ""
echo "  3. If rollback needed:"
echo "     find . -name \"*.py.bak\" -exec sh -c 'mv \"\$1\" \"\${1%.bak}\"' _ {} \\;"
echo ""
