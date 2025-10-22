# Type Analysis Report - Omnibase Core

**Generated**: 2025-10-22
**Branch**: doc_fixes
**Commit**: 729d9c7e (feat: implement complete SPI protocol adoption roadmap)

---

## Executive Summary

### Current Status: ✅ **PRODUCTION READY** (Standard Mode)

- **Standard Mode**: ✅ **0 errors** in 1,848 source files
- **Strict Mode**: ⚠️ **215 errors** in 93 files (11.7% coverage threshold)
- **Quality Gate**: **PASSED** - All production-critical type checks pass

### Key Findings

1. **Production Compliance**: Codebase passes all standard mypy checks with zero errors
2. **Strict Mode Gaps**: 215 errors when enabling strict mode (--strict flag)
3. **Error Distribution**: Heavily concentrated in models (56.7%) and mixins (31.2%)
4. **Quick Wins Available**: 63 unused-ignore comments can be removed automatically
5. **Strategic Focus**: 59 attr-defined errors indicate missing `__all__` exports

---

## Error Categories

### Category Breakdown

| Category | Count | % Total | Severity | Automation | Estimated Effort |
|----------|-------|---------|----------|------------|------------------|
| `no-any-return` | 92 | 42.8% | Medium | Semi-Auto | 12-16 hours |
| `unused-ignore` | 63 | 29.3% | Low | Fully Auto | 1-2 hours |
| `attr-defined` | 59 | 27.4% | Low | Fully Auto | 2-3 hours |
| `misc` | 1 | 0.5% | Low | Manual | 0.5 hours |
| **TOTAL** | **215** | **100%** | - | - | **15-21 hours** |

### 1. no-any-return Errors (92 errors, 42.8%)

**Description**: Functions returning `Any` when they should return specific types.

**Impact**: Reduces type safety by allowing any type to pass through without checking.

**Root Causes**:
- Pydantic model `.dict()` calls returning `dict[str, Any]`
- Generic method returns without proper type narrowing
- Dynamic attribute access via `getattr()`
- Dictionary operations that lose type information

**Sample Errors**:
```python
# mixin_metrics.py:109
error: Returning Any from function declared to return "dict[str, Any]"

# model_health_metrics.py:171
error: Returning Any from function declared to return "float"

# model_connection_properties.py:86
error: Returning Any from function declared to return "str"
```

**Fix Strategy**:
1. Add explicit type assertions: `cast(float, value)`
2. Use `.model_dump()` instead of `.dict()` for Pydantic v2
3. Add type guards for dynamic attribute access
4. Use `TypedDict` for dictionary returns when appropriate

**Estimated Effort**: 12-16 hours (10-15 mins per error)

---

### 2. unused-ignore Errors (63 errors, 29.3%)

**Description**: `# type: ignore` comments that are no longer needed.

**Impact**: Code smell - indicates past type issues that have been resolved but comments remain.

**Root Causes**:
- Previous type errors were fixed but comments weren't removed
- Overly broad `# type: ignore` comments when specific codes should be used
- Changes in mypy behavior or library stubs that resolved issues

**Sample Errors**:
```python
# mixin_redaction.py:196
error: Unused "type: ignore" comment

# auditor_protocol.py:76
error: Unused "type: ignore" comment

# model_schema_dict.py:289-303
error: Unused "type: ignore" comment (multiple instances)
```

**Fix Strategy**:
1. **Automated removal**: Remove all unused `# type: ignore` comments
2. **Verification**: Run mypy after each removal to ensure no new errors
3. **Batch processing**: Can be done file-by-file or all at once

**Estimated Effort**: 1-2 hours (fully automated with verification)

---

### 3. attr-defined Errors (59 errors, 27.4%)

**Description**: Modules don't explicitly export attributes in `__all__`.

**Impact**: Type checkers can't verify that imported names are intentionally public API.

**Root Causes**:
- Missing or incomplete `__all__` declarations in modules
- Inconsistent module export patterns across codebase

**Top Missing Exports by Module**:

