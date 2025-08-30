# ONEX Model Domain Import Boundaries

> **Status:** Canonical  
> **Last Updated:** 2025-06-27  
> **Purpose:** Definitive rules for import boundaries between model domains

## Domain Dependency Rules

This document defines the allowed import relationships between model domains to maintain clean architecture and prevent circular dependencies.

### 🏗️ Domain Architecture Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                            CORE                                 │
│  (Foundational models, shared types, contracts, events)        │
└─────────────────────┬───────────────────┬───────────────────────┘
                      │                   │
        ┌─────────────▼─────────────┐     │
        │         SERVICE           │     │
        │ (Services, event bus,     │     │
        │  orchestration)           │     │
        └─────────────┬─────────────┘     │
                      │                   │
              ┌───────▼───────┐           │
              │   REGISTRY    │           │
              │  (Registry    │           │
              │   operations) │           │
              └───────────────┘           │
                                          │
    ┌─────────────┬─────────────┬─────────▼─────────────┬─────────────┐
    │             │             │                       │             │
┌───▼───┐    ┌────▼────┐   ┌────▼──────┐          ┌────▼─────┐  ┌───▼─────┐
│HEALTH │    │SECURITY │   │CONFIG     │          │VALIDATION│  │SCENARIO │
│       │    │         │   │           │          │          │  │         │
└───────┘    └─────────┘   └───┬───────┘          └────┬─────┘  └─────┬───┘
                               │                       │              │
                        ┌──────▼──────┐                │              │
                        │  ENDPOINTS  │                │              │
                        │             │                │              │
                        └─────────────┘                │              │
                                                       │              │
                                                ┌──────▼──────┐       │
                                                │  DETECTION  │       │
                                                │             │       │
                                                └─────────────┘       │
                                                                     │
                                               ┌─────────────────────▼┘
                                               │
                                        (Can import from
                                         multiple domains)
```

## 📜 Import Rules Matrix

| Domain        | Can Import From                           | Rationale |
|---------------|-------------------------------------------|-----------|
| **CORE**      | *(None - foundational layer)*           | Core provides foundation for all other domains |
| **SERVICE**   | core, configuration, security, health   | Services need config, security, and health monitoring |
| **REGISTRY**  | core, configuration, security, health, validation | Registry needs validation and all infrastructure |
| **HEALTH**    | core                                     | Health is a foundational monitoring concern |
| **SECURITY**  | core                                     | Security is a foundational concern |
| **CONFIGURATION** | core                                 | Configuration is foundational infrastructure |
| **VALIDATION** | core                                    | Validation is foundational infrastructure |
| **SCENARIO**  | core, service, registry, validation     | Scenarios test services and registries |
| **ENDPOINTS** | core, configuration                      | Endpoints need core types and configuration |
| **DETECTION** | core, service, configuration            | Detection discovers services and needs config |

## 🚫 Forbidden Import Patterns

### ❌ Circular Dependencies
```python
# FORBIDDEN: Core importing from other domains
from omnibase.model.service.model_service_config import ServiceConfig  # ❌

