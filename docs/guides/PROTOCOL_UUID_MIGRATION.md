# Protocol UUID Migration Guide

> **Version**: 0.4.0
> **Last Updated**: 2025-12-08
> **Breaking Change**: Yes
> **Related**: [CLAUDE.md](../../CLAUDE.md), [Container Protocols](../../src/omnibase_core/protocols/container.py)

---

## Overview

**PR #119** changes ID fields in protocol definitions from `str` to `UUID`. This is a **breaking change** for downstream consumers that implement these protocols.

### Why This Change?

1. **Strong Typing**: UUID types provide compile-time and runtime type safety, preventing accidental assignment of non-UUID strings
2. **Consistency**: Aligns with Pydantic best practices and ONEX type system conventions
3. **Validation**: UUID type ensures all IDs are valid UUIDs, catching malformed identifiers early
4. **Clarity**: Makes the expected format explicit in the type signature

### Impact

- **Breaking**: Any class implementing affected protocols must update field types from `str` to `UUID`
- **Breaking**: Methods accepting or returning IDs must be updated
- **Migration Required**: Existing string-based ID values must be converted

---

## Affected Protocols

The following protocols have ID fields changed from `str` to `UUID`:

### Container Protocols (`protocols/container.py`)

| Protocol | Field | Change |
|----------|-------|--------|
| `ProtocolServiceRegistrationMetadata` | `service_id` | `str` -> `UUID` |
| `ProtocolServiceRegistration` | `registration_id` | `str` -> `UUID` |
| `ProtocolServiceInstance` | `instance_id` | `str` -> `UUID` |
| `ProtocolServiceInstance` | `service_registration_id` | `str` -> `UUID` |
| `ProtocolDependencyGraph` | `service_id` | `str` -> `UUID` |
| `ProtocolInjectionContext` | `context_id` | `str` -> `UUID` |
| `ProtocolInjectionContext` | `target_service_id` | `str` -> `UUID` |
| `ProtocolServiceRegistryStatus` | `registry_id` | `str` -> `UUID` |

### Type Protocols (`protocols/types.py`)

| Protocol | Field/Method | Change |
|----------|--------------|--------|
| `ProtocolIdentifiable` | `id` (property) | `str` -> `UUID` |
| `ProtocolValidatable` | `get_validation_id()` (return type) | `str` -> `UUID` |
| `ProtocolNodeMetadataBlock` | `uuid` | `str` -> `UUID` |
| `ProtocolNodeMetadata` | `node_id` | `str` -> `UUID` |
| `ProtocolServiceInstance` | `service_id` | `str` -> `UUID` |

### Schema Protocols (`protocols/schema.py`)

| Protocol | Field | Change |
|----------|-------|--------|
| `ProtocolSchemaModel` | `schema_id` | `str` -> `UUID` |

### Validation Protocols (`protocols/validation.py`)

| Protocol | Field | Change |
|----------|-------|--------|
| `ProtocolComplianceRule` | `rule_id` | `str` -> `UUID` |

---

## Migration Steps

### Step 1: Update Imports

Add the `UUID` import from the standard library:

```python
# Before
from typing import Protocol

# After
from typing import Protocol
from uuid import UUID
```

### Step 2: Update Field Type Annotations

Change field type annotations from `str` to `UUID`:

```python
# Before
class MyServiceMetadata:
    service_id: str

# After
class MyServiceMetadata:
    service_id: UUID
```

### Step 3: Update ID Generation

Replace string ID generation with proper UUID generation:

```python
# Before
import uuid

class MyService:
    def __init__(self):
        self.service_id = str(uuid.uuid4())  # String representation

# After
from uuid import UUID, uuid4

class MyService:
    def __init__(self):
        self.service_id = uuid4()  # UUID object
```

### Step 4: Convert Existing String IDs

For existing string IDs in databases or configurations:

```python
from uuid import UUID

# Convert string to UUID
string_id = "550e8400-e29b-41d4-a716-446655440000"
uuid_id = UUID(string_id)

# With validation and error handling
def convert_string_to_uuid(string_id: str) -> UUID:
    """Convert a string ID to UUID with validation."""
    try:
        return UUID(string_id)
    except ValueError as e:
        raise ValueError(f"Invalid UUID format: {string_id}") from e
```

