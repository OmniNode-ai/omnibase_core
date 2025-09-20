# Configuration Base Class Refactoring Analysis

## Overview

Created `ModelConfigurationBase` and related classes to standardize common patterns found across configuration models. This eliminates field duplication and provides consistent configuration interfaces.

## New Base Classes

### 1. `ModelConfigurationBase[T]`
Generic base class providing:
- Core metadata: `name`, `description`, `version`
- Lifecycle control: `enabled`, `created_at`, `updated_at`
- Generic typed data: `config_data: T`
- Common utility methods

### 2. `ModelTypedConfiguration[T]`
Extends `ModelConfigurationBase` with `ModelCustomProperties` for configurations needing custom fields.

### 3. `ModelSimpleConfiguration`
For basic key-value configurations using `dict[str, Any]`.

## Refactoring Examples

### Before and After: ModelArtifactTypeConfig

**Before:**
```python
class ModelArtifactTypeConfig(BaseModel):
    """Configuration for artifact types."""

    name: EnumArtifactType = Field(...)
    metadata_file: Path | None = Field(None)
    version_pattern: str | None = Field(None)
```

**After:**
```python
from pydantic import Field
from pathlib import Path
from ..core.model_configuration_base import ModelConfigurationBase
from ...enums.enum_artifact_type import EnumArtifactType

class ArtifactTypeConfigData(BaseModel):
    """Typed configuration data for artifact types."""
    artifact_type: EnumArtifactType = Field(...)
    metadata_file: Path | None = Field(None)
    version_pattern: str | None = Field(None)

class ModelArtifactTypeConfig(ModelConfigurationBase[ArtifactTypeConfigData]):
    """Configuration for artifact types with standardized base."""

    @classmethod
    def create_for_type(
        cls,
        artifact_type: EnumArtifactType,
        metadata_file: Path | None = None,
        version_pattern: str | None = None
    ) -> 'ModelArtifactTypeConfig':
        """Create configuration for specific artifact type."""
        data = ArtifactTypeConfigData(
            artifact_type=artifact_type,
            metadata_file=metadata_file,
            version_pattern=version_pattern
        )
        return cls.create_with_data(
            name=f"{artifact_type.value}_config",
            config_data=data
        )
```

**Benefits:**
- Gains automatic `enabled`, `created_at`, `updated_at` fields
- Consistent configuration interface
- Built-in utility methods like `is_enabled()`, `update_timestamp()`

### Before and After: ModelNamespaceConfig

**Before:**
```python
class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling."""

    enabled: bool = True
    strategy: Literal["ONEX_DEFAULT", "EXPLICIT", "AUTO"] = "ONEX_DEFAULT"
```

**After:**
```python
from typing import Literal
from pydantic import BaseModel, Field
from ..core.model_configuration_base import ModelConfigurationBase

class NamespaceConfigData(BaseModel):
    """Typed configuration data for namespaces."""
    strategy: Literal["ONEX_DEFAULT", "EXPLICIT", "AUTO"] = Field(
        default="ONEX_DEFAULT",
        description="Namespace resolution strategy"
    )

class ModelNamespaceConfig(ModelConfigurationBase[NamespaceConfigData]):
    """Configuration for namespace handling with standardized base."""

    @classmethod
    def create_with_strategy(
        cls,
        strategy: Literal["ONEX_DEFAULT", "EXPLICIT", "AUTO"]
    ) -> 'ModelNamespaceConfig':
        """Create namespace configuration with specific strategy."""
        data = NamespaceConfigData(strategy=strategy)
        return cls.create_with_data(
            name=f"namespace_{strategy.lower()}",
            config_data=data
        )

    def get_strategy(self) -> str:
        """Get the namespace strategy."""
        return self.config_data.strategy if self.config_data else "ONEX_DEFAULT"
```

**Benefits:**
- `enabled` field now comes from base class with consistent semantics
- Gains metadata fields (`name`, `description`, `version`)
- Automatic timestamps and validation

### Before and After: ModelNodeConfiguration

**Before:**
```python
class ModelNodeConfiguration(BaseModel):
    """Configuration for a node."""

    # Execution settings
    max_retries: int | None = Field(default=None)
    timeout_seconds: int | None = Field(default=None)
    batch_size: int | None = Field(default=None)
    parallel_execution: bool = Field(default=False)

    # Resource limits
    max_memory_mb: int | None = Field(default=None)
    max_cpu_percent: float | None = Field(default=None)

    # Feature flags
    enable_caching: bool = Field(default=False)
    enable_monitoring: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)

    # Connection settings
    endpoint: str | None = Field(default=None)
    port: int | None = Field(default=None)
    protocol: str | None = Field(default=None)

    # Custom configuration
    custom_settings: dict[str, str] | None = Field(default=None)
    custom_flags: dict[str, bool] | None = Field(default=None)
    custom_limits: dict[str, int] | None = Field(default=None)
```

