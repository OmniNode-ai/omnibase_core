"""
Unit tests for typed metadata validation - Error path tests.

This module tests that dict[str, Any] metadata is properly rejected
and that helpful error messages are provided for migration guidance.

Test Categories:
1. ModelEffectMetadata validation (extra="forbid")
2. ModelReducerMetadata validation (extra="allow")
3. ModelActionMetadata validation
4. Error messages include migration guidance
5. Edge cases: empty dicts, nested dicts, partial conversions
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.effect.model_effect_metadata import ModelEffectMetadata

# =============================================================================
# ModelEffectMetadata Validation Tests (extra="forbid")
# =============================================================================


@pytest.mark.unit
class TestModelEffectMetadataValidation:
    """Test that ModelEffectMetadata rejects extra fields (extra='forbid')."""

    def test_rejects_extra_field_single(self) -> None:
        """Test that single extra field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            # Pydantic rejects extra fields at runtime (not caught by mypy)
            ModelEffectMetadata(
                trace_id="abc123",
                correlation_id="corr-456",
                invalid_field="should_fail",  # pyright: ignore[reportArgumentType]
            )

        error_str = str(exc_info.value)
        assert "extra" in error_str.lower() or "unexpected" in error_str.lower()
        assert "invalid_field" in error_str

    def test_rejects_extra_fields_multiple(self) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            # Pydantic rejects extra fields at runtime (not caught by mypy)
            ModelEffectMetadata(
                trace_id="abc123",
                extra_field_1="value1",  # pyright: ignore[reportArgumentType]
                extra_field_2="value2",  # pyright: ignore[reportArgumentType]
                extra_field_3="value3",  # pyright: ignore[reportArgumentType]
            )

        error_str = str(exc_info.value)
        # At least one of the extra fields should be mentioned
        assert any(
            field in error_str
            for field in ["extra_field_1", "extra_field_2", "extra_field_3"]
        )

    def test_accepts_all_valid_fields(self) -> None:
        """Test that all valid fields are accepted."""
        metadata = ModelEffectMetadata(
            source="test_service",
            trace_id="trace-123",
            span_id="span-456",
            correlation_id="corr-789",
            environment="production",
            tags=["tag1", "tag2"],
            priority="HIGH",
            retry_count=3,
        )

        assert metadata.source == "test_service"
        assert metadata.trace_id == "trace-123"
        assert metadata.span_id == "span-456"
        assert metadata.correlation_id == "corr-789"
        assert metadata.environment == "production"
        assert metadata.tags == ["tag1", "tag2"]
        assert metadata.priority == "HIGH"
        assert metadata.retry_count == 3

    def test_rejects_dict_unpacking_with_extra_keys(self) -> None:
        """Test that dict unpacking with extra keys is rejected."""
        dict_metadata = {
            "trace_id": "abc123",
            "correlation_id": "corr-456",
            "unknown_key": "unknown_value",
        }

        with pytest.raises(ValidationError) as exc_info:
            ModelEffectMetadata(**dict_metadata)

        error_str = str(exc_info.value)
        assert "unknown_key" in error_str


# =============================================================================
# ModelReducerMetadata Validation Tests (extra="allow")
# =============================================================================


@pytest.mark.unit
class TestModelReducerMetadataValidation:
    """Test that ModelReducerMetadata allows extra fields (extra='allow')."""

    def test_accepts_extra_field_single(self) -> None:
        """Test that single extra field is allowed (intentional design)."""
        metadata = ModelReducerMetadata(
            trace_id="abc123",
            correlation_id="corr-456",
            custom_user_id="user-789",  # Extra field allowed
        )

        assert metadata.trace_id == "abc123"
        assert metadata.correlation_id == "corr-456"
        # Access extra field via __dict__ or __pydantic_extra__
        assert (
            hasattr(metadata, "__pydantic_extra__")
            or "custom_user_id" in metadata.__dict__
        )

    def test_accepts_extra_fields_multiple(self) -> None:
        """Test that multiple extra fields are allowed (intentional design)."""
        metadata = ModelReducerMetadata(
            trace_id="abc123",
            user_id="user-123",  # Extra field
            request_id="req-456",  # Extra field
            session_id="sess-789",  # Extra field
        )

        assert metadata.trace_id == "abc123"
        # Verify at least one extra field is preserved
        assert (
            hasattr(metadata, "__pydantic_extra__")
            and len(metadata.__pydantic_extra__) >= 3
        )

    def test_accepts_all_typed_fields(self) -> None:
        """Test that all typed fields are accepted."""
        metadata = ModelReducerMetadata(
            source="test_reducer",
            trace_id="trace-123",
            span_id="span-456",
            correlation_id="corr-789",
            group_key="group-abc",
            tags=["reducer", "fsm"],
            trigger="EVENT_TRANSITION",
        )

        assert metadata.source == "test_reducer"
        assert metadata.trace_id == "trace-123"
        assert metadata.span_id == "span-456"
        assert metadata.correlation_id == "corr-789"
        assert metadata.group_key == "group-abc"
        assert metadata.tags == ["reducer", "fsm"]
        assert metadata.trigger == "EVENT_TRANSITION"

    def test_dict_unpacking_with_extra_keys_succeeds(self) -> None:
        """Test that dict unpacking with extra keys succeeds (extra='allow')."""
        dict_metadata = {
            "trace_id": "abc123",
            "correlation_id": "corr-456",
            "custom_context": "custom_value",  # Extra field allowed
        }

        metadata = ModelReducerMetadata(**dict_metadata)

        assert metadata.trace_id == "abc123"
        assert metadata.correlation_id == "corr-456"
        # Extra field should be preserved
        assert hasattr(metadata, "__pydantic_extra__")


