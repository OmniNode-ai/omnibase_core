# ONEX Model Architecture

> **Status:** Production Ready  
> **Last Updated:** 2025-06-27  
> **Domain Structure:** Post nm_arch_010 reorganization

## 🏗️ Domain-Based Architecture

The ONEX model system is organized into **10 functional domains** with strict import boundaries to maintain clean architecture and prevent circular dependencies.

### Domain Structure

```
src/omnibase_spi/model/
├── __init__.py              # Main package exports (backward compatibility)
├── __exposed__.py           # Cross-domain interface definitions
├── DOMAIN_DEPENDENCIES.md  # Import boundary rules (📖 READ THIS)
├── core/                    # 🏛️ Foundation (37 models)
│   ├── model_base_*.py     # Base classes and errors
│   ├── model_shared_*.py   # Shared types and contracts
│   ├── model_onex_*.py     # Core ONEX types
│   └── model_tool_*.py     # Tool and metadata models
├── service/                 # ⚙️ Services (14 models)
│   ├── model_service_*.py  # Service configurations
│   ├── model_event_bus_*.py # Event bus models
│   └── model_orchestrator.py # Orchestration
├── registry/                # �� Registry (10 models)
│   └── model_registry_*.py # Registry operations and health
├── configuration/           # ⚙️ Configuration (13 models)
│   ├── model_*_config.py   # Connection configurations
│   ├── model_handler_*.py  # Handler configurations
│   └── model_metadata.py   # Metadata configurations
├── security/                # 🔒 Security (7 models)
│   ├── model_secret_*.py   # Secret management
│   ├── model_security_*.py # Security utilities
│   └── model_fallback_*.py # Security fallback strategies
├── health/                  # 🏥 Health (2 models)
│   └── model_*_health.py   # Health monitoring
├── validation/              # ✅ Validation (5 models)
│   ├── model_validate_*.py # Validation results
│   ├── model_schema.py     # Schema validation
│   └── model_fixture_*.py  # Testing fixtures
├── scenario/                # 🎭 Scenarios (6 models)
│   ├── model_scenario_*.py # Scenario execution
│   └── model_template_*.py # Template variables
├── endpoints/               # 🔗 Endpoints (1 model)
│   └── model_service_endpoint.py # Service endpoints
└── detection/               # 🔍 Detection (1 model)
    └── model_service_detection_config.py # Service discovery
```

## 🚫 Import Boundaries (CRITICAL)

**⚠️ MANDATORY:** All imports between domains must follow the rules in [`DOMAIN_DEPENDENCIES.md`](./DOMAIN_DEPENDENCIES.md).

### Quick Rules
- ✅ **Any domain** can import from `core/`
- ✅ **Higher-level domains** can import from their dependencies
- ❌ **Core** cannot import from any other domain
- ❌ **Peer domains** (same level) cannot import from each other
- ❌ **Circular dependencies** are forbidden

### Enforcement
```bash
# Check import boundaries before committing
python scripts/import_boundary_linter.py src/omnibase_spi/model/

# Dry run (show violations without failing)  
python scripts/import_boundary_linter.py src/omnibase_spi/model/ --dry-run
```

### Cross-Domain Access
Use the `__exposed__.py` interface for approved cross-domain imports:
```python
# ✅ GOOD: Use cross-domain interface
from omnibase_spi.model.__exposed__ import BaseError, HealthCheck

# ❌ BAD: Direct cross-domain import  
from omnibase_spi.model.health.model_health_check import HealthCheck
```

## 📦 Usage Patterns

### Import All Models (Backward Compatibility)
```python
# Import everything (maintains backward compatibility)
from omnibase_spi.model import *

# Specific model classes
from omnibase_spi.model import ModelServiceConfiguration, BaseError
```

### Domain-Specific Imports
```python
# Import from specific domains
from omnibase_spi.model.core import *
from omnibase_spi.model.service import ModelServiceConfiguration
from omnibase_spi.model.registry import ModelRegistryConfig
```

