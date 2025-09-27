"""
Test suite for ModelExampleContextData.

Tests the clean, strongly-typed replacement for dict[str, Any] in example context data.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_execution_mode import EnumExecutionMode
from omnibase_core.models.config.model_example_context_data import (
    ModelExampleContextData,
)
from omnibase_core.models.metadata.model_semver import ModelSemVer


class TestModelExampleContextData:
    """Test cases for ModelExampleContextData."""

    def test_initialization_empty(self):
        """Test empty initialization with defaults."""
        context = ModelExampleContextData()

        assert context.context_type == EnumContextType.USER
        assert context.environment == EnumEnvironment.DEVELOPMENT
        assert context.execution_mode == EnumExecutionMode.AUTO
        assert context.timeout_seconds == 30.0
        assert context.environment_variables == {}
        assert context.configuration_overrides == {}
        assert context.user_id is None
        assert context.user_display_name == ""
        assert context.session_id is None
        assert context.tags == []
        assert context.notes == ""
        assert context.schema_version is None

    def test_initialization_with_values(self):
        """Test initialization with specific values."""
        test_user_id = uuid4()
        test_session_id = uuid4()

        context = ModelExampleContextData(
            context_type=EnumContextType.SYSTEM,
            environment=EnumEnvironment.STAGING,
            execution_mode=EnumExecutionMode.MANUAL,
            timeout_seconds=60.0,
            environment_variables={"DEBUG": "true"},
            user_id=test_user_id,
            user_display_name="test_user",
            session_id=test_session_id,
            tags=["integration", "test"],
            notes="Test run notes",
        )

        assert context.context_type == EnumContextType.SYSTEM
        assert context.environment == EnumEnvironment.STAGING
        assert context.execution_mode == EnumExecutionMode.MANUAL
        assert context.timeout_seconds == 60.0
        assert context.environment_variables == {"DEBUG": "true"}
        assert context.user_id == test_user_id
        assert context.user_display_name == "test_user"
        assert context.session_id == test_session_id
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
        """Test configuration overrides with string types."""
        context = ModelExampleContextData()

        # Test string value types (as required by dict[str, str])
        context.configuration_overrides["max_connections"] = "100"
        context.configuration_overrides["debug_enabled"] = "true"
        context.configuration_overrides["service_name"] = "test-service"

        assert context.configuration_overrides["max_connections"] == "100"
        assert context.configuration_overrides["debug_enabled"] == "true"
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
        test_user_id = uuid4()
        test_session_id = uuid4()

        context = ModelExampleContextData(
            context_type=EnumContextType.BATCH,
            environment=EnumEnvironment.PRODUCTION,
            execution_mode=EnumExecutionMode.SCHEDULED,
            timeout_seconds=300.0,
            environment_variables={
                "DATABASE_URL": "postgresql://localhost:5432/test",
                "REDIS_URL": "redis://localhost:6379",
                "SECRET_KEY": "test_secret",
            },
            configuration_overrides={
                "max_workers": "4",
                "enable_cache": "true",
                "cache_ttl": "300",
                "compression_enabled": "true",
            },
            user_id=test_user_id,
            user_display_name="admin_user",
            session_id=test_session_id,
            tags=["production", "high-priority", "batch-job"],
            notes="Production batch job with high priority settings",
            schema_version=version,
        )

        # Verify all fields
        assert context.context_type == EnumContextType.BATCH
        assert context.environment == EnumEnvironment.PRODUCTION
        assert context.execution_mode == EnumExecutionMode.SCHEDULED
        assert context.timeout_seconds == 300.0
        assert len(context.environment_variables) == 3
        assert (
            context.environment_variables["DATABASE_URL"]
            == "postgresql://localhost:5432/test"
        )
        assert len(context.configuration_overrides) == 4
        assert context.configuration_overrides["max_workers"] == "4"
        assert context.configuration_overrides["enable_cache"] == "true"
        assert context.user_id == test_user_id
        assert context.user_display_name == "admin_user"
        assert context.session_id == test_session_id
        assert len(context.tags) == 3
        assert "production" in context.tags
        assert context.notes == "Production batch job with high priority settings"
        assert context.schema_version == version

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""
        context = ModelExampleContextData(
            context_type=EnumContextType.SYSTEM,
            environment=EnumEnvironment.DEVELOPMENT,
            timeout_seconds=60.0,
            environment_variables={"TEST": "true"},
            tags=["unit", "fast"],
        )

        # Test model_dump
        data = context.model_dump()

        assert data["context_type"] == "system"
        assert data["environment"] == "development"
        assert data["timeout_seconds"] == 60.0
        assert data["environment_variables"] == {"TEST": "true"}
        assert data["tags"] == ["unit", "fast"]

        # Test excluding None values
        data_exclude_none = context.model_dump(exclude_none=True)

        assert "user_id" not in data_exclude_none
        assert "session_id" not in data_exclude_none
        # notes defaults to empty string, not None, so it will be included

    def test_pydantic_deserialization(self):
        """Test Pydantic model deserialization."""
        test_user_id = str(uuid4())
        test_session_id = str(uuid4())

        data = {
            "context_type": "api",
            "environment": "testing",
            "execution_mode": "auto",
            "timeout_seconds": 45.0,
            "environment_variables": {"MODE": "test"},
            "configuration_overrides": {"debug": "true", "port": "8080"},
            "user_id": test_user_id,
            "user_display_name": "test_user",
            "session_id": test_session_id,
            "tags": ["deserialization", "validation"],
            "notes": "Deserialization test case",
        }

        context = ModelExampleContextData.model_validate(data)

        assert context.context_type == EnumContextType.API
        assert context.environment == EnumEnvironment.TESTING
        assert context.execution_mode == EnumExecutionMode.AUTO
        assert context.timeout_seconds == 45.0
        assert context.environment_variables == {"MODE": "test"}
        assert context.configuration_overrides == {"debug": "true", "port": "8080"}
        assert str(context.user_id) == test_user_id
        assert context.user_display_name == "test_user"
        assert str(context.session_id) == test_session_id
        assert context.tags == ["deserialization", "validation"]
        assert context.notes == "Deserialization test case"

    def test_model_copy(self):
        """Test model copying functionality."""
        original = ModelExampleContextData(
            context_type=EnumContextType.BATCH,
            environment=EnumEnvironment.PRODUCTION,
            tags=["tag1", "tag2"],
        )

        # Test copy with updates
        copy = original.model_copy(
            update={
                "context_type": EnumContextType.SYSTEM,
                "environment": EnumEnvironment.STAGING,
            }
        )

        assert copy.context_type == EnumContextType.SYSTEM
        assert copy.environment == EnumEnvironment.STAGING
        assert copy.tags == ["tag1", "tag2"]  # Should preserve other fields

        # Original should remain unchanged
        assert original.context_type == EnumContextType.BATCH
        assert original.environment == EnumEnvironment.PRODUCTION

    def test_model_round_trip(self):
        """Test serialization -> deserialization round trip."""
        test_user_id = uuid4()
        test_session_id = uuid4()

        original = ModelExampleContextData(
            context_type=EnumContextType.INTERACTIVE,
            environment=EnumEnvironment.TESTING,
            execution_mode=EnumExecutionMode.MANUAL,
            timeout_seconds=120.0,
            environment_variables={"ROUND_TRIP": "test"},
            configuration_overrides={"setting": "42", "enabled": "true"},
            user_id=test_user_id,
            user_display_name="round_trip_user",
            session_id=test_session_id,
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
        assert restored.user_id == original.user_id
        assert restored.user_display_name == original.user_display_name
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
        """Test edge cases with None values for optional fields."""
        context = ModelExampleContextData(
            user_id=None,
            session_id=None,
            schema_version=None,
        )

        # These fields can be None
        assert context.user_id is None
        assert context.session_id is None
        assert context.schema_version is None

        # These fields have defaults and cannot be None
        assert context.environment == EnumEnvironment.DEVELOPMENT
        assert context.timeout_seconds == 30.0
        assert context.user_display_name == ""
        assert context.notes == ""

    def test_field_types_validation(self):
        """Test field type validation."""
        # Valid initialization should work
        context = ModelExampleContextData(
            context_type=EnumContextType.API, timeout_seconds=30.0
        )
        assert context.context_type == EnumContextType.API
        assert context.timeout_seconds == 30.0

        # Test that configuration_overrides accepts string types
        context.configuration_overrides["string_val"] = "test"
        context.configuration_overrides["int_val"] = "42"
        context.configuration_overrides["bool_val"] = "true"

        assert context.configuration_overrides["string_val"] == "test"
        assert context.configuration_overrides["int_val"] == "42"
        assert context.configuration_overrides["bool_val"] == "true"

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        context = ModelExampleContextData(
            context_type=EnumContextType.BATCH,
            environment=EnumEnvironment.INTEGRATION,
            timeout_seconds=60.5,
            environment_variables={"JSON_TEST": "true"},
            tags=["json", "serialization"],
        )

        # Test JSON serialization
        json_str = context.model_dump_json()
        assert isinstance(json_str, str)
        assert '"context_type":"batch"' in json_str
        assert '"environment":"integration"' in json_str

        # Test JSON deserialization
        restored = ModelExampleContextData.model_validate_json(json_str)
        assert restored.context_type == EnumContextType.BATCH
        assert restored.environment == EnumEnvironment.INTEGRATION
        assert restored.timeout_seconds == 60.5

    def test_model_equality(self):
        """Test model equality comparison."""
        context1 = ModelExampleContextData(
            context_type=EnumContextType.USER, environment=EnumEnvironment.TESTING
        )

        context2 = ModelExampleContextData(
            context_type=EnumContextType.USER, environment=EnumEnvironment.TESTING
        )

        context3 = ModelExampleContextData(
            context_type=EnumContextType.SYSTEM, environment=EnumEnvironment.TESTING
        )

        # Should be equal with same values
        assert context1 == context2

        # Should not be equal with different values
        assert context1 != context3
