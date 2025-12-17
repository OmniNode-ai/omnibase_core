# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""
Unit tests for ModelNodeRegistrationMetadata.

Tests all aspects of the node registration metadata model including:
- Basic instantiation with required and optional fields
- Tag normalization (lowercase, strip whitespace, deduplicate)
- Tag max length enforcement (20 max)
- Label key validation (valid k8s-style patterns)
- Label max count enforcement (50 max)
- Model configuration (frozen, extra forbidden, from_attributes)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.models.common.model_node_registration_metadata import (
    ModelNodeRegistrationMetadata,
)

# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataBasicInstantiation:
    """Tests for basic model instantiation."""

    def test_instantiation_with_required_field_only(self) -> None:
        """Test that model can be instantiated with only the required field."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT
        )

        assert metadata.environment == EnumEnvironment.DEVELOPMENT
        assert metadata.tags == []
        assert metadata.labels == {}
        assert metadata.release_channel is None
        assert metadata.region is None

    def test_instantiation_with_all_fields(self) -> None:
        """Test model instantiation with all fields populated."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.PRODUCTION,
            tags=["api", "core"],
            labels={"app": "myapp", "version": "1.0"},
            release_channel="stable",
            region="us-east-1",
        )

        assert metadata.environment == EnumEnvironment.PRODUCTION
        assert metadata.tags == ["api", "core"]
        assert metadata.labels == {"app": "myapp", "version": "1.0"}
        assert metadata.release_channel == "stable"
        assert metadata.region == "us-east-1"

    def test_instantiation_with_all_environment_values(self) -> None:
        """Test that model accepts all valid EnumEnvironment values."""
        environments = [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.TESTING,
            EnumEnvironment.STAGING,
            EnumEnvironment.PRODUCTION,
            EnumEnvironment.LOCAL,
            EnumEnvironment.INTEGRATION,
            EnumEnvironment.PREVIEW,
            EnumEnvironment.SANDBOX,
        ]

        for env in environments:
            metadata = ModelNodeRegistrationMetadata(environment=env)
            assert metadata.environment == env

    def test_environment_is_required(self) -> None:
        """Test that environment field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("environment",)
        assert errors[0]["type"] == "missing"

    def test_invalid_environment_value_raises_error(self) -> None:
        """Test that invalid environment value raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(environment="invalid_env")  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("environment",)


