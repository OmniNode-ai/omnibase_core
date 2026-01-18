> **Navigation**: [Home](../index.md) > Reference > Mixin Discovery API

# Mixin Discovery API

Programmatic mixin discovery and compatibility checking for ONEX nodes.

## Overview

The Mixin Discovery API provides programmatic access to mixin metadata, enabling developers to intelligently compose ONEX nodes with appropriate mixins based on requirements, compatibility, and dependencies.

## Features

- **Mixin Discovery**: Query all available mixins with comprehensive metadata
- **Category-Based Filtering**: Browse mixins by functional category
- **Compatibility Checking**: Find mixins compatible with existing compositions
- **Dependency Resolution**: Resolve transitive dependencies for mixins
- **Composition Validation**: Validate mixin compositions before generation
- **Intelligent Caching**: Automatic caching for improved performance

## Installation

The discovery API is included in omnibase_core. No additional installation required.

```
poetry install
```

## Quick Start

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

# Initialize discovery system
discovery = MixinDiscovery()

# Get all available mixins
all_mixins = discovery.get_all_mixins()
print(f"Found {len(all_mixins)} mixins")

# Browse by category
flow_control_mixins = discovery.get_mixins_by_category("flow_control")

# Check compatibility
base_mixins = ["MixinRetry"]
compatible = discovery.find_compatible_mixins(base_mixins)

# Validate composition
composition = ["MixinRetry", "MixinHealthCheck"]
is_valid, errors = discovery.validate_composition(composition)

# Resolve dependencies
deps = discovery.get_mixin_dependencies("MixinRetry")
```

## API Reference

### MixinInfo Model

Pydantic model representing mixin metadata:

```
class MixinInfo(BaseModel):
    name: str                           # Mixin class name
    description: str                    # Human-readable description
    version: str                        # Semantic version
    category: str                       # Functional category
    requires: list[str]                 # Required dependencies
    compatible_with: list[str]          # Compatible mixins
    incompatible_with: list[str]        # Incompatible mixins
    config_schema: dict[str, Any]       # Configuration schema
    usage_examples: list[str]           # Usage examples
```

### MixinDiscovery Class

Main discovery API class:

#### Initialization

```
discovery = MixinDiscovery(mixins_path: Optional[Path] = None)
```

- `mixins_path`: Optional custom path to mixins directory (defaults to src/omnibase_core/mixins)

#### Methods

##### get_all_mixins() → list[MixinInfo]

Get all available mixins with metadata.

```
all_mixins = discovery.get_all_mixins()
for mixin in all_mixins:
    print(f"{mixin.name}: {mixin.description}")
```

##### get_mixins_by_category(category: str) → list[MixinInfo]

Get mixins filtered by category.

```
caching_mixins = discovery.get_mixins_by_category("performance")
```

##### get_mixin(name: str) → MixinInfo

Get a specific mixin by name.

```
retry_mixin = discovery.get_mixin("MixinRetry")
print(f"Version: {retry_mixin.version}")
```

##### find_compatible_mixins(base_mixins: list[str]) → list[MixinInfo]

Find mixins compatible with given base mixins.

```
base = ["MixinRetry", "MixinHealthCheck"]
compatible = discovery.find_compatible_mixins(base)
```

##### get_mixin_dependencies(mixin_name: str) → list[str]

Get transitive dependencies for a mixin.

```
deps = discovery.get_mixin_dependencies("MixinRetry")
# Returns: ["omnibase_core.models.infrastructure.model_retry_policy", ...]
```

##### validate_composition(mixin_names: list[str]) → tuple[bool, list[str]]

Validate that a set of mixins can be composed together.

```
composition = ["MixinRetry", "MixinHealthCheck"]
is_valid, errors = discovery.validate_composition(composition)

if is_valid:
    print("Composition is valid!")
else:
    for error in errors:
        print(f"Error: {error}")
```

##### get_categories() → list[str]

Get all unique mixin categories.

```
categories = discovery.get_categories()
# Returns: ["flow_control", "monitoring", "performance", ...]
```

## Usage Examples

### Example 1: List All Mixins

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

discovery = MixinDiscovery()
all_mixins = discovery.get_all_mixins()

print(f"Found {len(all_mixins)} available mixins:\n")
for mixin in all_mixins:
    print(f"  • {mixin.name} (v{mixin.version})")
    print(f"    Category: {mixin.category}")
    print(f"    Description: {mixin.description}")
```

### Example 2: Build Intelligent Composition

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

discovery = MixinDiscovery()

# Start with base requirement
composition = ["MixinRetry"]

# Find compatible mixins
compatible = discovery.find_compatible_mixins(composition)

# Add health monitoring
health_mixin = next(m for m in compatible if m.name == "MixinHealthCheck")
composition.append(health_mixin.name)

# Validate composition
is_valid, errors = discovery.validate_composition(composition)

if is_valid:
    print(f"Valid composition: {' + '.join(composition)}")

    # Get all dependencies
    all_deps = set()
    for mixin_name in composition:
        deps = discovery.get_mixin_dependencies(mixin_name)
        all_deps.update(deps)

    print(f"Total dependencies: {len(all_deps)}")
