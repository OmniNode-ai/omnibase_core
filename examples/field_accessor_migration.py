"""
Examples showing how to migrate from dict-like interfaces to ModelFieldAccessor pattern.

This demonstrates the replacement of custom field access methods across CLI, Config,
and Data domains with the unified ModelFieldAccessor pattern.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

# Import the new field accessor patterns
from src.omnibase_core.models.core import (
    ModelCustomFieldsAccessor,
    ModelEnvironmentAccessor,
    ModelFieldAccessor,
    ModelResultAccessor,
)


# ========== BEFORE: Original ModelCliOutputData ==========
class OriginalModelCliOutputData:
    """Original implementation with custom field access methods."""

    results: dict[str, str | int | bool | float] = Field(default_factory=dict)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    def get_field_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get a field value from results or metadata."""
        if key in self.results:
            return self.results[key]
        if key in self.metadata:
            return self.metadata[key]
        return default

    def set_field_value(self, key: str, value: str | int | bool | float) -> None:
        """Set a field value in results."""
        self.results[key] = value


# ========== AFTER: Migrated with ModelResultAccessor ==========
class MigratedModelCliOutputData(ModelResultAccessor):
    """Migrated implementation using ModelResultAccessor pattern."""

    results: dict[str, str | int | bool | float] = Field(default_factory=dict)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    # The get_field_value and set_field_value methods are now inherited
    # from ModelResultAccessor as get_result_value and set_result_value

    # Additional dot notation access is now available:
    # - get_field("results.some_key")
    # - set_field("metadata.some_key", value)
    # - has_field("results.some_key")
    # - remove_field("results.some_key")


# ========== BEFORE: Original ModelGenericMetadata ==========
class OriginalModelGenericMetadata:
    """Original implementation with custom field access."""

    custom_fields: dict[str, str | int | bool | float] | None = Field(default=None)

    def get_field(self, key: str, default: Any = None) -> Any:
        """Get a custom field value."""
        if self.custom_fields is None:
            return default
        return self.custom_fields.get(key, default)

    def set_field(self, key: str, value: Any) -> None:
        """Set a custom field value."""
        if self.custom_fields is None:
            self.custom_fields = {}
        self.custom_fields[key] = value

    def has_field(self, key: str) -> bool:
        """Check if a custom field exists."""
        if self.custom_fields is None:
            return False
        return key in self.custom_fields

    def remove_field(self, key: str) -> bool:
        """Remove a custom field."""
        if self.custom_fields is None:
            return False
        if key in self.custom_fields:
            del self.custom_fields[key]
            return True
        return False


# ========== AFTER: Migrated with ModelCustomFieldsAccessor ==========
class MigratedModelGenericMetadata(ModelCustomFieldsAccessor):
    """Migrated implementation using ModelCustomFieldsAccessor pattern."""

    custom_fields: dict[str, str | int | bool | float] | None = Field(default=None)

    # The get_field, set_field, has_field, remove_field methods are now inherited
    # from ModelCustomFieldsAccessor as:
    # - get_custom_field(key, default)
    # - set_custom_field(key, value)
    # - has_custom_field(key)
    # - remove_custom_field(key)

    # Additional dot notation access is now available:
    # - get_field("custom_fields.nested.key")
    # - set_field("custom_fields.nested.key", value)


# ========== BEFORE: Original ModelEnvironmentProperties ==========
class OriginalModelEnvironmentProperties:
    """Original implementation with typed getter methods."""

    properties: dict[str, Any] = Field(default_factory=dict)

    def get_string(self, key: str, default: str = "") -> str:
        """Get string property value."""
        value = self.properties.get(key, default)
        return str(value) if value is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer property value."""
        value = self.properties.get(key, default)
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.isdigit()
        ):
            return int(value)
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean property value."""
        value = self.properties.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        if isinstance(value, (int, float)):
            return bool(value)
        return default