# =============================================================================
# Tag Normalization Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataTagNormalization:
    """Tests for tag normalization behavior."""

    def test_tags_normalized_to_lowercase(self) -> None:
        """Test that tags are normalized to lowercase."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["API", "Core", "BACKEND"],
        )

        assert metadata.tags == ["api", "core", "backend"]

    def test_tags_whitespace_stripped(self) -> None:
        """Test that whitespace is stripped from tags."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["  api  ", "\tcore\t", " backend "],
        )

        assert metadata.tags == ["api", "core", "backend"]

    def test_tags_deduplicated(self) -> None:
        """Test that duplicate tags are removed."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["api", "core", "api", "backend", "core"],
        )

        assert metadata.tags == ["api", "core", "backend"]

    def test_tags_case_insensitive_deduplication(self) -> None:
        """Test that tags are deduplicated case-insensitively."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["API", "api", "Api", "CORE", "core"],
        )

        # First occurrence of each unique lowercase tag is kept
        assert metadata.tags == ["api", "core"]

    def test_empty_tags_filtered_out(self) -> None:
        """Test that empty/whitespace-only tags are filtered out."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["api", "", "  ", "core", "\t", "backend"],
        )

        assert metadata.tags == ["api", "core", "backend"]

    def test_tags_order_preserved(self) -> None:
        """Test that tag order is preserved after normalization."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["zebra", "alpha", "middle"],
        )

        assert metadata.tags == ["zebra", "alpha", "middle"]

    def test_none_tags_defaults_to_empty_list(self) -> None:
        """Test that None tags value results in empty list."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=None,  # type: ignore[arg-type]
        )

        assert metadata.tags == []


# =============================================================================
# Tag Max Length Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataTagMaxLength:
    """Tests for tag maximum length enforcement."""

    def test_tags_up_to_max_allowed(self) -> None:
        """Test that up to 20 tags are allowed."""
        tags = [f"tag{i}" for i in range(20)]
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=tags,
        )

        assert len(metadata.tags) == 20

    def test_tags_exceeding_max_raises_error(self) -> None:
        """Test that more than 20 tags raises validation error."""
        tags = [f"tag{i}" for i in range(21)]

        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                tags=tags,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("tags",)
        assert "too_long" in errors[0]["type"]

    def test_duplicate_tags_count_after_dedup(self) -> None:
        """Test that tag count is checked after deduplication."""
        # 25 tags but only 20 unique after lowercasing
        tags = [f"tag{i}" for i in range(20)] + [
            "TAG0",
            "TAG1",
            "TAG2",
            "TAG3",
            "TAG4",
        ]

        # After normalization, should be exactly 20 unique tags
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=tags,
        )

        assert len(metadata.tags) == 20


# =============================================================================
# Label Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataLabelValidation:
    """Tests for label key validation (k8s-style patterns)."""

    def test_valid_simple_label_keys(self) -> None:
        """Test that simple alphanumeric label keys are valid."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"app": "myapp", "version": "v1", "tier": "frontend"},
        )

        assert metadata.labels == {"app": "myapp", "version": "v1", "tier": "frontend"}

    def test_valid_label_keys_with_hyphens(self) -> None:
        """Test that label keys with hyphens are valid."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"app-name": "myapp", "release-version": "v1"},
        )

        assert metadata.labels == {"app-name": "myapp", "release-version": "v1"}

    def test_valid_label_keys_with_dots(self) -> None:
        """Test that label keys with dots (k8s namespace style) are valid."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"app.kubernetes.io": "myapp", "domain.org": "value"},
        )

        assert metadata.labels == {"app.kubernetes.io": "myapp", "domain.org": "value"}

    def test_valid_label_keys_with_numbers(self) -> None:
        """Test that label keys with numbers are valid."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"v1": "value", "app2": "myapp", "1label": "value"},
        )

        assert "v1" in metadata.labels
        assert "app2" in metadata.labels
        assert "1label" in metadata.labels

    def test_label_keys_normalized_to_lowercase(self) -> None:
        """Test that label keys are normalized to lowercase."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"APP": "myapp", "Version": "v1", "TIER": "frontend"},
        )

        assert metadata.labels == {"app": "myapp", "version": "v1", "tier": "frontend"}

    def test_label_values_converted_to_string(self) -> None:
        """Test that label values are converted to strings."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"count": 42, "enabled": True, "rate": 3.14},  # type: ignore[dict-item]
        )

        assert metadata.labels["count"] == "42"
        assert metadata.labels["enabled"] == "True"
        assert metadata.labels["rate"] == "3.14"

    def test_invalid_label_key_with_underscore_raises_error(self) -> None:
        """Test that label key with underscore raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"app_name": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_invalid_label_key_with_uppercase_fails_pattern(self) -> None:
        """Test that label keys are validated after lowercasing."""
        # Uppercase letters are lowercased first, so this should pass
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"APP": "myapp"},
        )
        assert metadata.labels == {"app": "myapp"}

    def test_invalid_label_key_with_special_chars_raises_error(self) -> None:
        """Test that label key with special characters raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"app@name": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_invalid_label_key_with_spaces_raises_error(self) -> None:
        """Test that label key with spaces raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"app name": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_invalid_label_key_starting_with_hyphen_raises_error(self) -> None:
        """Test that label key starting with hyphen raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"-app": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_invalid_label_key_ending_with_hyphen_raises_error(self) -> None:
        """Test that label key ending with hyphen raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"app-": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_invalid_label_key_empty_raises_error(self) -> None:
        """Test that empty label key raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels={"": "myapp"},
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Invalid label key format" in str(errors[0]["msg"])

    def test_none_labels_defaults_to_empty_dict(self) -> None:
        """Test that None labels value results in empty dict."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels=None,  # type: ignore[arg-type]
        )

        assert metadata.labels == {}


# =============================================================================
# Label Max Count Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataLabelMaxCount:
    """Tests for label maximum count enforcement."""

    def test_labels_up_to_max_allowed(self) -> None:
        """Test that up to 50 labels are allowed."""
        labels = {f"label{i}": f"value{i}" for i in range(50)}
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels=labels,
        )

        assert len(metadata.labels) == 50

    def test_labels_exceeding_max_raises_error(self) -> None:
        """Test that more than 50 labels raises validation error."""
        labels = {f"label{i}": f"value{i}" for i in range(51)}

        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                labels=labels,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Maximum 50 labels allowed" in str(errors[0]["msg"])


