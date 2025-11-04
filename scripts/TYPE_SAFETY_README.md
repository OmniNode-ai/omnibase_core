# Type Safety Scripts - Omnibase Core

This directory contains automated scripts for improving type safety in the omnibase_core project, specifically targeting strict mypy compliance.

## Overview

**Current Status** (as of 2025-10-22):
- ✅ **Standard Mode**: 0 errors (production ready)
- ⚠️ **Strict Mode**: 215 errors across 93 files (5.0% of codebase)

**Goal**: Achieve 100% strict mode compliance through automated fixes.

## Available Scripts

### Phase 1: Quick Wins (Automated, 3-5 hours)

#### 1. `phase1_quick_wins.sh` - Master Script
**Purpose**: Execute all Phase 1 fixes in one go

**Usage**:
```bash
# Dry run (preview changes only)
./scripts/phase1_quick_wins.sh

# Apply changes
DRY_RUN=false ./scripts/phase1_quick_wins.sh
```

**Impact**: Removes 122 errors (56.7% of total)
- 63 unused-ignore errors
- 59 attr-defined errors

**Features**:
- Pre-flight checks (uncommitted changes warning)
- Baseline error counting
- Automated fixing
- Post-fix verification with mypy and pytest
- Summary report with improvement metrics

---

#### 2. `remove_unused_ignores.sh` - Remove Unused Type Ignores
**Purpose**: Remove `# type: ignore` comments that are no longer needed

**Usage**:
```bash
./scripts/remove_unused_ignores.sh
```

**What it does**:
1. Scans codebase for unused type ignore comments
2. Creates backup of affected files
3. Removes unused comments
4. Verifies with mypy

**Safety**:
- Creates timestamped backup directory
- Processes files individually
- Can be rolled back if issues occur

**Expected**: 63 errors fixed in 1-2 hours

---

#### 3. `generate_all_exports.py` - Add __all__ Exports
**Purpose**: Add `__all__` declarations to modules missing them

**Usage**:
```bash
# Dry run (preview only)
poetry run python scripts/generate_all_exports.py

# Apply changes
poetry run python scripts/generate_all_exports.py --apply

# Apply to specific module only
poetry run python scripts/generate_all_exports.py --apply --module omnibase_core.models.security
```

**What it does**:
1. Scans for attr-defined errors in mypy output
2. Analyzes each module's public API (classes, functions, constants)
3. Generates comprehensive `__all__` declarations
4. Inserts `__all__` after imports, before first definition
5. Preserves module docstrings and structure

