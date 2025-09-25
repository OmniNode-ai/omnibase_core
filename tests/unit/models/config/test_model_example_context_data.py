"""
Test suite for ModelExampleContextData.

Tests the clean, strongly-typed replacement for dict[str, Any] in example context data.
"""

import pytest
from pydantic import ValidationError

from src.omnibase_core.models.config.model_example_context_data import (
    ModelExampleContextData,
)
from src.omnibase_core.models.metadata.model_semver import ModelSemVer


class TestModelExampleContextData:
    """Test cases for ModelExampleContextData."""

    def test_initialization_empty(self):
        """Test empty initialization with defaults."""
        context = ModelExampleContextData()

        assert context.context_type == "example"
        assert context.environment is None
        assert context.execution_mode == "standard"
        assert context.timeout_seconds is None
        assert context.environment_variables == {}
        assert context.configuration_overrides == {}
        assert context.user_context is None
        assert context.session_id is None
        assert context.tags == []
        assert context.notes is None
        assert context.schema_version is None

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        context = ModelExampleContextData(
            context_type="test",
            environment="staging",
            execution_mode="debug",
            timeout_seconds=60.0,
            environment_variables={"DEBUG": "true"},
            user_context="test_user",
            session_id="sess_123",
            tags=["integration", "test"],
            notes="Test run notes",
        )

        assert context.context_type == "test"
        assert context.environment == "staging"
        assert context.execution_mode == "debug"
        assert context.timeout_seconds == 60.0
        assert context.environment_variables == {"DEBUG": "true"}
        assert context.user_context == "test_user"
        assert context.session_id == "sess_123"
        assert context.tags == ["integration", "test"]
        assert context.notes == "Test run notes"

    def test_environment_variables_management(self):
        """Test environment variables handling."""
        context = ModelExampleContextData()

        # Start with empty
        assert context.environment_variables == {}

        # Add variables via initialization
        context.environment_variables["NODE_ENV"] = "test"
        context.environment_variables["LOG_LEVEL"] = "debug"

        assert context.environment_variables["NODE_ENV"] == "test"
        assert context.environment_variables["LOG_LEVEL"] == "debug"
        assert len(context.environment_variables) == 2

    def test_configuration_overrides_management(self):
        """Test configuration overrides with mixed types."""
        context = ModelExampleContextData()

        # Test different value types
        context.configuration_overrides["max_connections"] = 100
        context.configuration_overrides["debug_enabled"] = True
        context.configuration_overrides["service_name"] = "test-service"

        assert context.configuration_overrides["max_connections"] == 100
        assert context.configuration_overrides["debug_enabled"] is True
        assert context.configuration_overrides["service_name"] == "test-service"

    def test_tags_management(self):
        """Test tags list handling."""
        context = ModelExampleContextData()

        # Start with empty
        assert context.tags == []

        # Add tags
        context.tags.append("unit-test")
        context.tags.extend(["performance", "regression"])

        assert "unit-test" in context.tags
        assert "performance" in context.tags
        assert "regression" in context.tags
        assert len(context.tags) == 3

    def test_schema_version_with_semver(self):
        """Test schema version with ModelSemVer."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        context = ModelExampleContextData(schema_version=version)

        assert context.schema_version == version
        assert context.schema_version.major == 1
        assert context.schema_version.minor == 2
        assert context.schema_version.patch == 3

    def test_timeout_validation_positive(self):
        """Test timeout seconds accepts positive values."""
        context = ModelExampleContextData(timeout_seconds=120.5)
        assert context.timeout_seconds == 120.5

        # Test very small positive value
        context = ModelExampleContextData(timeout_seconds=0.1)
        assert context.timeout_seconds == 0.1

    def test_complex_initialization(self):
        """Test complex initialization with all fields."""
        version = ModelSemVer(major=2, minor=0, patch=0)

        context = ModelExampleContextData(
            context_type="integration",
            environment="production",
            execution_mode="parallel",
            timeout_seconds=300.0,
            environment_variables={
                "DATABASE_URL": "postgresql://localhost:5432/test",
                "REDIS_URL": "redis://localhost:6379",
                "SECRET_KEY": "test_secret",
            },
            configuration_overrides={
                "max_workers": 4,
                "enable_cache": True,
                "cache_ttl": "300",
                "compression_enabled": True,
            },
            user_context="admin_user",
            session_id="session_abc123",
            tags=["production", "high-priority", "batch-job"],
            notes="Production batch job with high priority settings",
            schema_version=version,
        )

        # Verify all fields
        assert context.context_type == "integration"
        assert context.environment == "production"
        assert context.execution_mode == "parallel"
        assert context.timeout_seconds == 300.0
        assert len(context.environment_variables) == 3
        assert (
            context.environment_variables["DATABASE_URL"]
            == "postgresql://localhost:5432/test"
        )
        assert len(context.configuration_overrides) == 4
        assert context.configuration_overrides["max_workers"] == 4
        assert context.configuration_overrides["enable_cache"] is True
        assert context.user_context == "admin_user"
        assert context.session_id == "session_abc123"
        assert len(context.tags) == 3
        assert "production" in context.tags
        assert context.notes == "Production batch job with high priority settings"
        assert context.schema_version == version

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        context = ModelExampleContextData(
            context_type="test",
            environment="dev",
            timeout_seconds=60.0,
            environment_variables={"TEST": "true"},
            tags=["unit", "fast"],
        )

        # Test model_dump
        data = context.model_dump()

        assert data["context_type"] == "test"
        assert data["environment"] == "dev"
        assert data["timeout_seconds"] == 60.0
        assert data["environment_variables"] == {"TEST": "true"}
        assert data["tags"] == ["unit", "fast"]

        # Test excluding None values
        data_exclude_none = context.model_dump(exclude_none=True)

        assert "user_context" not in data_exclude_none
        assert "session_id" not in data_exclude_none
        assert "notes" not in data_exclude_none

    def test_pydantic_deserialization(self):
        """Test Pydantic model deserialization."""
        data = {
            "context_type": "deserialize_test",
            "environment": "testing",
            "execution_mode": "isolated",
            "timeout_seconds": 45.0,
            "environment_variables": {"MODE": "test"},
            "configuration_overrides": {"debug": True, "port": 8080},
            "user_context": "test_user",
            "session_id": "test_session",
            "tags": ["deserialization", "validation"],
            "notes": "Deserialization test case",
        }

        context = ModelExampleContextData.model_validate(data)

        assert context.context_type == "deserialize_test"
        assert context.environment == "testing"
        assert context.execution_mode == "isolated"
        assert context.timeout_seconds == 45.0
        assert context.environment_variables == {"MODE": "test"}
        assert context.configuration_overrides == {"debug": True, "port": 8080}
        assert context.user_context == "test_user"
        assert context.session_id == "test_session"
        assert context.tags == ["deserialization", "validation"]
        assert context.notes == "Deserialization test case"

    def test_model_copy(self):
        """Test model copying functionality."""
        original = ModelExampleContextData(
            context_type="original", environment="prod", tags=["tag1", "tag2"]
        )

        # Test copy with updates
        copy = original.model_copy(
            update={"context_type": "copied", "environment": "staging"}
        )

        assert copy.context_type == "copied"
        assert copy.environment == "staging"
        assert copy.tags == ["tag1", "tag2"]  # Should preserve other fields

        # Original should remain unchanged
        assert original.context_type == "original"
        assert original.environment == "prod"

    def test_model_round_trip(self):
        """Test serialization -> deserialization round trip."""
        original = ModelExampleContextData(
            context_type="round_trip",
            environment="test",
            execution_mode="benchmark",
            timeout_seconds=120.0,
            environment_variables={"ROUND_TRIP": "test"},
            configuration_overrides={"setting": 42, "enabled": True},
            user_context="round_trip_user",
            session_id="rt_session",
            tags=["round-trip", "test"],
            notes="Round trip test",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back to model
        restored = ModelExampleContextData.model_validate(data)

        # Should be equal
        assert restored.context_type == original.context_type
        assert restored.environment == original.environment
        assert restored.execution_mode == original.execution_mode
        assert restored.timeout_seconds == original.timeout_seconds
        assert restored.environment_variables == original.environment_variables
        assert restored.configuration_overrides == original.configuration_overrides
        assert restored.user_context == original.user_context
        assert restored.session_id == original.session_id
        assert restored.tags == original.tags
        assert restored.notes == original.notes

    def test_edge_cases_empty_collections(self):
        """Test edge cases with empty collections."""
        context = ModelExampleContextData(
            environment_variables={}, configuration_overrides={}, tags=[]
        )

        assert context.environment_variables == {}
        assert context.configuration_overrides == {}
        assert context.tags == []

        # Verify serialization handles empty collections
        data = context.model_dump()
        assert data["environment_variables"] == {}
        assert data["configuration_overrides"] == {}
        assert data["tags"] == []

    def test_edge_cases_none_values(self):
        """Test edge cases with None values."""
        context = ModelExampleContextData(
            environment=None,
            timeout_seconds=None,
            user_context=None,
            session_id=None,
            notes=None,
            schema_version=None,
        )

        assert context.environment is None
        assert context.timeout_seconds is None
        assert context.user_context is None
        assert context.session_id is None
        assert context.notes is None
        assert context.schema_version is None

    def test_field_types_validation(self):
        """Test field type validation."""
        # Valid initialization should work
        context = ModelExampleContextData(context_type="test", timeout_seconds=30.0)
        assert context.context_type == "test"
        assert context.timeout_seconds == 30.0

        # Test that configuration_overrides accepts mixed types
        context.configuration_overrides["string_val"] = "test"
        context.configuration_overrides["int_val"] = 42
        context.configuration_overrides["bool_val"] = True

        assert context.configuration_overrides["string_val"] == "test"
        assert context.configuration_overrides["int_val"] == 42
        assert context.configuration_overrides["bool_val"] is True

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        context = ModelExampleContextData(
            context_type="json_test",
            environment="test_env",
            timeout_seconds=60.5,
            environment_variables={"JSON_TEST": "true"},
            tags=["json", "serialization"],
        )

        # Test JSON serialization
        json_str = context.model_dump_json()
        assert isinstance(json_str, str)
        assert '"context_type":"json_test"' in json_str
        assert '"environment":"test_env"' in json_str

        # Test JSON deserialization
        restored = ModelExampleContextData.model_validate_json(json_str)
        assert restored.context_type == "json_test"
        assert restored.environment == "test_env"
        assert restored.timeout_seconds == 60.5

    def test_model_equality(self):
        """Test model equality comparison."""
        context1 = ModelExampleContextData(
            context_type="equal_test", environment="test"
        )

        context2 = ModelExampleContextData(
            context_type="equal_test", environment="test"
        )

        context3 = ModelExampleContextData(
            context_type="different_test", environment="test"
        )

        # Should be equal with same values
        assert context1 == context2

        # Should not be equal with different values
        assert context1 != context3