# =============================================================================
# ModelActionMetadata Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionMetadataValidation:
    """Test ModelActionMetadata validation behavior."""

    @staticmethod
    def create_test_action_type() -> ModelNodeActionType:
        """Helper to create test action type."""
        category = ModelActionCategory(
            name="compute", display_name="Compute", description="Computation actions"
        )
        return ModelNodeActionType(
            name="test_action",
            category=category,
            display_name="Test Action",
            description="Test action for unit tests",
        )

    def test_accepts_all_valid_fields(self) -> None:
        """Test that all valid fields are accepted."""
        action_type = self.create_test_action_type()
        metadata = ModelActionMetadata(
            action_type=action_type,
            action_name="Test Action",
            trust_score=0.8,
            timeout_seconds=60,
            tool_discovery_tags=["tag1", "tag2"],
        )

        assert metadata.action_type == action_type
        assert metadata.action_name == "Test Action"
        assert metadata.trust_score == 0.8
        assert metadata.timeout_seconds == 60
        assert metadata.tool_discovery_tags == ["tag1", "tag2"]

    def test_minimal_construction_succeeds(self) -> None:
        """Test that minimal construction (no args) succeeds."""
        # ModelActionMetadata now supports no-arg construction
        metadata = ModelActionMetadata()

        assert metadata.action_name == ""
        assert metadata.action_type is None
        assert metadata.trust_score == 1.0
        assert metadata.status == "created"

    def test_dict_unpacking_with_valid_keys_succeeds(self) -> None:
        """Test that dict unpacking with valid keys succeeds."""
        action_type = self.create_test_action_type()
        dict_metadata = {
            "action_type": action_type,
            "action_name": "Test Action",
            "trust_score": 0.9,
        }

        metadata = ModelActionMetadata(**dict_metadata)

        assert metadata.action_type == action_type
        assert metadata.action_name == "Test Action"
        assert metadata.trust_score == 0.9


# =============================================================================
# Error Message Quality Tests
# =============================================================================


@pytest.mark.unit
class TestMetadataErrorMessages:
    """Test that validation errors provide helpful migration guidance."""

    def test_effect_metadata_error_message_quality(self) -> None:
        """Test that ModelEffectMetadata errors are informative."""
        with pytest.raises(ValidationError) as exc_info:
            # Pydantic rejects extra fields at runtime (not caught by mypy)
            ModelEffectMetadata(
                trace_id="abc123",
                invalid_field="should_fail",  # pyright: ignore[reportArgumentType]
            )

        error_str = str(exc_info.value)
        # Error should mention the field name
        assert "invalid_field" in error_str
        # Error should indicate it's not allowed (Pydantic 2.x behavior)
        assert "extra" in error_str.lower() or "unexpected" in error_str.lower()

    def test_reducer_metadata_accepts_extra_without_error(self) -> None:
        """Test that ModelReducerMetadata doesn't error on extra fields."""
        # This should NOT raise an error
        metadata = ModelReducerMetadata(
            trace_id="abc123",
            custom_field="custom_value",  # Should be allowed
        )

        assert metadata.trace_id == "abc123"


# =============================================================================
# Edge Case Tests
# =============================================================================


