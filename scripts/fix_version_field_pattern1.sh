#!/bin/bash
# ==============================================================================
# Phase 1: Pattern 1 Automation - Empty Instantiation Fixes
# ==============================================================================
#
# This script automates fixing ~30-40% of version field failures
# by using sed to replace empty model instantiations with version parameter.
#
# Pattern: ModelXxxSubcontract() → ModelXxxSubcontract(version=ModelSemVer(1, 0, 0))
#
# Usage:
#   bash scripts/fix_version_field_pattern1.sh [--dry-run] [--verbose]
#
# Safety:
#   - Backs up files before modification
#   - Use --dry-run to preview changes first
#   - Easily reversible with git
#
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$PROJECT_ROOT/tests/unit/models/contracts/subcontracts"

DRY_RUN=false
VERBOSE=false
BACKUP=true

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --no-backup)
      BACKUP=false
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run] [--verbose] [--no-backup]"
      exit 1
      ;;
  esac
done

# Models that have empty instantiation patterns
MODELS=(
  "ModelActionConfigParameter"
  "ModelAggregationFunction"
  "ModelAggregationParameter"
  "ModelAggregationPerformance"
  "ModelAggregationSubcontract"
  "ModelBaseHeaderTransformation"
  "ModelCacheDistribution"
  "ModelCacheInvalidation"
  "ModelCacheKeyStrategy"
  "ModelCachePerformance"
  "ModelCachingSubcontract"
  "ModelCircuitBreakerSubcontract"
  "ModelComponentHealth"
  "ModelComponentHealthCollection"
  "ModelComponentHealthDetail"
  "ModelConfigurationSource"
  "ModelConfigurationSubcontract"
  "ModelConfigurationValidation"
  "ModelCoordinationResult"
  "ModelCoordinationRules"
  "ModelDataGrouping"
  "ModelDependencyHealth"
  "ModelDiscoverySubcontract"
  "ModelEnvironmentValidationRule"
  "ModelEnvironmentValidationRules"
  "ModelEventBusSubcontract"
  "ModelEventDefinition"
  "ModelEventHandlingSubcontract"
  "ModelEventMappingRule"
  "ModelEventPersistence"
  "ModelEventRouting"
  "ModelEventTransformation"
  "ModelEventTypeSubcontract"
  "ModelEventrouting"
  "ModelExecutionGraph"
  "ModelFSMOperation"
  "ModelFSMStateDefinition"
  "ModelFSMStateTransition"
  "ModelFSMSubcontract"
  "ModelFSMTransitionAction"
  "ModelFsmtransitionaction"
  "ModelHeaderTransformation"
  "ModelHealthCheckSubcontract"
  "ModelHealthCheckSubcontractResult"
  "ModelIntrospectionSubcontract"
  "ModelLifecycleSubcontract"
  "ModelLoadBalancing"
  "ModelLogLevelOverride"
  "ModelLoggingSubcontract"
  "ModelMetricsSubcontract"
  "ModelNodeAssignment"
  "ModelNodeHealthStatus"
  "ModelNodeProgress"
  "ModelObservabilitySubcontract"
  "ModelProgressStatus"
  "ModelQueryParameterRule"
  "ModelRequestTransformation"
  "ModelResourceUsageMetric"
  "ModelResponseHeaderRule"
  "ModelRetrySubcontract"
  "ModelRouteDefinition"
  "ModelRoutingMetrics"
  "ModelRoutingSubcontract"
  "ModelSecuritySubcontract"
  "ModelSerializationSubcontract"
  "ModelStateManagementSubcontract"
  "ModelStatePersistence"
  "ModelStateSynchronization"
  "ModelStateValidation"
  "ModelStateVersioning"
  "ModelStatisticalComputation"
  "ModelSynchronizationPoint"
  "ModelToolExecutionSubcontract"
  "ModelValidationSchemaRule"
  "ModelValidationSubcontract"
  "ModelWindowing Strategy"
  "ModelWorkflowCoordinationSubcontract"
  "ModelWorkflowDefinition"
  "ModelWorkflowDefinitionMetadata"
  "ModelWorkflowInstance"
  "ModelWorkflowNode"
)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
  echo ""
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
}

