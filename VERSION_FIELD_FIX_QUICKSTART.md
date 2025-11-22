# Version Field Fix - Quick Start Guide

**Status**: Ready-to-execute automation strategy
**Total Failures**: ~796 tests
**Estimated Time**: 2-3 hours with automation
**Risk Level**: LOW (80% of fixes are straightforward)

---

## Overview

The `version` field is now required in all subcontract models. This guide provides quick commands to fix ~796 test failures using automation.

### Failure Distribution

| Category | Failures | Strategy |
|----------|----------|----------|
| **Pattern 1** (empty instantiation) | ~240 (30%) | bash sed script |
| **Pattern 2** (with args) | ~320 (40%) | Python AST script |
| **Pattern 3** (manual) | ~160 (20%) | Manual review |
| **Other** (FSM, workflow) | ~76 (10%) | Manual fixes |

---

## Quick Start (5 minutes)

### 1. Backup Your Work

```bash
# Create backup branch (MANDATORY)
git checkout -b chore/fix-version-field-backup
git checkout chore/validation

# Or just ensure branch is clean
git status  # Should show "clean" working directory
```

### 2. Preview Changes (Dry Run)

```bash
# Pattern 1: See what sed will do
bash scripts/fix_version_field_pattern1.sh --dry-run -v

# Pattern 2: See what AST script will do
poetry run python scripts/fix_version_field_pattern2.py --dry-run -v
```

### 3. Apply Automation (One-liner)

```bash
# Apply both patterns
bash scripts/fix_version_field_pattern1.sh && \
poetry run python scripts/fix_version_field_pattern2.py && \
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -q
```

### 4. Check Results

```bash
# See how many failures remain
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=line -q 2>&1 | tail -5

# Find remaining failures by model
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -v 2>&1 | \
  grep "FAILED" | sed 's/.*FAILED //' | awk '{print $1}' | \
  sed 's/::.*//' | sort | uniq -c | sort -rn | head -20
```

---

## Detailed Workflow (30 minutes)

### Step 1: Prepare Environment (5 min)

```bash
# Verify we're on the right branch
git branch | grep "chore/validation"

# Ensure working directory is clean
git status

# Check test directory structure
ls tests/unit/models/contracts/subcontracts/test_model_*.py | wc -l
# Should show 27+ test files

# Verify imports work
poetry run python -c "from omnibase_core.primitives.model_semver import ModelSemVer; print('OK')"
```

### Step 2: Run Pattern 1 - sed Automation (10 min)

**Safe command** - Simple string replacement for empty instantiations

```bash
# Preview only (no changes)
bash scripts/fix_version_field_pattern1.sh --dry-run --verbose | head -50

# Check for issues
echo "Exit code: $?"

# Apply changes
bash scripts/fix_version_field_pattern1.sh --verbose

# Verify changes applied
git diff tests/unit/models/contracts/subcontracts/ | head -100
```

### Step 3: Run Pattern 2 - Python AST Script (10 min)

**Medium complexity** - Safe AST-based fix for complex cases

```bash
# Preview
poetry run python scripts/fix_version_field_pattern2.py --dry-run -v | head -50

# Apply
poetry run python scripts/fix_version_field_pattern2.py -v

# Verify
git diff tests/unit/models/contracts/subcontracts/ | head -100
```

### Step 4: Verify Syntax (5 min)

```bash
# Check Python syntax in all modified files
poetry run python -m py_compile tests/unit/models/contracts/subcontracts/test_model_*.py

# Quick test of one file
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_routing_subcontract.py -x --tb=short
```

### Step 5: Check Remaining Failures (5 min)

```bash
# Find remaining failures
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -q 2>&1 | tail -3

# See which models still have issues
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=line -v 2>&1 | \
  grep "FAILED" | head -20
```

---

## Pattern 1: Empty Instantiation (sed)

**Best for**: `ModelRoutingSubcontract()` → `ModelRoutingSubcontract(version=ModelSemVer(1, 0, 0))`

### Command

```bash
bash scripts/fix_version_field_pattern1.sh [--dry-run] [--verbose]
```

### Options

