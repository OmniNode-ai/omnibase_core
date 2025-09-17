# ONEX Scripts Directory

This directory contains development tools, validation scripts, and shared pre-commit hooks for the ONEX ecosystem.

## 📁 Directory Structure

```
scripts/
├── README.md                          # This file
├── shared/                            # Shared tools for all omni* repositories
│   ├── pre-commit/                   # Pre-commit hook templates
│   │   ├── onex-core-hooks.yaml     # Core ONEX validation hooks
│   │   ├── onex-python-hooks.yaml   # Python-specific hooks
│   │   └── integration-guide.md      # How to integrate hooks
│   └── validation/                    # ALL validation scripts (shareable)
│       ├── validate_onex_standards.py        # Comprehensive ONEX validation
│       ├── validate_ecosystem.py             # Cross-repository validation
│       ├── validate_naming.py                # Naming convention validation
│       ├── validate_structure.py             # Repository structure validation
│       ├── audit_optional.py                 # Optional type usage audit
│       ├── audit_protocol_duplicates.py      # Protocol duplication detection
│       ├── migrate_protocols_safe.py         # Protocol migration (any repo)
│       ├── CENTRALIZED_VALIDATION_STRATEGY.md
│       └── REPOSITORY_INTEGRATION_GUIDE.md
├── active/                           # Current development scripts (omnibase_core specific)
│   ├── fix-imports.py
│   ├── intelligence_hook.py
│   ├── validate-contracts.py
│   ├── validate-downstream.py
│   ├── validate-imports.py
│   ├── validate-no-backward-compatibility.py
│   ├── validate-no-manual-yaml.py
│   ├── validate-pydantic-patterns.py
│   ├── validate-stability.py
│   ├── validate-string-versions.py
│   └── validate-union-usage.py
├── spi-copy/                         # SPI-related documentation
└── templates/                        # Templates and examples
```

## 🚀 Quick Start

### For omnibase_core Development
```bash
# Run all validations
poetry run python scripts/validation/validate-contracts.py
poetry run python scripts/validation/validate_structure.py . omnibase_core
poetry run python scripts/validation/validate_naming.py .

# Fix imports
# fix-imports.py has been removed as it's no longer needed
```

### For Other omni* Repositories

**IMPORTANT**: Other repositories should use the **installed Python package**, not copy any files.

Since `omnibase_core` is a dependency, just import the validation functions directly:
```python
# In your .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-onex-structure
        name: ONEX Repository Structure Validation
        entry: python -c "
from omnibase_core.validation import validate_repository_structure;
import sys;
result = validate_repository_structure('.', 'your_repo_name');
sys.exit(0 if result.success else 1)
"
        language: system
        always_run: true
        pass_filenames: false

      - id: validate-onex-naming
        name: ONEX Naming Convention Validation
        entry: python -c "
from omnibase_core.validation import validate_naming_conventions;
import sys;
result = validate_naming_conventions('.');
sys.exit(0 if result.success else 1)
"
        language: system
        always_run: true
        pass_filenames: false
```

Or in your own Python scripts:
```python
from omnibase_core.validation import validate_repository_structure

result = validate_repository_structure(".", "your_repo_name")
if not result.success:
    print("❌ Validation failed:")
    for violation in result.violations:
        print(f"   • {violation}")
    exit(1)
```

## 📋 Script Categories

### 🔍 Validation Scripts (validation/)
- **Structure validation**: Repository structure compliance
- **Naming conventions**: ONEX naming standard enforcement
- **Protocol auditing**: Protocol duplication detection
- **Optional type usage**: Type hint quality auditing

### 🛠 Active Development Scripts (active/)
- **Contract validation**: ONEX contract compliance
- **Import validation**: Import statement verification
- **Pattern validation**: Pydantic and architectural patterns
- **Version validation**: String version anti-pattern detection

### 📦 Shared Tools (shared/)
- **Pre-commit hooks**: Shareable hook configurations
- **Ecosystem validation**: Cross-repository validation
- **Standard compliance**: ONEX framework compliance

### 🔄 Migration Tools (migration/)
- **Model migration**: Domain-specific model migration tools
- **Import updates**: Automated import statement updates

### 📚 Legacy Scripts (legacy/)
- **to_dict migration**: Pydantic v1 to v2 migration scripts
- **Pattern updates**: Legacy pattern modernization
- **Deprecated tools**: Scripts to be removed after cleanup

## 🎯 Integration with Other Repositories

This repository provides shared validation and pre-commit hooks for the entire omni* ecosystem:

- **omnibase_spi**: Independent validation (no omnibase_core dependency)
- **omniagent**: Imports validation from omnibase_core
- **omnibase_infra**: Imports validation from omnibase_core
- **All other omni***: Import shared tools from omnibase_core

See `scripts/validation/REPOSITORY_INTEGRATION_GUIDE.md` for detailed integration instructions.

## 🔧 Development Workflow

1. **Add new validation**: Place in `scripts/validation/`
2. **Create shared hooks**: Place in `scripts/hooks/`
3. **Add intelligence tools**: Place in `scripts/intelligence/`
3. **Test locally**: Run script on omnibase_core
4. **Update pre-commit**: Add to `.pre-commit-config.yaml`
5. **Document**: Update this README and integration guides

## 📝 Pre-commit Hook Usage

The shared pre-commit hooks ensure consistency across all repositories:

```yaml
# In other omni* repositories
repos:
  - repo: local
    hooks:
      - id: onex-standards
        name: ONEX Standards Validation
        entry: python -c "from omnibase_core.validation import validate_onex_standards; validate_onex_standards('.')"
        language: system
        always_run: true
```

## 🚨 Important Notes

- **Never modify legacy scripts** - they will be removed after cleanup
- **Test all validation scripts** before adding to pre-commit
- **Keep shared tools generic** - repository-specific logic goes in repository scripts
- **Document all new scripts** in this README
- **Follow ONEX standards** in all script implementations

## 🔄 Migration Status

- ✅ Validation framework centralized
- ✅ Pre-commit hooks organized
- 🔄 Legacy script cleanup (in progress)
- 📋 Shared tool templates (planned)
- 📋 Cross-repository testing (planned)