### Step 5: Update Method Signatures

Update methods that accept or return IDs:

```python
# Before
async def get_service(self, service_id: str) -> Service:
    ...

async def register_service(self, service: Service) -> str:
    ...

# After
from uuid import UUID

async def get_service(self, service_id: UUID) -> Service:
    ...

async def register_service(self, service: Service) -> UUID:
    ...
```

### Step 6: Update Pydantic Models

For Pydantic models implementing protocols:

```python
# Before
from pydantic import BaseModel

class ServiceMetadata(BaseModel):
    service_id: str
    service_name: str

# After
from pydantic import BaseModel
from uuid import UUID

class ServiceMetadata(BaseModel):
    service_id: UUID
    service_name: str
```

Pydantic automatically handles UUID serialization/deserialization.

---

## Handling Legacy Serialized Data

### Existing JSON/YAML Without UUID Fields

When deserializing existing data that predates the UUID migration:

#### ModelNodeMetadataBlock

The `uuid` field has `default_factory=uuid4`, so existing data without this field will automatically get a new UUID:

```python
from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Legacy data without uuid field
legacy_data = {
    "name": "my-node",
    "version": {"major": 1, "minor": 0, "patch": 0},
    "author": "developer",
    "created_at": "2024-01-01T00:00:00Z",
    "last_modified_at": "2024-01-01T00:00:00Z",
    "hash": "a" * 64,
    "entrypoint": "python://main.py",
    "namespace": "onex.tools.example"
}

# Pydantic auto-generates uuid via default_factory
block = ModelNodeMetadataBlock(**legacy_data)
assert block.uuid is not None  # New UUID generated
```

#### Service Registration Models

For models with required UUID fields:

```python
from uuid import UUID, uuid4
from pydantic import ValidationError

# Option 1: Provide UUID during deserialization
def deserialize_with_uuid(data: dict) -> ModelServiceMetadata:
    if "service_id" not in data:
        data["service_id"] = uuid4()
    elif isinstance(data["service_id"], str):
        data["service_id"] = UUID(data["service_id"])
    return ModelServiceMetadata(**data)
```

### Database Migration Strategy

For persisted data in databases:

```python
# Example: SQLAlchemy migration
def upgrade():
    # 1. Add nullable uuid column
    op.add_column('nodes', sa.Column('uuid', sa.UUID(), nullable=True))

    # 2. Populate existing rows
    op.execute("""
        UPDATE nodes
        SET uuid = gen_random_uuid()
        WHERE uuid IS NULL
    """)

    # 3. Make column non-nullable
    op.alter_column('nodes', 'uuid', nullable=False)
```

---

## Implementation Changes

### Method Signature Updates

The following method signatures have changed to use UUID types:

#### ServiceRegistry (`container/service_registry.py`)

| Method | Parameter | Before | After |
|--------|-----------|--------|-------|
| `unregister_service` | `registration_id` | `str` | `UUID` |
| `get_registration` | `registration_id` | `str` | `UUID` |
| `get_active_instances` | `registration_id` | `str \| None` | `UUID \| None` |
| `dispose_instances` | `registration_id` | `str` | `UUID` |
| `get_dependency_graph` | `service_id` | `str` | `UUID` |
| `validate_service_health` | `registration_id` | `str` | `UUID` |
| `update_service_configuration` | `registration_id` | `str` | `UUID` |
| `create_injection_scope` | `parent_scope` | `str \| None` | `UUID \| None` |
| `create_injection_scope` | return type | `str` | `UUID` |
| `dispose_injection_scope` | `scope_id` | `str` | `UUID` |
| `get_injection_context` | `context_id` | `str` | `UUID` |

### Updating Method Calls

**Before**:
```python
registry = container.get_service("ProtocolServiceRegistry")
await registry.unregister_service("service-id-string")
scope_id = await registry.create_injection_scope("my-scope", "parent-scope-string")
```

