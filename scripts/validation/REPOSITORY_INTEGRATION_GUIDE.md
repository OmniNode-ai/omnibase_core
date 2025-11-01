# Repository Integration Guide
## Using omnibase_core Centralized Protocol Validation

This guide shows how other omni* repositories can integrate with the centralized protocol validation framework in omnibase_core.

## 🎯 Architecture Overview

```text
omnibase_core (Validation Hub)
├── src/omnibase_core/validation/
│   ├── __init__.py                    # Importable validation functions
│   ├── protocol_auditor.py           # Core audit logic
│   ├── protocol_migrator.py          # Migration utilities
│   └── validation_utils.py           # Shared utilities
└── scripts/validation/               # CLI wrappers

Other Repositories (Importers)         omnibase_spi (Special Case)
├── .pre-commit-config.yaml          ├── scripts/validation/
├── scripts/validate_protocols.py    │   ├── spi_protocol_auditor.py
└── pyproject.toml (depends on       │   └── spi-pre-commit-config.yaml
    omnibase_core)                    └── (Independent validation)
```

## 📦 For Other omni* Repositories

Since all repositories except SPI depend on omnibase_core, they can import validation directly.

### 1. Basic Import Usage

```python
# Simple protocol validation
from omnibase_core.validation import audit_protocols

result = audit_protocols(".")
if not result.success:
    print("❌ Protocol violations found!")
    for violation in result.violations:
        print(f"   • {violation}")
    exit(1)
```

### 2. Advanced Validation

```python
from omnibase_core.validation import (
    ProtocolAuditor,
    ProtocolMigrator,
    check_against_spi
)

# Detailed auditing
auditor = ProtocolAuditor(".")
result = auditor.check_current_repository()
auditor.print_audit_summary(result)

# Check for SPI duplicates
duplication_report = check_against_spi(".", "../omnibase_spi")
if not duplication_report.success:
    print("⚠️  Duplicates found with SPI!")

# Plan migration to SPI
migrator = ProtocolMigrator(".", "../omnibase_spi")
plan = migrator.create_migration_plan()
migrator.print_migration_plan(plan)
```

### 3. Pre-commit Integration

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-no-protocol-duplicates
        name: Protocol Duplication Check
        entry: python -c "
from omnibase_core.validation import audit_protocols;
import sys;
result = audit_protocols('.');
if not result.success:
    print('❌ Protocol validation failed:');
    for v in result.violations: print(f'   • {v}');
    sys.exit(1);
print('✅ Protocol validation passed')
"
        language: system
        always_run: true
        stages: [commit]

      - id: check-spi-duplicates
        name: SPI Duplication Check
        entry: python -c "
from omnibase_core.validation import check_against_spi;
import sys;
result = check_against_spi('.', '../omnibase_spi');
if not result.success:
    print('⚠️  Duplicates found with SPI:');
    for d in result.exact_duplicates: print(f'   • {d.protocols[0].name}');
    sys.exit(1);
print('✅ No SPI duplicates found')
"
        language: system
        always_run: true
        stages: [commit]
```

### 4. CLI Script Wrapper

Create `scripts/validate_protocols.py`:

```python
#!/usr/bin/env python3
"""Protocol validation CLI wrapper for this repository."""

import argparse
import sys
from pathlib import Path

# Import from omnibase_core
from omnibase_core.validation import (
    ProtocolAuditor,
    ProtocolMigrator,
    audit_protocols,
    check_against_spi
)

def main():
    parser = argparse.ArgumentParser(description="Validate protocols in this repository")
    parser.add_argument("--mode", choices=["audit", "spi-check", "migration-plan"],
                       default="audit", help="Validation mode")
    parser.add_argument("--spi-path", default="../omnibase_spi",
                       help="Path to omnibase_spi")

    args = parser.parse_args()

    if args.mode == "audit":
        result = audit_protocols(".")
        if result.success:
            print(f"✅ Repository validation passed: {result.protocols_found} protocols found")
        else:
            print(f"❌ Repository validation failed:")
            for violation in result.violations:
                print(f"   • {violation}")
            sys.exit(1)

    elif args.mode == "spi-check":
        result = check_against_spi(".", args.spi_path)
        if result.success:
            print("✅ No duplicates found with SPI")
        else:
            print("⚠️  Duplicates found with SPI:")
            for dup in result.exact_duplicates:
                print(f"   • {dup.protocols[0].name}")
            sys.exit(1)

    elif args.mode == "migration-plan":
        migrator = ProtocolMigrator(".", args.spi_path)
        plan = migrator.create_migration_plan()
        migrator.print_migration_plan(plan)

        if not plan.can_proceed():
            sys.exit(1)