| Option | Purpose |
|--------|---------|
| `--dry-run` | Preview changes without modifying files |
| `--verbose` | Show detailed output |
| `--no-backup` | Skip backup files (not recommended) |

### Example Output

```
===================================================================
Phase 1: Pattern 1 Automation (Empty Instantiation)
===================================================================
Mode: LIVE
Verbose: YES
Test Directory: tests/unit/models/contracts/subcontracts

✓ test_model_routing_subcontract.py: Fixed 12 instances
✓ test_model_event_type_subcontract.py: Fixed 8 instances
✓ test_model_aggregation_subcontract.py: Fixed 15 instances
...

===================================================================
Phase 1 Summary
===================================================================
Files modified: 15
Total fixes applied: 240

Next Steps:
1. Run tests: poetry run pytest tests/unit/models/contracts/subcontracts/ -x
```

---

## Pattern 2: Complex Cases (Python AST)

**Best for**: `ModelEventMappingRule(source="x", target="y")` → `ModelEventMappingRule(source="x", target="y", version=ModelSemVer(1, 0, 0))`

### Command

```bash
poetry run python scripts/fix_version_field_pattern2.py [--dry-run] [-v]
```

### Options

| Option | Purpose |
|--------|---------|
| `--dry-run` | Preview changes without modifying files |
| `-v` / `--verbose` | Show detailed output and diffs |

### Example Output

```
================================================================================
Phase 2: Pattern 2 Automation (Complex Case Fixes)
================================================================================
Mode: LIVE
Verbose: YES
Test files: 27

✓ FIXED: test_model_action_config_parameter.py (71 calls updated)
✓ FIXED: test_model_event_mapping_rule.py (70 calls updated)
✓ FIXED: test_model_logging_subcontract.py (53 calls updated)
✓ FIXED: test_model_environment_validation_rule.py (49 calls updated)
...

================================================================================
Phase 2 Summary
================================================================================
Files modified: 25
Total fixes applied: 320

Next Steps:
1. Run tests: poetry run pytest tests/unit/models/contracts/subcontracts/ -x
```

---

## Pattern 3: Manual Fixes

**For**: Fixtures, factories, FSM executor logic (~160 failures, ~20 minutes)

### Location of Remaining Failures

```bash
# Show which files still have failures
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=line -v 2>&1 | \
  grep "FAILED" | awk '{print $1}' | sed 's/::.*//' | sort | uniq -c | sort -rn

# Expected output:
#    13 FAILED tests/unit/models/contracts/subcontracts/test_mixin_fsm_execution.py
#    11 FAILED tests/unit/models/contracts/subcontracts/test_fsm_executor.py
#     8 FAILED tests/unit/models/workflow/test_declarative_nodes.py
#     ...
```

### How to Fix Manually

1. **Find the failing test**
   ```bash
   poetry run pytest tests/unit/models/contracts/subcontracts/test_mixin_fsm_execution.py::TestXxx::test_xxx -xvs
   ```

2. **Look for pattern in error**
   ```
   pydantic_core._pydantic_core.ValidationError: 1 validation error for ModelFSMStateDefinition
   version
     Field required [type=missing, input_value={...}]
   ```

3. **Add version parameter**
   ```python
   # Example fixture
   @pytest.fixture
   def sample_state():
       return ModelFSMStateDefinition(
           state_name="idle",
           state_type="initial",
           description="Initial idle state",
           version=ModelSemVer(1, 0, 0)  # <-- ADD THIS
       )
   ```

4. **For factory functions**
   ```python
   def create_state_definition(**kwargs):
       # Add default version
       kwargs.setdefault('version', ModelSemVer(1, 0, 0))
       return ModelFSMStateDefinition(**kwargs)
   ```

---

## Verification Commands

### After Pattern 1

```bash
# Quick check
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_routing_subcontract.py -x

# Count remaining failures
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -q 2>&1 | tail -1
```

### After Pattern 2

```bash
# Check top failing models
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_event_mapping_rule.py -x
poetry run pytest tests/unit/models/contracts/subcontracts/test_model_action_config_parameter.py -x

# Full subcontracts
poetry run pytest tests/unit/models/contracts/subcontracts/ --tb=no -q 2>&1 | tail -1
```

