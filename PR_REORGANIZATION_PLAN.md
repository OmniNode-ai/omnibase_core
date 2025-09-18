# Model Domain Reorganization Plan

## Overview

This document outlines the strategic plan to reorganize all models from the redundant `/models/core/` directory into proper domain-based subdirectories. The goal is to eliminate architectural inconsistency where a "core" subdirectory exists within a core repository.

## Problem Statement

- Current structure: `/models/core/` contains 422 files (too large for single PR)
- Issue: Having a "core" subdirectory in a core repository is architecturally redundant
- Solution: Split into 8 domain-specific PRs with ~15-50 files each

## Implementation Strategy

### Phase 1: Domain Analysis ✅ COMPLETED
- Analyzed all 422 files in `/models/core/`
- Identified domain patterns by model prefixes
- Created 8-PR breakdown strategy
- Established file move and import update methodology

### Phase 2: Execution Plan

## PR Breakdown

### PR 1: Nodes Domain ✅ COMPLETED
- **Branch**: `reorganize-models-nodes`
- **Files**: 42 models moved
- **Target**: `/models/nodes/`
- **Status**: ✅ Ready for review
- **Models**:
  - 39 `model_node_*.py` files
  - 4 `model_metadata_node_*.py` files
- **Commits**:
  - `e936ca3`: Pure file reorganization
  - `484b91e`: Import updates (37 files modified)

### PR 2: Contracts Domain 🔄 NEXT
- **Branch**: `reorganize-models-contracts`
- **Files**: ~18 models
- **Target**: `/models/contracts/`
- **Models**:
  - `model_contract_*.py`
  - `model_subcontract_*.py`
  - Contract-related validation models

### PR 3: CLI Domain
- **Branch**: `reorganize-models-cli`
- **Files**: ~13 models
- **Target**: `/models/cli/`
- **Models**:
  - `model_cli_*.py`
  - `model_argument_*.py`
  - `model_parsed_*.py`

### PR 4: Events Domain
- **Branch**: `reorganize-models-events`
- **Files**: ~12 models
- **Target**: `/models/events/`
- **Models**:
  - `model_event_*.py`
  - `model_onex_event_*.py`
  - Event handling models

### PR 5: Performance Domain
- **Branch**: `reorganize-models-performance`
- **Files**: ~10 models
- **Target**: `/models/performance/`
- **Models**:
  - `model_performance_*.py`
  - `model_execution_*.py`
  - `model_benchmark_*.py`

### PR 6: Primitives Domain
- **Branch**: `reorganize-models-primitives`
- **Files**: ~15 models
- **Target**: `/models/primitives/`
- **Models**:
  - `model_semver*.py`
  - `model_custom_*.py`
  - `model_generic_*.py`
  - Basic data types and utilities

### PR 7: Validation Domain
- **Branch**: `reorganize-models-validation`
- **Files**: ~8 models
- **Target**: `/models/validation/`
- **Models**:
  - `model_validation_*.py`
  - Validation-specific models

### PR 8: Remaining Domains
- **Branch**: `reorganize-models-remaining`
- **Files**: ~246 models (may need further splitting)
- **Target**: Multiple subdirectories based on analysis
- **Note**: This may need to be split into multiple PRs if too large

## Technical Implementation Pattern

### Established Methodology (from PR 1)

1. **Pure File Move**:
   ```bash
   git checkout -b reorganize-models-[domain]
   cd src/omnibase_core/models/core
   mkdir ../[domain]
   mv model_[pattern]*.py ../[domain]/
   ```

2. **Create Domain `__init__.py`**:
   - Comprehensive exports for all moved models
   - Organized by logical groups
   - Maintains backward compatibility

3. **Update Imports** (3 phases):
   - Self-references within moved models (relative imports)
   - Core models that reference moved models
   - Codebase-wide import updates

4. **Commit Strategy**:
   - Commit 1: Pure reorganization (`--no-verify`)
   - Commit 2: Import updates

## Quality Gates

### Pre-commit Hooks
- Files may fail pre-commit due to existing issues (not reorganization-caused)
- Use `--no-verify` for pure reorganization commits
- Import update commits should pass or identify pre-existing issues

### Validation Checklist
- [ ] All moved files properly exported in `__init__.py`
- [ ] Self-references use relative imports
- [ ] Core model imports updated
- [ ] No broken imports across codebase
- [ ] Git correctly recognizes as renames (R flag)

## Success Metrics

### PR 1 Results ✅
- ✅ 42 files successfully moved
- ✅ 37 files updated for import fixes
- ✅ Clean git history with proper renames
- ✅ All imports functional
- ✅ Zero broken references

### Expected Outcomes
- Eliminate redundant `/models/core/` structure
- Achieve proper domain-based organization
- Maintain 100% backward compatibility
- Improve code organization and discoverability
- Enable easier maintenance and development

## Risk Mitigation

### Import Dependencies
- Systematic approach to import updates
- Three-phase import fixing strategy
- Comprehensive testing after each phase

### Large PR Management
- Each PR limited to ~50 files maximum
- Domain-based logical grouping
- Independent PR workflow (can be merged separately)

### Rollback Strategy
- Each branch can be independently reverted
- Pure file moves in separate commits
- Import updates in separate commits

## Timeline

- **PR 1 (Nodes)**: ✅ COMPLETED - Ready for review
- **PR 2 (Contracts)**: Next immediate task
- **PRs 3-7**: Sequential implementation
- **PR 8 (Remaining)**: Final cleanup (may split further)

## Notes

- This reorganization addresses architectural debt
- Maintains full backward compatibility
- Improves long-term maintainability
- Follows ONEX clean architecture principles
- Each domain becomes independently manageable

---

**Current Status**: PR 1 completed successfully, ready to begin PR 2 (Contracts Domain)
**Last Updated**: 2025-01-18
**Implementation**: Following approved user strategy