# FORBIDDEN: Domain A and B importing from each other
from omnibase.model.health.model_health_check import HealthCheck       # In security/
from omnibase.model.security.model_secret_config import SecretConfig   # In health/
```

### ❌ Horizontal Dependencies (Same Level)
```python
# FORBIDDEN: Same-level domain imports (unless explicitly allowed)
from omnibase.model.health.model_health_check import HealthCheck       # In security/
from omnibase.model.security.model_fallback_strategy import Fallback   # In health/
```

### ❌ Upward Dependencies
```python
# FORBIDDEN: Lower-level importing from higher-level
from omnibase.model.scenario.model_scenario import Scenario            # In core/
from omnibase.model.registry.model_registry_config import RegistryConfig # In service/
```

## ✅ Allowed Import Patterns

### ✅ Foundation Imports
```python
# ALLOWED: Any domain importing from core
from omnibase.model.core.model_base_error import BaseError             # ✅
from omnibase.model.core.model_shared_types import SharedTypes         # ✅
```

### ✅ Service Layer Imports
```python
# ALLOWED: Service importing from infrastructure domains
from omnibase.model.configuration.model_handler_config import HandlerConfig  # ✅
from omnibase.model.security.model_fallback_strategy import FallbackStrategy  # ✅
from omnibase.model.health.model_health_check import HealthCheck              # ✅
```

### ✅ Cross-Domain Interface Usage
```python
# ALLOWED: Using __exposed__ interface for approved cross-domain access
from omnibase.model.__exposed__ import (
    BaseError,      # From core
    HealthCheck,    # From health  
    HandlerConfig   # From configuration
)
```

## 🔧 Enforcement Mechanisms

### 1. Static Analysis Linter
- **Tool**: `import_boundary_linter.py`
- **Location**: `scripts/import_boundary_linter.py`
- **Usage**: `python scripts/import_boundary_linter.py src/omnibase/model/`

### 2. CI Integration
- **Pre-commit hook**: Validates import boundaries before commit
- **CI Pipeline**: Blocks PRs with boundary violations
- **Command**: `poetry run python scripts/import_boundary_linter.py`

### 3. IDE Integration
- **VS Code**: Custom linter extension
- **PyCharm**: External tool configuration
- **Real-time feedback**: Immediate violation detection

## 🎯 Violation Categories

### Critical Violations (Build Breaking)
- Circular dependencies between domains
- Core domain importing from any other domain
- Horizontal imports between peer domains

### Warning Violations (Review Required)
- Complex multi-hop dependencies
- Unused imports from allowed domains
- Potential architectural debt

### Info Violations (Best Practice)
- Missing __exposed__ interface usage
- Overly broad imports when specific imports available
- Import organization opportunities

## 🔍 Validation Commands

```bash
# Check all model imports
python scripts/import_boundary_linter.py src/omnibase/model/

# Check specific domain
python scripts/import_boundary_linter.py src/omnibase/model/service/

# Dry run (show violations without failing)
python scripts/import_boundary_linter.py --dry-run src/omnibase/model/

# Fix auto-fixable violations
python scripts/import_boundary_linter.py --fix src/omnibase/model/
```

## 📚 Implementation Guidelines

### For Developers
1. **Before importing**: Check this dependency matrix
2. **Use __exposed__**: Prefer cross-domain interface when available
3. **Minimize dependencies**: Import only what you need
4. **Run linter**: Validate before committing

### For Code Reviewers
1. **Check imports**: Verify new imports follow rules
2. **Question violations**: Ask for justification
3. **Suggest alternatives**: Recommend __exposed__ usage
4. **Enforce compliance**: Block PRs with violations

### For CI/CD
1. **Automated checks**: Run linter on every PR
2. **Block violations**: Fail build on critical violations
3. **Report warnings**: Surface review-required violations
4. **Maintain rules**: Keep linter updated with architecture

## 🔄 Evolution and Updates

### Rule Changes
- All rule changes require architecture team approval
- Document rationale for any rule modifications
- Update linter and CI when rules change
- Communicate changes to all contributors

### New Domains
- Define dependencies before creating new domains
- Update this document and linter rules
- Consider impact on existing domains
- Maintain hierarchical relationships

### Legacy Migration
- Existing violations get technical debt tickets
- Gradual migration to compliance required
- No new violations permitted
- Document exceptions with expiration dates

## 🎓 Educational Examples

### Good Import Structure
```python
# service/model_service_config.py
from omnibase.model.core.model_base_result import BaseResult           # ✅ Foundation
from omnibase.model.configuration.model_handler_config import Config  # ✅ Infrastructure
from omnibase.model.security.model_secret_config import SecretConfig  # ✅ Allowed dependency
```

### Bad Import Structure
```python
# security/model_secret_config.py
from omnibase.model.service.model_service_config import ServiceConfig  # ❌ Upward dependency
from omnibase.model.registry.model_registry_config import RegConfig    # ❌ Horizontal import
```

### Refactored Structure
```python
# security/model_secret_config.py
from omnibase.model.core.model_shared_types import ConfigurationType   # ✅ Foundation
from omnibase.model.__exposed__ import HandlerConfig                   # ✅ Cross-domain interface
```

## 📞 Contact and Support

- **Architecture Questions**: Open issue with `architecture` label
- **Linter Issues**: Open issue with `tooling` label
- **Rule Clarifications**: Contact architecture team
- **CI Problems**: Open issue with `ci` label

---

**Remember**: These boundaries exist to maintain clean architecture, prevent circular dependencies, and ensure the ONEX model system remains scalable and maintainable. When in doubt, prefer the stricter interpretation and ask for guidance.
