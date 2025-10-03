# Import Standardization Report - Error/Exception Patterns

**Generated:** 2025-10-02
**Scope:** All files importing from `omnibase_core.errors.*` or `omnibase_core.exceptions.*`
**Total Files Analyzed:** 196 import statements across 195 unique files

---

## Executive Summary

The codebase has **severe fragmentation** in error handling imports with:
- **3 duplicate OnexError implementations** (errors.error_codes, exceptions.onex_error, errors.error_onex)
- **3 duplicate CoreErrorCode implementations** (errors.error_codes.CoreErrorCode, enums.EnumCoreErrorCode, errors.error_onex.CoreErrorCode)
- **8 different import patterns** in use
- **91.8% of files** use one pattern, **8.2%** use 6 other patterns

**Critical Finding:** The "official" package-level export (`from omnibase_core.errors import OnexError`) re-exports `errors.error_codes.OnexError`, which has Pydantic circular dependency issues and cannot be instantiated cleanly.

---

## Part 1: Current Import Pattern Catalog

### Pattern Distribution Summary

| Pattern | Files | % | Status |
|---------|-------|---|--------|
| **Pattern 1** | 179 | 91.3% | ✓ WORKING |
| **Pattern 2** | 8 | 4.1% | ⚠ PARTIAL |
| **Pattern 3** | 4 | 2.0% | ✗ DEPRECATED |
| **Pattern 4** | 1 | 0.5% | ⚠ INDIRECT |
| **Pattern 5** | 1 | 0.5% | ⚠ PARTIAL |
| **Pattern 6** | 1 | 0.5% | ⚠ INDIRECT |
| **Pattern 7** | 1 | 0.5% | ⚠ MULTI-LINE |
| **Pattern 8** | 1 | 0.5% | ✓ SPECIALIZED |

### Pattern 1: exceptions.onex_error (91.3% - DOMINANT)

```python
from omnibase_core.exceptions.onex_error import OnexError
```

**Status:** ✓ Working, lightweight, no circular dependencies
**Files:** 179 (91.3%)
**Usage:**
- Used throughout models/, infrastructure/, validation/
- Works with EnumCoreErrorCode
- Uses ModelErrorContext for structured details
- No Pydantic circular dependency issues

**Example files:**
- `src/omnibase_core/utils/safe_yaml_loader.py:17`
- `src/omnibase_core/models/core/model_configuration_base.py:22`
- `src/omnibase_core/models/cli/model_cli_debug_info.py:17`
- ... and 176 more

**Signature:**
```python
OnexError(
    code: EnumCoreErrorCode,
    message: str,
    details: ModelErrorContext | None = None,
    cause: Exception | None = None
)
```

---

### Pattern 2: errors.error_codes (4.1% - OFFICIAL BUT BROKEN)

```python
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
```

**Status:** ⚠ Official export but has circular dependency issues
**Files:** 8 (4.1%)
**Problems:**
- Cannot instantiate cleanly due to Pydantic model dependencies
- Circular dependency: `ModelOnexError` requires `ModelSchemaValue` not fully defined
- Heavier implementation with Pydantic integration

**Example files:**
- `src/omnibase_core/infrastructure/node_reducer.py:32`
- `src/omnibase_core/infrastructure/node_base.py:27`
- `src/omnibase_core/infrastructure/node_effect.py:33`
- `src/omnibase_core/utils/util_contract_loader.py:20`

**Signature:**
```python
OnexError(
    message: str,
    error_code: OnexErrorCode | str | None = None,
    status: EnumOnexStatus = EnumOnexStatus.ERROR,
    correlation_id: UUID | None = None,
    timestamp: datetime | None = None,
    **context: Any
)
```

---

### Pattern 3: errors.error_onex (2.0% - DEPRECATED LEGACY)

```python
from omnibase_core.errors.error_onex import CoreErrorCode, OnexError
```

**Status:** ✗ Deprecated legacy duplicate
**Files:** 4 (2.0%)
**Problems:**
- Complete duplicate of error system
- Uses simple dict for details (not ModelErrorContext)
- Should be removed entirely