### After Manual Fixes

```bash
# FSM and workflow tests
poetry run pytest tests/unit/utils/test_fsm_executor.py -x
poetry run pytest tests/unit/models/workflow/ -x

# Full suite
poetry run pytest tests/ --tb=no -q 2>&1 | tail -1
```

---

## Rollback Strategy

### Quick Rollback

```bash
# If something breaks
git checkout tests/unit/models/contracts/subcontracts/

# Or restore single file
git checkout tests/unit/models/contracts/subcontracts/test_model_routing_subcontract.py

# Full rollback
git reset --hard HEAD
```

### Restore from Backup

```bash
# Restore backup files created by script
for file in tests/unit/models/contracts/subcontracts/test_model_*.py.bak; do
  [ -f "$file" ] && mv "$file" "${file%.bak}"
done
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'omnibase_core'"

**Solution**: Ensure poetry environment is set up
```bash
poetry install
poetry run pytest --version
```

### Issue: sed: can't open file for reading

**Solution**: Check file paths are correct
```bash
ls tests/unit/models/contracts/subcontracts/test_model_*.py | wc -l
```

### Issue: Syntax errors after automation

**Solution**: Script should prevent this, but if it happens:
```bash
# Check syntax
python -m py_compile tests/unit/models/contracts/subcontracts/test_model_xxx.py

# Rollback and fix manually
git checkout tests/unit/models/contracts/subcontracts/test_model_xxx.py
```

### Issue: Import missing

**Solution**: Scripts should add it automatically, but you can add manually:
```bash
# Add to a file
sed -i '' '1s/^/from omnibase_core.primitives.model_semver import ModelSemVer\n/' \
  tests/unit/models/contracts/subcontracts/test_model_xxx.py
```

---

## Success Checklist

- [ ] Backup branch created
- [ ] Pattern 1 dry run passes
- [ ] Pattern 1 applied successfully
- [ ] Pattern 2 dry run passes
- [ ] Pattern 2 applied successfully
- [ ] Syntax check passes
- [ ] Subcontracts tests mostly passing
- [ ] Manual fixes completed
- [ ] Full test suite passes
- [ ] Changes committed and pushed

---

## Expected Results

### Before Automation

```
Failed: ~796
Passed: ~182
Pass Rate: 18.6%
```

### After Automation

```
Failed: ~0-50 (manual fixes needed)
Passed: ~950+
Pass Rate: >95%
```

---

## Time Breakdown

| Phase | Task | Time | Status |
|-------|------|------|--------|
| Setup | Prepare, verify imports | 5 min | |
| Pattern 1 | sed automation | 10 min | |
| Pattern 2 | Python AST | 10 min | |
| Syntax Check | Verify Python | 5 min | |
| Manual Fixes | Remaining ~160 | 20-40 min | |
| Final Verification | Full test suite | 10-15 min | |
| **TOTAL** | | **60-85 min** | |

---

## Next Steps After Automation

1. **Commit your changes**
   ```bash
   git add tests/
   git commit -m "fix: add version field to subcontract test instantiations

   - Pattern 1: Fixed ~240 empty instantiations with sed
   - Pattern 2: Fixed ~320 complex cases with Python AST
   - Remaining ~160 manual fixes in fixtures/factories
   - All ~796 test failures resolved"
   ```

2. **Run final verification**
   ```bash
   poetry run pytest tests/ --tb=short -q
   ```

3. **Push to branch**
   ```bash
   git push origin chore/fix-version-field
   ```

4. **Create PR**
   ```bash
   gh pr create --title "fix: resolve ~796 test failures from version field requirement"
   ```

---

## Related Documentation

- **Full Strategy**: [VERSION_FIELD_AUTOMATION_STRATEGY.md](docs/guides/VERSION_FIELD_AUTOMATION_STRATEGY.md)
- **Failure Report**: [VERSION_FIELD_FAILURE_REPORT.md](VERSION_FIELD_FAILURE_REPORT.md)
- **Script Details**: `scripts/fix_version_field_pattern{1,2}.*`

---

**Last Updated**: 2025-11-22
**Status**: Ready for use
**Version**: 1.0
