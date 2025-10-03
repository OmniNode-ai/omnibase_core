# Naming Validator Investigation Report

## Summary
The naming validator in `scripts/validation/validate_naming.py` is **NOT catching error file naming violations** in the `src/omnibase_core/errors/` directory due to three critical gaps in the validation logic.

## Files Examined
- `src/omnibase_core/errors/core_errors.py`
- `src/omnibase_core/errors/document_freshness_errors.py`
- `src/omnibase_core/errors/onex_error.py`

## Root Causes

### 1. No Naming Pattern Defined for Errors/Exceptions
**Issue**: The validator only defines patterns for:
- Models (`Model*`)
- Protocols (`Protocol*`)
- Enums (`Enum*`)
- Services (`Service*`)
- Mixins (`Mixin*`)
- Nodes (`Node*`)
- TypedDicts (`TypedDict*`)

**Impact**: There is **NO category for error/exception classes** in `NAMING_PATTERNS`, so the validator has no rules to enforce for these files.

**Current State**:
```python
NAMING_PATTERNS = {
    "models": {...},
    "protocols": {...},
    "enums": {...},
    # NO "errors" category!
}
```

### 2. Enum Classes Not Detected

**Classes in errors/**:
- `CLIExitCode`
- `OnexErrorCode`
- `CoreErrorCode`
- `RegistryErrorCode`

**Expected**: Should be named `Enum*` (e.g., `EnumCLIExitCode`)

**Why Not Caught**: The `_should_match_pattern()` method checks if class names contain indicators:
```python
"enums": ["enum", "choice", "status", "type", "kind"]
```

None of the `*ErrorCode` classes contain these indicators, so:
- `should_match_pattern` returns `False`
- Classes are **never checked** by the validator

**Test Results**:
```
CLIExitCode: should_match=False, matches_pattern=False → NOT CHECKED
OnexErrorCode: should_match=False, matches_pattern=False → NOT CHECKED
CoreErrorCode: should_match=False, matches_pattern=False → NOT CHECKED
```

### 3. Model Classes Not Checked for Directory Location

**Classes in errors/**:
- `ModelOnexError` ✓ (correctly named)
- `ModelOnexWarning` ✓ (correctly named)
- `ModelRegistryError` ✓ (correctly named)
- `ModelDocumentFreshnessDatabaseError` ✓ (correctly named)

**Expected**: Should be in `models/` directory, not `errors/`

**Why Not Caught**: The `_validate_all_classes_in_file()` method has a logic flaw:

```python
# Line 212-215
if self._should_match_pattern(node.name, category) and not self._matches_any_valid_pattern(node.name):
    self._check_class_naming(file_path, node, category, rules)
```

For `ModelOnexError`:
- `should_match_pattern("ModelOnexError", "models")` = `True` (contains "model")
- `matches_any_valid_pattern("ModelOnexError")` = `True` (matches `^Model[A-Z][A-Za-z0-9]*$`)
- Condition: `True AND NOT True` = **False**
- Result: `_check_class_naming()` is **NEVER CALLED**

The validator assumes correctly-named classes don't need location validation, which is incorrect.

### 4. File Naming Not Validated

**Files**:
- `core_errors.py` ❌ (no standard prefix)
- `document_freshness_errors.py` ❌ (no standard prefix)
- `onex_error.py` ❌ (no standard prefix)

**Why Not Caught**:
1. No `error_` prefix pattern defined in `NAMING_PATTERNS`
2. Files don't start with any recognized prefix (`model_`, `enum_`, etc.)
3. No `errors` directory rule in `NAMING_PATTERNS`
4. File naming validation only triggers for files matching expected patterns

## What the Validator Expects (Current Behavior)

### For Enums:
- **Class Pattern**: `^Enum[A-Z][A-Za-z0-9]*$`
- **File Pattern**: `enum_*.py`
- **Directory**: `enums/`
- **Detection**: Only if class name contains ["enum", "choice", "status", "type", "kind"]

### For Models:
- **Class Pattern**: `^Model[A-Z][A-Za-z0-9]*$`
- **File Pattern**: `model_*.py`
- **Directory**: `models/`
- **Location Check**: ❌ BROKEN (skipped if class already matches pattern)

### For Errors:
- **Class Pattern**: ❌ UNDEFINED
- **File Pattern**: ❌ UNDEFINED
- **Directory**: ❌ UNDEFINED
- **Detection**: ❌ NOT IMPLEMENTED

## Validation Logic Flow (Simplified)

```
For each category (models, enums, etc.):
  1. Check files with matching prefix (e.g., model_*.py)
  2. Check files in matching directory (e.g., models/)
  3. Check all other Python files:
     - For each class:
       - Should it match this category? (heuristic check)
       - Does it already match ANY valid pattern? (regex check)
       - If YES and NO: validate it ← BUG: skips if YES and YES
```

## Violations That Should Be Flagged (But Aren't)

### Enum Violations:
```
❌ CLIExitCode (Line 54 in core_errors.py)
   Expected: EnumCLIExitCode
   File should be: enum_cli_exit_code.py in enums/

❌ OnexErrorCode (Line 103 in core_errors.py)
   Expected: EnumOnexErrorCode
   File should be: enum_onex_error_code.py in enums/

❌ CoreErrorCode (Line 139 in core_errors.py)
   Expected: EnumCoreErrorCode
   File should be: enum_core_error_code.py in enums/

❌ RegistryErrorCode (Line 937 in core_errors.py)
   Expected: EnumRegistryErrorCode
   File should be: enum_registry_error_code.py in enums/

❌ CoreErrorCode (Line 12 in onex_error.py) [duplicate]
   Expected: EnumCoreErrorCode
   File should be: enum_core_error_code.py in enums/
```

### Model Location Violations:
```
⚠️  ModelOnexError (Line 348 in core_errors.py)
   Correctly named, but should be in models/ directory
   Expected location: src/omnibase_core/models/model_onex_error.py

⚠️  ModelOnexWarning (Line 401 in core_errors.py)
   Correctly named, but should be in models/ directory
   Expected location: src/omnibase_core/models/model_onex_warning.py

⚠️  ModelRegistryError (Line 968 in core_errors.py)
   Correctly named, but should be in models/ directory
   Expected location: src/omnibase_core/models/model_registry_error.py

⚠️  ModelDocumentFreshnessDatabaseError (Line 215 in document_freshness_errors.py)
   Correctly named, but should be in models/ directory
   Expected location: src/omnibase_core/models/model_document_freshness_database_error.py
```

### File Naming Violations:
```
❌ core_errors.py
   Should follow pattern: error_* or model_* or enum_* (depending on contents)

❌ document_freshness_errors.py
   Should follow pattern: error_* (if error classes) or model_* (if model classes)

❌ onex_error.py
   Should follow pattern: error_* or enum_*
```

## Recommended Fixes

### Option 1: Add Error Category to Validator
```python
NAMING_PATTERNS = {
    # ... existing patterns ...
    "errors": {
        "pattern": r"^[A-Z][A-Za-z0-9]*Error$",  # Or ^Error[A-Z]...
        "file_prefix": "error_",
        "description": "Error classes should end with 'Error'",
        "directory": "errors",
    },
}
```

### Option 2: Fix Directory Validation Logic
```python
# In _validate_all_classes_in_file, change line 212-215:
if self._should_match_pattern(node.name, category):
    if self._matches_any_valid_pattern(node.name):
        # Class is correctly named, but check if it's in the right directory
        self._check_class_naming(file_path, node, category, rules)
    else:
        # Class should match but doesn't
        self._check_class_naming(file_path, node, category, rules)
```

### Option 3: Improve Enum Detection Heuristics
```python
category_indicators = {
    "enums": ["enum", "choice", "status", "type", "kind", "code"],  # Add "code"
    # ...
}
```

## Conclusion

The validator has **three critical gaps**:

1. **No error/exception category** → Error files completely ignored
2. **Broken directory validation** → Model classes in wrong location not flagged
3. **Weak enum detection** → *ErrorCode classes not recognized as enums

These gaps combine to create a blind spot where the entire `errors/` directory escapes validation, despite containing multiple naming violations.