**Example files:**
- `src/omnibase_core/models/nodes/model_node_configuration_value.py:14`
- `src/omnibase_core/models/metadata/model_metadata_node_collection.py:13`
- `src/omnibase_core/models/validation/model_migration_conflict_union.py:13`
- `src/omnibase_core/models/common/model_flexible_value.py:17`

**Signature:**
```python
OnexError(
    code: CoreErrorCode,  # local enum duplicate
    message: str,
    details: dict[str, Any] | None = None,
    cause: Exception | None = None
)
```

---

### Pattern 4: Package-level import (0.5% - INDIRECT)

```python
from omnibase_core.errors import CoreErrorCode, OnexError
```

**Status:** ⚠ Re-exports Pattern 2 (broken implementation)
**Files:** 1
**Note:** Used in package __init__.py, re-exports `errors.error_codes` classes

**Example files:**
- `src/omnibase_core/__init__.py:34`

---

### Pattern 5-8: Various partial patterns (2.6%)

Minor patterns for specialized imports like error_document_freshness.

---

## Part 2: Root Cause Analysis

### Problem 1: Three Duplicate OnexError Implementations

| Location | Purpose | Status | Issue |
|----------|---------|--------|-------|
| `errors/error_codes.py:458` | Official full-featured | Broken | Pydantic circular deps |
| `exceptions/onex_error.py:16` | Lightweight working | ✓ Working | None |
| `errors/error_onex.py:28` | Legacy duplicate | Deprecated | Should be removed |

### Problem 2: Three Duplicate CoreErrorCode/EnumCoreErrorCode

| Location | Purpose | Type | Status |
|----------|---------|------|--------|
| `enums/enum_core_error_code.py:11` | Canonical enum | EnumCoreErrorCode | ✓ Canonical |
| `errors/error_codes.py:141` | Extended enum | CoreErrorCode(OnexErrorCode) | Official but complex |
| `errors/error_onex.py:12` | Legacy duplicate | CoreErrorCode | Deprecated |

### Problem 3: Inconsistent Error Code Enums

- **EnumCoreErrorCode** (enums module): Simple error codes like "validation_error"
- **CoreErrorCode** (errors module): ONEX-formatted codes like "ONEX_CORE_001_INVALID_PARAMETER"
- These are **different enums with different values**

### Problem 4: Architectural Confusion

The official architecture wants:
```
errors/error_codes.py → Full-featured OnexError with Pydantic integration
exceptions/onex_error.py → Should not exist or be internal-only
```

Reality:
```
exceptions/onex_error.py → What 91% of code actually uses (because it works)
errors/error_codes.py → What package exports (but broken)
errors/error_onex.py → Old duplicate that should be deleted
```

---

## Part 3: Recommended Canonical Pattern

### Option A: Fix errors.error_codes and standardize on it (IDEAL BUT RISKY)

**Canonical Pattern:**
```python
from omnibase_core.errors import OnexError, CoreErrorCode
```

**Justification:**
- Package-level import (cleanest)
- Official architecture intent
- Full-featured with Pydantic integration
- Proper error code hierarchy

**Requirements:**
1. Fix Pydantic circular dependency in errors.error_codes
2. Migrate 179 files from exceptions.onex_error
3. Remove errors.error_onex entirely
4. Update all error code usages (EnumCoreErrorCode → CoreErrorCode)

**Risk:** High - breaks working code to fix broken code

---

### Option B: Standardize on exceptions.onex_error (PRAGMATIC, RECOMMENDED)

**Canonical Pattern:**
```python
from omnibase_core.exceptions import OnexError
from omnibase_core.enums import EnumCoreErrorCode
```

**Justification:**
- Already used by 91.3% of codebase
- Works reliably with no circular dependencies
- Lightweight and focused
- Uses canonical EnumCoreErrorCode from enums module
- Minimal risk migration

**Requirements:**
1. Export OnexError from exceptions/__init__.py (already done)
2. Migrate 16 files from errors.* patterns
3. Remove errors.error_onex entirely
4. Deprecate direct use of errors.error_codes.OnexError
5. Document exceptions.onex_error as canonical

**Risk:** Low - codifies existing working pattern

---

### ✅ RECOMMENDED: Option B (exceptions.onex_error)

**Why this is correct:**

