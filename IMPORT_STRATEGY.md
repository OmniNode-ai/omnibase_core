# Import Strategy Documentation

## Wildcard Import Pattern

### Purpose
The ONEX architecture uses wildcard imports (`from .module import *`) in `__init__.py` files for the following strategic reasons:

1. **Backward Compatibility**: Ensures existing code continues to work when internal module structure changes
2. **Convenience API**: Provides clean, flat import paths for commonly used models and utilities
3. **Domain Aggregation**: Groups related functionality under logical domain namespaces

### Pattern Usage
Wildcard imports are used in these specific contexts:
- Model package `__init__.py` files for Pydantic models
- Core package `__init__.py` files for frequently used utilities
- Domain-specific packages for logical grouping

### Example
```python
# Instead of: from omnibase_core.model.health.model_health_status import ModelHealthStatus
# Users can write: from omnibase_core.model.health import ModelHealthStatus
# Or even: from omnibase_core.model import ModelHealthStatus
```

### Standards Compliance
- All wildcard imports include `# noqa: F403` for explicit linting exceptions
- Only used in `__init__.py` files, never in implementation modules
- Each module defines `__all__` to control exported symbols

### Future Considerations
- Consider gradual migration to explicit imports for better IDE support
- Maintain compatibility layers during any future refactoring
- Use type stubs for better static analysis support

## Maintenance Guidelines
1. Always define `__all__` in modules with wildcard imports
2. Document any new wildcard imports with clear justification
3. Prefer explicit imports in new code, use wildcards only for established APIs
4. Consider performance implications in high-frequency import paths
