# EXECUTE DUPLICATE RESOLUTION - START HERE

**Generated**: 2025-11-08
**Status**: ✅ READY TO EXECUTE

---

## WHAT THIS DOES

Eliminates **all 79 duplicate model filename sets** in omnibase_core by:
1. Deleting ~88 duplicate/stub/re-export files
2. Renaming ~12 files to domain-specific names
3. Updating ~500-800 import statements
4. Ensuring tests pass

**User Requirements Met**:
- ✅ NO backwards compatibility (breaking changes allowed)
- ✅ NO re-exports (all eliminated)
- ✅ ALL generic names renamed to domain-specific
- ✅ models/common/ contains only truly common models
- ✅ Tests pass after completion

---

## QUICK START - AUTOMATED EXECUTION (RECOMMENDED)

```bash
# 1. Review the plan (optional but recommended)
less DUPLICATE_MODELS_RESOLUTION_PLAN.md

# 2. Execute ALL phases automatically (15-30 minutes)
bash scripts/execute_duplicate_resolution.sh
```

**What happens**:
- Creates backup branch automatically
- Executes 5 phases sequentially
- Commits after each phase
- Updates all imports
- Runs verification tests
- Provides summary

**Estimated runtime**: 15-30 minutes (mostly test execution)

---

## AVAILABLE DOCUMENTATION

### 1. DUPLICATE_MODELS_AUDIT_REPORT.md (29KB, 877 lines)
**Original audit findings** - background on the problem

### 2. DUPLICATE_MODELS_RESOLUTION_PLAN.md (70KB, 2,036 lines) ⭐ **MAIN PLAN**
**Complete detailed plan** with:
- All 79 duplicate sets analyzed
- Specific action for each duplicate
- Git commands for every change
- Import update strategy
- Phase breakdown
- Risk assessment

### 3. DUPLICATE_RESOLUTION_MASTER_TABLE.md (12KB, 241 lines)
**Quick reference table** of all 79 duplicates with actions

### 4. DUPLICATE_RESOLUTION_QUICK_REFERENCE.md (17KB, 528 lines)
**Execution guide** with:
- Both automated and manual workflows
- Critical issues explained
- Testing strategy
- Rollback procedures

### 5. scripts/execute_duplicate_resolution.sh (15KB, 380 lines)
**Master execution script** - runs all phases automatically

### 6. scripts/update_all_imports.sh (22KB, 322 lines)
**Import update script** - updates ~500-800 import statements

---

## DOCUMENT HIERARCHY

```
START HERE → EXECUTE_DUPLICATE_RESOLUTION.md (this file)
    ↓
    ├─ Quick Start → scripts/execute_duplicate_resolution.sh (AUTOMATED)
    │                     OR
    ├─ Manual Execution → DUPLICATE_RESOLUTION_QUICK_REFERENCE.md
    │
    └─ Deep Dive:
        ├─ DUPLICATE_MODELS_RESOLUTION_PLAN.md (ALL DETAILS)
        ├─ DUPLICATE_RESOLUTION_MASTER_TABLE.md (TABLE OF 79)
        └─ DUPLICATE_MODELS_AUDIT_REPORT.md (BACKGROUND)
```

---

## EXECUTION OPTIONS

### Option 1: Fully Automated (15-30 minutes) ⭐ **RECOMMENDED**

```bash
bash scripts/execute_duplicate_resolution.sh
```

**Pros**:
- Fast and consistent
- Creates backup automatically
- Commits after each phase
- Runs all verifications
- Provides summary

**Cons**:
- Less control
- Hard to stop mid-execution

---

### Option 2: Manual Phase-by-Phase (8-12 hours)

See **DUPLICATE_RESOLUTION_QUICK_REFERENCE.md** for detailed manual steps

**Pros**:
- Full control
- Can review after each phase
- Can stop and resume

**Cons**:
- Time consuming
- Requires careful attention
- More prone to errors

---

## CRITICAL ISSUES BEING FIXED

### 1. model_registry_error.py - CONFLICTING BASE CLASSES ⚠️
- **Problem**: Same name, different base classes (ModelOnexWarning vs ModelOnexError)
- **Fix**: Delete core/ version, keep common/ (canonical)

### 2. model_validation_result.py - 5 DIFFERENT VERSIONS ⚠️
- **Problem**: 5 completely different implementations
- **Fix**: Keep common/ (canonical), rename models/ for import validation, delete 3 others

### 3. model_action.py - 4 DIFFERENT IMPLEMENTATIONS ⚠️
- **Problem**: 4 versions with different purposes
- **Fix**: Keep orchestrator/ (canonical), rename infrastructure/ to clarify purpose

### 4. model_metadata.py - GENERIC NAME ⚠️
- **Problem**: Same generic name in 3 domains
- **Fix**: Rename to model_configuration_metadata.py, model_core_metadata.py, model_security_metadata.py

### 5. Re-exports ⚠️
- **Problem**: Multiple re-export files for convenience
- **Fix**: Delete ALL re-exports (per user requirement)