1. **Working Code Wins:** 179/195 files (91.8%) already use this and it works
2. **No Circular Dependencies:** Clean import graph
3. **Separation of Concerns:**
   - `exceptions/` = Exception classes
   - `errors/` = Error codes and CLI adapters
   - `enums/` = Error code enums
4. **Minimal Migration Risk:** Only need to migrate 16 files
5. **Canonical Enum Usage:** Uses EnumCoreErrorCode from enums module

---

## Part 4: Complete Migration Plan

### Phase 1: Preparation (Risk: Low)

**Goal:** Ensure canonical exports are in place

**Actions:**
1. ✓ Verify `exceptions/__init__.py` exports OnexError (DONE)
2. Add EnumCoreErrorCode to `enums/__init__.py` if not present
3. Add deprecation warnings to `errors/error_onex.py`
4. Document canonical pattern in CONTRIBUTING.md

**Files affected:** 2-3 files
**Risk:** None
**Time estimate:** 30 minutes

---

### Phase 2: Migrate Core Infrastructure (Risk: Medium)

**Goal:** Migrate infrastructure and base classes

**Files to migrate:** 8 files using Pattern 2

| File | Current Import | New Import |
|------|---------------|------------|
| `infrastructure/node_base.py` | `from omnibase_core.errors.error_codes import CoreErrorCode, OnexError` | `from omnibase_core.exceptions import OnexError`<br>`from omnibase_core.enums import EnumCoreErrorCode` |
| `infrastructure/node_effect.py` | Same | Same |
| `infrastructure/node_compute.py` | Same | Same |
| `infrastructure/node_reducer.py` | Same | Same |
| `infrastructure/node_orchestrator.py` | Same | Same |
| `infrastructure/node_core_base.py` | Same | Same |
| `utils/util_contract_loader.py` | Same | Same |
| `container/container_service_resolver.py` | `from omnibase_core.errors.error_codes import CoreErrorCode` | `from omnibase_core.enums import EnumCoreErrorCode` |

**Migration steps per file:**
1. Change import statement
2. Update error code references: `CoreErrorCode.X` → `EnumCoreErrorCode.X`
3. Update OnexError instantiation if needed (signature is compatible)
4. Run tests

**Risk:** Medium - infrastructure files are critical
**Time estimate:** 2-3 hours
**Testing required:** Full integration test suite

---

### Phase 3: Migrate Legacy Pattern (Risk: High)

**Goal:** Migrate 4 files using deprecated Pattern 3

| File | Current Import | Issue |
|------|---------------|-------|
| `models/nodes/model_node_configuration_value.py` | `from omnibase_core.errors.error_onex import CoreErrorCode, OnexError` | Uses legacy duplicate |
| `models/metadata/model_metadata_node_collection.py` | Same | Same |
| `models/validation/model_migration_conflict_union.py` | Same | Same |
| `models/common/model_flexible_value.py` | Same | Same |

**Migration steps per file:**
1. Replace: `from omnibase_core.errors.error_onex import` → `from omnibase_core.exceptions import OnexError`
2. Add: `from omnibase_core.enums import EnumCoreErrorCode`
3. Update error instantiation:
   - OLD: `OnexError(CoreErrorCode.VALIDATION_ERROR, "msg", details={})`
   - NEW: `OnexError(EnumCoreErrorCode.VALIDATION_ERROR, "msg", details=ModelErrorContext(...))`
4. Run model validation tests

**Risk:** High - may need details format conversion
**Time estimate:** 2 hours
**Testing required:** Model validation suite

---

### Phase 4: Clean Package-Level Import (Risk: Low)

**Goal:** Update package __init__.py

| File | Current | New |
|------|---------|-----|
| `__init__.py` | `from omnibase_core.errors import CoreErrorCode, OnexError` | `from omnibase_core.exceptions import OnexError`<br>`from omnibase_core.enums import EnumCoreErrorCode` |

**Risk:** Low - just package re-export
**Time estimate:** 15 minutes

---

### Phase 5: Remove Deprecated Code (Risk: Low)

**Goal:** Delete legacy duplicates

