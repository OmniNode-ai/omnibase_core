"""
Generic Models Demo and Test.

Demonstrates the new generic patterns implemented in the omnibase core models
for type-safe collections, containers, and factory patterns.
"""

from datetime import datetime, UTC
from typing import Any, Union
from uuid import uuid4, UUID

from .model_generic_collection import (
    ModelGenericCollection,
    ModelIdentifiableCollection,
    ModelSearchableCollection,
    create_collection,
    create_identifiable_collection,
)
from .model_generic_container import (
    ModelGenericContainer,
    ModelKeyValueContainer,
    ModelCachingContainer,
    create_container,
    create_key_value_container,
    create_caching_container,
)
from .model_schema_value import ModelSchemaValue, ModelSchemaValueFactory, ConvertibleToSchema
from .model_result import Result, collect_results
from omnibase_core.core.core_uuid_service import UUIDService


class DemoUser:
    """Demo user class implementing Identifiable protocol."""

    def __init__(self, name: str, email: str):
        self.user_id = UUIDService.generate_correlation_id()
        self.name = name
        self.email = email
        self.created_at = datetime.now(UTC)

    def get_id(self) -> Union[str, UUID]:
        """Identifiable protocol implementation."""
        return self.user_id

    def matches_criteria(self, criteria: dict[str, Any]) -> bool:
        """SearchableItem protocol implementation."""
        if "name" in criteria:
            return self.name.lower() == criteria["name"].lower()
        if "email" in criteria:
            return self.email.lower() == criteria["email"].lower()
        return False

    def get_search_fields(self) -> dict[str, Any]:
        """SearchableItem protocol implementation."""
        return {
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at
        }

    def to_dict(self) -> dict[str, Any]:
        """Serializable protocol implementation."""
        return {
            "user_id": str(self.user_id),
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat()
        }

    def to_schema_value(self) -> ModelSchemaValue:
        """ConvertibleToSchema protocol implementation."""
        return ModelSchemaValueFactory.from_value(self.to_dict())


def demo_generic_collections() -> None:
    """Demonstrate generic collection patterns."""
    print("=== Generic Collections Demo ===")

    # Create users
    users = [
        DemoUser("Alice Smith", "alice@example.com"),
        DemoUser("Bob Jones", "bob@example.com"),
        DemoUser("Charlie Brown", "charlie@example.com"),
    ]

    # 1. Basic Generic Collection
    basic_collection = create_collection(
        items=users,
        name="User Collection",
        description="Demo collection of users"
    )

    print(f"Basic collection size: {basic_collection.size()}")
    print(f"Collection name: {basic_collection.name}")

    # 2. Identifiable Collection with ID-based operations
    id_collection = create_identifiable_collection(
        items=users,
        name="ID-Based User Collection"
    )

    # Get user by ID
    first_user = users[0]
    found_user = id_collection.get_by_id(first_user.get_id())
    print(f"Found user by ID: {found_user.name if found_user else 'None'}")

    # 3. Collection operations with type safety
    filtered_collection = basic_collection.filter(lambda u: u.name.startswith("A"))
    print(f"Filtered collection (names starting with 'A'): {filtered_collection.size()}")

    # Map operation
    name_collection = basic_collection.map(lambda u: u.name)
    print(f"Mapped to names: {list(name_collection)}")

    # Group by domain
    grouped = basic_collection.group_by(lambda u: u.email.split("@")[1])
    print(f"Grouped by domain: {list(grouped.keys())}")

    print()


def demo_generic_containers() -> None:
    """Demonstrate generic container patterns."""
    print("=== Generic Containers Demo ===")

    # 1. Basic Generic Container
    user_container = create_container(
        content=DemoUser("Container User", "container@example.com"),
        name="User Container",
        description="Container holding a single user"
    )

    print(f"Container has content: {user_container.has_content()}")
    print(f"Container age: {user_container.get_age_seconds():.2f} seconds")

    # 2. Key-Value Container
    kv_container = create_key_value_container(
        data={"setting1": "value1", "setting2": "value2"},
        name="Settings Container",
        max_size=10
    )

    kv_container.set("setting3", "value3")
    print(f"KV container size: {kv_container.size()}")
    print(f"Setting1 value: {kv_container.get('setting1')}")

    # 3. Caching Container with statistics
    cache_container = create_caching_container(
        content="cached_data",
        name="Cache Container",
        auto_refresh=True
    )

    # Simulate cache accesses
    for _ in range(5):
        data = cache_container.get_content_with_cache()

    print(f"Cache hit ratio: {cache_container.get_cache_hit_ratio():.2f}")
    print(f"Cache hits: {cache_container.cache_hit_count}")

    print()