if __name__ == "__main__":
    main()
```

### 5. pyproject.toml Dependency

Ensure your `pyproject.toml` includes omnibase_core:

```toml
[tool.poetry.dependencies]
python = "^3.11"
omnibase_core = "*"  # or specific version
```

### 6. GitHub Actions Integration

```yaml
# .github/workflows/validate-protocols.yml
name: Protocol Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need full history for multi-repo checks

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Validate protocols
        run: |
          poetry run python scripts/validate_protocols.py --mode audit

      - name: Check SPI duplicates
        run: |
          # Clone SPI for comparison
          git clone https://github.com/OmniNode-ai/omnibase_spi ../omnibase_spi
          poetry run python scripts/validate_protocols.py --mode spi-check
```

## 🎯 Repository-Specific Examples

### omniagent Example

```python
# omniagent/scripts/validate_protocols.py
from omnibase_core.validation import audit_protocols, check_against_spi

def validate_omniagent():
    # Agent-specific validation
    result = audit_protocols(".")

    if result.protocols_found > 0:
        print(f"⚠️  omniagent has {result.protocols_found} protocols")
        print("💡 Consider migrating these to omnibase_spi:")

        # Check what would conflict with SPI
        spi_check = check_against_spi(".", "../omnibase_spi")
        for protocol in spi_check.migration_candidates:
            print(f"   • {protocol.name}")

    return result.success

if __name__ == "__main__":
    import sys
    sys.exit(0 if validate_omniagent() else 1)
```

### omnibase_infra Example

```python
# omnibase_infra/scripts/validate_protocols.py
from omnibase_core.validation import ProtocolAuditor

def validate_infrastructure_protocols():
    auditor = ProtocolAuditor(".")
    result = auditor.check_current_repository()

    # Infrastructure-specific checks
    if result.protocols_found > 5:
        print("⚠️  Infrastructure repository has many protocols")
        print("💡 Consider if these should be in omnibase_spi")

    auditor.print_audit_summary(result)
    return result.success

if __name__ == "__main__":
    import sys
    sys.exit(0 if validate_infrastructure_protocols() else 1)
```

## 🔧 Advanced Usage Patterns

### Custom Validation Rules

```python
from omnibase_core.validation import ProtocolAuditor

class CustomRepoAuditor(ProtocolAuditor):
    def check_repository_specific_rules(self):
        """Add repository-specific validation rules."""
        protocols = self._get_protocols()
        violations = []

        for protocol in protocols:
            # Custom rule: Agent protocols must have lifecycle methods
            if "agent" in protocol.name.lower():
                required_methods = ["start", "stop", "get_status"]
                missing = [m for m in required_methods if m not in protocol.methods]
                if missing:
                    violations.append(f"Agent protocol {protocol.name} missing: {missing}")

        return violations

# Usage
auditor = CustomRepoAuditor(".")
custom_violations = auditor.check_repository_specific_rules()
```

### Batch Processing Multiple Repositories

```python
from pathlib import Path
from omnibase_core.validation import ProtocolAuditor

def audit_all_repositories(root_path: Path):
    """Audit all omni* repositories in a directory."""
    results = {}

    for repo_path in root_path.iterdir():
        if repo_path.is_dir() and repo_path.name.startswith("omni"):
            if repo_path.name == "omnibase_spi":
                continue  # SPI uses its own validation

            auditor = ProtocolAuditor(str(repo_path))
            result = auditor.check_current_repository()
            results[repo_path.name] = result

    # Generate ecosystem report
    total_protocols = sum(r.protocols_found for r in results.values())
    print(f"🌐 Ecosystem Summary: {total_protocols} protocols across {len(results)} repositories")

    return results

# Usage
ecosystem_results = audit_all_repositories(Path("../"))
```

## 📋 Migration Checklist

When adding validation to a new repository:

- [ ] Add omnibase_core dependency to pyproject.toml
- [ ] Create scripts/validate_protocols.py wrapper
- [ ] Add pre-commit hooks for validation
- [ ] Update CI/CD pipeline with protocol validation
- [ ] Test validation with existing protocols
- [ ] Document repository-specific validation rules
- [ ] Set up SPI duplication checks

## 🚨 Important Notes

### For omnibase_spi Only
- Cannot import from omnibase_core (circular dependency)
- Must use standalone scripts in `scripts/validation/`
- Has specialized SPI-specific validation rules

### For All Other Repositories
- Import validation functions from omnibase_core
- Use centralized, up-to-date validation logic
- Benefit from ecosystem-wide consistency
- Automatic updates when omnibase_core validation improves

This architecture ensures all repositories have consistent, high-quality protocol validation while maintaining appropriate dependency relationships.