**After**:
```python
from uuid import UUID

registry = container.get_service("ProtocolServiceRegistry")
await registry.unregister_service(UUID("550e8400-e29b-41d4-a716-446655440000"))
parent = UUID("660e8400-e29b-41d4-a716-446655440000")
scope_id = await registry.create_injection_scope("my-scope", parent)
# scope_id is now UUID, not str
```

---

## Code Examples

### Example 1: Implementing ProtocolIdentifiable

**Before**:
```python
from typing import Literal

class MyEntity:
    __omnibase_identifiable_marker__: Literal[True] = True

    def __init__(self, entity_id: str):
        self._id = entity_id

    @property
    def id(self) -> str:
        return self._id
```

**After**:
```python
from typing import Literal
from uuid import UUID, uuid4

class MyEntity:
    __omnibase_identifiable_marker__: Literal[True] = True

    def __init__(self, entity_id: UUID | None = None):
        self._id = entity_id or uuid4()

    @property
    def id(self) -> UUID:
        return self._id
```

### Example 2: Implementing ProtocolValidatable

**Before**:
```python
from typing import Any

class MyValidatable:
    def __init__(self, validation_id: str):
        self._validation_id = validation_id

    async def get_validation_context(self) -> dict[str, Any]:
        return {"entity_type": "my_entity"}

    async def get_validation_id(self) -> str:
        return self._validation_id
```

**After**:
```python
from typing import Any
from uuid import UUID, uuid4

class MyValidatable:
    def __init__(self, validation_id: UUID | None = None):
        self._validation_id = validation_id or uuid4()

    async def get_validation_context(self) -> dict[str, Any]:
        return {"entity_type": "my_entity"}

    async def get_validation_id(self) -> UUID:
        return self._validation_id
```

### Example 3: Implementing ProtocolServiceInstance

**Before**:
```python
from datetime import datetime
from typing import Any

class ServiceInstance:
    def __init__(
        self,
        instance_id: str,
        registration_id: str,
        instance: Any,
    ):
        self.instance_id = instance_id
        self.service_registration_id = registration_id
        self.instance = instance
        self.lifecycle = "transient"
        self.scope = "global"
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0
        self.is_disposed = False
        self.metadata: dict[str, Any] = {}

    async def validate_instance(self) -> bool:
        return not self.is_disposed

    def is_active(self) -> bool:
        return not self.is_disposed
```

**After**:
```python
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

class ServiceInstance:
    def __init__(
        self,
        instance: Any,
        instance_id: UUID | None = None,
        registration_id: UUID | None = None,
    ):
        self.instance_id = instance_id or uuid4()
        self.service_registration_id = registration_id or uuid4()
        self.instance = instance
        self.lifecycle = "transient"
        self.scope = "global"
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0
        self.is_disposed = False
        self.metadata: dict[str, Any] = {}

    async def validate_instance(self) -> bool:
        return not self.is_disposed

    def is_active(self) -> bool:
        return not self.is_disposed
```

### Example 4: Handling Legacy String IDs

For systems with existing string IDs in storage:

```python
from uuid import UUID

class LegacyMigrationHelper:
    """Helper for migrating legacy string IDs to UUID."""

    @staticmethod
    def migrate_id(legacy_id: str | UUID) -> UUID:
        """Convert legacy string ID to UUID.

        Args:
            legacy_id: Either a string UUID or UUID object

        Returns:
            UUID object

        Raises:
            ValueError: If string is not a valid UUID format
        """
        if isinstance(legacy_id, UUID):
            return legacy_id
        return UUID(legacy_id)

    @staticmethod
    def safe_migrate_id(legacy_id: str | UUID, default: UUID | None = None) -> UUID | None:
        """Safely convert legacy string ID to UUID.

        Args:
            legacy_id: Either a string UUID or UUID object
            default: Default value if conversion fails

        Returns:
            UUID object or default value
        """
        try:
            return LegacyMigrationHelper.migrate_id(legacy_id)
        except ValueError:
            return default
```

---

## Migration Checklist

### For External Projects Consuming omnibase_core

- [ ] **Update imports**: Add `from uuid import UUID, uuid4`
  ```python
  from uuid import UUID, uuid4
  ```

- [ ] **Update field types**: Change `str` to `UUID` for all ID fields
  ```python
  # Before: service_id: str
  # After:  service_id: UUID
  ```