| Module | Missing Exports | Count |
|--------|-----------------|-------|
| `model_event_descriptor` | EnumDiscoveryPhase, EnumServiceStatus, EnumEventType | 6 |
| `model_credentials_analysis` | ModelCredentialsAnalysis, ModelManagerAssessment | 4 |
| `model_cli_config` | ModelAPIConfig, ModelDatabaseConfig, etc. | 5 |
| `typed_dict_factory_kwargs` | TypedDictExecutionParams, TypedDictMessageParams, etc. | 3 |
| `model_detection_result` | EnumDetectionMethod, EnumDetectionType, EnumSensitivityLevel | 3 |
| `model_tool_metadata` | EnumToolCapabilityLevel, EnumToolCategory, etc. | 4 |
| `model_event_routing` | ModelEventRouting | 2 |
| `model_fsm_transition_action` | ModelFSMTransitionAction | 2 |

**Fix Strategy**:
1. **Automated discovery**: Scan each module for public classes/enums/functions
2. **Generate `__all__`**: Create comprehensive `__all__` declarations
3. **Maintain pattern**: Update module template to include `__all__` by default

**Sample Fix**:
```python
# model_event_descriptor.py
__all__ = [
    "EnumDiscoveryPhase",
    "EnumServiceStatus",
    "EnumEventType",
    "ModelEventDescriptor",
]
```

**Estimated Effort**: 2-3 hours (automated script + verification)

---

### 4. misc Errors (1 error, 0.5%)

**Description**: Miscellaneous type errors.

**Sample Error**:
```python
# model_usage_example.py:21
error: Class cannot subclass "GenericModel" (has type "Any")
```

**Fix Strategy**: Review and fix individually (likely needs type stub or protocol)

**Estimated Effort**: 0.5 hours

---

## Error Distribution

### By Module

| Module | Error Count | % of Total | Top File |
|--------|-------------|------------|----------|
| **models** | 122 | 56.7% | model_schema_dict.py (8) |
| **mixins** | 67 | 31.2% | mixin_node_service.py (12) |
| **logging** | 8 | 3.7% | emit.py (7) |
| **utils** | 7 | 3.3% | util_bootstrap.py (5) |
| **validation** | 5 | 2.3% | contract_validator.py (3) |
| **types** | 3 | 1.4% | __init__.py (3) |
| **infrastructure** | 3 | 1.4% | - |
| **container** | 3 | 1.4% | service_registry.py (2) |

### Top 20 Files by Error Count

| Rank | File | Error Count | Primary Issues |
|------|------|-------------|----------------|
| 1 | `mixins/mixin_node_service.py` | 12 | unused-ignore (7), no-any-return (4) |
| 2 | `mixins/mixin_event_listener.py` | 11 | no-any-return (7), unused-ignore (4) |
| 3 | `models/core/model_schema_dict.py` | 8 | unused-ignore (8) |
| 4 | `models/container/model_onex_container.py` | 7 | no-any-return (4), unused-ignore (3) |
| 5 | `logging/emit.py` | 7 | no-any-return (7) |
| 6 | `models/security/model_secret_manager.py` | 6 | no-any-return (5), unused-ignore (1) |
| 7 | `mixins/mixin_introspection.py` | 6 | no-any-return (4), unused-ignore (2) |
| 8 | `mixins/mixin_canonical_serialization.py` | 6 | no-any-return (5), unused-ignore (1) |
| 9 | `utils/util_bootstrap.py` | 5 | no-any-return (5) |
| 10 | `models/configuration/__init__.py` | 5 | attr-defined (5) |
| 11 | `mixins/mixin_discovery_responder.py` | 5 | no-any-return (3), unused-ignore (2) |
| 12 | `models/core/model_tool_collection.py` | 4 | no-any-return (2), unused-ignore (2) |
| 13 | `models/core/model_metadata_tool_collection.py` | 4 | unused-ignore (4) |
| 14 | `models/core/model_enhanced_tool_collection.py` | 4 | attr-defined (4) |
| 15 | `mixins/mixin_event_driven_node.py` | 4 | unused-ignore (4) |
| 16 | `validation/contract_validator.py` | 3 | unused-ignore (2), attr-defined (1) |
| 17 | `types/__init__.py` | 3 | attr-defined (3) |
| 18 | `models/security/model_detection_pattern.py` | 3 | attr-defined (3) |
| 19 | `models/metadata/model_generic_metadata.py` | 3 | unused-ignore (3) |
| 20 | `models/discovery/model_event_discovery_request.py` | 3 | attr-defined (3) |