# ========== AFTER: Migrated with ModelEnvironmentAccessor ==========
class MigratedModelEnvironmentProperties(ModelEnvironmentAccessor):
    """Migrated implementation using ModelEnvironmentAccessor pattern."""

    properties: dict[str, Any] = Field(default_factory=dict)

    # The typed getter methods are now inherited from ModelEnvironmentAccessor:
    # - get_string(path, default)
    # - get_int(path, default)
    # - get_bool(path, default)
    # - get_float(path, default)
    # - get_list(path, default)

    # Additional dot notation access is now available:
    # - get_field("properties.nested.key")
    # - set_field("properties.nested.key", value)
    # - get_string("properties.database.host", "localhost")


# ========== USAGE EXAMPLES ==========
def demonstrate_migration():
    """Demonstrate the before and after usage patterns."""

    print("=== CLI Output Data Migration ===")

    # Before: Original usage
    original_cli = OriginalModelCliOutputData()
    original_cli.set_field_value("exit_code", 0)
    original_cli.set_field_value("duration_ms", 150.5)
    exit_code = original_cli.get_field_value("exit_code", -1)

    # After: Migrated usage (backward compatible + new features)
    migrated_cli = MigratedModelCliOutputData()
    migrated_cli.set_result_value("exit_code", 0)  # Same functionality
    migrated_cli.set_field("results.duration_ms", 150.5)  # Dot notation
    migrated_cli.set_field("metadata.timestamp", "2024-01-01T12:00:00")

    # New capabilities with dot notation
    exit_code = migrated_cli.get_result_value("exit_code", -1)
    duration = migrated_cli.get_field("results.duration_ms", 0.0)
    timestamp = migrated_cli.get_field("metadata.timestamp")

    print(f"Exit code: {exit_code}, Duration: {duration}ms, Timestamp: {timestamp}")

    print("\n=== Environment Properties Migration ===")

    # Before: Original usage
    original_env = OriginalModelEnvironmentProperties()
    original_env.properties["database_host"] = "localhost"
    original_env.properties["database_port"] = "5432"
    original_env.properties["debug_mode"] = "true"

    host = original_env.get_string("database_host", "unknown")
    port = original_env.get_int("database_port", 3306)
    debug = original_env.get_bool("debug_mode", False)

    # After: Migrated usage (same API + dot notation)
    migrated_env = MigratedModelEnvironmentProperties()
    migrated_env.set_field("properties.database.host", "localhost")
    migrated_env.set_field("properties.database.port", "5432")
    migrated_env.set_field("properties.debug_mode", "true")

    # Same API with dot notation paths
    host = migrated_env.get_string("properties.database.host", "unknown")
    port = migrated_env.get_int("properties.database.port", 3306)
    debug = migrated_env.get_bool("properties.debug_mode", False)

    print(f"Database: {host}:{port}, Debug: {debug}")

    print("\n=== Generic Metadata Migration ===")

    # Before: Original usage
    original_meta = OriginalModelGenericMetadata()
    original_meta.set_field("version", "1.0.0")
    original_meta.set_field("author", "team@company.com")

    version = original_meta.get_field("version", "unknown")
    has_author = original_meta.has_field("author")

    # After: Migrated usage
    migrated_meta = MigratedModelGenericMetadata()
    migrated_meta.set_custom_field("version", "1.0.0")  # Explicit custom field method
    migrated_meta.set_field("custom_fields.author", "team@company.com")  # Dot notation

    version = migrated_meta.get_custom_field("version", "unknown")
    has_author = migrated_meta.has_custom_field("author")

    # New nested capabilities
    migrated_meta.set_field("custom_fields.build.number", 42)
    migrated_meta.set_field("custom_fields.build.timestamp", "2024-01-01T12:00:00")

    build_number = migrated_meta.get_field("custom_fields.build.number", 0)
    build_timestamp = migrated_meta.get_field("custom_fields.build.timestamp")

    print(f"Version: {version}, Has author: {has_author}")
    print(f"Build: #{build_number} at {build_timestamp}")


if __name__ == "__main__":
    demonstrate_migration()