def demo_enhanced_schema_factory() -> None:
    """Demonstrate enhanced schema value factory with generics."""
    print("=== Enhanced Schema Factory Demo ===")

    # 1. Custom type converter registration
    factory: ModelSchemaValueFactory = ModelSchemaValueFactory()

    # Register converter for DemoUser
    def user_converter(user: DemoUser) -> ModelSchemaValue:
        return factory.from_value(user.to_dict())

    factory.register_converter(DemoUser, user_converter)

    # 2. Convert custom type
    user = DemoUser("Schema User", "schema@example.com")
    schema_value = factory.from_value(user)
    print(f"Custom type converted: {type(schema_value)}")

    # 3. Batch operations
    values = [1, "hello", True, [1, 2, 3], {"key": "value"}]
    schema_values = factory.batch_convert(values)
    print(f"Batch converted {len(schema_values)} values")

    # 4. Typed converter
    str_converter = factory.create_typed_converter(str)
    converted_str = str_converter(42)
    print(f"Typed conversion 42 -> str: '{converted_str}' (type: {type(converted_str)})")

    print()


def demo_result_patterns() -> None:
    """Demonstrate Result pattern enhancements."""
    print("=== Result Patterns Demo ===")

    # 1. Basic Result operations
    success_result: Result[str, str] = Result.ok("Operation successful")
    error_result: Result[str, str] = Result.err("Operation failed")

    print(f"Success result: {success_result}")
    print(f"Error result: {error_result}")

    # 2. Result chaining with map
    result = success_result.map(lambda s: s.upper())
    print(f"Mapped result: {result}")

    # 3. Collect multiple results
    results: list[Result[int, str]] = [
        Result.ok(1),
        Result.ok(2),
        Result.ok(3),
    ]

    collected = collect_results(results)
    if collected.is_ok():
        print(f"Collected values: {collected.unwrap()}")

    # 4. Error handling with results
    mixed_results = [
        Result.ok(1),
        Result.err("Failed"),
        Result.ok(3),
    ]

    collected_mixed = collect_results(mixed_results)
    if collected_mixed.is_err():
        print(f"Collected errors: {collected_mixed.error}")

    print()


def demo_type_safety() -> None:
    """Demonstrate type safety benefits."""
    print("=== Type Safety Demo ===")

    # 1. Type-safe collection operations
    users = [
        DemoUser("Type User 1", "type1@example.com"),
        DemoUser("Type User 2", "type2@example.com"),
    ]

    # Collection maintains type safety
    user_collection = ModelGenericCollection[DemoUser](items=users)

    # Filter maintains type - MyPy will understand this returns ModelGenericCollection[DemoUser]
    filtered = user_collection.filter(lambda u: u.name.endswith("1"))
    first_filtered = filtered.get_by_index(0)
    if first_filtered:
        # MyPy knows this is DemoUser, not Any
        print(f"Type-safe access: {first_filtered.name}")

    # 2. Container type safety
    user_container = ModelGenericContainer[DemoUser](content=users[0])
    stored_user = user_container.get_content()
    if stored_user:
        # MyPy knows this is DemoUser
        print(f"Type-safe container access: {stored_user.email}")

    # 3. Result type safety
    def get_user_by_email(email: str) -> Result[DemoUser, str]:
        for user in users:
            if user.email == email:
                return Result.ok(user)
        return Result.err("User not found")

    result = get_user_by_email("type1@example.com")
    if result.is_ok():
        # MyPy knows unwrap() returns DemoUser
        user = result.unwrap()
        print(f"Type-safe result: {user.name}")

    print()


def run_all_demos() -> None:
    """Run all generic pattern demonstrations."""
    print("🚀 Generic Patterns Implementation Demo")
    print("=====================================")
    print()

    demo_generic_collections()
    demo_generic_containers()
    demo_enhanced_schema_factory()
    demo_result_patterns()
    demo_type_safety()

    print("✅ All demos completed successfully!")
    print()
    print("Key Benefits Demonstrated:")
    print("- Type-safe collection operations with proper generics")
    print("- Reusable container patterns for various use cases")
    print("- Enhanced factory patterns with custom type support")
    print("- Proper Result pattern implementation with monadic operations")
    print("- Strong typing that helps catch errors at development time")


if __name__ == "__main__":
    run_all_demos()