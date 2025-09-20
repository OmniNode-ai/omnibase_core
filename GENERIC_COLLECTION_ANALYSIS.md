# Generic Collection Pattern Analysis

This document analyzes existing collection patterns in the Omnibase Core codebase and demonstrates how they can be refactored to use the new `ModelGenericCollection` base class.

## Overview

The `ModelGenericCollection` provides a standardized, type-safe approach to managing collections of Pydantic models. It includes common operations like adding, removing, filtering, and querying items while maintaining strong typing throughout.

## Existing Collection Patterns Identified

### 1. ModelExamples (Examples Collection)

**Location**: `/app/src/omnibase_core/src/omnibase_core/models/config/model_examples_collection.py`

**Current Pattern**:
```python
class ModelExamples(BaseModel):
    examples: list[ModelExample] = Field(default_factory=list)

    def add_example(self, input_data, output_data=None, name=None, ...):
        # Manual creation and appending
        example = ModelExample(...)
        self.examples.append(example)

    def remove_example(self, index: int) -> bool:
        # Index-based removal with bounds checking
        if 0 <= index < len(self.examples):
            del self.examples[index]
            return True
        return False

    def get_example_by_name(self, name: str) -> ModelExample | None:
        # Manual iteration and matching
        for example in self.examples:
            if example.name == name:
                return example
        return None

    def get_valid_examples(self) -> list[ModelExample]:
        # Manual filtering
        return [example for example in self.examples if example.is_valid]

    def example_count(self) -> int:
        return len(self.examples)
```

**Refactored with Generic Collection**:
```python
from omnibase_core.models.core.model_generic_collection import ModelGenericCollection

class ModelExamples(ModelGenericCollection[ModelExample]):
    """Examples collection using generic collection base."""

    # Inherits: items, collection_name, created_at, updated_at
    # Inherits: add_item, remove_item, get_item_by_name, get_valid_items, item_count

    def add_example(
        self,
        input_data: ModelGenericMetadata[Any],
        output_data: ModelGenericMetadata[Any] | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        context: ModelGenericMetadata[Any] | None = None,
    ) -> None:
        """Add a new example with full type safety."""
        example = ModelExample(
            name=name or f"Example_{len(self.items) + 1}",
            description=description,
            input_data=input_data,
            output_data=output_data,
            context=context,
            tags=tags or [],
            is_valid=True,
            validation_notes=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.add_item(example)  # Use inherited method

    # These methods are now inherited and work automatically:
    # - get_example_by_name() -> get_item_by_name()
    # - get_valid_examples() -> get_valid_items()
    # - example_count() -> item_count()
    # - remove_example() -> remove_item() or remove_item_by_index()

    # Additional domain-specific methods
    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index (legacy compatibility)."""
        return self.get_item_by_index(index)

    def get_example_names(self) -> list[str]:
        """Get all example names (uses inherited functionality)."""
        return self.get_item_names()
```

### 2. ModelMCPToolCollection (Tool Collection)

**Location**: `/app/src/omnibase_core/archived/src/omnibase_core/models/mcp/model_mcp_tool_collection.py`

**Current Pattern**:
```python
class ModelMCPToolCollection(BaseModel):
    tools: dict[str, ModelToolDefinition] = Field(default_factory=dict)

    def add_tool(self, name: str, tool_definition: ModelToolDefinition) -> None:
        self.tools[name] = tool_definition

    def get_tool(self, name: str) -> ModelToolDefinition | None:
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        return list(self.tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self.tools
```

**Refactored with Generic Collection**:
```python
class ModelMCPToolCollection(ModelGenericCollection[ModelToolDefinition]):
    """Tool collection using generic collection base."""

    def add_tool(self, tool_definition: ModelToolDefinition) -> None:
        """Add a tool to the collection."""
        self.add_item(tool_definition)  # Use inherited method

    def get_tool(self, name: str) -> ModelToolDefinition | None:
        """Get a tool by name."""
        return self.get_item_by_name(name)  # Use inherited method

    def list_tool_names(self) -> list[str]:
        """List all tool names."""
        return self.get_item_names()  # Use inherited method

    def has_tool(self, name: str) -> bool:
        """Check if a tool exists."""
        return self.has_item_with_name(name)  # Use inherited method
```

### 3. ModelExternalServiceCollection (Service Collection)

**Current Pattern**:
```python
class ModelExternalServiceCollection(BaseModel):
    services: dict[str, ModelExternalServiceConfig] = Field(default_factory=dict)

    def get_service(self, service_name: str) -> ModelExternalServiceConfig:
        return self.services.get(service_name)

    def has_service(self, service_name: str) -> bool:
        return service_name in self.services

    def add_service(self, service_name: str, config: ModelExternalServiceConfig) -> None:
        self.services[service_name] = config

    def remove_service(self, service_name: str) -> bool:
        if service_name in self.services:
            del self.services[service_name]
            return True
        return False

    def get_service_count(self) -> int:
        return len(self.services)

    def get_service_names(self) -> list:
        return list(self.services.keys())
```

**Refactored with Generic Collection**:
```python
class ModelExternalServiceCollection(ModelGenericCollection[ModelExternalServiceConfig]):
    """External service collection using generic collection base."""

    def get_service(self, service_name: str) -> ModelExternalServiceConfig | None:
        """Get a service by name."""
        return self.get_item_by_name(service_name)

    def has_service(self, service_name: str) -> bool:
        """Check if service exists."""
        return self.has_item_with_name(service_name)

    def add_service(self, config: ModelExternalServiceConfig) -> None:
        """Add a service configuration."""
        self.add_item(config)

    def remove_service(self, service_name: str) -> bool:
        """Remove a service by name."""
        service = self.get_item_by_name(service_name)
        if service and hasattr(service, 'id'):
            return self.remove_item(service.id)
        return False

    def get_service_count(self) -> int:
        """Get service count."""
        return self.item_count()

    def get_service_names(self) -> list[str]:
        """Get service names."""
        return self.get_item_names()
```