**After:**
```python
from pydantic import BaseModel, Field
from ..core.model_configuration_base import ModelTypedConfiguration

class NodeConfigurationData(BaseModel):
    """Typed configuration data for nodes."""

    # Execution settings
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    timeout_seconds: int | None = Field(default=None, description="Execution timeout")
    batch_size: int | None = Field(default=None, description="Batch processing size")
    parallel_execution: bool = Field(default=False, description="Enable parallel execution")

    # Resource limits
    max_memory_mb: int | None = Field(default=None, description="Maximum memory usage in MB")
    max_cpu_percent: float | None = Field(default=None, description="Maximum CPU usage percentage")

    # Feature flags
    enable_caching: bool = Field(default=False, description="Enable result caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_tracing: bool = Field(default=False, description="Enable detailed tracing")

    # Connection settings
    endpoint: str | None = Field(default=None, description="Service endpoint")
    port: int | None = Field(default=None, description="Service port")
    protocol: str | None = Field(default=None, description="Communication protocol")

class ModelNodeConfiguration(ModelTypedConfiguration[NodeConfigurationData]):
    """Configuration for a node with standardized base and custom properties."""

    def get_execution_timeout(self) -> int:
        """Get execution timeout with default."""
        return self.get_config_value('timeout_seconds', 30)

    def is_parallel_enabled(self) -> bool:
        """Check if parallel execution is enabled."""
        return self.get_config_value('parallel_execution', False)

    def get_resource_limits(self) -> dict[str, int | float]:
        """Get resource limits as a dictionary."""
        return {
            'memory_mb': self.get_config_value('max_memory_mb', 512),
            'cpu_percent': self.get_config_value('max_cpu_percent', 80.0)
        }

    @classmethod
    def create_for_service(
        cls,
        service_name: str,
        endpoint: str,
        port: int,
        **config_overrides
    ) -> 'ModelNodeConfiguration':
        """Create configuration for a specific service."""
        data = NodeConfigurationData(
            endpoint=endpoint,
            port=port,
            **config_overrides
        )
        return cls.create_with_data(
            name=f"{service_name}_node_config",
            config_data=data
        )
```

**Benefits:**
- Eliminates custom field dictionaries - now uses `ModelCustomProperties`
- Gains standard configuration metadata and lifecycle management
- Type-safe configuration data access
- Consistent API across all configuration models

### Before and After: ModelEnvironmentProperties

**Before:**
```python
class ModelEnvironmentProperties(BaseModel):
    """Type-safe custom environment properties."""

    properties: dict[str, PropertyValue] = Field(default_factory=dict)
    property_metadata: dict[str, dict[str, str]] = Field(default_factory=dict)

    # ... many utility methods
```

**After:**
```python
from ..core.model_configuration_base import ModelConfigurationBase

class ModelEnvironmentProperties(ModelConfigurationBase[dict[str, PropertyValue]]):
    """Type-safe custom environment properties with standardized base."""

    property_metadata: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Metadata about each property"
    )

    @property
    def properties(self) -> dict[str, PropertyValue]:
        """Access properties through config_data."""
        return self.config_data or {}

    def set_property(
        self,
        key: str,
        value: PropertyValue,
        description: str | None = None,
        source: str | None = None,
    ) -> None:
        """Set a property with optional metadata."""
        if self.config_data is None:
            self.config_data = {}
        self.config_data[key] = value

        if description or source:
            metadata = self.property_metadata.get(key, {})
            if description:
                metadata["description"] = description
            if source:
                metadata["source"] = source
            self.property_metadata[key] = metadata

        self.update_timestamp()

    # ... keep existing utility methods but update to use self.config_data
```

**Benefits:**
- Gains configuration lifecycle management
- Properties become part of standard `config_data` pattern
- Automatic timestamp updates on property changes

## Migration Strategy

1. **Phase 1**: Create new base classes (✅ Complete)
2. **Phase 2**: Update existing config models to inherit from base classes
3. **Phase 3**: Update consumers to use new standardized interface
4. **Phase 4**: Remove legacy patterns and custom field dictionaries

## Breaking Changes

- Configuration models will have additional fields (`created_at`, `updated_at`, etc.)
- Custom field dictionaries replaced with `ModelCustomProperties` pattern
- Some field access patterns will need updating to use `get_config_value()`

## Benefits Summary

1. **Consistency**: All configuration models follow the same patterns
2. **Reduced Duplication**: Common fields and methods defined once
3. **Type Safety**: Generic typing for configuration data
4. **Extensibility**: Built-in custom properties support
5. **Lifecycle Management**: Automatic timestamps and validation
6. **Migration Support**: Helper methods for backward compatibility