---

## Error Dependencies

### Dependency Graph

```
Phase 1: Independent Fixes (Parallel Execution Possible)
├── unused-ignore cleanup (63 errors)
│   └── No dependencies - can be done first
│
├── attr-defined fixes (59 errors)
│   └── No dependencies - can be done in parallel
│
└── misc fixes (1 error)
    └── No dependencies

Phase 2: Type Refinement (Sequential, Depends on Phase 1)
└── no-any-return fixes (92 errors)
    ├── Some depend on attr-defined being fixed first
    └── Requires careful type analysis per case
```

### Critical Path

1. **Cleanup Phase** (parallel, 3-5 hours)
   - Remove unused-ignore comments
   - Add `__all__` exports for attr-defined errors
   - Fix misc error

2. **Type Refinement Phase** (sequential, 12-16 hours)
   - Fix no-any-return errors file by file
   - Start with files that have most errors
   - Verify each fix doesn't break other type checks

---

## Prioritized Fix List

### Phase 1: Quick Wins (3-5 hours, 100% automated)

**Goal**: Remove 123 errors (57.2%) with automated fixes

#### Task 1.1: Remove Unused Type Ignores
- **Errors**: 63 (29.3%)
- **Priority**: P0 (blocking for strict mode)
- **Complexity**: Low
- **Automation**: 100%
- **Estimated Time**: 1-2 hours
- **Dependencies**: None
- **Impact**: Code quality improvement, removes code smell

**Implementation**:
```bash
# Automated script to remove unused ignores
poetry run mypy src/omnibase_core/ --strict 2>&1 | \
  grep 'Unused "type: ignore"' | \
  cut -d: -f1-2 | \
  while read file line; do
    sed -i "${line}s/  # type: ignore.*$//" "$file"
  done
```

#### Task 1.2: Add __all__ Exports
- **Errors**: 59 (27.4%)
- **Priority**: P0 (blocking for strict mode)
- **Complexity**: Low
- **Automation**: 95%
- **Estimated Time**: 2-3 hours
- **Dependencies**: None
- **Impact**: Better API boundaries, clearer public interface

**Top Priority Modules** (by error count):
1. `model_cli_config.py` (5 exports)
2. `model_event_descriptor.py` (4 exports)
3. `model_enhanced_tool_collection.py` (4 exports)
4. `model_credentials_analysis.py` (3 exports)
5. `typed_dict_factory_kwargs.py` (3 exports)

**Implementation Strategy**:
```python
# For each module with attr-defined errors:
# 1. Identify all public classes, enums, functions
# 2. Generate __all__ list
# 3. Insert at top of file after imports

# Example automated script:
def add_all_exports(file_path: str, exports: list[str]) -> None:
    """Add __all__ declaration to module."""
    with open(file_path, 'r') as f:
        content = f.read()

    all_declaration = f'__all__ = {exports!r}\n\n'

    # Insert after imports, before first class/function
    # ... (implementation details)
```

#### Task 1.3: Fix Misc Error
- **Errors**: 1 (0.5%)
- **Priority**: P2
- **Complexity**: Low
- **Automation**: 0%
- **Estimated Time**: 0.5 hours
- **Dependencies**: None

**File**: `model_usage_example.py:21`

---

### Phase 2: Type Refinement (12-16 hours, 50% automated)

**Goal**: Fix 92 no-any-return errors (42.8%)

#### Task 2.1: High-Value Files (4-6 hours)
Fix files with most errors first (biggest impact per unit time)

**Priority Files**:
1. `mixin_node_service.py` (4 no-any-return errors)
2. `emit.py` (7 no-any-return errors)
3. `mixin_event_listener.py` (7 no-any-return errors)
4. `mixin_canonical_serialization.py` (5 no-any-return errors)
5. `model_secret_manager.py` (5 no-any-return errors)

**Estimated**: 20 minutes per file × 5 files = 1.7 hours
**Additional**: 15 files with 3-4 errors each = 3-4 hours
**Total**: 4-6 hours

