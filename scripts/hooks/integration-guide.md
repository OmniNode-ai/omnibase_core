# ONEX Pre-commit Hook Integration Guide

This guide shows how to integrate ONEX validation into any omni* repository.

## 🚀 Quick Integration

Since `omnibase_core` is already a dependency, just import the validation functions directly in your hooks.

### Update .pre-commit-config.yaml

Create or update your `.pre-commit-config.yaml`:

```yaml
# Standard file formatting hooks
repos:
  # YAML formatting
  - repo: https://github.com/google/yamlfmt
    rev: v0.17.2
    hooks:
      - id: yamlfmt
        args: [--formatter, retain_line_breaks=true]
        exclude: ^work_tickets/

  # Essential file formatting
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
        args: [--markdown-linebreak-ext=md]
      - id: end-of-file-fixer
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=1000]

# ONEX Core Framework Hooks (REQUIRED)
repos:
  - repo: local
    hooks:
      # Repository structure validation
      - id: validate-repository-structure
        name: ONEX Repository Structure Validation
        entry: python -c "
from omnibase_core.validation import validate_repository_structure;
import sys;
result = validate_repository_structure('.');
if not result.success:
    print('❌ Repository structure validation failed:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ Repository structure validation passed')
"
        language: system
        always_run: true
        pass_filenames: false
        stages: [commit]

      # Naming convention validation
      - id: validate-naming-conventions
        name: ONEX Naming Convention Validation
        entry: python -c "
from omnibase_core.validation import validate_naming_conventions;
import sys;
result = validate_naming_conventions('.');
if not result.success:
    print('❌ Naming convention validation failed:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ Naming convention validation passed')
"
        language: system
        always_run: true
        pass_filenames: false
        stages: [commit]

      # String version anti-pattern detection
      - id: validate-string-versions
        name: ONEX String Version Anti-Pattern Detection
        entry: python -c "
from omnibase_core.validation import validate_no_string_versions;
import sys;
result = validate_no_string_versions('.');
if not result.success:
    print('❌ String version anti-patterns found:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ No string version anti-patterns found')
"
        language: system
        pass_filenames: true
        files: ^.*\.(py|yaml|yml)$
        stages: [commit]

      # Backward compatibility anti-pattern detection
      - id: validate-no-backward-compatibility
        name: ONEX Backward Compatibility Anti-Pattern Detection
        entry: python -c "
from omnibase_core.validation import validate_no_backward_compatibility;
import sys;
result = validate_no_backward_compatibility('.');
if not result.success:
    print('❌ Backward compatibility anti-patterns found:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ No backward compatibility anti-patterns found')
"
        language: system
        pass_filenames: true
        files: ^.*\.py$
        exclude: ^(scripts/.*|archived/.*)$
        stages: [commit]

# ONEX Python Development Hooks (For Python repositories)
  # Python Code Formatting
  - repo: https://github.com/psf/black
    rev: 25.1.0
    hooks:
      - id: black
        name: Black Python Formatter
        args: [--line-length, "88", --target-version, py311]

  # Python Import Sorting
  - repo: https://github.com/pycqa/isort
    rev: 6.0.1
    hooks:
      - id: isort
        name: isort Import Sorter
        args: [--profile, black, --line-length, "88"]

  # Python Type Checking via Poetry
  - repo: local
    hooks:
      - id: mypy-poetry
        name: MyPy Type Checking (via Poetry)
        entry: poetry run mypy
        language: system
        types: [python]
        args: [
          --ignore-missing-imports,
          --show-error-codes,
          --no-strict-optional,
          --no-error-summary,
          --follow-imports=skip,
          --config-file=mypy.ini
        ]
        # CUSTOMIZE: Update file patterns for your repository structure
        files: ^src/.*/(core|model|enums|exceptions|decorators).*\.py$
        exclude: ^(tests/|.*examples.*|.*contracts.*effect).*\.py$

# Configuration
ci:
  autofix_commit_msg: |
    [pre-commit.ci] auto fixes for {repository_name}

    for more information, see https://pre-commit.ci
  autofix_prs: true
  autoupdate_schedule: weekly
  submodules: false
```

### 3. Update pyproject.toml Dependencies

Ensure omnibase_core dependency:

```toml
[tool.poetry.dependencies]
python = "^3.11"
omnibase_core = "*"  # or specific version like "^1.0.0"
```

### 4. Install and Test

```bash
# Install pre-commit
poetry add --group dev pre-commit

# Install hooks
poetry run pre-commit install

# Test hooks on all files
poetry run pre-commit run --all-files

# Test hooks on staged files
git add .
poetry run pre-commit run
```

## 🎯 Repository-Specific Customization

### For omniagent (Agent-focused repository)

```yaml
# Additional agent-specific validation
repos:
  - repo: local
    hooks:
      - id: validate-agent-patterns
        name: Agent Pattern Validation
        entry: python -c "
from omnibase_core.validation import validate_agent_patterns;
import sys;
result = validate_agent_patterns('.');
if not result.success:
    print('❌ Agent pattern violations found:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ Agent pattern validation passed')
"
        language: system
        files: ^src/.*agent.*\.py$
        stages: [commit]
```

