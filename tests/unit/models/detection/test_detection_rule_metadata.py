"""Comprehensive tests for ModelDetectionRuleMetadata.

Tests cover:
- Basic instantiation with valid data
- Default values
- Immutability (frozen=True)
- from_attributes=True (creation from object with attributes)
- Integration with ModelDetectionMatch
"""

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod
from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_sensitivity_level import EnumSensitivityLevel
from omnibase_core.models.detection.model_detection_rule_metadata import (
    ModelDetectionRuleMetadata,
)
from omnibase_core.models.security.model_detection_match import ModelDetectionMatch


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataBasicInstantiation:
    """Test basic instantiation of ModelDetectionRuleMetadata."""

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating metadata with all fields populated."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="RULE-001",
            rule_name="Credit Card Detection",
            category="PCI",
            source="security_scanner",
            tags=["financial", "sensitive"],
            extra={"version": "1.0", "author": "security_team"},
        )

        assert metadata.rule_id == "RULE-001"
        assert metadata.rule_name == "Credit Card Detection"
        assert metadata.category == "PCI"
        assert metadata.source == "security_scanner"
        assert metadata.tags == ["financial", "sensitive"]
        assert metadata.extra == {"version": "1.0", "author": "security_team"}

    def test_instantiation_minimal(self) -> None:
        """Test creating metadata with no fields (all defaults)."""
        metadata = ModelDetectionRuleMetadata()

        assert metadata.rule_id is None
        assert metadata.rule_name is None
        assert metadata.category is None
        assert metadata.source is None
        assert metadata.tags == []
        assert metadata.extra == {}

    def test_instantiation_partial_fields(self) -> None:
        """Test creating metadata with some fields populated."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="RULE-002",
            rule_name="SSN Detection",
        )

        assert metadata.rule_id == "RULE-002"
        assert metadata.rule_name == "SSN Detection"
        assert metadata.category is None
        assert metadata.source is None
        assert metadata.tags == []
        assert metadata.extra == {}


# =============================================================================
# Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataDefaultValues:
    """Test default values of ModelDetectionRuleMetadata."""

    def test_tags_default_is_empty_list(self) -> None:
        """Test that tags defaults to empty list."""
        metadata = ModelDetectionRuleMetadata()
        assert metadata.tags == []
        assert isinstance(metadata.tags, list)

    def test_extra_default_is_empty_dict(self) -> None:
        """Test that extra defaults to empty dict."""
        metadata = ModelDetectionRuleMetadata()
        assert metadata.extra == {}
        assert isinstance(metadata.extra, dict)

    def test_optional_fields_default_to_none(self) -> None:
        """Test all optional fields default to None."""
        metadata = ModelDetectionRuleMetadata()
        assert metadata.rule_id is None
        assert metadata.rule_name is None
        assert metadata.category is None
        assert metadata.source is None

    def test_default_factory_creates_new_instances(self) -> None:
        """Test that default_factory creates new instances for each model."""
        metadata1 = ModelDetectionRuleMetadata()
        metadata2 = ModelDetectionRuleMetadata()

        # The lists and dicts should be different instances
        assert metadata1.tags is not metadata2.tags
        assert metadata1.extra is not metadata2.extra


# =============================================================================
# Immutability Tests (frozen=True)
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataImmutability:
    """Test immutability of ModelDetectionRuleMetadata (frozen=True)."""

    def test_cannot_modify_rule_id(self) -> None:
        """Test that rule_id field cannot be modified after creation."""
        metadata = ModelDetectionRuleMetadata(rule_id="RULE-001")
        with pytest.raises(ValidationError):
            metadata.rule_id = "RULE-002"  # type: ignore[misc]

    def test_cannot_modify_rule_name(self) -> None:
        """Test that rule_name field cannot be modified after creation."""
        metadata = ModelDetectionRuleMetadata(rule_name="Original Name")
        with pytest.raises(ValidationError):
            metadata.rule_name = "Modified Name"  # type: ignore[misc]

    def test_cannot_modify_category(self) -> None:
        """Test that category field cannot be modified after creation."""
        metadata = ModelDetectionRuleMetadata(category="PCI")
        with pytest.raises(ValidationError):
            metadata.category = "HIPAA"  # type: ignore[misc]

    def test_cannot_modify_source(self) -> None:
        """Test that source field cannot be modified after creation."""
        metadata = ModelDetectionRuleMetadata(source="scanner_v1")
        with pytest.raises(ValidationError):
            metadata.source = "scanner_v2"  # type: ignore[misc]

    def test_cannot_modify_tags(self) -> None:
        """Test that tags field cannot be reassigned after creation."""
        metadata = ModelDetectionRuleMetadata(tags=["tag1"])
        with pytest.raises(ValidationError):
            metadata.tags = ["tag2"]  # type: ignore[misc]

    def test_cannot_modify_extra(self) -> None:
        """Test that extra field cannot be reassigned after creation."""
        metadata = ModelDetectionRuleMetadata(extra={"key": "value"})
        with pytest.raises(ValidationError):
            metadata.extra = {"new_key": "new_value"}  # type: ignore[misc]


# =============================================================================
# from_attributes=True Tests
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataFromAttributes:
    """Test from_attributes=True functionality."""

    def test_create_from_dataclass_with_all_fields(self) -> None:
        """Test creating model from a dataclass with all fields."""

        @dataclass
        class MockRuleMetadataSource:
            rule_id: str = "DC-RULE-001"
            rule_name: str = "Dataclass Rule"
            category: str = "TEST"
            source: str = "dataclass_source"
            tags: list[str] | None = None
            extra: dict[str, str] | None = None

            def __post_init__(self) -> None:
                if self.tags is None:
                    self.tags = ["dc_tag"]
                if self.extra is None:
                    self.extra = {"dc_key": "dc_value"}

        source_obj = MockRuleMetadataSource()
        metadata = ModelDetectionRuleMetadata.model_validate(source_obj)

        assert metadata.rule_id == "DC-RULE-001"
        assert metadata.rule_name == "Dataclass Rule"
        assert metadata.category == "TEST"
        assert metadata.source == "dataclass_source"
        assert metadata.tags == ["dc_tag"]
        assert metadata.extra == {"dc_key": "dc_value"}

    def test_create_from_object_with_attributes(self) -> None:
        """Test creating model from a plain object with attributes."""

        class MockObject:
            def __init__(self) -> None:
                self.rule_id = "OBJ-RULE-001"
                self.rule_name = "Object Rule"
                self.category = "OBJ_CATEGORY"
                self.source = "obj_source"
                self.tags = ["obj_tag"]
                self.extra = {"obj_key": "obj_value"}

        source_obj = MockObject()
        metadata = ModelDetectionRuleMetadata.model_validate(source_obj)

        assert metadata.rule_id == "OBJ-RULE-001"
        assert metadata.rule_name == "Object Rule"
        assert metadata.category == "OBJ_CATEGORY"
        assert metadata.source == "obj_source"
        assert metadata.tags == ["obj_tag"]
        assert metadata.extra == {"obj_key": "obj_value"}

    def test_create_from_object_with_partial_attributes(self) -> None:
        """Test creating model from object with only some attributes."""

        class PartialMockObject:
            def __init__(self) -> None:
                self.rule_id = "PARTIAL-RULE-001"
                self.rule_name = None
                self.category = None
                self.source = None
                self.tags = []
                self.extra = {}

        source_obj = PartialMockObject()
        metadata = ModelDetectionRuleMetadata.model_validate(source_obj)

        assert metadata.rule_id == "PARTIAL-RULE-001"
        assert metadata.rule_name is None
        assert metadata.category is None
        assert metadata.tags == []


# =============================================================================
# Integration with ModelDetectionMatch Tests
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataIntegration:
    """Test integration with ModelDetectionMatch parent model."""

    def test_detection_match_with_metadata(self) -> None:
        """Test ModelDetectionMatch can contain ModelDetectionRuleMetadata."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="MATCH-RULE-001",
            rule_name="Credit Card Pattern",
            category="PCI",
            tags=["financial"],
        )

        detection_match = ModelDetectionMatch(
            start_position=10,
            end_position=25,
            matched_text="4111-1111-1111-1111",
            confidence_score=0.95,
            detection_type=EnumDetectionType.FINANCIAL,
            sensitivity_level=EnumSensitivityLevel.HIGH,
            detection_method=EnumDetectionMethod.REGEX,
            metadata=metadata,
        )

        assert detection_match.metadata is not None
        assert detection_match.metadata.rule_id == "MATCH-RULE-001"
        assert detection_match.metadata.rule_name == "Credit Card Pattern"
        assert detection_match.metadata.category == "PCI"
        assert detection_match.metadata.tags == ["financial"]

    def test_detection_match_without_metadata(self) -> None:
        """Test ModelDetectionMatch with no metadata (None)."""
        detection_match = ModelDetectionMatch(
            start_position=0,
            end_position=10,
            matched_text="secret-key",
            confidence_score=0.85,
            detection_type=EnumDetectionType.SECRET,
            sensitivity_level=EnumSensitivityLevel.CRITICAL,
            detection_method=EnumDetectionMethod.ENTROPY_ANALYSIS,
        )

        assert detection_match.metadata is None

    def test_detection_match_serialization_with_metadata(self) -> None:
        """Test serialization of ModelDetectionMatch with metadata."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="SERIAL-RULE-001",
            rule_name="Serialization Test Rule",
            tags=["serialize"],
            extra={"format": "json"},
        )

        detection_match = ModelDetectionMatch(
            start_position=50,
            end_position=70,
            matched_text="SSN-123-45-6789",
            confidence_score=0.99,
            detection_type=EnumDetectionType.PII,
            sensitivity_level=EnumSensitivityLevel.HIGH,
            detection_method=EnumDetectionMethod.DICTIONARY_MATCH,
            metadata=metadata,
        )

        # Serialize to dict
        data_dict = detection_match.model_dump()

        assert data_dict["metadata"]["rule_id"] == "SERIAL-RULE-001"
        assert data_dict["metadata"]["rule_name"] == "Serialization Test Rule"
        assert data_dict["metadata"]["tags"] == ["serialize"]
        assert data_dict["metadata"]["extra"] == {"format": "json"}
        assert data_dict["start_position"] == 50
        assert data_dict["end_position"] == 70


# =============================================================================
# Validation Tests (extra="forbid")
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataValidation:
    """Test validation behavior of ModelDetectionRuleMetadata."""

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDetectionRuleMetadata(
                rule_id="RULE-001",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value)
        assert "unknown_field" in error_str or "Extra inputs" in error_str


# =============================================================================
# Edge Cases and Special Scenarios
# =============================================================================


@pytest.mark.unit
class TestModelDetectionRuleMetadataEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string_values(self) -> None:
        """Test that empty strings are valid for optional string fields."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="",
            rule_name="",
            category="",
            source="",
        )

        assert metadata.rule_id == ""
        assert metadata.rule_name == ""
        assert metadata.category == ""
        assert metadata.source == ""

    def test_unicode_values(self) -> None:
        """Test that unicode values are handled correctly."""
        metadata = ModelDetectionRuleMetadata(
            rule_id="RULE-unicode",
            rule_name="Rule Name: unicode-test",
            category="Category-unicode",
            tags=["tag-unicode"],
            extra={"key-unicode": "value-unicode"},
        )

        assert "unicode" in metadata.rule_name  # type: ignore[operator]
        assert "unicode" in metadata.tags[0]
        assert "unicode" in metadata.extra["key-unicode"]

    def test_large_tags_list(self) -> None:
        """Test handling of large tags list."""
        large_tags = [f"tag_{i}" for i in range(100)]
        metadata = ModelDetectionRuleMetadata(tags=large_tags)

        assert len(metadata.tags) == 100
        assert metadata.tags[0] == "tag_0"
        assert metadata.tags[99] == "tag_99"

    def test_large_extra_dict(self) -> None:
        """Test handling of large extra dict."""
        large_extra = {f"key_{i}": f"value_{i}" for i in range(100)}
        metadata = ModelDetectionRuleMetadata(extra=large_extra)

        assert len(metadata.extra) == 100
        assert metadata.extra["key_0"] == "value_0"
        assert metadata.extra["key_99"] == "value_99"

    def test_model_dump_roundtrip(self) -> None:
        """Test that model_dump and model_validate roundtrip works."""
        original = ModelDetectionRuleMetadata(
            rule_id="ROUNDTRIP-RULE",
            rule_name="Roundtrip Test Rule",
            category="ROUNDTRIP",
            source="roundtrip_source",
            tags=["tag1", "tag2"],
            extra={"a": "1", "b": "2"},
        )

        # Serialize to dict and back
        data_dict = original.model_dump()
        restored = ModelDetectionRuleMetadata.model_validate(data_dict)

        assert restored.rule_id == original.rule_id
        assert restored.rule_name == original.rule_name
        assert restored.category == original.category
        assert restored.source == original.source
        assert restored.tags == original.tags
        assert restored.extra == original.extra

    def test_model_json_roundtrip(self) -> None:
        """Test that JSON serialization roundtrip works."""
        original = ModelDetectionRuleMetadata(
            rule_id="JSON-RULE",
            rule_name="JSON Test Rule",
            tags=["json"],
            extra={"format": "json"},
        )

        # Serialize to JSON and back
        json_str = original.model_dump_json()
        restored = ModelDetectionRuleMetadata.model_validate_json(json_str)

        assert restored.rule_id == original.rule_id
        assert restored.rule_name == original.rule_name
        assert restored.tags == original.tags
        assert restored.extra == original.extra

    def test_docstring_example(self) -> None:
        """Test the example from the model's docstring works correctly."""
        # This tests the example from the docstring
        metadata = ModelDetectionRuleMetadata(
            rule_id="RULE-001",
            rule_name="Credit Card Detection",
            category="PCI",
            tags=["financial", "sensitive"],
        )

        assert metadata.rule_id == "RULE-001"
        assert metadata.rule_name == "Credit Card Detection"
        assert metadata.category == "PCI"
        assert metadata.tags == ["financial", "sensitive"]