```

### Example 3: Code Generation Context

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

discovery = MixinDiscovery()

# Target composition for code generation
composition = ["MixinRetry", "MixinHealthCheck"]

# Collect code generation context
context = {
    "mixins": [],
    "dependencies": set(),
    "config_schemas": {},
}

for mixin_name in composition:
    mixin = discovery.get_mixin(mixin_name)

    context["mixins"].append({
        "name": mixin.name,
        "version": mixin.version,
        "category": mixin.category,
    })

    deps = discovery.get_mixin_dependencies(mixin_name)
    context["dependencies"].update(deps)

    if mixin.config_schema:
        context["config_schemas"][mixin.name] = mixin.config_schema

# Use context for code generation
print(f"Generating node with {len(context['mixins'])} mixins")
print(f"Total dependencies: {len(context['dependencies'])}")
```

## Metadata File Format

Mixins are defined in `/src/omnibase_core/mixins/mixin_metadata.yaml`:

```
mixin_retry:
  name: "MixinRetry"
  description: "Automatic retry logic with configurable backoff strategies"
  version: "1.0.0"
  category: "flow_control"

  requires:
    - "omnibase_core.models.infrastructure.model_retry_policy"
    - "pydantic"

  compatible_with:
    - "MixinEventBus"
    - "MixinHealthCheck"

  incompatible_with:
    - "MixinSynchronous"

  config_schema:
    max_retries:
      type: "integer"
      minimum: 0
      maximum: 100
      default: 3

  usage_examples:
    - "HTTP API clients with transient failure recovery"
    - "Database operations with connection retry logic"
```

## Categories

Common mixin categories:

- **flow_control**: Retry, timeout, rate limiting
- **monitoring**: Health checks, metrics, logging
- **performance**: Caching, connection pooling
- **resilience**: Circuit breaker, fallback
- **security**: Authentication, authorization, encryption
- **data**: Serialization, validation, transformation
- **communication**: Event bus, message queue integration

## Error Handling

The API uses `ModelOnexError` for consistent error handling:

```
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

discovery = MixinDiscovery()

try:
    mixin = discovery.get_mixin("NonexistentMixin")
except ModelOnexError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.error_code}")
```

Common errors:

- `FILE_NOT_FOUND`: Metadata file not found
- `VALIDATION_ERROR`: Invalid metadata or mixin not found
- `FILE_READ_ERROR`: Failed to read metadata file

## Performance

- **Caching**: Metadata is cached after first load for improved performance
- **Memory**: ~2-5KB per mixin in cache
- **Load Time**: ~50-100ms initial load, <1ms cached queries
- **Scalability**: Handles 100+ mixins efficiently

## Testing

Run unit tests:

```
poetry run pytest tests/unit/discovery/test_mixin_discovery.py -xvs
```

Test coverage:

- ✅ 23 unit tests (100% pass rate)
- ✅ Model validation tests
- ✅ Discovery and filtering tests
- ✅ Compatibility checking tests
- ✅ Dependency resolution tests
- ✅ Composition validation tests
- ✅ Integration workflow tests

## Integration

### With Autonomous Code Generation

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery

def generate_node_class(node_name: str, requirements: list[str]) -> str:
    discovery = MixinDiscovery()

    # Find mixins matching requirements
    composition = []
    for requirement in requirements:
        mixins = discovery.get_mixins_by_category(requirement)
        if mixins:
            composition.append(mixins[0].name)

    # Validate composition
    is_valid, errors = discovery.validate_composition(composition)
    if not is_valid:
        raise ValueError(f"Invalid composition: {errors}")

    # Generate imports
    imports = set()
    for mixin_name in composition:
        deps = discovery.get_mixin_dependencies(mixin_name)
        imports.update(deps)

    # Generate class definition
    class_def = f"class {node_name}(ModelServiceEffect, {', '.join(composition)}):"

    return class_def
```

### With Template Systems

```
from omnibase_core.mixins.mixin_discovery import MixinDiscovery
from jinja2 import Template

discovery = MixinDiscovery()

# Get mixin information
mixin = discovery.get_mixin("MixinRetry")

# Generate code from template
template = Template("""
class {{ node_name }}(ModelServiceEffect, {{ mixin.name }}):
    \"\"\"{{ mixin.description }}\"\"\"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # {{ mixin.name }} configuration
        {% for key, schema in mixin.config_schema.items() %}
        self.{{ key }} = kwargs.get('{{ key }}', {{ schema.default }})
        {% endfor %}
""")

code = template.render(node_name="NodeApiClientEffect", mixin=mixin)
```

## Best Practices

1. **Cache Discovery Instance**: Reuse `MixinDiscovery` instances to benefit from caching
2. **Validate Early**: Always validate compositions before code generation
3. **Check Dependencies**: Resolve dependencies to ensure all imports are available
4. **Handle Errors**: Use try/except to handle missing mixins gracefully
5. **Document Compositions**: Include mixin versions in generated code comments
6. **Test Compositions**: Test generated code with various mixin combinations

## Future Enhancements

- Mixin recommendation engine based on node type and requirements
- Conflict resolution strategies for incompatible mixins
- Automatic dependency installation via Poetry
- Mixin version compatibility checking
- Code generation templates per mixin
- Performance profiling for mixin compositions

## Contributing

To add new mixin metadata:

1. Edit `/src/omnibase_core/mixins/mixin_metadata.yaml`
2. Follow the existing format and naming conventions
3. Include all required fields (name, description, version, category)
4. List dependencies, compatibility, and incompatibilities
5. Provide config schema and usage examples
6. Run tests to validate metadata

## License

Part of omnibase_core - MIT License

## Support

For issues or questions:

- Create an issue in the omnibase_core repository
- Refer to ONEX documentation for mixin patterns
- See examples in `/examples/mixin_discovery_usage.py`
