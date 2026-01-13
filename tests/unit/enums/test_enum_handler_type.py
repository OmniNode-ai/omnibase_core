"""
Tests for EnumHandlerType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_type import EnumHandlerType


@pytest.mark.unit
class TestEnumHandlerType:
    """Test cases for EnumHandlerType enum."""

    def test_abstract_handler_type_values(self):
        """Test that abstract handler type values are correct."""
        assert EnumHandlerType.EXTENSION == "extension"
        assert EnumHandlerType.SPECIAL == "special"
        assert EnumHandlerType.NAMED == "named"

    def test_concrete_handler_type_values(self):
        """Test that concrete handler type values are correct (v0.3.6+)."""
        assert EnumHandlerType.HTTP == "http"
        assert EnumHandlerType.DATABASE == "database"
        assert EnumHandlerType.KAFKA == "kafka"
        assert EnumHandlerType.FILESYSTEM == "filesystem"
        assert EnumHandlerType.VAULT == "vault"
        assert EnumHandlerType.VECTOR_STORE == "vector_store"
        assert EnumHandlerType.GRAPH_DATABASE == "graph_database"
        assert EnumHandlerType.REDIS == "redis"
        assert EnumHandlerType.EVENT_BUS == "event_bus"

    def test_local_handler_type_value(self):
        """Test that LOCAL handler type value is correct (v0.4.0+)."""
        assert EnumHandlerType.LOCAL == "local"
        assert EnumHandlerType.LOCAL.value == "local"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHandlerType, str)
        assert issubclass(EnumHandlerType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values.

        With StrValueHelper mixin, str(enum_member) returns the value string,
        not the full enum name. This enables cleaner serialization.
        """
        assert str(EnumHandlerType.EXTENSION) == "extension"
        assert str(EnumHandlerType.SPECIAL) == "special"
        assert str(EnumHandlerType.NAMED) == "named"
        assert str(EnumHandlerType.HTTP) == "http"
        assert str(EnumHandlerType.DATABASE) == "database"
        assert str(EnumHandlerType.LOCAL) == "local"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHandlerType)
        # 3 abstract + 9 concrete + 1 development/testing = 13 total
        assert len(values) == 13
        # Abstract types
        assert EnumHandlerType.EXTENSION in values
        assert EnumHandlerType.SPECIAL in values
        assert EnumHandlerType.NAMED in values
        # Concrete types
        assert EnumHandlerType.HTTP in values
        assert EnumHandlerType.DATABASE in values
        assert EnumHandlerType.KAFKA in values
        assert EnumHandlerType.FILESYSTEM in values
        assert EnumHandlerType.VAULT in values
        assert EnumHandlerType.VECTOR_STORE in values
        assert EnumHandlerType.GRAPH_DATABASE in values
        assert EnumHandlerType.REDIS in values
        assert EnumHandlerType.EVENT_BUS in values
        # Development/Testing types
        assert EnumHandlerType.LOCAL in values

    def test_enum_membership(self):
        """Test membership testing."""
        # Abstract types
        assert "extension" in EnumHandlerType
        assert "special" in EnumHandlerType
        assert "named" in EnumHandlerType
        # Concrete types
        assert "http" in EnumHandlerType
        assert "database" in EnumHandlerType
        assert "kafka" in EnumHandlerType
        assert "filesystem" in EnumHandlerType
        assert "vault" in EnumHandlerType
        assert "vector_store" in EnumHandlerType
        assert "graph_database" in EnumHandlerType
        assert "redis" in EnumHandlerType
        assert "event_bus" in EnumHandlerType
        # Development/Testing types
        assert "local" in EnumHandlerType
        # Invalid
        assert "invalid" not in EnumHandlerType

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHandlerType.EXTENSION == "extension"
        assert EnumHandlerType.SPECIAL == "special"
        assert EnumHandlerType.NAMED == "named"
        assert EnumHandlerType.HTTP == "http"
        assert EnumHandlerType.DATABASE == "database"
        assert EnumHandlerType.LOCAL == "local"

    def test_enum_serialization(self):
        """Test enum serialization."""
        # Abstract types
        assert EnumHandlerType.EXTENSION.value == "extension"
        assert EnumHandlerType.SPECIAL.value == "special"
        assert EnumHandlerType.NAMED.value == "named"
        # Concrete types
        assert EnumHandlerType.HTTP.value == "http"
        assert EnumHandlerType.DATABASE.value == "database"
        assert EnumHandlerType.KAFKA.value == "kafka"
        assert EnumHandlerType.FILESYSTEM.value == "filesystem"
        assert EnumHandlerType.VAULT.value == "vault"
        assert EnumHandlerType.VECTOR_STORE.value == "vector_store"
        assert EnumHandlerType.GRAPH_DATABASE.value == "graph_database"
        assert EnumHandlerType.REDIS.value == "redis"
        assert EnumHandlerType.EVENT_BUS.value == "event_bus"
        # Development/Testing types
        assert EnumHandlerType.LOCAL.value == "local"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        # Abstract types
        assert EnumHandlerType("extension") == EnumHandlerType.EXTENSION
        assert EnumHandlerType("special") == EnumHandlerType.SPECIAL
        assert EnumHandlerType("named") == EnumHandlerType.NAMED
        # Concrete types
        assert EnumHandlerType("http") == EnumHandlerType.HTTP
        assert EnumHandlerType("database") == EnumHandlerType.DATABASE
        assert EnumHandlerType("kafka") == EnumHandlerType.KAFKA
        assert EnumHandlerType("filesystem") == EnumHandlerType.FILESYSTEM
        assert EnumHandlerType("vault") == EnumHandlerType.VAULT
        assert EnumHandlerType("vector_store") == EnumHandlerType.VECTOR_STORE
        assert EnumHandlerType("graph_database") == EnumHandlerType.GRAPH_DATABASE
        assert EnumHandlerType("redis") == EnumHandlerType.REDIS
        assert EnumHandlerType("event_bus") == EnumHandlerType.EVENT_BUS
        # Development/Testing types
        assert EnumHandlerType("local") == EnumHandlerType.LOCAL

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerType("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [handler_type.value for handler_type in EnumHandlerType]
        expected_values = [
            # Abstract types
            "extension",
            "special",
            "named",
            # Concrete types
            "http",
            "database",
            "kafka",
            "filesystem",
            "vault",
            "vector_store",
            "graph_database",
            "redis",
            "event_bus",
            # Development/Testing types
            "local",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Handler type classification for the ONEX handler registry"
            in EnumHandlerType.__doc__
        )
        assert "v0.3.6" in EnumHandlerType.__doc__
        assert "v0.4.0" in EnumHandlerType.__doc__
        assert "LOCAL" in EnumHandlerType.__doc__

    def test_handler_type_categories(self):
        """Test that handler types represent different categories."""
        # Abstract types
        assert EnumHandlerType.EXTENSION in EnumHandlerType
        assert EnumHandlerType.SPECIAL in EnumHandlerType
        assert EnumHandlerType.NAMED in EnumHandlerType
        # Concrete handler types for I/O
        assert EnumHandlerType.HTTP in EnumHandlerType
        assert EnumHandlerType.DATABASE in EnumHandlerType
        assert EnumHandlerType.KAFKA in EnumHandlerType
        assert EnumHandlerType.FILESYSTEM in EnumHandlerType
        assert EnumHandlerType.VAULT in EnumHandlerType
        assert EnumHandlerType.VECTOR_STORE in EnumHandlerType
        assert EnumHandlerType.GRAPH_DATABASE in EnumHandlerType
        assert EnumHandlerType.REDIS in EnumHandlerType
        assert EnumHandlerType.EVENT_BUS in EnumHandlerType
        # Development/Testing handler types
        assert EnumHandlerType.LOCAL in EnumHandlerType


@pytest.mark.unit
class TestEnumHandlerTypeConcreteCategories:
    """Test cases for concrete handler type categorization."""

    def test_network_io_handlers(self):
        """Test handlers for network I/O operations."""
        network_handlers = {
            EnumHandlerType.HTTP,
            EnumHandlerType.KAFKA,
            EnumHandlerType.EVENT_BUS,
        }
        for handler in network_handlers:
            assert handler in EnumHandlerType

    def test_database_handlers(self):
        """Test handlers for database operations."""
        db_handlers = {
            EnumHandlerType.DATABASE,
            EnumHandlerType.VECTOR_STORE,
            EnumHandlerType.GRAPH_DATABASE,
            EnumHandlerType.REDIS,
        }
        for handler in db_handlers:
            assert handler in EnumHandlerType

    def test_system_access_handlers(self):
        """Test handlers for system access operations."""
        system_handlers = {
            EnumHandlerType.FILESYSTEM,
            EnumHandlerType.VAULT,
        }
        for handler in system_handlers:
            assert handler in EnumHandlerType

    def test_dev_test_handlers(self):
        """Test handlers for development/testing operations (v0.4.0+)."""
        dev_handlers = {
            EnumHandlerType.LOCAL,
        }
        for handler in dev_handlers:
            assert handler in EnumHandlerType

    def test_local_handler_is_dev_test_only(self):
        """Test that LOCAL handler is marked as dev/test only in docstring."""
        # The LOCAL enum member should have a docstring warning about dev/test only
        assert "dev/test" in EnumHandlerType.LOCAL.__doc__.lower()
        assert "not for production" in EnumHandlerType.LOCAL.__doc__.lower()
