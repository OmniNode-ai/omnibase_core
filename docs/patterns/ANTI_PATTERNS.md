> **Navigation**: [Home](../index.md) > [Patterns](./README.md) > Anti-Patterns

> **Note**: For authoritative coding standards, see [CLAUDE.md](../../CLAUDE.md).

# ONEX Anti-Patterns Documentation

This document catalogs prohibited patterns in the ONEX framework that compromise type safety, consistency, or maintainability. Each anti-pattern includes detection mechanisms and correct alternatives.

## Table of Contents

1. [String Version Literals](#string-version-literals)
2. [Contributing](#contributing)

---

## String Version Literals (NEVER ALLOWED)

**Severity**: 🔴 Critical
**Detection**: Pre-commit hook `validate-string-versions`
**First Enforced**: October 2025

### Problem Statement

String version literals bypass type safety and introduce runtime parsing failures that could be caught at compile time. They violate ONEX's principle of "fail fast, fail explicitly" and create inconsistent version representations across the codebase.

### ❌ WRONG - String Version Literals

```
# Direct string literals
version = "1.0.0"  # NEVER DO THIS

# In ModelSemVer.parse()
version = ModelSemVer.parse("1.0.0")  # NEVER DO THIS

# In function calls
node.update_version("1.0.0")  # NEVER DO THIS

# In YAML contracts (flat string)
version: "1.0.0"  # NEVER DO THIS
```

### ✅ CORRECT - Structured Versions

```
# Use ModelSemVer constructor
version = ModelSemVer(1, 0, 0)  # CORRECT

# In function calls
node.update_version(ModelSemVer(1, 0, 0))  # CORRECT

# In YAML contracts (structured)
version:
  major: 1
  minor: 0
  patch: 0
```

### Why This Matters

1. **Type Safety**: String versions bypass type checking at both compile and runtime
   - IDE autocomplete doesn't work
   - Mypy cannot validate version objects
   - Refactoring tools miss string literals

2. **Parsing Errors**: Runtime failures instead of compile-time errors
   - `ModelSemVer.parse("1.0.0.0")` fails at runtime
   - `ModelSemVer(1, 0, 0, 0)` fails at type check time

3. **Consistency**: Single source of truth for version representation
   - Structured versions ensure all code uses same format
   - Eliminates ambiguity between "1.0" vs "1.0.0"

4. **Validation**: Structured versions enable validation at construction
   - Major/minor/patch must be integers
   - Prerelease/build metadata validated immediately
   - No silent failures from malformed strings

### Detection Mechanism

The `validate-string-versions` pre-commit hook detects:

1. **ModelSemVer.parse() calls**:
   ```python
   # Detected patterns
   ModelSemVer.parse("1.0.0")
   ModelSemVer.parse(version="2.0.0")
   ModelSemVer.parse(version_str="3.0.0")
   ```

2. **Direct string literals** (semantic version format):
   ```python
   # Detected patterns
   version = "1.0.0"
   "version": "2.0.0"
   update_version("3.0.0")
   ```

3. **YAML flat string versions**:
   ```yaml
   # Detected pattern
   version: "1.0.0"

   # Should be
   version:
     major: 1
     minor: 0
     patch: 0
   ```

### Allowed Exceptions

The following patterns are **explicitly allowed** and will not trigger validation errors:

1. **Docstring Examples**:
   ```python
   def parse_version(version_str: str) -> ModelSemVer:
       """Parse a version string like "1.0.0" into ModelSemVer."""
       # Docstrings can mention "1.0.0" for documentation
       ...
   ```

2. **Regex Patterns**:
   ```python
   # Regex patterns for version validation
   VERSION_PATTERN = r"^\d+\.\d+\.\d+$"
   SEMVER_REGEX = re.compile(r"\d+\.\d+\.\d+")
   ```

3. **Test Fixture Data**:
   ```python
   # In tests/fixtures/ directories
   test_data = {"version": "1.0.0"}  # Allowed in fixtures
   ```

4. **User-facing output strings**:
   ```python
   # Display strings for users
   print(f"Version {version.major}.{version.minor}.{version.patch}")
   logger.info("Current version: 1.0.0")  # OK for logging
   ```

### Migration Guide

**Before**:
```
# Old pattern
from omnibase_core.models.model_semver import ModelSemVer

class MyNode:
    def __init__(self):
        self.version = ModelSemVer.parse("1.0.0")
```

**After**:
```
# New pattern
from omnibase_core.models.model_semver import ModelSemVer

class MyNode:
    def __init__(self):
        self.version = ModelSemVer(1, 0, 0)
```

**YAML Contracts Before**:
```
version: "1.0.0"
```

**YAML Contracts After**:
```
version:
  major: 1
  minor: 0
  patch: 0
```

### Related Documentation

- **ModelSemVer API**: `docs/API_DOCUMENTATION.md#modelsemver`
- **Contract Patterns**: `docs/CONTRACT_PATTERNS.md`
- **Pre-commit Hooks**: `.pre-commit-config.yaml#validate-string-versions`

---

## Contributing

When adding new anti-patterns to this document:

1. **Structure**: Follow the template above (Problem → Wrong → Correct → Why → Detection → Exceptions)
2. **Severity**: Mark as 🔴 Critical, 🟡 Warning, or 🟢 Info
3. **Detection**: Specify the validation mechanism (pre-commit hook, CI check, etc.)
4. **Examples**: Provide clear before/after code examples
5. **Context**: Explain why the pattern is problematic and what principle it violates

### Anti-Pattern Template

```markdown
## [Pattern Name] (NEVER ALLOWED)

**Severity**: 🔴/🟡/🟢
**Detection**: [Hook/Tool name]
**First Enforced**: [Date]

### Problem Statement
[Brief description of the issue]

### ❌ WRONG - [Anti-Pattern]
[Code examples showing incorrect usage]

### ✅ CORRECT - [Proper Pattern]
[Code examples showing correct usage]

### Why This Matters
1. **[Aspect 1]**: [Explanation]
2. **[Aspect 2]**: [Explanation]

### Detection Mechanism
[How violations are caught]

### Allowed Exceptions
[Legitimate use cases if any]

### Migration Guide
[Step-by-step migration instructions]

### Related Documentation
[Links to relevant docs]
```

---

## Document Metadata

- **Version**: 1.0.0
- **Last Updated**: October 16, 2025
- **Maintainer**: ONEX Core Team
- **Status**: Active