### Cross-Domain Safe Imports  
```python
# Use exposed interface for cross-domain access
from omnibase_spi.model.__exposed__ import (
    BaseError,      # From core
    HealthCheck,    # From health
    HandlerConfig   # From configuration
)
```

## 🔍 Model Discovery

### Find Models by Domain
```python
# Core foundational models
from omnibase_spi.model.core import (
    BaseError, BaseResult, Context, SharedTypes,
    OnexEvent, OnexMessage, StateContract
)

# Service configuration models
from omnibase_spi.model.service import (
    ModelServiceConfiguration, ModelEventBusConfig,
    ModelKafkaBroker, ModelOrchestrator
)

# Registry operation models  
from omnibase_spi.model.registry import (
    ModelRegistryConfig, ModelRegistryHealth,
    ModelRegistryResolution, ModelRegistryValidation
)
```

### Enhanced Tool Models (nm_arch_009)
```python
# Enterprise tool collection models
from omnibase_spi.model.core import (
    ModelToolCollection,           # 18x enhanced enterprise tool management
    ModelMetadataToolCollection,   # Enhanced metadata tool analytics
    ToolRegistrationStatus,        # Tool lifecycle management
    ToolPerformanceMetrics,        # Performance monitoring
    MetadataToolAnalytics          # Usage analytics and insights
)
```

## �� Testing Integration

The domain structure integrates with ONEX testing standards:

```python
# Test with domain-specific models
from omnibase_spi.model.validation import ModelFixtureData
from omnibase_spi.model.scenario import ModelScenario, ModelTemplateVariables

def test_with_domain_models(fixture_registry):
    fixture = ModelFixtureData(...)
    scenario = ModelScenario(...)
    # Test logic here
```

## 📚 Development Guidelines

### Adding New Models
1. **Choose the right domain** based on functionality
2. **Check import rules** in `DOMAIN_DEPENDENCIES.md`
3. **Use proper naming** following `model_domain_concept.py` pattern
4. **Add to domain `__init__.py`** for exports
5. **Run import linter** before committing

### Moving Models Between Domains
1. **Understand dependencies** of the model
2. **Check impact** on existing imports
3. **Update domain `__init__.py` files**
4. **Run full test suite** after moving
5. **Update documentation** if needed

### Creating New Domains
1. **Justify the need** for a new domain
2. **Define dependency rules** in `DOMAIN_DEPENDENCIES.md`
3. **Update linter configuration**
4. **Create domain directory** with `__init__.py`
5. **Add to main package imports**

## 🔧 Troubleshooting

### Import Errors
```bash
# Check for import boundary violations
python scripts/import_boundary_linter.py src/omnibase_spi/model/

# Check specific file
python scripts/import_boundary_linter.py src/omnibase_spi/model/service/model_service_config.py
```

### Missing Models
```python
# Check if model is in the right domain
from omnibase_spi.model.core import ModelName        # Try core first
from omnibase_spi.model.service import ModelName     # Then service
# etc.

# Use main package import as fallback
from omnibase_spi.model import ModelName             # Backward compatibility
```

### Circular Dependency Errors
1. Check `DOMAIN_DEPENDENCIES.md` for allowed imports
2. Refactor to use `__exposed__.py` interface
3. Move shared functionality to `core/` domain
4. Contact architecture team for complex cases

## 📞 Support

- **Architecture Questions**: See `DOMAIN_DEPENDENCIES.md`
- **Import Issues**: Run the import boundary linter
- **New Domain Requests**: Open architecture discussion issue
- **Migration Help**: Contact the ONEX team

## 🚀 Migration History

- **nm_arch_001-009**: Individual model extractions and enhancements
- **nm_arch_010**: Domain-based reorganization (96+ models → 10 domains)
- **nm_arch_011**: Import boundary enforcement and CI integration

---

**Remember**: The domain structure exists to maintain clean architecture and prevent technical debt. Always follow the import boundary rules and use the linter to validate your changes.
