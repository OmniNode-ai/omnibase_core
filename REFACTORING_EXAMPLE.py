"""
Example demonstrating how to refactor existing collection patterns
to use ModelGenericCollection.

This file shows concrete before/after examples for refactoring ModelExamples
and other collection classes to use the generic collection pattern.
"""

from datetime import UTC, datetime

# For this example, we'll define a simplified version
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Import the generic collection (in practice this would work once imports are fixed)
# from omnibase_core.models.core.model_generic_collection import ModelGenericCollection


T = TypeVar("T", bound=BaseModel)


class ModelGenericCollection(BaseModel, Generic[T]):
    """Simplified version for demonstration."""

    items: List[T] = Field(default_factory=list)
    collection_name: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_item(self, item: T) -> None:
        self.items.append(item)
        self.updated_at = datetime.now(UTC)

    def get_item_by_name(self, name: str) -> Optional[T]:
        for item in self.items:
            if hasattr(item, "name") and item.name == name:
                return item
        return None

    def get_valid_items(self) -> List[T]:
        return [item for item in self.items if getattr(item, "is_valid", True)]

    def item_count(self) -> int:
        return len(self.items)

    def remove_item_by_index(self, index: int) -> bool:
        if 0 <= index < len(self.items):
            del self.items[index]
            self.updated_at = datetime.now(UTC)
            return True
        return False

    def get_item_names(self) -> List[str]:
        return [item.name for item in self.items if hasattr(item, "name") and item.name]

    def valid_item_count(self) -> int:
        return len(self.get_valid_items())

    def enabled_item_count(self) -> int:
        return len([item for item in self.items if getattr(item, "enabled", True)])

    def has_item_with_name(self, name: str) -> bool:
        return self.get_item_by_name(name) is not None

    def filter_items(self, predicate: Callable[[T], bool]) -> List[T]:
        return [item for item in self.items if predicate(item)]

    def get_enabled_items(self) -> List[T]:
        return [item for item in self.items if getattr(item, "enabled", True)]

    def sort_by_name(self) -> None:
        self.items.sort(key=lambda item: getattr(item, "name", ""))
        self.updated_at = datetime.now(UTC)

    def get_summary(self) -> dict:
        return {
            "collection_name": self.collection_name,
            "total_items": self.item_count(),
            "valid_items": self.valid_item_count(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "has_items": self.item_count() > 0,
        }


# Example 1: ModelExample (simplified version)
class ModelExample(BaseModel):
    """Simplified example model."""

    example_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str | None = None
    is_valid: bool = True
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# BEFORE: Original ModelExamples implementation
class ModelExamplesOriginal(BaseModel):
    """Original implementation with ad-hoc collection operations."""

    examples: list[ModelExample] = Field(default_factory=list)
    format: str = Field(default="json")
    schema_compliant: bool = Field(default=True)

    def add_example(
        self,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Add a new example with manual creation."""
        example = ModelExample(
            name=name or f"Example_{len(self.examples) + 1}",
            description=description,
            tags=tags or [],
            is_valid=True,
            created_at=datetime.now(UTC),
        )
        self.examples.append(example)

    def get_example_by_name(self, name: str) -> ModelExample | None:
        """Get an example by name with manual iteration."""
        for example in self.examples:
            if example.name == name:
                return example
        return None

    def remove_example(self, index: int) -> bool:
        """Remove an example by index with manual bounds checking."""
        if 0 <= index < len(self.examples):
            del self.examples[index]
            return True
        return False

    def get_valid_examples(self) -> list[ModelExample]:
        """Get only valid examples with manual filtering."""
        return [example for example in self.examples if example.is_valid]

    def example_count(self) -> int:
        """Get total number of examples."""
        return len(self.examples)

    def get_example_names(self) -> list[str]:
        """Get all example names with manual iteration."""
        return [example.name for example in self.examples if example.name]


# AFTER: Refactored ModelExamples using generic collection
class ModelExamplesRefactored(ModelGenericCollection[ModelExample]):
    """Refactored implementation using generic collection base."""

    # Additional domain-specific fields
    format: str = Field(default="json")
    schema_compliant: bool = Field(default=True)

    # Inherits from ModelGenericCollection:
    # - items: List[ModelExample]
    # - collection_name: str
    # - created_at: datetime
    # - updated_at: datetime
    # - add_item(item: ModelExample)
    # - get_item_by_name(name: str)
    # - get_valid_items()
    # - item_count()
    # - remove_item_by_index(index: int)
    # - get_item_names()
    # ... and many more methods

    def add_example(
        self,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Add a new example - now delegates to inherited add_item()."""
        example = ModelExample(
            name=name or f"Example_{len(self.items) + 1}",
            description=description,
            tags=tags or [],
            is_valid=True,
            created_at=datetime.now(UTC),
        )
        self.add_item(example)  # Use inherited method

    # Wrapper methods (delegate to inherited methods)
    def get_example_by_name(self, name: str) -> ModelExample | None:
        """Get example by name - delegates to inherited get_item_by_name()."""
        return self.get_item_by_name(name)

    def remove_example(self, index: int) -> bool:
        """Remove example by index - delegates to inherited remove_item_by_index()."""
        return self.remove_item_by_index(index)

    def get_valid_examples(self) -> list[ModelExample]:
        """Get valid examples - delegates to inherited get_valid_items()."""
        return self.get_valid_items()

    def example_count(self) -> int:
        """Get example count - delegates to inherited item_count()."""
        return self.item_count()

    def get_example_names(self) -> list[str]:
        """Get example names - delegates to inherited get_item_names()."""
        return self.get_item_names()

    # New capabilities gained from generic collection
    def get_examples_by_tag(self, tag: str) -> list[ModelExample]:
        """Get examples with a specific tag - uses inherited functionality."""
        return [item for item in self.items if tag in item.tags]

    def sort_examples_by_name(self) -> None:
        """Sort examples by name - uses inherited functionality."""
        self.items.sort(key=lambda x: x.name)
        self.updated_at = datetime.now(UTC)

    def get_recent_examples(self, days: int = 7) -> list[ModelExample]:
        """Get recently created examples - uses inherited filtering."""
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=days)
        return [item for item in self.items if item.created_at >= cutoff]


# Example 2: Tool Collection refactoring
class ModelToolDefinition(BaseModel):
    """Simplified tool definition."""

    name: str
    description: str
    enabled: bool = True


# BEFORE: Original tool collection
class ModelToolCollectionOriginal(BaseModel):
    """Original tool collection with dict-based storage."""

    tools: dict[str, ModelToolDefinition] = Field(default_factory=dict)

    def add_tool(self, name: str, tool_definition: ModelToolDefinition) -> None:
        self.tools[name] = tool_definition

    def get_tool(self, name: str) -> ModelToolDefinition | None:
        return self.tools.get(name)

    def list_tool_names(self) -> list[str]:
        return list(self.tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self.tools

    def get_enabled_tools(self) -> dict[str, ModelToolDefinition]:
        return {name: tool for name, tool in self.tools.items() if tool.enabled}


# AFTER: Refactored tool collection
class ModelToolCollectionRefactored(ModelGenericCollection[ModelToolDefinition]):
    """Refactored tool collection using generic collection base."""

    def add_tool(self, tool_definition: ModelToolDefinition) -> None:
        """Add a tool - delegates to inherited add_item()."""
        self.add_item(tool_definition)

    def get_tool(self, name: str) -> ModelToolDefinition | None:
        """Get a tool by name - uses inherited get_item_by_name()."""
        return self.get_item_by_name(name)

    def list_tool_names(self) -> list[str]:
        """List tool names - uses inherited get_item_names()."""
        return self.get_item_names()

    def has_tool(self, name: str) -> bool:
        """Check if tool exists - uses inherited has_item_with_name()."""
        return self.has_item_with_name(name)

    def get_enabled_tools(self) -> list[ModelToolDefinition]:
        """Get enabled tools - uses inherited get_enabled_items()."""
        return self.get_enabled_items()

    # Bonus: New capabilities from generic collection
    def get_tool_count(self) -> int:
        """Get total tool count."""
        return self.item_count()

    def get_enabled_tool_count(self) -> int:
        """Get enabled tool count."""
        return self.enabled_item_count()

    def sort_tools_by_name(self) -> None:
        """Sort tools alphabetically."""
        self.sort_by_name()

    def find_tools_by_description(self, keyword: str) -> list[ModelToolDefinition]:
        """Find tools containing keyword in description."""
        return self.filter_items(
            lambda tool: keyword.lower() in tool.description.lower()
        )


def demonstrate_refactoring():
    """Demonstrate the benefits of refactoring to generic collection."""

    print("=== ModelExamples Refactoring Demo ===")

    # Original implementation
    original = ModelExamplesOriginal()
    original.add_example("Test Example 1", "First test")
    original.add_example("Test Example 2", "Second test")

    print(f"Original - Example count: {original.example_count()}")
    print(f"Original - Example names: {original.get_example_names()}")

    # Refactored implementation
    refactored = ModelExamplesRefactored(collection_name="Demo Examples")
    refactored.add_example("Test Example 1", "First test")
    refactored.add_example("Test Example 2", "Second test")

    print(f"Refactored - Example count: {refactored.example_count()}")
    print(f"Refactored - Example names: {refactored.get_example_names()}")

    # Show new capabilities from generic collection
    print(f"Refactored - Collection name: {refactored.collection_name}")
    print(f"Refactored - Created at: {refactored.created_at}")
    print(f"Refactored - Valid item count: {refactored.valid_item_count()}")

    # Show inherited filtering capabilities
    summary = refactored.get_summary()
    print(f"Refactored - Summary: {summary}")

    print("\n=== Tool Collection Refactoring Demo ===")

    # Original tool collection
    original_tools = ModelToolCollectionOriginal()
    tool1 = ModelToolDefinition(
        name="hammer", description="Useful for nails", enabled=True
    )
    tool2 = ModelToolDefinition(
        name="screwdriver", description="Useful for screws", enabled=False
    )
    original_tools.add_tool("hammer", tool1)
    original_tools.add_tool("screwdriver", tool2)

    print(f"Original tools - Count: {len(original_tools.tools)}")
    print(f"Original tools - Enabled: {len(original_tools.get_enabled_tools())}")

    # Refactored tool collection
    refactored_tools = ModelToolCollectionRefactored(collection_name="Workshop Tools")
    refactored_tools.add_tool(tool1)
    refactored_tools.add_tool(tool2)

    print(f"Refactored tools - Count: {refactored_tools.get_tool_count()}")
    print(f"Refactored tools - Enabled: {refactored_tools.get_enabled_tool_count()}")
    print(
        f"Refactored tools - Tools with 'screw': {len(refactored_tools.find_tools_by_description('screw'))}"
    )

    # Show new sorting capability
    refactored_tools.sort_tools_by_name()
    print(f"Refactored tools - Sorted names: {refactored_tools.list_tool_names()}")


if __name__ == "__main__":
    demonstrate_refactoring()
