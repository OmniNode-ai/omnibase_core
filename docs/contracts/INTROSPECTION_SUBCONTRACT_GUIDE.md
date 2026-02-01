> **Navigation**: [Home](../index.md) > Contracts > Introspection Subcontract Guide

# Introspection Subcontract Guide

## Overview

`ModelIntrospectionSubcontract` provides declarative configuration for node introspection capabilities in ONEX. This subcontract enables standardized node discovery, metadata exposure, and contract retrieval through YAML configuration.

**Version**: 1.0.0 (Interface Locked)
**Location**: `omnibase_core.models.contracts.subcontracts.ModelIntrospectionSubcontract`
**Stability**: Interface locked for code generation - safe for production use

---

## Features

- **Metadata Exposure**: Control what metadata is included in introspection responses
- **Contract Retrieval**: Enable/disable contract and schema information
- **Capability Discovery**: Expose node capabilities and dependencies
- **Security Controls**: Redact sensitive information and restrict access
- **Performance Optimization**: Cache introspection responses with configurable TTL
- **Field Filtering**: Exclude specific fields or patterns from introspection
- **Depth Control**: Limit introspection depth for nested objects

---

## Usage in YAML Contracts

### Basic Configuration

```yaml
# contract.yaml
introspection:
  introspection_enabled: true
  include_metadata: true
  include_contract: true
  include_capabilities: true
```

### Complete Configuration Example

```yaml
introspection:
  # Core settings
  introspection_enabled: true

  # Metadata controls
  include_metadata: true
  include_core_metadata: true           # Name, version, type
  include_organization_metadata: true   # Author, description, tags

  # Contract and schema
  include_contract: true
  include_input_schema: true
  include_output_schema: true
  include_cli_interface: true

  # Capabilities and dependencies
  include_capabilities: true
  include_dependencies: true
  include_optional_dependencies: true
  include_external_tools: true

  # State and error information
  include_state_models: true
  include_error_codes: true
  include_event_channels: true

  # Filtering and depth control
  depth_limit: 10                       # Max nesting depth
  exclude_fields:
    - _internal
    - _cache
    - _temporary
  exclude_field_patterns:
    - password
    - secret
    - token
    - api_key

  # Performance optimization
  cache_introspection_response: true
  cache_ttl_seconds: 300                # 5 minutes

  # Output formatting
  compact_output: false                 # Use indented JSON
  include_timestamps: true
  include_version_info: true

  # Discovery and integration
  enable_auto_discovery: true
  enable_health_check: true
  enable_lifecycle_hooks: true

  # Security
  redact_sensitive_info: true
  require_authentication: false
  allowed_introspection_sources: []
```

---

## Python API

### Creating from Python

```python
from omnibase_core.models.contracts.subcontracts import ModelIntrospectionSubcontract

# Minimal configuration
introspection = ModelIntrospectionSubcontract()

# Custom configuration
introspection = ModelIntrospectionSubcontract(
    introspection_enabled=True,
    include_metadata=True,
    include_capabilities=True,
    depth_limit=15,
    cache_ttl_seconds=600,
    redact_sensitive_info=True
)

# From YAML/JSON
config_dict = {
    'introspection_enabled': True,
    'include_metadata': True,
    'depth_limit': 10
}
introspection = ModelIntrospectionSubcontract(**config_dict)
```

### Integration with MixinIntrospection

```python
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_introspection import MixinNodeIntrospection
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MyNode(NodeCoreBase, MixinNodeIntrospection):
    """Node with declarative introspection configuration."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)

        # Load introspection configuration from contract
        self.introspection_config = self._load_introspection_config()

    def _load_introspection_config(self) -> ModelIntrospectionSubcontract:
        """Load introspection config from contract."""
        # Contract loading logic here
        return ModelIntrospectionSubcontract(
            introspection_enabled=True,
            include_metadata=True
        )

    @classmethod
    def get_introspection_response(cls):
        """Generate introspection response respecting configuration."""
        # Use inherited method from MixinNodeIntrospection
        return super().get_introspection_response()
```

