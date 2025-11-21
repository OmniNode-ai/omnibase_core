# Manifest Models

ONEX provides **structured manifest models** for validating and working with system-wide configuration files.

## Overview

Manifest models enable programmatic validation, manipulation, and querying of YAML configuration files that define system behavior. These models leverage Pydantic for schema validation and provide rich APIs for working with complex configurations.

## Available Manifests

### ModelMixinMetadata

**Purpose**: Load, validate, and query mixin metadata from `mixin_metadata.yaml`

**Location**: `src/omnibase_core/models/core/model_mixin_metadata.py`

**Features**:
- 11 nested Pydantic models for complete mixin metadata
- Version management with semantic versioning
- Configuration schema validation
- Code pattern definitions for generation
- Performance characteristics tracking
- Compatibility validation between mixins

**Usage Example**:
```python
from pathlib import Path
from omnibase_core.models.core.model_mixin_metadata import ModelMixinMetadataCollection

# Load all mixin metadata
collection = ModelMixinMetadataCollection.from_yaml(
    Path("src/omnibase_core/mixins/mixin_metadata.yaml")
)

# Get specific mixin
retry_mixin = collection.get_mixin("retry")
print(f"Version: {retry_mixin.version}")
print(f"Category: {retry_mixin.category}")

# Check compatibility
mixins_to_use = ["retry", "circuit_breaker", "caching"]
is_compatible, conflicts = collection.validate_compatibility(mixins_to_use)

# Get all mixins by category
flow_control_mixins = collection.get_mixins_by_category("flow_control")
```

**Model Structure**:

The `ModelMixinMetadata` system comprises 11 nested models:

1. **ModelMixinMetadata**: Root model for a single mixin
2. **ModelMixinMetadataCollection**: Container for all mixins with query capabilities
3. **ModelMixinConfig**: Configuration schema for mixin instances
4. **ModelMixinDependency**: Dependency declarations between mixins
5. **ModelMixinCompatibility**: Compatibility rules and conflict detection
6. **ModelMixinCodePattern**: Code generation patterns and templates
7. **ModelMixinPerformance**: Performance characteristics and benchmarks
8. **ModelMixinExample**: Usage examples and documentation
9. **ModelMixinVersion**: Version tracking with semantic versioning
10. **ModelMixinCategory**: Categorization and taxonomy
11. **ModelMixinMetrics**: Runtime metrics and monitoring data

**Key Methods**:

| Method | Purpose | Returns |
|--------|---------|---------|
| `load_from_yaml(path)` | Load metadata from YAML file | `ModelMixinMetadataCollection` |
| `get_mixin(name)` | Retrieve specific mixin metadata | `ModelMixinMetadata` |
| `get_mixins_by_category(category)` | Filter by category | `list[ModelMixinMetadata]` |
| `validate_compatibility(mixins)` | Check mixin compatibility | `tuple[bool, list[str]]` |
| `get_dependencies(mixin_name)` | Get dependency tree | `list[str]` |

### ModelDockerComposeManifest

**Purpose**: Validate and manipulate complete `docker-compose.yaml` files

**Location**: `src/omnibase_core/models/docker/model_docker_compose_manifest.py`

**Features**:
- Integrates 16 existing Docker models into unified structure
- Service, network, volume, config, and secret definitions
- Dependency validation (circular dependency detection)
- Port conflict detection
- Load from/save to YAML with full validation

**Usage Example**:
```python
from pathlib import Path
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest
)

# Load from YAML
manifest = ModelDockerComposeManifest.from_yaml(
    Path("docker-compose.yaml")
)

# Access services
api_service = manifest.get_service("api")
print(f"Image: {api_service.image}")
print(f"Ports: {api_service.ports}")

# Validate dependencies
dep_warnings = manifest.validate_dependencies()
if dep_warnings:
    print("Dependency issues:", dep_warnings)

# Detect port conflicts
port_warnings = manifest.detect_port_conflicts()
if port_warnings:
    print("Port conflicts:", port_warnings)

# Save to YAML
manifest.save_to_yaml(Path("output.yaml"))
```

**Model Structure**:

The `ModelDockerComposeManifest` integrates these Docker models:

1. **ModelDockerService**: Service definitions with image, command, environment
2. **ModelDockerNetwork**: Network configurations
3. **ModelDockerVolume**: Volume definitions and mount points
4. **ModelDockerConfig**: Configuration file management
5. **ModelDockerSecret**: Secret management
6. **ModelDockerBuild**: Build context and Dockerfile specifications
7. **ModelDockerDeploy**: Deployment strategies and resource limits
8. **ModelDockerHealthCheck**: Health check configurations
9. **ModelDockerLogging**: Logging driver configurations
10. **ModelDockerPort**: Port mapping definitions
11. **ModelDockerEnvironment**: Environment variable management
12. **ModelDockerDependency**: Service dependency declarations
13. **ModelDockerRestart**: Restart policy configurations
14. **ModelDockerResource**: Resource limit and reservation
15. **ModelDockerLabel**: Label and metadata management
16. **ModelDockerExtension**: Custom extensions and overrides