# =============================================================================
# Model Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataConfiguration:
    """Tests for model configuration (frozen, extra forbidden, from_attributes)."""

    def test_model_is_frozen_immutable(self) -> None:
        """Test that model is immutable (frozen=True)."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["api"],
        )

        with pytest.raises(ValidationError):
            metadata.environment = EnumEnvironment.PRODUCTION  # type: ignore[misc]

        with pytest.raises(ValidationError):
            metadata.tags = ["new_tag"]  # type: ignore[misc]

        with pytest.raises(ValidationError):
            metadata.labels = {"new": "label"}  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                extra_field="should_fail",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"

    def test_from_attributes_allows_object_instantiation(self) -> None:
        """Test that from_attributes=True allows instantiation from objects.

        This is important for pytest-xdist parallel execution where model
        classes may be imported in separate workers with different identities.
        """

        # Create a simple object with matching attributes
        class MockMetadata:
            environment = EnumEnvironment.DEVELOPMENT
            tags = ["api", "core"]
            labels = {"app": "myapp"}
            release_channel = "stable"
            region = "us-east-1"

        mock = MockMetadata()

        # from_attributes=True allows model_validate to accept objects
        metadata = ModelNodeRegistrationMetadata.model_validate(mock)

        assert metadata.environment == EnumEnvironment.DEVELOPMENT
        assert metadata.tags == ["api", "core"]
        assert metadata.labels == {"app": "myapp"}
        assert metadata.release_channel == "stable"
        assert metadata.region == "us-east-1"


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataSerialization:
    """Tests for model serialization and deserialization."""

    def test_model_dump(self) -> None:
        """Test model serialization with model_dump."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.PRODUCTION,
            tags=["api", "core"],
            labels={"app": "myapp"},
            release_channel="stable",
            region="us-east-1",
        )

        data = metadata.model_dump()

        assert data["environment"] == EnumEnvironment.PRODUCTION
        assert data["tags"] == ["api", "core"]
        assert data["labels"] == {"app": "myapp"}
        assert data["release_channel"] == "stable"
        assert data["region"] == "us-east-1"

    def test_model_dump_json(self) -> None:
        """Test model JSON serialization."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.PRODUCTION,
            tags=["api"],
            labels={"app": "myapp"},
        )

        json_str = metadata.model_dump_json()

        assert isinstance(json_str, str)
        assert "production" in json_str
        assert "api" in json_str
        assert "myapp" in json_str

    def test_model_roundtrip(self) -> None:
        """Test model roundtrip serialization/deserialization."""
        original = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.STAGING,
            tags=["api", "core"],
            labels={"app": "myapp", "version": "v1"},
            release_channel="canary",
            region="eu-west-1",
        )

        data = original.model_dump()
        restored = ModelNodeRegistrationMetadata.model_validate(data)

        assert restored.environment == original.environment
        assert restored.tags == original.tags
        assert restored.labels == original.labels
        assert restored.release_channel == original.release_channel
        assert restored.region == original.region

    def test_model_validate_from_dict(self) -> None:
        """Test model validation from dictionary."""
        data = {
            "environment": "production",
            "tags": ["API", "Core"],  # Should be normalized
            "labels": {"APP": "myapp"},  # Should be normalized
            "release_channel": "stable",
            "region": "us-west-2",
        }

        metadata = ModelNodeRegistrationMetadata.model_validate(data)

        assert metadata.environment == EnumEnvironment.PRODUCTION
        assert metadata.tags == ["api", "core"]  # Normalized
        assert metadata.labels == {"app": "myapp"}  # Normalized
        assert metadata.release_channel == "stable"
        assert metadata.region == "us-west-2"


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_complex_label_keys(self) -> None:
        """Test complex but valid k8s-style label keys."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={
                "app.kubernetes.io": "myapp",
                "helm.sh": "chart",
                "release-name": "v1-beta",
                "a1b2c3": "alphanumeric",
            },
        )

        assert "app.kubernetes.io" in metadata.labels
        assert "helm.sh" in metadata.labels
        assert "release-name" in metadata.labels
        assert "a1b2c3" in metadata.labels

    def test_single_character_label_key(self) -> None:
        """Test that single character label keys are valid."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            labels={"a": "value", "1": "number"},
        )

        assert metadata.labels["a"] == "value"
        assert metadata.labels["1"] == "number"

    def test_tags_with_mixed_normalization(self) -> None:
        """Test tags with various normalization requirements."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=[
                "  UPPER  ",
                "lower",
                " Mixed Case ",
                "",
                "   ",
                "UPPER",  # Duplicate after normalization
                "lower",  # Exact duplicate
            ],
        )

        # Should be deduplicated and normalized
        assert metadata.tags == ["upper", "lower", "mixed case"]

    def test_empty_optional_fields(self) -> None:
        """Test model with empty optional fields."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=[],
            labels={},
            release_channel=None,
            region=None,
        )

        assert metadata.tags == []
        assert metadata.labels == {}
        assert metadata.release_channel is None
        assert metadata.region is None

    def test_model_equality(self) -> None:
        """Test model equality comparison."""
        metadata1 = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["api", "core"],
            labels={"app": "myapp"},
        )

        metadata2 = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["API", "CORE"],  # Different case, same after normalization
            labels={"APP": "myapp"},  # Different case, same after normalization
        )

        assert metadata1 == metadata2

    def test_model_not_hashable_due_to_mutable_fields(self) -> None:
        """Test that model is not hashable due to list and dict fields.

        Even though frozen=True, Pydantic models containing mutable types
        (list, dict) cannot be hashed because the underlying types are
        unhashable. This is expected Python behavior.
        """
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=["api"],
            labels={"app": "myapp"},
        )

        # Frozen models with list/dict fields are not hashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(metadata)

    def test_model_hashable_without_mutable_fields(self) -> None:
        """Test that model without list/dict content could theoretically hash.

        Note: Even with empty lists/dicts, the model is not hashable because
        Python's list and dict types are inherently unhashable, even when empty.
        """
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.DEVELOPMENT,
            tags=[],
            labels={},
        )

        # Even with empty mutable containers, model is not hashable
        with pytest.raises(TypeError, match="unhashable type"):
            hash(metadata)

    def test_release_channel_accepts_any_string(self) -> None:
        """Test that release_channel accepts any string value."""
        channels = ["stable", "canary", "beta", "alpha", "custom-channel", "v1.2.3"]

        for channel in channels:
            metadata = ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                release_channel=channel,
            )
            assert metadata.release_channel == channel

    def test_region_accepts_any_string(self) -> None:
        """Test that region accepts any string value."""
        regions = [
            "us-east-1",
            "eu-west-1",
            "ap-southeast-1",
            "custom-region",
            "on-premise",
        ]

        for region in regions:
            metadata = ModelNodeRegistrationMetadata(
                environment=EnumEnvironment.DEVELOPMENT,
                region=region,
            )
            assert metadata.region == region


# =============================================================================
# Model String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataRepresentation:
    """Tests for model string representation."""

    def test_str_representation(self) -> None:
        """Test string representation of model."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.PRODUCTION,
            tags=["api"],
        )

        str_repr = str(metadata)
        assert isinstance(str_repr, str)

    def test_repr_representation(self) -> None:
        """Test repr representation of model."""
        metadata = ModelNodeRegistrationMetadata(
            environment=EnumEnvironment.PRODUCTION,
            tags=["api"],
        )

        repr_str = repr(metadata)
        assert isinstance(repr_str, str)
        assert "ModelNodeRegistrationMetadata" in repr_str


# =============================================================================
# Model Schema Tests
# =============================================================================


@pytest.mark.unit
class TestModelNodeRegistrationMetadataSchema:
    """Tests for model schema and field information."""

    def test_model_json_schema(self) -> None:
        """Test that model generates valid JSON schema."""
        schema = ModelNodeRegistrationMetadata.model_json_schema()

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "environment" in schema["properties"]
        assert "tags" in schema["properties"]
        assert "labels" in schema["properties"]
        assert "release_channel" in schema["properties"]
        assert "region" in schema["properties"]

    def test_model_fields(self) -> None:
        """Test model fields metadata."""
        fields = ModelNodeRegistrationMetadata.model_fields

        assert "environment" in fields
        assert "tags" in fields
        assert "labels" in fields
        assert "release_channel" in fields
        assert "region" in fields

        # Check required vs optional
        assert fields["environment"].is_required() is True
        assert fields["tags"].is_required() is False
        assert fields["labels"].is_required() is False
        assert fields["release_channel"].is_required() is False
        assert fields["region"].is_required() is False