**Actions:**
1. Delete `src/omnibase_core/errors/error_onex.py`
2. Remove imports in `errors/__init__.py`
3. Update documentation references
4. Add migration note to CHANGELOG

**Risk:** Low - code is no longer used after Phase 3
**Time estimate:** 30 minutes

---

### Phase 6: Documentation & Validation (Risk: None)

**Goal:** Update all documentation and validate

**Actions:**
1. Update all .md files with new canonical pattern
2. Add import standards to CONTRIBUTING.md
3. Create pre-commit hook to enforce pattern
4. Run full test suite
5. Update type stubs if needed

**Risk:** None
**Time estimate:** 1 hour

---

## Part 5: Migration Statistics

### Total Effort Estimate

| Phase | Files | Time | Risk | Can Parallelize |
|-------|-------|------|------|-----------------|
| Phase 1 | 2-3 | 30 min | Low | No |
| Phase 2 | 8 | 2-3 hrs | Medium | Yes (per file) |
| Phase 3 | 4 | 2 hrs | High | Yes (per file) |
| Phase 4 | 1 | 15 min | Low | No |
| Phase 5 | 1 | 30 min | Low | No |
| Phase 6 | All | 1 hr | None | Partial |
| **Total** | **16** | **6-7 hrs** | **Medium** | **Mostly** |

### File Categories

| Category | Count | % of Total | Migration Complexity |
|----------|-------|------------|---------------------|
| Already canonical (Pattern 1) | 179 | 91.3% | ✓ No change needed |
| Core infrastructure (Pattern 2) | 8 | 4.1% | Medium - signature compatible |
| Legacy duplicates (Pattern 3) | 4 | 2.0% | High - needs detail conversion |
| Package-level (Pattern 4) | 1 | 0.5% | Low - simple re-export |
| Partial/specialized (Patterns 5-8) | 4 | 2.0% | Low - context-specific |
| **Total files** | **196** | **100%** | **16 files need migration** |

---

## Part 6: Example Transformations

### Example 1: Simple Infrastructure File (node_base.py)

**BEFORE:**
```python
from omnibase_core.errors.error_codes import CoreErrorCode, OnexError

class NodeBase:
    def validate(self):
        if not self.name:
            raise OnexError(
                message="Node name is required",
                error_code=CoreErrorCode.MISSING_REQUIRED_PARAMETER
            )
```

**AFTER:**
```python
from omnibase_core.exceptions import OnexError
from omnibase_core.enums import EnumCoreErrorCode

class NodeBase:
    def validate(self):
        if not self.name:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Node name is required"
            )
```

**Changes:**
- Import from exceptions instead of errors.error_codes
- Use EnumCoreErrorCode instead of CoreErrorCode
- Use `code=` parameter instead of `error_code=`
- Signature is simpler (no correlation_id, timestamp, **context)

---

### Example 2: Legacy Pattern with Details (model_flexible_value.py)

**BEFORE:**
```python
from omnibase_core.errors.error_onex import CoreErrorCode, OnexError

class ModelFlexibleValue:
    def validate(self, value: Any) -> None:
        if not isinstance(value, (str, int, float)):
            raise OnexError(
                code=CoreErrorCode.VALIDATION_ERROR,
                message="Invalid value type",
                details={"value": value, "type": type(value).__name__}
            )
```

**AFTER:**
```python
from omnibase_core.exceptions import OnexError
from omnibase_core.enums import EnumCoreErrorCode
from omnibase_core.models.common import ModelErrorContext, ModelSchemaValue

class ModelFlexibleValue:
    def validate(self, value: Any) -> None:
        if not isinstance(value, (str, int, float)):
            details = ModelErrorContext.with_context({
                "value": ModelSchemaValue.from_value(value),
                "type": ModelSchemaValue.from_value(type(value).__name__)
            })
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Invalid value type",
                details=details
            )
```

**Changes:**
- Import from exceptions instead of errors.error_onex
- Use EnumCoreErrorCode from enums module
- Convert dict details to ModelErrorContext
- Wrap detail values in ModelSchemaValue

**Note:** For simple cases, you can pass None for details if not needed:
```python
raise OnexError(
    code=EnumCoreErrorCode.VALIDATION_ERROR,
    message="Invalid value type"
    # details=None is default
)
```