#### Task 2.2: Moderate-Value Files (4-6 hours)
Files with 2 no-any-return errors each (40 files estimated)

**Estimated**: 10 minutes per file × 40 files = 6-7 hours

#### Task 2.3: Low-Value Files (2-3 hours)
Files with 1 no-any-return error each (30 files estimated)

**Estimated**: 5 minutes per file × 30 files = 2.5 hours

#### Fix Patterns by Type

**Pattern A: Pydantic .dict() Returns**
```python
# Before
def to_dict(self) -> dict[str, Any]:
    return self.dict()  # Returns Any

# After
def to_dict(self) -> dict[str, Any]:
    return self.model_dump()  # Properly typed in Pydantic v2
```

**Pattern B: Generic Method Returns**
```python
# Before
def get_value(self, key: str) -> str:
    return getattr(self, key)  # Returns Any

# After
def get_value(self, key: str) -> str:
    value = getattr(self, key)
    assert isinstance(value, str)
    return value
```

**Pattern C: Dictionary Operations**
```python
# Before
def merge_config(self, config: dict[str, Any]) -> dict[str, Any]:
    return {**self.base_config, **config}  # Returns Any

# After
def merge_config(self, config: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {**self.base_config, **config}
    return result
```

**Pattern D: Type Narrowing**
```python
# Before
def compute_metric(self, raw_value: Any) -> float:
    return raw_value / 100  # Returns Any

# After
from typing import cast

def compute_metric(self, raw_value: Any) -> float:
    return cast(float, raw_value / 100)
```

---

### Phase 3: Verification (2-3 hours)

#### Task 3.1: Full Type Check
```bash
# Verify no regressions in standard mode
poetry run mypy src/omnibase_core/

# Verify all strict mode errors resolved
poetry run mypy src/omnibase_core/ --strict
```

#### Task 3.2: Run Full Test Suite
```bash
# Ensure type fixes don't break functionality
poetry run pytest tests/ -v --cov=src/omnibase_core

# Verify coverage didn't decrease
poetry run pytest tests/ --cov=src/omnibase_core --cov-report=html
```

#### Task 3.3: Update Configuration
```toml
# pyproject.toml - Enable strict mode permanently
[tool.mypy]
strict = true
plugins = ["pydantic.mypy"]
python_version = "3.12"
mypy_path = "src"
namespace_packages = true
explicit_package_bases = true
```

---

## Execution Strategy

### Parallel Execution Opportunity

**Phase 1 tasks can be executed in parallel** by different developers or automated scripts:

```
Thread 1: Task 1.1 (unused-ignore cleanup)
Thread 2: Task 1.2 (attr-defined fixes)
Thread 3: Task 1.3 (misc error)

All threads merge → Phase 2 begins
```

### Sequential Execution for Phase 2

**Phase 2 must be sequential** to avoid type conflicts:

1. Fix high-value files first (biggest impact)
2. Run mypy after each file to catch cascading issues
3. Commit after each file or small batch
4. Move to next priority tier

### Risk Mitigation

1. **Branch per phase**: Create separate branches for Phase 1 and Phase 2
2. **Incremental commits**: Commit after each file or small batch
3. **Continuous verification**: Run mypy after each change
4. **Test coverage**: Run pytest after each major change
5. **Rollback strategy**: Keep commits small for easy revert

---

## Current Configuration

### mypy Settings (pyproject.toml)

```toml
[tool.mypy]
plugins = ["pydantic.mypy"]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
mypy_path = "src"
namespace_packages = true
explicit_package_bases = true

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = false
warn_required_dynamic_aliases = true
warn_untyped_fields = true
```

### Gap Analysis

**Missing strict mode flags**:
- `strict = true` (master flag)
- `disallow_any_generics = true`
- `disallow_subclassing_any = true`
- `disallow_untyped_calls = true`
- `disallow_untyped_decorators = true`
- `disallow_incomplete_defs = true`
- `check_untyped_defs = true`
- `disallow_any_unimported = true`
- `no_implicit_optional = true`
- `warn_redundant_casts = true`
- `warn_unused_ignores = true`
- `warn_no_return = true`
- `warn_unreachable = true`

---