---

## Configuration Reference

### Core Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `introspection_enabled` | `bool` | `true` | Enable/disable all introspection |
| `correlation_id` | `UUID` | Auto-generated | Correlation ID for tracing |

### Metadata Controls

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `include_metadata` | `bool` | `true` | Include node metadata |
| `include_core_metadata` | `bool` | `true` | Name, version, type |
| `include_organization_metadata` | `bool` | `true` | Author, description, tags |

### Contract and Schema

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `include_contract` | `bool` | `true` | Contract details |
| `include_input_schema` | `bool` | `true` | Input state schema |
| `include_output_schema` | `bool` | `true` | Output state schema |
| `include_cli_interface` | `bool` | `true` | CLI details |
| `export_json_schema` | `bool` | `true` | Export JSON schema |
| `export_openapi_schema` | `bool` | `false` | Export OpenAPI schema |

### Capabilities and Dependencies

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `include_capabilities` | `bool` | `true` | Node capabilities |
| `include_dependencies` | `bool` | `true` | Runtime dependencies |
| `include_optional_dependencies` | `bool` | `true` | Optional dependencies |
| `include_external_tools` | `bool` | `true` | External tool dependencies |

### State and Error Information

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `include_state_models` | `bool` | `true` | State model information |
| `include_error_codes` | `bool` | `true` | Error codes |
| `include_event_channels` | `bool` | `true` | Event channels |

### Filtering and Depth Control

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `depth_limit` | `int` | `10` | Max nesting depth (1-50) |
| `exclude_fields` | `list[str]` | `[]` | Fields to exclude |
| `exclude_field_patterns` | `list[str]` | See below* | Field patterns to exclude |

*Default patterns: `password`, `secret`, `token`, `api_key`, `private_key`, `credential`

### Performance Optimization

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cache_introspection_response` | `bool` | `true` | Cache responses |
| `cache_ttl_seconds` | `int` | `300` | Cache TTL (60-3600s) |

### Output Formatting

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `compact_output` | `bool` | `false` | Use compact JSON |
| `include_timestamps` | `bool` | `true` | Include timestamps |
| `include_version_info` | `bool` | `true` | Include version info |

### Discovery and Integration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_auto_discovery` | `bool` | `true` | Auto-discovery |
| `enable_health_check` | `bool` | `true` | Health check endpoint |
| `enable_lifecycle_hooks` | `bool` | `true` | Lifecycle hook info |

### Security

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `redact_sensitive_info` | `bool` | `true` | Redact sensitive data |
| `require_authentication` | `bool` | `false` | Require auth |
| `allowed_introspection_sources` | `list[str]` | `[]` | Allowed IP addresses |

---

## Validators

### Depth Limit Validation

```python
# Valid: depth_limit <= 30
introspection = ModelIntrospectionSubcontract(depth_limit=15)

# Warning: depth_limit > 30 raises ModelOnexError
introspection = ModelIntrospectionSubcontract(depth_limit=35)
# ❌ Error: depth_limit exceeding 30 may cause performance issues
```

### Cache TTL Validation

```python
# Valid: cache_ttl_seconds >= 60
introspection = ModelIntrospectionSubcontract(
    cache_introspection_response=True,
    cache_ttl_seconds=300
)

# Warning: cache_ttl_seconds < 60 raises ModelOnexError
introspection = ModelIntrospectionSubcontract(
    cache_introspection_response=True,
    cache_ttl_seconds=30
)
# ❌ Error: cache_ttl_seconds below 60 seconds may cause excessive cache churn
```

### Introspection Consistency Validation

```python
# Valid: introspection enabled with features
introspection = ModelIntrospectionSubcontract(
    introspection_enabled=True,
    include_metadata=True
)

# Invalid: introspection disabled but features enabled
introspection = ModelIntrospectionSubcontract(
    introspection_enabled=False,
    include_metadata=True  # Will have no effect
)
# ❌ Error: introspection_enabled is False, but include_metadata is enabled
```