**Smart Features**:
- Detects existing `__all__` declarations (won't duplicate)
- Extracts public names via AST parsing
- Combines mypy-expected exports with actual public API
- Handles TypedDict, Enums, and Protocols correctly

**Expected**: 59 errors fixed in 2-3 hours

---

### Phase 2: Type Refinement (Semi-Automated, 12-16 hours)

Phase 2 scripts will fix `no-any-return` errors (92 remaining after Phase 1).

**Status**: Not yet implemented. See TYPE_ANALYSIS_REPORT.md for strategy.

**Planned approach**:
1. Start with high-value files (most errors per file)
2. Apply common fix patterns:
   - Replace `.dict()` with `.model_dump()` (Pydantic v2)
   - Add type assertions with `cast()`
   - Use type guards for dynamic access
   - Convert to TypedDict where appropriate
3. Verify after each file with mypy

---

## Usage Workflows

### Quick Start: Run All Phase 1 Fixes

```bash
# 1. Review what will be fixed
./scripts/phase1_quick_wins.sh

# 2. Apply all Phase 1 fixes
DRY_RUN=false ./scripts/phase1_quick_wins.sh

# 3. Review changes
git diff

# 4. Commit
git add -A
git commit -m "chore: Phase 1 type safety improvements

- Remove 63 unused type: ignore comments
- Add __all__ exports to 29 modules
- Reduce strict mode errors by 56.7%

Addresses: TYPE_ANALYSIS_REPORT.md Phase 1"
```

### Incremental Approach: Run Individual Scripts

```bash
# Step 1: Remove unused ignores
./scripts/remove_unused_ignores.sh

# Review and test
git diff
poetry run pytest tests/

# Commit
git add -A
git commit -m "chore: remove unused type ignore comments"

# Step 2: Add __all__ exports
poetry run python scripts/generate_all_exports.py --apply

# Review and test
git diff
poetry run pytest tests/

# Commit
git add -A
git commit -m "feat: add __all__ exports for explicit public API"
```

### Targeted Fix: Specific Module

```bash
# Fix only security models
poetry run python scripts/generate_all_exports.py \
    --apply \
    --module omnibase_core.models.security

# Verify
poetry run mypy src/omnibase_core/models/security/ --strict
```

---

## Error Categories

### 1. unused-ignore (63 errors, 29.3%)

**Description**: `# type: ignore` comments that are no longer needed

**Cause**: Previous type errors were fixed but comments remained

**Impact**: Code smell, reduces readability

**Fix Script**: `remove_unused_ignores.sh`

**Examples**:
```python
# Before
value = getattr(self, key)  # type: ignore

# After (comment no longer needed)
value = getattr(self, key)
```

---

### 2. attr-defined (59 errors, 27.4%)

**Description**: Modules don't explicitly export attributes in `__all__`

**Cause**: Missing or incomplete `__all__` declarations

**Impact**: Type checkers can't verify public API boundaries

**Fix Script**: `generate_all_exports.py`

**Examples**:
```python
# Before (no __all__)
class ModelFoo:
    pass

class ModelBar:
    pass

# After
__all__ = [
    "ModelFoo",
    "ModelBar",
]

class ModelFoo:
    pass

class ModelBar:
    pass
```

**Top Affected Modules**:
- `model_cli_config.py` (5 missing exports)
- `model_event_descriptor.py` (4 missing exports)
- `model_enhanced_tool_collection.py` (4 missing exports)
- `typed_dict_factory_kwargs.py` (3 missing exports)

---

### 3. no-any-return (92 errors, 42.8%)

**Description**: Functions returning `Any` when they should return specific types

**Cause**: Pydantic `.dict()` calls, dynamic attribute access, dictionary operations

**Impact**: Reduces type safety, allows any type to pass through

**Fix Strategy**: Manual fixes required (Phase 2)

**Common Patterns**:

#### Pattern A: Pydantic .dict() Returns

```python
# Before
def to_dict(self) -> dict[str, Any]:
    return self.dict()  # Returns Any

# After
def to_dict(self) -> dict[str, Any]:
    return self.model_dump()  # Properly typed in Pydantic v2
```

#### Pattern B: Dynamic Attribute Access

```python
# Before
def get_value(self, key: str) -> str:
    return getattr(self, key)  # Returns Any

# After
from typing import cast

def get_value(self, key: str) -> str:
    value = getattr(self, key)
    return cast(str, value)
```

#### Pattern C: Dictionary Merging

```python
# Before
def merge_config(self, config: dict[str, Any]) -> dict[str, Any]:
    return {**self.base_config, **config}  # Returns Any

# After
def merge_config(self, config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {**self.base_config, **config}
    return result
```

---

## Testing & Verification

### After Running Scripts

```bash
# 1. Run mypy to verify error reduction
poetry run mypy src/omnibase_core/ --strict

# 2. Run full test suite
poetry run pytest tests/ -v

# 3. Check test coverage
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=term-missing

# 4. Run linters
poetry run ruff check src/
poetry run black --check src/
```

### Expected Results

**After Phase 1**:
- Strict mode errors: 215 → 93 (57% reduction)
- Standard mode: Still 0 errors
- Test coverage: Maintained at >95%
- No functional changes (pure type safety improvements)

**After Phase 2** (future):
- Strict mode errors: 93 → 0 (100% compliance)
- Full strict mode enabled in pyproject.toml

---

## Rollback Strategy

### If Something Goes Wrong

#### Option 1: Use Git

```bash
# See what changed
git diff

# Revert all changes
git checkout -- src/

# Or revert specific file
git checkout -- src/omnibase_core/models/core/model_foo.py
```

**Option 2: Use Backups** (for remove_unused_ignores.sh)
```bash
# Backups are in timestamped directory
ls .backup_*

# Restore specific file
cp .backup_20251022_084500/model_foo.py.bak src/path/to/model_foo.py
```

---

## Integration with CI/CD

### Current Configuration

```toml
# pyproject.toml
[tool.mypy]
plugins = ["pydantic.mypy"]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
# strict = false  # Not yet enabled
```

### After Phase 2 Completion

```toml
# pyproject.toml
[tool.mypy]
strict = true  # Enable strict mode
plugins = ["pydantic.mypy"]
python_version = "3.12"
mypy_path = "src"
namespace_packages = true
explicit_package_bases = true
```

### Pre-commit Hook (Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        args: [--strict, --config-file=pyproject.toml]
        additional_dependencies: [pydantic, types-PyYAML]
```

---

## Performance Considerations

### Script Execution Times

| Script | Expected Time | Parallelizable |
|--------|---------------|----------------|
| `remove_unused_ignores.sh` | 1-2 hours | No (modifies files) |
| `generate_all_exports.py` | 2-3 hours | No (modifies files) |
| `phase1_quick_wins.sh` | 3-5 hours | No (sequential) |
| Phase 2 (future) | 12-16 hours | Partially (by file) |

### Mypy Performance Impact

- Current (standard mode): ~15-20 seconds for full codebase
- With strict mode: ~25-35 seconds for full codebase
- Increase: ~50-75% (acceptable for quality gain)

---

## Troubleshooting

### Common Issues

#### Issue 1: Script says "No errors found" but report shows errors

**Cause**: Mypy cache is stale

**Solution**:
```bash
# Clear mypy cache
rm -rf .mypy_cache/

# Re-run mypy
poetry run mypy src/omnibase_core/ --strict
```

---

#### Issue 2: Tests fail after applying fixes

**Cause**: Changes affected runtime behavior (shouldn't happen with these fixes)

**Solution**:
```bash
# Identify failing test
poetry run pytest tests/ -v -x  # Stop on first failure

# Review specific change
git diff src/path/to/changed/file.py

# If needed, revert specific file
git checkout -- src/path/to/changed/file.py
```

---

#### Issue 3: generate_all_exports.py creates duplicate __all__

**Cause**: Module already has `__all__` but script didn't detect it

**Solution**: Script has built-in check and should skip. If it happens:
```bash
# Manually remove duplicate
# Edit file and keep only one __all__ declaration
```

---

#### Issue 4: Permission denied when running scripts

**Solution**:
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Or run with bash/python explicitly
bash scripts/remove_unused_ignores.sh
poetry run python scripts/generate_all_exports.py
```

---

## References

- **Full Analysis**: `/Volumes/PRO-G40/Code/omnibase_core/TYPE_ANALYSIS_REPORT.md`
- **Mypy Documentation**: https://mypy.readthedocs.io/
- **Pydantic v2 Migration**: https://docs.pydantic.dev/latest/migration/
- **Python Type Hints**: https://docs.python.org/3/library/typing.html

---

## Support & Questions

For questions or issues:
1. Review TYPE_ANALYSIS_REPORT.md for detailed context
2. Check git history for similar fixes: `git log --all --grep="type"`
3. Consult mypy error codes: https://mypy.readthedocs.io/en/stable/error_code_list.html

---

**Last Updated**: 2025-10-22
**Maintainer**: Claude Code (Sonnet 4.5)
**Status**: Phase 1 ready for execution