@pytest.mark.unit
class TestMetadataEdgeCases:
    """Test edge cases: empty dicts, nested dicts, partial conversions."""

    def test_effect_metadata_empty_dict_succeeds(self) -> None:
        """Test that empty dict creates valid metadata with defaults."""
        metadata = ModelEffectMetadata()

        assert metadata.source is None
        assert metadata.trace_id is None
        assert metadata.tags == []
        assert metadata.retry_count is None

    def test_reducer_metadata_empty_dict_succeeds(self) -> None:
        """Test that empty dict creates valid metadata with defaults."""
        metadata = ModelReducerMetadata()

        assert metadata.source is None
        assert metadata.trace_id is None
        assert metadata.tags == []
        assert metadata.trigger is None

    def test_effect_metadata_partial_dict_succeeds(self) -> None:
        """Test that partial dict (subset of fields) succeeds."""
        metadata = ModelEffectMetadata(
            trace_id="trace-123",
            # Other fields use defaults
        )

        assert metadata.trace_id == "trace-123"
        assert metadata.source is None
        assert metadata.correlation_id is None
        assert metadata.tags == []

    def test_reducer_metadata_partial_dict_succeeds(self) -> None:
        """Test that partial dict (subset of fields) succeeds."""
        metadata = ModelReducerMetadata(
            trigger="EVENT_TRIGGERED",
            # Other fields use defaults
        )

        assert metadata.trigger == "EVENT_TRIGGERED"
        assert metadata.source is None
        assert metadata.trace_id is None
        assert metadata.tags == []

    def test_effect_metadata_rejects_nested_dict_as_extra(self) -> None:
        """Test that nested dict as extra field is rejected."""
        with pytest.raises(ValidationError):
            # Pydantic rejects extra fields at runtime (not caught by mypy)
            ModelEffectMetadata(
                trace_id="abc123",
                nested_data={"key": "value"},  # pyright: ignore[reportArgumentType]
            )

    def test_reducer_metadata_accepts_nested_dict_as_extra(self) -> None:
        """Test that nested dict as extra field is allowed (extra='allow')."""
        metadata = ModelReducerMetadata(
            trace_id="abc123",
            nested_context={"key": "value"},  # Should be allowed
        )

        assert metadata.trace_id == "abc123"
        assert hasattr(metadata, "__pydantic_extra__")

    def test_effect_metadata_list_tags_field_works(self) -> None:
        """Test that list[str] field (tags) works correctly."""
        metadata = ModelEffectMetadata(
            tags=["tag1", "tag2", "tag3"],
        )

        assert metadata.tags == ["tag1", "tag2", "tag3"]
        assert isinstance(metadata.tags, list)

    def test_reducer_metadata_list_tags_field_works(self) -> None:
        """Test that list[str] field (tags) works correctly."""
        metadata = ModelReducerMetadata(
            tags=["reducer", "fsm", "state-machine"],
        )

        assert metadata.tags == ["reducer", "fsm", "state-machine"]
        assert isinstance(metadata.tags, list)


# =============================================================================
# Default Factory Tests (Performance Verification)
# =============================================================================


@pytest.mark.unit
class TestMetadataDefaultFactoryPerformance:
    """Test that default_factory usage is correct and performant."""

    def test_effect_metadata_tags_default_factory_creates_new_list(self) -> None:
        """Test that each instance gets its own tags list (not shared)."""
        metadata1 = ModelEffectMetadata()
        metadata2 = ModelEffectMetadata()

        # Each should have its own list instance
        assert metadata1.tags is not metadata2.tags

        # Modifying one should not affect the other
        metadata1.tags.append("tag1")
        assert len(metadata1.tags) == 1
        assert len(metadata2.tags) == 0

    def test_reducer_metadata_tags_default_factory_creates_new_list(self) -> None:
        """Test that each instance gets its own tags list (not shared)."""
        metadata1 = ModelReducerMetadata()
        metadata2 = ModelReducerMetadata()

        # Each should have its own list instance
        assert metadata1.tags is not metadata2.tags

        # Modifying one should not affect the other
        metadata1.tags.append("tag1")
        assert len(metadata1.tags) == 1
        assert len(metadata2.tags) == 0

    def test_effect_metadata_default_factory_not_called_on_field_definition(
        self,
    ) -> None:
        """Test that default_factory is called per instance, not at class definition time.

        This is a performance verification - default_factory should create objects
        lazily (when the instance is created), not eagerly (when the class is defined).
        """
        # Create multiple instances
        instances = [ModelEffectMetadata() for _ in range(10)]

        # Each should have a unique tags list
        tag_ids = {id(inst.tags) for inst in instances}
        assert len(tag_ids) == 10  # All unique IDs

    def test_reducer_metadata_default_factory_not_called_on_field_definition(
        self,
    ) -> None:
        """Test that default_factory is called per instance, not at class definition time."""
        # Create multiple instances
        instances = [ModelReducerMetadata() for _ in range(10)]

        # Each should have a unique tags list
        tag_ids = {id(inst.tags) for inst in instances}
        assert len(tag_ids) == 10  # All unique IDs


# =============================================================================
# Configuration Documentation Tests
# =============================================================================


@pytest.mark.unit
class TestMetadataConfigurationDocumentation:
    """Test that configuration decisions are documented in code."""

    def test_effect_metadata_has_forbid_config(self) -> None:
        """Test that ModelEffectMetadata has extra='forbid' configured."""
        # Check model_config directly
        config = ModelEffectMetadata.model_config
        assert config.get("extra") == "forbid"

    def test_reducer_metadata_has_allow_config(self) -> None:
        """Test that ModelReducerMetadata has extra='allow' configured."""
        # Check model_config directly
        config = ModelReducerMetadata.model_config
        assert config.get("extra") == "allow"

    def test_reducer_metadata_has_from_attributes_config(self) -> None:
        """Test that ModelReducerMetadata has from_attributes=True for parallel tests."""
        config = ModelReducerMetadata.model_config
        assert config.get("from_attributes") is True

    def test_effect_metadata_has_from_attributes_config(self) -> None:
        """Test that ModelEffectMetadata has from_attributes=True for parallel tests."""
        config = ModelEffectMetadata.model_config
        assert config.get("from_attributes") is True