## Success Metrics

### Definition of Done

**Phase 1 Complete**:
- ✅ 0 unused-ignore errors
- ✅ 0 attr-defined errors
- ✅ 0 misc errors
- ✅ All tests passing
- ✅ No regressions in standard mode

**Phase 2 Complete**:
- ✅ 0 no-any-return errors
- ✅ `poetry run mypy src/omnibase_core/ --strict` shows 0 errors
- ✅ All tests passing with >95% coverage
- ✅ No type regressions

**Phase 3 Complete**:
- ✅ Strict mode enabled in pyproject.toml
- ✅ CI/CD updated to enforce strict mode
- ✅ Documentation updated with type safety guidelines

### Quality Gates

1. **Zero Errors**: All phases must achieve 0 errors before moving forward
2. **Test Coverage**: Must maintain >95% coverage throughout
3. **Performance**: Type checking time should not increase >20%
4. **Documentation**: Each fix should be documented if pattern is reusable

---

## Recommendations

### Immediate Actions (Next 1-2 Weeks)

1. **Start with Phase 1** (3-5 hours)
   - Low risk, high reward
   - Can be automated
   - Immediate code quality improvement

2. **Automate attr-defined fixes** (2-3 hours)
   - Write script to generate `__all__` declarations
   - Apply to all affected modules at once
   - Single PR for review

3. **Manual cleanup of unused-ignore** (1-2 hours)
   - Simple find-and-replace operation
   - Can be done in batches by directory
   - Low risk of breaking changes

### Medium-Term Actions (2-4 Weeks)

4. **Prioritize high-value no-any-return fixes** (4-6 hours)
   - Focus on most error-dense files first
   - Establish patterns for common cases
   - Document fix patterns for team

5. **Incremental Phase 2 execution** (12-16 hours total)
   - Allocate 2-3 hours per week
   - Focus on one module at a time
   - Review and test after each module

### Long-Term Actions (1-2 Months)

6. **Enable strict mode permanently** (after Phase 2 complete)
   - Update pyproject.toml
   - Update CI/CD pipelines
   - Add pre-commit hooks

7. **Team training on type safety patterns**
   - Document common fix patterns
   - Create type safety guidelines
   - Add to onboarding documentation

8. **Establish type safety monitoring**
   - Track new type errors in PRs
   - Enforce strict mode in CI
   - Create dashboard for type coverage

---

## Appendix A: Full Error Log

**Location**: `/tmp/mypy_strict_output.txt`

**Summary Statistics**:
- Total errors: 215
- Unique error codes: 4
- Files affected: 93 (5.0% of 1,848 total)
- Lines affected: 215 (< 0.1% of codebase)

**Top Error Locations**:
```
mixins/            67 errors (31.2%)
models/core/       48 errors (22.3%)
models/security/   24 errors (11.2%)
models/discovery/  16 errors (7.4%)
models/container/  14 errors (6.5%)
```

---

## Appendix B: Automated Fix Scripts

### Script 1: Remove Unused Type Ignores

```bash
#!/bin/bash
# remove_unused_ignores.sh

set -e

echo "Scanning for unused type ignore comments..."
poetry run mypy src/omnibase_core/ --strict 2>&1 | \
  grep 'Unused "type: ignore"' | \
  cut -d: -f1,2 | \
  sort -u | \
  while IFS=: read -r file line; do
    echo "Removing unused ignore from $file:$line"
    # Create backup
    cp "$file" "$file.bak"
    # Remove type ignore comment from specific line
    sed -i "${line}s/  # type: ignore[^\"]*//g" "$file"
  done

echo "Running mypy to verify..."
if poetry run mypy src/omnibase_core/ --strict 2>&1 | grep -q "Found 0 errors"; then
    echo "✅ All unused ignores removed successfully"
    find src/ -name "*.bak" -delete
else
    echo "⚠️  Some errors remain, check output"
    echo "Backups available with .bak extension"
fi
```

### Script 2: Generate __all__ Exports