- [ ] **Update ID generation**: Use `uuid4()` instead of `str(uuid.uuid4())`
  ```python
  # Before: self.id = str(uuid.uuid4())
  # After:  self.id = uuid4()
  ```

- [ ] **Update method signatures**: Change parameter and return types
  ```python
  # Before: def get_by_id(self, id: str) -> T
  # After:  def get_by_id(self, id: UUID) -> T
  ```

- [ ] **Convert stored string IDs**: Add migration for existing data
  ```python
  legacy_id = UUID(stored_string_id)
  ```

- [ ] **Update tests**: Fix test fixtures and assertions
  ```python
  # Before: assert entity.id == "some-uuid-string"
  # After:  assert entity.id == UUID("some-uuid-string")
  ```

- [ ] **Run type checker**: Ensure mypy passes
  ```bash
  poetry run mypy src/
  ```

- [ ] **Run tests**: Ensure all tests pass
  ```bash
  poetry run pytest tests/ -x
  ```

---

## Common Pitfalls

### Do Not Compare UUID to String Directly

```python
from uuid import UUID

uuid_id = UUID("550e8400-e29b-41d4-a716-446655440000")
string_id = "550e8400-e29b-41d4-a716-446655440000"

# WRONG - comparison works but is not type-safe
if uuid_id == string_id:  # Works but mypy will warn
    pass

# RIGHT - explicit conversion
if uuid_id == UUID(string_id):
    pass

# RIGHT - compare string representations
if str(uuid_id) == string_id:
    pass
```

### Do Not Use str() for Storage When UUID is Expected

```python
from uuid import UUID, uuid4

# WRONG - converts UUID back to string
def create_entity() -> dict:
    return {"id": str(uuid4())}  # Returns string

# RIGHT - keep as UUID
def create_entity() -> dict:
    return {"id": uuid4()}  # Returns UUID
```

### Handle None IDs Explicitly

```python
from uuid import UUID, uuid4

# WRONG - ambiguous default
def __init__(self, id: UUID = None):  # Type error
    self.id = id

# RIGHT - explicit optional type
def __init__(self, id: UUID | None = None):
    self.id = id or uuid4()
```

### JSON Serialization

UUIDs need explicit serialization for JSON:

```python
import json
from uuid import UUID, uuid4

entity_id = uuid4()

# WRONG - UUID is not JSON serializable
json.dumps({"id": entity_id})  # TypeError

# RIGHT - convert to string for JSON
json.dumps({"id": str(entity_id)})

# RIGHT with Pydantic - automatic serialization
from pydantic import BaseModel

class Entity(BaseModel):
    id: UUID

entity = Entity(id=uuid4())
entity.model_dump_json()  # Works automatically
```

---

## API Reference

### UUID Generation

```python
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS

# Generate random UUID (version 4)
random_id = uuid4()

# Generate deterministic UUID (version 5)
deterministic_id = uuid5(NAMESPACE_DNS, "my-service-name")
```

### UUID Conversion

```python
from uuid import UUID

# String to UUID
uuid_from_string = UUID("550e8400-e29b-41d4-a716-446655440000")

# UUID to string
string_from_uuid = str(uuid_from_string)

# UUID to hex (no hyphens)
hex_from_uuid = uuid_from_string.hex
# Result: "550e8400e29b41d4a716446655440000"

# UUID to bytes
bytes_from_uuid = uuid_from_string.bytes
```

### UUID Properties

```python
from uuid import UUID

uuid_id = UUID("550e8400-e29b-41d4-a716-446655440000")

uuid_id.version  # 4 (for uuid4)
uuid_id.variant  # RFC_4122
uuid_id.hex      # "550e8400e29b41d4a716446655440000"
uuid_id.int      # Integer representation
```

---

## Support

- **Questions**: See [CLAUDE.md](../../CLAUDE.md) for quick reference
- **Protocol Documentation**: See [Container Protocols](../../src/omnibase_core/protocols/container.py)
- **Type Protocols**: See [Type Protocols](../../src/omnibase_core/protocols/types.py)

---

**Last Updated**: 2025-12-08
**Version**: 0.4.0