---

### Example 3: Error Code Only Import (container_service_resolver.py)

**BEFORE:**
```python
from omnibase_core.errors.error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError

class ContainerServiceResolver:
    def resolve(self, service_name: str):
        if service_name not in self.services:
            raise OnexError(
                message=f"Service not found: {service_name}",
                error_code=CoreErrorCode.NOT_FOUND
            )
```

**AFTER:**
```python
from omnibase_core.exceptions import OnexError
from omnibase_core.enums import EnumCoreErrorCode

class ContainerServiceResolver:
    def resolve(self, service_name: str):
        if service_name not in self.services:
            raise OnexError(
                code=EnumCoreErrorCode.NOT_FOUND,
                message=f"Service not found: {service_name}"
            )
```

**Changes:**
- Single import block for both OnexError and error codes
- Use EnumCoreErrorCode instead of CoreErrorCode
- Parameter name `code` instead of `error_code`

---

## Part 7: Automation Scripts

### Script 1: Identify Files Needing Migration

```bash
#!/bin/bash
# find_migration_candidates.sh

echo "Files importing from errors.error_codes:"
grep -r "from omnibase_core.errors.error_codes" src/ --include="*.py" -l | sort

echo ""
echo "Files importing from errors.error_onex:"
grep -r "from omnibase_core.errors.error_onex" src/ --include="*.py" -l | sort

echo ""
echo "Files importing from errors package level:"
grep -r "from omnibase_core.errors import.*OnexError\|CoreErrorCode" src/ --include="*.py" -l | sort
```

### Script 2: Automated Pattern Detection

```python
#!/usr/bin/env python3
# detect_error_patterns.py

import re
from pathlib import Path

def analyze_file(filepath):
    """Analyze a file for error import patterns."""
    with open(filepath) as f:
        content = f.read()

    patterns = {
        'error_codes': re.search(r'from omnibase_core\.errors\.error_codes import', content),
        'error_onex': re.search(r'from omnibase_core\.errors\.error_onex import', content),
        'errors_pkg': re.search(r'from omnibase_core\.errors import.*(?:OnexError|CoreErrorCode)', content),
        'exceptions': re.search(r'from omnibase_core\.exceptions', content),
    }

    # Check usage patterns
    usage = {
        'CoreErrorCode': len(re.findall(r'\bCoreErrorCode\.[A-Z_]+', content)),
        'EnumCoreErrorCode': len(re.findall(r'\bEnumCoreErrorCode\.[A-Z_]+', content)),
        'OnexError_old_sig': len(re.findall(r'OnexError\([^)]*error_code=', content)),
        'OnexError_new_sig': len(re.findall(r'OnexError\([^)]*code=', content)),
    }

    return patterns, usage

# Run on all Python files
for py_file in Path('src').rglob('*.py'):
    patterns, usage = analyze_file(py_file)
    if any(patterns.values()):
        print(f"{py_file}: {patterns}, Usage: {usage}")
```

### Script 3: Semi-Automated Migration Tool

```python
#!/usr/bin/env python3
# migrate_imports.py

import re
import sys
from pathlib import Path

def migrate_file(filepath, dry_run=True):
    """Migrate a single file to canonical pattern."""
    with open(filepath) as f:
        content = f.read()

    original = content

    # Step 1: Replace imports
    content = re.sub(
        r'from omnibase_core\.errors\.error_codes import CoreErrorCode, OnexError',
        'from omnibase_core.exceptions import OnexError\nfrom omnibase_core.enums import EnumCoreErrorCode',
        content
    )

    content = re.sub(
        r'from omnibase_core\.errors\.error_onex import CoreErrorCode, OnexError',
        'from omnibase_core.exceptions import OnexError\nfrom omnibase_core.enums import EnumCoreErrorCode',
        content
    )

    content = re.sub(
        r'from omnibase_core\.errors import CoreErrorCode, OnexError',
        'from omnibase_core.exceptions import OnexError\nfrom omnibase_core.enums import EnumCoreErrorCode',
        content
    )

    # Step 2: Replace CoreErrorCode references
    content = re.sub(r'\bCoreErrorCode\.', 'EnumCoreErrorCode.', content)

    # Step 3: Fix OnexError signature (error_code → code)
    content = re.sub(
        r'OnexError\(\s*message=([^,]+),\s*error_code=',
        r'OnexError(code=',
        content
    )

    if content != original:
        print(f"✓ Would migrate: {filepath}")
        if not dry_run:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  → Migrated")
        return True
    return False

# Usage
if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv

    files_to_migrate = [
        # Add file paths here
    ]

    for filepath in files_to_migrate:
        migrate_file(Path(filepath), dry_run=dry_run)
```