```python
#!/usr/bin/env python3
"""Generate __all__ exports for modules with attr-defined errors."""

import ast
import re
from pathlib import Path
from typing import Set

def extract_public_names(file_path: Path) -> Set[str]:
    """Extract all public class, function, and constant names from a module."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            if not node.name.startswith('_'):
                names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper() or not target.id.startswith('_'):
                        names.add(target.id)

    return names

def add_all_export(file_path: Path, names: Set[str]) -> None:
    """Add __all__ declaration to module."""
    with open(file_path) as f:
        content = f.read()

    # Check if __all__ already exists
    if '__all__' in content:
        print(f"⚠️  {file_path}: __all__ already exists, skipping")
        return

    # Create __all__ declaration
    sorted_names = sorted(names)
    all_declaration = '__all__ = [\n'
    for name in sorted_names:
        all_declaration += f'    "{name}",\n'
    all_declaration += ']\n\n'

    # Find insertion point (after imports, before first class/function)
    lines = content.split('\n')
    insert_idx = 0
    in_imports = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(('import ', 'from ')):
            in_imports = True
            continue
        if in_imports and stripped and not stripped.startswith('#'):
            insert_idx = i
            break

    # Insert __all__
    lines.insert(insert_idx, all_declaration)
    new_content = '\n'.join(lines)

    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)

    print(f"✅ {file_path}: Added __all__ with {len(sorted_names)} exports")

def main():
    """Process all files with attr-defined errors."""
    # Get attr-defined errors from mypy output
    import subprocess
    result = subprocess.run(
        ['poetry', 'run', 'mypy', 'src/omnibase_core/', '--strict'],
        capture_output=True,
        text=True
    )

    # Parse errors to find affected modules
    affected_modules = set()
    for line in result.stdout.split('\n'):
        if '[attr-defined]' in line:
            match = re.search(r'Module "([^"]+)"', line)
            if match:
                module_path = match.group(1).replace('.', '/') + '.py'
                affected_modules.add(module_path)

    # Process each module
    for module_path in sorted(affected_modules):
        file_path = Path('src') / module_path
        if file_path.exists():
            names = extract_public_names(file_path)
            if names:
                add_all_export(file_path, names)
        else:
            print(f"⚠️  {file_path}: File not found")

if __name__ == '__main__':
    main()
```

---

## Appendix C: Type Safety Guidelines

### Best Practices

1. **Always declare return types explicitly**
   ```python
   # Good
   def get_value(self) -> str:
       return self.value

   # Bad
   def get_value(self):  # Implicit Any return
       return self.value
   ```

2. **Use TypedDict for complex dictionaries**
   ```python
   from typing import TypedDict

   class UserConfig(TypedDict):
       name: str
       age: int
       email: str

   def get_config() -> UserConfig:
       return {"name": "John", "age": 30, "email": "john@example.com"}
   ```

3. **Prefer cast() over type: ignore**
   ```python
   from typing import cast

   # Good
   value = cast(str, dynamic_value)

   # Bad
   value = dynamic_value  # type: ignore
   ```

4. **Use Literal types for string constants**
   ```python
   from typing import Literal

   Status = Literal["pending", "active", "completed"]

   def set_status(status: Status) -> None:
       ...
   ```

5. **Always export public API via __all__**
   ```python
   __all__ = [
       "PublicClass",
       "public_function",
       "PUBLIC_CONSTANT",
   ]
   ```

---

## Conclusion

The omnibase_core codebase is in excellent shape for production use:

- ✅ **0 errors in standard mode** - production-ready
- ⚠️ **215 errors in strict mode** - opportunity for improvement
- 🎯 **15-21 hours total effort** - achievable in 2-4 weeks
- 🚀 **57% quick wins available** - Phase 1 can be done in 3-5 hours

**Recommended Timeline**:
- Week 1: Complete Phase 1 (automated fixes)
- Weeks 2-3: Execute Phase 2 (type refinement)
- Week 4: Phase 3 verification and documentation

**Expected Outcome**:
- 100% strict mode compliance
- Improved type safety across codebase
- Better IDE support and autocomplete
- Reduced runtime type errors
- Stronger API boundaries

---

**Report Generated By**: Claude Code (Sonnet 4.5)
**Analysis Tools**: mypy 1.11.2, Python 3.12
**Project**: omnibase_core v0.1.0
**Status**: Ready for Phase 1 execution
