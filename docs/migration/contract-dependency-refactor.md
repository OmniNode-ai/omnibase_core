# Contract Dependency Model Refactor Migration Guide

## Overview

This guide provides step-by-step migration instructions for teams transitioning from legacy string-based dependencies to the new strongly-typed contract dependency format introduced in PR #19.

**⚠️ BREAKING CHANGES**: This refactor eliminates all backward compatibility for string dependencies in accordance with the ONEX "ZERO BACKWARDS COMPATIBILITY" policy outlined in CLAUDE.md.

## What Changed

### Before (Legacy Format)
```yaml
dependencies:
  - "omnibase_spi.core.protocol_event_bus"
  - "omnibase_spi.core.protocol_health_check"
  - "some_service_module"
```

### After (New Structured Format)
```yaml
dependencies:
  - name: "ProtocolEventBus"
    module: "omnibase_spi.core.protocol_event_bus"
    dependency_type: "PROTOCOL"
    required: true
    version_constraint:
      major: 1
      minor: 0
      patch: 0
  - name: "ProtocolHealthCheck"
    module: "omnibase_spi.core.protocol_health_check"
    dependency_type: "PROTOCOL"
    required: true
  - name: "SomeServiceModule"
    module: "some_service_module"
    dependency_type: "SERVICE"
    required: false
```

## Migration Steps

### 1. Update Contract YAML Files

**For each contract YAML file in your project:**