print_success() {
  echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

# Verify test directory exists
if [ ! -d "$TEST_DIR" ]; then
  print_error "Test directory not found: $TEST_DIR"
  exit 1
fi

print_header "Phase 1: Pattern 1 Automation (Empty Instantiation)"
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN' || echo 'LIVE')"
echo "Verbose: $([ "$VERBOSE" = true ] && echo 'YES' || echo 'NO')"
echo "Test Directory: $TEST_DIR"
echo ""

# Step 1: Check for ModelSemVer import
print_header "Step 1: Checking for ModelSemVer Import"

files_need_import=0
files_checked=0

for file in "$TEST_DIR"/test_model_*.py; do
  if [ -f "$file" ]; then
    files_checked=$((files_checked + 1))

    if ! grep -q "from omnibase_core.primitives.model_semver import ModelSemVer" "$file"; then
      files_need_import=$((files_need_import + 1))

      if [ "$VERBOSE" = true ]; then
        print_warning "$(basename $file) - Missing ModelSemVer import"
      fi
    fi
  fi
done

echo "Files checked: $files_checked"
echo "Files needing import: $files_need_import"
echo ""

if [ $files_need_import -gt 0 ]; then
  print_header "Step 1b: Adding ModelSemVer Imports"

  if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: Would add ModelSemVer import to $files_need_import files"
  else
    for file in "$TEST_DIR"/test_model_*.py; do
      if [ -f "$file" ]; then
        if ! grep -q "from omnibase_core.primitives.model_semver import ModelSemVer" "$file"; then
          # Find the first import line and add ModelSemVer after omnibase_core imports
          sed -i '' '/^from omnibase_core\./a\
from omnibase_core.primitives.model_semver import ModelSemVer
' "$file" 2>/dev/null || true

          [ "$VERBOSE" = true ] && print_success "Added import to $(basename $file)"
        fi
      fi
    done
    echo "Imports added successfully"
  fi
  echo ""
fi

# Step 2: Apply sed replacements
print_header "Step 2: Applying sed Replacements for Empty Instantiations"

total_fixes=0
files_modified=0

for model in "${MODELS[@]}"; do
  # Find test file for this model
  # Convert ModelActionConfigParameter → test_model_action_config_parameter.py
  test_name=$(echo "$model" | sed 's/Model//g' | \
    sed 's/\([A-Z]\)/_\L\1/g' | sed 's/^_//' | tr '[A-Z]' '[a-z]')
  test_file="$TEST_DIR/test_model_${test_name}.py"

  if [ -f "$test_file" ]; then
    # Count instances before
    before=$(grep -c "${model}()" "$test_file" 2>/dev/null || echo "0")

    if [ "$before" -gt 0 ]; then
      if [ "$DRY_RUN" = true ]; then
        # Show what would be changed
        echo ""
        echo "Would fix in: $(basename $test_file)"
        echo "Instances: $before"
        if [ "$VERBOSE" = true ]; then
          echo "Preview:"
          sed "s/${model}()/${model}(version=ModelSemVer(1, 0, 0))/g" "$test_file" | \
            grep "${model}" | head -3
        fi
      else
        # Backup file if requested
        if [ "$BACKUP" = true ]; then
          cp "$test_file" "${test_file}.bak"
        fi

        # Apply replacement
        sed -i '' "s/${model}()/${model}(version=ModelSemVer(1, 0, 0))/g" "$test_file"

        # Count after
        after=$(grep -c "${model}()" "$test_file" 2>/dev/null || echo "0")

        files_modified=$((files_modified + 1))
        fixed=$((before - after))
        total_fixes=$((total_fixes + fixed))

        print_success "$(basename $test_file): Fixed $fixed instances"
      fi
    fi
  fi
done

echo ""
print_header "Step 2 Summary"
echo "Files modified: $files_modified"
echo "Total fixes applied: $total_fixes"
echo ""

# Step 3: Verification
print_header "Step 3: Verification"

if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN: Skipping verification (would run tests in live mode)"
else
  echo "Running quick test verification..."

  # Try to run a sample test to verify syntax
  sample_test="$TEST_DIR/test_model_routing_subcontract.py"
  if [ -f "$sample_test" ]; then
    echo "Verifying Python syntax..."
    if python -m py_compile "$sample_test" 2>/dev/null; then
      print_success "Syntax verification passed"
    else
      print_error "Syntax verification failed - manual review needed"
      echo "Run: python -m py_compile $TEST_DIR/test_model_*.py"
      exit 1
    fi
  fi
fi

echo ""
print_header "Phase 1 Complete"
echo ""
echo "Next Steps:"
echo "1. Review changes (if needed)"
echo "2. Run tests: poetry run pytest tests/unit/models/contracts/subcontracts/ -x"
echo "3. If issues found, rollback: git checkout tests/unit/models/contracts/subcontracts/"
echo "4. Proceed to Phase 2: python scripts/fix_version_field_pattern2.py"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo -e "${YELLOW}DRY RUN MODE: No files were actually modified${NC}"
  echo "To apply changes, run: bash scripts/fix_version_field_pattern1.sh"
  echo ""
fi