**Key Methods**:

| Method | Purpose | Returns |
|--------|---------|---------|
| `load_from_yaml(path)` | Load from docker-compose.yaml | `ModelDockerComposeManifest` |
| `save_to_yaml(path)` | Save to docker-compose.yaml | `None` |
| `get_service(name)` | Retrieve service by name | `ModelDockerService` |
| `validate_dependencies()` | Check for circular dependencies | `list[str]` (warnings) |
| `detect_port_conflicts()` | Find port binding conflicts | `list[str]` (warnings) |
| `get_all_services()` | List all service names | `list[str]` |
| `add_service(name, service)` | Add new service definition | `None` |
| `remove_service(name)` | Remove service definition | `None` |

## Common Patterns

### Pattern 1: Validation Before Deployment

```python
from pathlib import Path
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest
)

# Load manifest
manifest = ModelDockerComposeManifest.from_yaml(
    Path("docker-compose.yaml")
)

# Run all validations
dep_issues = manifest.validate_dependencies()
port_issues = manifest.detect_port_conflicts()

if dep_issues or port_issues:
    print("⚠️  Validation failed:")
    for issue in dep_issues:
        print(f"  - Dependency: {issue}")
    for issue in port_issues:
        print(f"  - Port: {issue}")
    exit(1)

print("✅ Validation passed - safe to deploy")
```

### Pattern 2: Dynamic Service Configuration

```python
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest,
    ModelDockerService
)

# Load existing manifest
manifest = ModelDockerComposeManifest.from_yaml(
    Path("docker-compose.yaml")
)

# Add new service programmatically
new_service = ModelDockerService(
    image="nginx:latest",
    ports=["8080:80"],
    environment={"ENV": "production"}
)

manifest.add_service("web-server", new_service)

# Save updated manifest
manifest.save_to_yaml(Path("docker-compose.yaml"))
```

### Pattern 3: Mixin Discovery and Selection

```python
from pathlib import Path
from omnibase_core.models.core.model_mixin_metadata import (
    ModelMixinMetadataCollection
)

# Load all available mixins
collection = ModelMixinMetadataCollection.from_yaml(
    Path("src/omnibase_core/mixins/mixin_metadata.yaml")
)

# Find mixins for specific use case
desired_capabilities = ["retry", "caching", "metrics"]

# Validate compatibility
is_compatible, conflicts = collection.validate_compatibility(
    desired_capabilities
)

if not is_compatible:
    print(f"⚠️  Conflicts detected: {conflicts}")
    # Resolve conflicts or choose alternatives
else:
    print(f"✅ Mixins compatible: {desired_capabilities}")

    # Get full dependency tree
    all_required_mixins = set(desired_capabilities)
    for mixin_name in desired_capabilities:
        deps = collection.get_dependencies(mixin_name)
        all_required_mixins.update(deps)

    print(f"Total mixins required: {all_required_mixins}")
```

## Integration with ONEX Workflow

### Workflow Step 1: Load Configuration

```python
from pathlib import Path
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest
)

# Load during initialization
class NodeDockerOrchestrator(NodeOrchestrator):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

        # Load and validate manifest
        self.manifest = ModelDockerComposeManifest.from_yaml(
            Path(container.get_config("docker_compose_path"))
        )

        # Run validations
        self.validate_manifest()

    def validate_manifest(self) -> None:
        """Run all manifest validations."""
        issues = []
        issues.extend(self.manifest.validate_dependencies())
        issues.extend(self.manifest.detect_port_conflicts())

        if issues:
            raise ModelOnexError(
                message="Docker manifest validation failed",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={"issues": issues}
            )
```

### Workflow Step 2: Dynamic Reconfiguration

```python
async def execute_orchestration(
    self,
    input_data: ModelOrchestratorInput
) -> ModelOrchestratorOutput:
    """Reconfigure services based on runtime conditions."""

    # Get current service
    service = self.manifest.get_service("api")

    # Scale based on load
    current_replicas = service.deploy.replicas if service.deploy else 1
    new_replicas = self.calculate_required_replicas(input_data)

    if new_replicas != current_replicas:
        # Update service
        service.deploy.replicas = new_replicas

        # Save updated manifest
        self.manifest.save_to_yaml(
            Path(self.container.get_config("docker_compose_path"))
        )

        # Trigger deployment
        await self.redeploy_service("api")

    return ModelOrchestratorOutput(success=True)
```