---

## PHASES OVERVIEW

### Phase 1: Delete Identical Duplicates
- 4 sets, 8 files deleted
- Low risk, high confidence
- **Examples**: model_config.py (5 identical stubs), model_unified_version.py

### Phase 2: Delete Re-exports and Stubs
- 27 sets, ~30 files deleted
- Medium risk, requires import updates
- **Examples**: model_error_context.py (re-export), model_action.py (stubs)

### Phase 3: Consolidate to Canonical
- 45 sets, ~50 files deleted
- Medium risk, comprehensive changes
- **Examples**: All core/ stubs moved to correct domains

### Phase 4: Rename to Domain-Specific
- 5 sets, 15 files renamed
- High risk, requires import updates
- **Examples**: model_metadata.py → model_{domain}_metadata.py

### Phase 5: Update All Imports
- ~500-800 files updated
- High risk, comprehensive changes
- Automated via scripts/update_all_imports.sh

---

## VERIFICATION TESTS

After execution, all must pass:

```bash
# 1. Unit tests (12,000+)
poetry run pytest tests/ -x

# 2. Type checking (must be zero errors)
poetry run mypy src/omnibase_core/

# 3. Linting
poetry run ruff check src/ tests/

# 4. Formatting
poetry run black --check src/ tests/
poetry run isort --check src/ tests/
```

---

## ROLLBACK PROCEDURE

If anything goes wrong:

```bash
# Automatic backup branch created by script
git checkout backup/pre-duplicate-resolution-YYYYMMDD-HHMMSS

# Or revert specific phase
git revert <commit-hash>
```

**IMPORTANT**: Backup branch is created automatically before any changes

---

## SUCCESS CRITERIA

- [ ] All 79 duplicate filename sets eliminated
- [ ] All tests pass (12,000+)
- [ ] Zero mypy errors
- [ ] Zero duplicate model filenames
- [ ] All re-exports eliminated
- [ ] All generic names renamed to domain-specific
- [ ] models/common/ contains only truly common models
- [ ] No broken imports

---

## EXPECTED RESULTS

### Before
- 79 duplicate filename sets
- ~170 files with duplicate names
- Multiple import paths for same model
- Type confusion (e.g., model_registry_error.py)
- Generic names without domain context

### After
- 0 duplicate filename sets
- ~88 fewer files
- Single canonical import path per model
- No type confusion
- All names domain-specific

---

## FILE STATISTICS

### Created Documentation
| File | Size | Lines | Purpose |
|------|------|-------|---------|
| DUPLICATE_MODELS_RESOLUTION_PLAN.md | 70KB | 2,036 | Complete detailed plan |
| DUPLICATE_RESOLUTION_MASTER_TABLE.md | 12KB | 241 | Table of all 79 duplicates |
| DUPLICATE_RESOLUTION_QUICK_REFERENCE.md | 17KB | 528 | Execution guide |
| EXECUTE_DUPLICATE_RESOLUTION.md | This | File | Start here |

### Created Scripts
| Script | Size | Lines | Purpose |
|--------|------|-------|---------|
| execute_duplicate_resolution.sh | 15KB | 380 | Master execution |
| update_all_imports.sh | 22KB | 322 | Import updates |

**Total**: ~138KB of documentation + scripts

---

## NEXT STEPS

### If you want to execute NOW:

```bash
bash scripts/execute_duplicate_resolution.sh
```

### If you want to review first:

1. Read DUPLICATE_MODELS_RESOLUTION_PLAN.md (complete details)
2. Review DUPLICATE_RESOLUTION_MASTER_TABLE.md (table of all 79)
3. Check DUPLICATE_RESOLUTION_QUICK_REFERENCE.md (manual workflow)
4. Then execute when ready

### If you want to understand the problem first:

1. Read DUPLICATE_MODELS_AUDIT_REPORT.md (original findings)
2. Then proceed with execution

---

## SUPPORT

**Questions about the plan?**
- See DUPLICATE_MODELS_RESOLUTION_PLAN.md (section-by-section breakdown)

**Want to see all 79 duplicates?**
- See DUPLICATE_RESOLUTION_MASTER_TABLE.md (complete table)

**Need step-by-step manual execution?**
- See DUPLICATE_RESOLUTION_QUICK_REFERENCE.md (manual workflow)

**Encounter issues during execution?**
- Check backup branch exists: `git branch | grep backup/pre-duplicate`
- Review git diff: `git diff`
- Check test failures: `poetry run pytest tests/ -x -v`

---

## READY TO EXECUTE?

```bash
# Execute all phases automatically (recommended)
bash scripts/execute_duplicate_resolution.sh
```

**Estimated time**: 15-30 minutes

**Backup**: Created automatically

**Verification**: All tests run automatically

**Rollback**: Available via backup branch

---

**Generated**: 2025-11-08
**Total Duplicates**: 79
**Files to Delete**: ~88
**Files to Rename**: ~12
**Import Updates**: ~500-800

✅ **READY TO EXECUTE**