---

## Part 8: Validation & Testing Strategy

### Pre-Migration Testing

1. **Ensure all tests pass:**
   ```bash
   pytest tests/ -v
   mypy src/
   ruff check src/
   ```

2. **Document current coverage:**
   ```bash
   pytest --cov=omnibase_core tests/
   ```

### During Migration Testing

**Per-file testing:**
```bash
# After migrating each file
pytest tests/unit/path/to/test_file.py -v
mypy src/path/to/migrated_file.py
```

**Integration testing:**
```bash
# After Phase 2 (infrastructure)
pytest tests/unit/infrastructure/ -v
pytest tests/integration/ -v
```

**Model validation testing:**
```bash
# After Phase 3 (legacy patterns)
python -m omnibase_core.validation all
```

### Post-Migration Validation

1. **Full test suite:**
   ```bash
   pytest tests/ -v --cov=omnibase_core
   ```

2. **Type checking:**
   ```bash
   mypy src/ --strict
   ```

3. **Import validation:**
   ```bash
   # Custom script to ensure no old patterns remain
   ./scripts/validate_imports.sh
   ```

4. **Pattern enforcement:**
   ```bash
   # Add to pre-commit
   grep -r "from omnibase_core.errors.error_onex" src/ && exit 1
   grep -r "from omnibase_core.errors.error_codes import.*OnexError" src/ && exit 1
   ```

---

## Part 9: Pre-Commit Hook for Enforcement

```yaml
# Add to .pre-commit-config.yaml

- repo: local
  hooks:
    - id: enforce-canonical-error-imports
      name: Enforce canonical error import pattern
      entry: python scripts/validate_error_imports.py
      language: python
      files: \.py$

    - id: no-deprecated-error-imports
      name: Prevent deprecated error imports
      entry: bash -c 'grep -r "from omnibase_core.errors.error_onex" src/ && exit 1 || exit 0'
      language: system
      files: \.py$
```

---

## Part 10: Risk Mitigation

### High-Risk Areas

1. **Infrastructure nodes** (node_base.py, etc.)
   - Mitigation: Test with full integration suite
   - Rollback plan: Git revert per file

2. **Model validation** (model_*.py files)
   - Mitigation: Run validation suite after each change
   - Rollback plan: Keep validation tests passing

3. **Details format conversion** (dict → ModelErrorContext)
   - Mitigation: Manual review of all conversions
   - Rollback plan: Compatibility shim if needed

### Rollback Strategy

**Per-phase rollback:**
```bash
# Rollback Phase 2
git revert --no-commit $(git log --grep="Phase 2" --format="%H")

# Rollback specific file
git checkout HEAD~1 -- src/omnibase_core/infrastructure/node_base.py
```

**Full migration rollback:**
```bash
# Create rollback branch before starting
git checkout -b before-import-migration
git checkout main

# After migration, if issues:
git checkout before-import-migration
```

---

## Part 11: Success Criteria

### Migration Completion Checklist

- [ ] Phase 1: Preparation complete (canonical exports verified)
- [ ] Phase 2: All 8 infrastructure files migrated and tested
- [ ] Phase 3: All 4 legacy pattern files migrated and tested
- [ ] Phase 4: Package __init__.py updated
- [ ] Phase 5: error_onex.py deleted
- [ ] Phase 6: Documentation updated
- [ ] All tests passing (pytest)
- [ ] Type checking clean (mypy)
- [ ] Linting clean (ruff)
- [ ] No import pattern violations (pre-commit hooks)
- [ ] Coverage maintained or improved
- [ ] CHANGELOG updated
- [ ] Migration guide published

### Metrics