## Testing

All manifest models have comprehensive test coverage:

- **Mixin Metadata Tests**: [../../tests/unit/models/core/test_model_mixin_metadata.py](../../tests/unit/models/core/test_model_mixin_metadata.py) - 39 tests
- **Docker Compose Manifest Tests**: [../../tests/unit/models/docker/test_model_docker_compose_manifest.py](../../tests/unit/models/docker/test_model_docker_compose_manifest.py) - 26 tests

**Example Test Pattern**:
```python
import pytest
from pathlib import Path
from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest
)

def test_load_and_validate_manifest():
    """Test loading and validating a docker-compose.yaml file."""
    # Load test fixture
    manifest = ModelDockerComposeManifest.from_yaml(
        Path("tests/fixtures/docker-compose.yaml")
    )

    # Validate structure
    assert manifest.version == "3.8"
    assert len(manifest.services) > 0

    # Validate dependencies
    dep_warnings = manifest.validate_dependencies()
    assert len(dep_warnings) == 0  # No circular dependencies

    # Validate ports
    port_warnings = manifest.detect_port_conflicts()
    assert len(port_warnings) == 0  # No port conflicts
```

## Related Documentation

- [Mixin System Architecture](../architecture/MIXIN_ARCHITECTURE.md) - Complete mixin system documentation
- [Validation Framework](VALIDATION_FRAMEWORK.md) - Pydantic validation patterns
- [Configuration Management](../patterns/CONFIGURATION_MANAGEMENT.md) - Managing system configuration

## Best Practices

### 1. Always Validate on Load

```python
# ✅ Good: Validate immediately after loading
manifest = ModelDockerComposeManifest.from_yaml(path)
if warnings := manifest.validate_dependencies():
    logger.warning(f"Validation warnings: {warnings}")

# ❌ Bad: Skip validation
manifest = ModelDockerComposeManifest.from_yaml(path)
# ... use manifest without validation
```

### 2. Use Type-Safe Access

```python
# ✅ Good: Type-safe access with error handling
try:
    service = manifest.get_service("api")
    port = service.ports[0] if service.ports else None
except KeyError:
    logger.error("Service 'api' not found")

# ❌ Bad: Unsafe dictionary access
service = manifest.services["api"]  # May raise KeyError
port = service.ports[0]  # May raise IndexError
```

### 3. Handle YAML Serialization Carefully

```python
# ✅ Good: Use built-in save methods
manifest.save_to_yaml(Path("docker-compose.yaml"))

# ❌ Bad: Manual YAML serialization
with open("docker-compose.yaml", "w") as f:
    yaml.dump(manifest.dict(), f)  # Loses validation and formatting
```

### 4. Version Control Configuration Files

```python
# ✅ Good: Track changes to generated manifests
manifest.save_to_yaml(Path("docker-compose.yaml"))
subprocess.run(["git", "add", "docker-compose.yaml"])
subprocess.run(["git", "commit", "-m", "Update service configuration"])

# ❌ Bad: Overwrite without tracking
manifest.save_to_yaml(Path("docker-compose.yaml"))
# ... no version control
```

## Troubleshooting

### Common Issues

**Issue**: `ValidationError` when loading YAML
```python
# Solution: Check YAML syntax and schema compatibility
try:
    manifest = ModelDockerComposeManifest.from_yaml(path)
except ValidationError as e:
    print(f"Validation errors: {e.errors()}")
    # Fix YAML structure based on error messages
```

**Issue**: Circular dependency detected
```python
# Solution: Review service dependencies
warnings = manifest.validate_dependencies()
for warning in warnings:
    print(f"Circular dependency: {warning}")
# Refactor service dependencies to remove cycles
```

**Issue**: Port conflicts between services
```python
# Solution: Review port mappings
conflicts = manifest.detect_port_conflicts()
for conflict in conflicts:
    print(f"Port conflict: {conflict}")
# Update port mappings to resolve conflicts
```

## Future Enhancements

Planned improvements for manifest models:

1. **Schema Versioning**: Support multiple docker-compose schema versions
2. **Merge Strategies**: Intelligent merging of multiple manifest files
3. **Templating**: Jinja2-based templating for dynamic configuration
4. **Validation Plugins**: Extensible validation framework for custom rules
5. **Import/Export**: Support for other formats (Kubernetes, Nomad, etc.)

---

**See Also**:
- [Architecture Overview](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)
- [Error Handling Best Practices](../conventions/ERROR_HANDLING_BEST_PRACTICES.md)
- [Testing Guide](../guides/TESTING_GUIDE.md)