## Benefits of Using ModelGenericCollection

### 1. Consistency Across Collections
- **Standardized API**: All collections use the same method names and signatures
- **Common Operations**: filtering, sorting, counting, and querying work the same way
- **Type Safety**: Generic typing ensures compile-time type checking

### 2. Reduced Code Duplication
- **Inherited Methods**: Common operations like `add_item`, `remove_item`, `filter_items` are inherited
- **Automatic Timestamps**: Collections automatically track `created_at` and `updated_at`
- **Standard Queries**: Methods like `get_valid_items`, `get_enabled_items` work across all collections

### 3. Enhanced Functionality
- **Rich Filtering**: Built-in support for filtering by predicates, tags, attributes
- **Multiple Sorting Options**: Sort by priority, name, creation date
- **Comprehensive Queries**: Find items by multiple attributes, check existence by ID/name
- **Batch Operations**: `extend_items`, `clear_all`, `find_items`

### 4. Maintainability
- **Single Source of Truth**: Collection logic is centralized in one place
- **Easy Testing**: Generic collection has comprehensive test coverage
- **Future Enhancements**: New collection features are automatically available to all collections

## Migration Strategy

### Phase 1: Create Adapter Methods
Keep existing public APIs while delegating to generic collection:
```python
class ModelExamples(ModelGenericCollection[ModelExample]):
    # Legacy compatibility methods
    def add_example(self, ...):
        # Convert parameters and delegate to add_item()

    def remove_example(self, index: int) -> bool:
        return self.remove_item_by_index(index)
```

### Phase 2: Deprecate Old Methods
Add deprecation warnings to guide users to new methods:
```python
import warnings

def example_count(self) -> int:
    warnings.warn("example_count() is deprecated, use item_count()", DeprecationWarning)
    return self.item_count()
```

### Phase 3: Remove Legacy Methods
After sufficient transition time, remove old methods and update documentation.

## Advanced Use Cases

### Custom Collection Behaviors
```python
class ModelPrioritizedTaskCollection(ModelGenericCollection[ModelTask]):
    """Task collection with priority-based operations."""

    def add_high_priority_task(self, task: ModelTask) -> None:
        """Add a task with high priority."""
        task.priority = 10
        self.add_item(task)
        self.sort_by_priority(reverse=True)  # Keep high priority first

    def get_next_task(self) -> ModelTask | None:
        """Get the highest priority task."""
        enabled_tasks = self.get_enabled_items()
        return enabled_tasks[0] if enabled_tasks else None

    def complete_task(self, task_id: UUID) -> bool:
        """Mark a task as completed."""
        return self.update_item(task_id, completed=True, enabled=False)
```

### Collection Composition
```python
class ModelWorkflowCollection(ModelGenericCollection[ModelWorkflow]):
    """Workflow collection with sub-collections."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_workflows = ModelGenericCollection[ModelWorkflow]()
        self.completed_workflows = ModelGenericCollection[ModelWorkflow]()

    def add_item(self, workflow: ModelWorkflow) -> None:
        """Add workflow and categorize by status."""
        super().add_item(workflow)
        if workflow.status == "active":
            self.active_workflows.add_item(workflow)
        elif workflow.status == "completed":
            self.completed_workflows.add_item(workflow)
```

## Testing the Generic Collection

Create comprehensive tests to ensure the generic collection works correctly:

```python
# tests/unit/models/core/test_model_generic_collection.py

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from pydantic import BaseModel, Field

from omnibase_core.models.core.model_generic_collection import ModelGenericCollection

class MockItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    enabled: bool = True
    is_valid: bool = True
    priority: int = 0
    tags: list[str] = Field(default_factory=list)

class TestModelGenericCollection:
    def test_add_and_get_items(self):
        collection = ModelGenericCollection[MockItem]()
        item = MockItem(name="test_item")

        collection.add_item(item)

        assert collection.item_count() == 1
        assert collection.get_item(item.id) == item
        assert collection.get_item_by_name("test_item") == item

    def test_filter_operations(self):
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="enabled", enabled=True),
            MockItem(name="disabled", enabled=False),
            MockItem(name="invalid", is_valid=False),
        ]
        collection.extend_items(items)

        enabled_items = collection.get_enabled_items()
        valid_items = collection.get_valid_items()

        assert len(enabled_items) == 2
        assert len(valid_items) == 2

    def test_sorting_operations(self):
        collection = ModelGenericCollection[MockItem]()
        items = [
            MockItem(name="C", priority=1),
            MockItem(name="A", priority=3),
            MockItem(name="B", priority=2),
        ]
        collection.extend_items(items)

        collection.sort_by_priority(reverse=True)
        assert collection.items[0].name == "A"  # Highest priority first

        collection.sort_by_name()
        assert collection.items[0].name == "A"  # Alphabetical order
```

## Conclusion

The `ModelGenericCollection` provides a powerful, type-safe foundation for all collection operations in Omnibase Core. By standardizing collection patterns, we:

1. **Reduce Code Duplication**: Common operations are implemented once
2. **Improve Type Safety**: Generic typing catches errors at compile time
3. **Enhance Maintainability**: Changes to collection behavior apply everywhere
4. **Provide Rich Functionality**: Advanced filtering, sorting, and querying built-in
5. **Enable Consistency**: All collections work the same way across the codebase

The migration can be done gradually with backward compatibility, ensuring existing code continues to work while new collections benefit from the enhanced functionality.