### Security Consistency Validation

```python
# Valid: authentication with redaction
introspection = ModelIntrospectionSubcontract(
    require_authentication=True,
    redact_sensitive_info=True
)

# Warning: authentication without redaction
introspection = ModelIntrospectionSubcontract(
    require_authentication=True,
    redact_sensitive_info=False
)
# ❌ Error: require_authentication is True but redact_sensitive_info is False
```

---

## Common Use Cases

### 1. Production Node (Minimal Exposure)

```yaml
introspection:
  introspection_enabled: true
  include_metadata: true
  include_contract: false           # Don't expose contract details
  include_capabilities: false       # Don't expose capabilities
  depth_limit: 5                    # Limit depth
  cache_ttl_seconds: 600            # Cache longer
  redact_sensitive_info: true
  require_authentication: true
```

### 2. Development Node (Full Exposure)

```yaml
introspection:
  introspection_enabled: true
  include_metadata: true
  include_contract: true
  include_capabilities: true
  include_dependencies: true
  include_state_models: true
  depth_limit: 20
  cache_ttl_seconds: 60             # Short cache for development
  redact_sensitive_info: true
  require_authentication: false
```

### 3. Registry Service Node (Discovery Optimized)

```yaml
introspection:
  introspection_enabled: true
  enable_auto_discovery: true
  enable_health_check: true
  cache_introspection_response: true
  cache_ttl_seconds: 300
  compact_output: true              # Faster network transfer
```

### 4. Secure Internal Service

```yaml
introspection:
  introspection_enabled: true
  redact_sensitive_info: true
  require_authentication: true
  allowed_introspection_sources:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
  exclude_field_patterns:
    - password
    - secret
    - token
    - api_key
    - private_key
    - credential
    - connection_string
```

---

## Best Practices

### Security

1. **Always Enable Redaction**: Keep `redact_sensitive_info: true` in production
2. **Use Authentication**: Enable `require_authentication` for sensitive nodes
3. **Limit Exposure**: Only include necessary information in introspection
4. **Filter Sensitive Fields**: Use `exclude_field_patterns` for security-sensitive fields

### Performance

1. **Enable Caching**: Set `cache_introspection_response: true` for frequently queried nodes
2. **Appropriate TTL**: Use 300-600s for production, 60s for development
3. **Limit Depth**: Keep `depth_limit` ≤ 20 for better performance
4. **Compact Output**: Use `compact_output: true` for network-constrained environments

### Development Workflow

1. **Full Introspection in Dev**: Enable all fields during development
2. **Minimal in Production**: Disable unnecessary fields in production
3. **Contract Documentation**: Use introspection to auto-generate docs
4. **Testing**: Test introspection responses in CI/CD

---

## Migration from Legacy Introspection

### Before (Hardcoded in Code)

```python
class MyNode(MixinNodeIntrospection):
    @classmethod
    def get_introspection_response(cls):
        # Hardcoded logic
        if os.getenv("ENABLE_FULL_INTROSPECT") == "true":
            return full_response
        return minimal_response
```

### After (Declarative Configuration)

```yaml
# contract.yaml
introspection:
  introspection_enabled: true
  include_metadata: true
  include_contract: ${ENABLE_FULL_INTROSPECT}
```

```python
class MyNode(MixinNodeIntrospection):
    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.introspection_config = self._load_config()

    # Introspection behavior now controlled by YAML config
```

---

## Related Documentation

- [Mixin Architecture](../architecture/MIXIN_ARCHITECTURE.md)
- [Node Building Guide](../guides/node-building/README.md)
- [Contract System Overview](../architecture/CONTRACT_SYSTEM.md)
- [ONEX Four-Node Architecture](../architecture/ONEX_FOUR_NODE_ARCHITECTURE.md)

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Status**: Stable - Interface Locked