**Before Migration:**
- Import patterns: 8 unique patterns
- Files using canonical pattern: 179 (91.3%)
- Files needing migration: 16 (8.2%)
- Duplicate implementations: 3 (OnexError), 3 (CoreErrorCode)

**After Migration Target:**
- Import patterns: 1-2 canonical patterns
- Files using canonical pattern: 195 (100%)
- Files needing migration: 0
- Duplicate implementations: 0 (all removed)

---

## Appendices

### Appendix A: Complete File List

**Files using Pattern 1 (canonical, no change needed):** 179 files

See grep output: `grep -r "from omnibase_core.exceptions.onex_error import OnexError" src/ -l`

**Files needing migration (Pattern 2-4):** 16 files

1. `src/omnibase_core/infrastructure/node_base.py`
2. `src/omnibase_core/infrastructure/node_effect.py`
3. `src/omnibase_core/infrastructure/node_compute.py`
4. `src/omnibase_core/infrastructure/node_reducer.py`
5. `src/omnibase_core/infrastructure/node_orchestrator.py`
6. `src/omnibase_core/infrastructure/node_core_base.py`
7. `src/omnibase_core/utils/util_contract_loader.py`
8. `src/omnibase_core/container/container_service_resolver.py`
9. `src/omnibase_core/models/nodes/model_node_configuration_value.py`
10. `src/omnibase_core/models/metadata/model_metadata_node_collection.py`
11. `src/omnibase_core/models/validation/model_migration_conflict_union.py`
12. `src/omnibase_core/models/common/model_flexible_value.py`
13. `src/omnibase_core/__init__.py`
14. `src/omnibase_core/errors/__init__.py` (update exports)
15. `src/omnibase_core/errors/error_onex.py` (DELETE)
16. `src/omnibase_core/errors/error_document_freshness.py` (verify imports)

### Appendix B: Error Code Mapping

| OLD (CoreErrorCode) | NEW (EnumCoreErrorCode) |
|---------------------|-------------------------|
| VALIDATION_ERROR | VALIDATION_ERROR |
| OPERATION_FAILED | OPERATION_FAILED |
| NOT_FOUND | NOT_FOUND |
| CONFIGURATION_ERROR | CONFIGURATION_ERROR |
| DEPENDENCY_ERROR | DEPENDENCY_ERROR |
| NETWORK_ERROR | NETWORK_ERROR |
| TIMEOUT_ERROR | TIMEOUT_ERROR |
| PERMISSION_ERROR | PERMISSION_ERROR |
| RESOURCE_ERROR | RESOURCE_ERROR |
| INTERNAL_ERROR | INTERNAL_ERROR |
| IMPORT_ERROR | *(not in EnumCoreErrorCode, map to INTERNAL_ERROR)* |

### Appendix C: Signature Comparison

**OLD (errors.error_codes.OnexError):**
```python
OnexError(
    message: str,
    error_code: OnexErrorCode | str | None = None,
    status: EnumOnexStatus = EnumOnexStatus.ERROR,
    correlation_id: UUID | None = None,
    timestamp: datetime | None = None,
    **context: Any
)
```

**NEW (exceptions.onex_error.OnexError):**
```python
OnexError(
    code: EnumCoreErrorCode,
    message: str,
    details: ModelErrorContext | None = None,
    cause: Exception | None = None
)
```

**Key Differences:**
1. `error_code` → `code` (parameter name)
2. No `status`, `correlation_id`, `timestamp` in simple version
3. `**context` → `details: ModelErrorContext`
4. Added `cause` for exception chaining

---

## Summary

**Current State:**
- 196 import statements across 195 files
- 8 different import patterns
- 3 duplicate OnexError implementations
- 91.3% already using working pattern (exceptions.onex_error)
- 8.2% using broken/deprecated patterns

**Recommended Action:**
Standardize on **exceptions.onex_error** pattern (Option B)

**Migration Scope:**
- 16 files need changes
- 6-7 hours estimated effort
- Medium risk (mostly straightforward)
- Can parallelize most work

**Expected Outcome:**
- Single canonical import pattern
- Remove all duplicates
- 100% of files using working, lightweight implementation
- Better separation of concerns (exceptions vs error codes vs enums)