1. **Locate dependency sections** - Find all `dependencies:` sections in your contract files
2. **Convert each string dependency** to the new structured format using the templates below
3. **Validate dependency types** according to ONEX patterns (see [Dependency Types](#dependency-types))

### 2. Dependency Type Mapping

| Legacy Pattern | New dependency_type | Required Fields |
|---------------|-------------------|-----------------|
| `*protocol*` | `"PROTOCOL"` | name, module, dependency_type |
| `*service*` | `"SERVICE"` | name, module, dependency_type |
| `*module*` | `"MODULE"` | name, module, dependency_type |
| Others | `"EXTERNAL"` | name, module, dependency_type |

### 3. Conversion Templates

#### Protocol Dependency
```yaml
# OLD
dependencies:
  - "omnibase_spi.core.protocol_event_bus"

# NEW
dependencies:
  - name: "ProtocolEventBus"
    module: "omnibase_spi.core.protocol_event_bus"
    dependency_type: "PROTOCOL"
    required: true
    description: "Event bus protocol for inter-node communication"
```

#### Service Dependency
```yaml
# OLD
dependencies:
  - "service_name.module_path"

# NEW
dependencies:
  - name: "ServiceName"
    module: "service_name.module_path"
    dependency_type: "SERVICE"
    required: true
    description: "Service description"
```

#### Module Dependency
```yaml
# OLD
dependencies:
  - "utils.helper_module"

# NEW
dependencies:
  - name: "HelperModule"
    module: "utils.helper_module"
    dependency_type: "MODULE"
    required: false
    description: "Utility helper functions"
```

## Automated Migration Script

Create a Python script to automate the conversion:

```python
#!/usr/bin/env python3
"""
Automated migration script for contract dependency refactor.
Converts legacy string dependencies to new structured format.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Any

def convert_dependency(dep_string: str) -> Dict[str, Any]:
    """Convert legacy string dependency to structured format."""

    # Determine dependency type based on patterns
    dep_type = "EXTERNAL"  # Default
    if "protocol" in dep_string.lower():
        dep_type = "PROTOCOL"
    elif "service" in dep_string.lower():
        dep_type = "SERVICE"
    elif "module" in dep_string.lower():
        dep_type = "MODULE"

    # Extract name from module path (convert to PascalCase)
    module_parts = dep_string.split('.')
    name = ''.join(word.title() for word in module_parts[-1].split('_'))

    return {
        "name": name,
        "module": dep_string,
        "dependency_type": dep_type,
        "required": True,  # Default to required
        "description": f"Migrated from legacy string: {dep_string}"
    }

def migrate_contract_file(file_path: Path) -> bool:
    """Migrate a single contract YAML file."""
    try:
        # Read original file
        with open(file_path, 'r') as f:
            contract = yaml.safe_load(f)

        # Check if dependencies need migration
        if 'dependencies' not in contract:
            return False

        dependencies = contract['dependencies']
        if not dependencies or all(isinstance(dep, dict) for dep in dependencies):
            print(f"✅ {file_path.name}: Already migrated")
            return False

        # Convert string dependencies
        new_dependencies = []
        for dep in dependencies:
            if isinstance(dep, str):
                new_dependencies.append(convert_dependency(dep))
            elif isinstance(dep, dict):
                new_dependencies.append(dep)  # Already structured
            else:
                raise ValueError(f"Unexpected dependency type: {type(dep)}")

        # Update contract
        contract['dependencies'] = new_dependencies

        # Write updated file
        with open(file_path, 'w') as f:
            yaml.dump(contract, f, default_flow_style=False, sort_keys=False)

        print(f"✅ {file_path.name}: Migrated {len(new_dependencies)} dependencies")
        return True

    except Exception as e:
        print(f"❌ {file_path.name}: Migration failed - {e}")
        return False

def main():
    """Run migration on all contract files."""
    contract_files = list(Path('.').glob('**/*contract*.yml')) + list(Path('.').glob('**/*contract*.yaml'))

    print(f"Found {len(contract_files)} contract files to migrate")

    migrated = 0
    for file_path in contract_files:
        if migrate_contract_file(file_path):
            migrated += 1

    print(f"\n✅ Migration complete: {migrated}/{len(contract_files)} files migrated")

if __name__ == "__main__":
    main()
```

## Validation After Migration

### 1. Run Contract Validation
```bash
# Validate all contracts
python scripts/run_7_gate_validation.py --all-contracts

# Validate specific contract
python scripts/run_7_gate_validation.py contracts/my_contract.yml
```

### 2. Test Contract Loading
```python
from omnibase_core.core.contracts.model_contract_base import ModelContractBase

# Test loading your migrated contract
try:
    with open('contracts/my_contract.yml', 'r') as f:
        contract_data = yaml.safe_load(f)

    # This will validate the new dependency format
    contract = YourContractClass(**contract_data)
    print("✅ Contract loads successfully")
except Exception as e:
    print(f"❌ Contract validation failed: {e}")
```

## Dependency Types

### PROTOCOL Dependencies
- **Pattern**: Must contain "protocol" in module path
- **Naming**: PascalCase (e.g., "ProtocolEventBus")
- **Required**: Usually `true`
- **Example**: `omnibase_spi.core.protocol_event_bus` → `ProtocolEventBus`

### SERVICE Dependencies
- **Pattern**: Must contain "service" in module path
- **Naming**: PascalCase service name
- **Required**: Usually `true`
- **Example**: `user_service.core` → `UserService`

### MODULE Dependencies
- **Pattern**: General module dependencies
- **Naming**: PascalCase module name
- **Required**: Can be `true` or `false`
- **Example**: `utils.helper_module` → `HelperModule`

### EXTERNAL Dependencies
- **Pattern**: Third-party or external dependencies
- **Naming**: Library or external service name
- **Required**: Usually `false`
- **Example**: `redis.client` → `RedisClient`

## Common Migration Issues

### Issue 1: Name Generation
**Problem**: Automated name generation produces unclear names
```yaml
# Auto-generated (unclear)
name: "SomeLongModuleName"
```
**Solution**: Manually review and improve names
```yaml
# Improved (clear)
name: "EventProcessor"
```

### Issue 2: Dependency Type Classification
**Problem**: Script guesses wrong dependency type
```yaml
# Wrong classification
dependency_type: "EXTERNAL"
```
**Solution**: Review and correct based on actual usage
```yaml
# Correct classification
dependency_type: "SERVICE"
```

### Issue 3: Required Field Setting
**Problem**: All dependencies marked as required
```yaml
required: true  # May be incorrect
```
**Solution**: Review each dependency's criticality
```yaml
required: false  # For optional dependencies
```

## Verification Checklist

After migration, verify:

- [ ] All contract YAML files load without errors
- [ ] Contract validation passes (7-gate validation)
- [ ] No string dependencies remain in any contract
- [ ] Dependency types are correctly classified (PROTOCOL/SERVICE/MODULE/EXTERNAL)
- [ ] Required fields are set appropriately
- [ ] Names follow PascalCase convention
- [ ] All module paths are valid and importable

## Rollback Strategy

**⚠️ Important**: Due to the "ZERO BACKWARDS COMPATIBILITY" policy, rollback requires reverting to a previous version of the codebase before the refactor.

### Emergency Rollback
```bash
# Revert to previous commit before refactor
git revert <commit-hash-of-refactor>

# Or create emergency branch from last working commit
git checkout -b emergency-rollback <commit-hash-before-refactor>
```

## Support

If you encounter issues during migration:

1. **Check the validation errors** - Run 7-gate validation for specific error messages
2. **Review dependency patterns** - Ensure module paths follow ONEX conventions
3. **Test incrementally** - Migrate one contract at a time to isolate issues
4. **Consult examples** - Look at successfully migrated contracts as templates

## Breaking Change Summary

| Component | Change | Impact |
|-----------|--------|---------|
| Contract Dependencies | String → Structured Objects | **HIGH** - All contracts must be updated |
| YAML Deserialization | Dict → ModelDependency conversion | **MEDIUM** - Handled automatically |
| Validation Logic | Enhanced type checking | **LOW** - Better error detection |
| API Compatibility | No backward compatibility | **HIGH** - All consuming code must update |

---

**Migration Support**: For questions about this migration, consult the ONEX architecture team or create an issue in the project repository.