### For omnibase_infra (Infrastructure repository)

```yaml
# Additional infrastructure-specific validation
repos:
  - repo: local
    hooks:
      - id: validate-infrastructure-patterns
        name: Infrastructure Pattern Validation
        entry: python -c "
from omnibase_core.validation import validate_infrastructure_patterns;
import sys;
result = validate_infrastructure_patterns('.');
if not result.success:
    print('❌ Infrastructure pattern violations found:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ Infrastructure pattern validation passed')
"
        language: system
        files: ^src/.*infra.*\.py$
        stages: [commit]
```

### For repositories with protocols

Add protocol-specific hooks:

```yaml
repos:
  - repo: local
    hooks:
      # Protocol duplication check
      - id: validate-no-protocol-duplicates
        name: ONEX Protocol Duplication Check
        entry: python -c "
from omnibase_core.validation import audit_protocols;
import sys;
result = audit_protocols('.');
if not result.success:
    print('❌ Protocol validation failed:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print(f'✅ Protocol validation passed ({result.protocols_found} protocols found)')
"
        language: system
        always_run: true
        pass_filenames: false
        stages: [commit]

      # SPI duplication check
      - id: check-spi-duplicates
        name: ONEX SPI Duplication Check
        entry: python -c "
import os, sys;
if not os.path.exists('../omnibase_spi'):
    print('⚠️  Skipping SPI check (omnibase_spi not found)');
    sys.exit(0);
from omnibase_core.validation import check_against_spi;
result = check_against_spi('.', '../omnibase_spi');
if not result.success:
    print('⚠️  Duplicates found with SPI:');
    for d in result.exact_duplicates: print(f'   • {d.protocols[0].name}');
    sys.exit(1);
print('✅ No SPI duplicates found')
"
        language: system
        always_run: true
        pass_filenames: false
        stages: [commit]
```

## 🔧 Advanced Configuration

### Custom Validation Rules

Create repository-specific validation:

```python
# scripts/validate_custom.py
from omnibase_core.validation import BaseValidator

class CustomRepoValidator(BaseValidator):
    def validate_custom_patterns(self):
        # Add repository-specific validation logic
        violations = []
        # ... custom validation logic
        return violations

# Use in pre-commit hook
if __name__ == "__main__":
    validator = CustomRepoValidator(".")
    result = validator.validate_custom_patterns()
    if result:
        print("❌ Custom validation failed:")
        for violation in result:
            print(f"   • {violation}")
        sys.exit(1)
    print("✅ Custom validation passed")
```

### File Pattern Customization

Adjust file patterns for your repository structure:

```yaml
# For repositories with different source structure
files: ^lib/.*\.py$              # Instead of ^src/.*\.py$
files: ^packages/.*/src/.*\.py$  # For monorepo structure
files: ^(src|lib|app)/.*\.py$    # Multiple source directories
```

### MyPy Configuration Customization

Adjust MyPy settings per repository:

```yaml
# Stricter type checking for core libraries
args: [
  --strict,
  --show-error-codes,
  --config-file=mypy.ini
]

# More lenient for application code
args: [
  --ignore-missing-imports,
  --show-error-codes,
  --no-strict-optional,
  --config-file=mypy.ini
]
```

## 🚨 Special Cases

### omnibase_spi (No omnibase_core dependency)

omnibase_spi cannot import from omnibase_core due to circular dependencies. Use standalone scripts:

```yaml
# .pre-commit-config.yaml for omnibase_spi
repos:
  - repo: local
    hooks:
      - id: validate-spi-structure
        name: SPI Structure Validation
        entry: python scripts/validation/validate_spi_structure.py
        language: system
        always_run: true
        stages: [commit]
```

### Non-Python repositories

For repositories without Python code, use only file formatting hooks:

```yaml
repos:
  # Standard file formatting only
  - repo: https://github.com/google/yamlfmt
    rev: v0.17.2
    hooks:
      - id: yamlfmt

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-merge-conflict
```

## 📋 Integration Checklist

- [ ] Copy shared hook templates to `.pre-commit-shared/`
- [ ] Add omnibase_core dependency to `pyproject.toml`
- [ ] Create/update `.pre-commit-config.yaml` with ONEX hooks
- [ ] Install pre-commit: `poetry add --group dev pre-commit`
- [ ] Install hooks: `poetry run pre-commit install`
- [ ] Test on all files: `poetry run pre-commit run --all-files`
- [ ] Customize file patterns for repository structure
- [ ] Add repository-specific validation hooks if needed
- [ ] Update CI/CD pipeline to use pre-commit
- [ ] Document repository-specific hook customizations

## 🔄 Maintenance

### Updating Shared Hooks

When omnibase_core updates shared hooks:

```bash
# Update shared hooks
cp -r ../omnibase_core/scripts/hooks/ .pre-commit-shared/

# Update pre-commit hooks
poetry run pre-commit autoupdate

# Test updated hooks
poetry run pre-commit run --all-files
```

### Adding New Validation

1. Add validation function to omnibase_core
2. Update shared hook templates
3. Test in omnibase_core
4. Distribute to other repositories

This integration ensures all omni* repositories maintain consistent ONEX standards while allowing repository-specific customization.
