# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelActionParameters.

Tests all ModelActionParameters functionality including:
- Basic instantiation with all fields
- Partial instantiation with optional fields
- Default value verification
- Field validation (timeout_override_ms must be > 0)
- ModelSemVer field handling
- Extensions dict field
- Frozen behavior (immutability)
- Extra fields forbidden
- JSON serialization/deserialization
- from_attributes behavior
"""

from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelActionParameters
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Helper classes for from_attributes testing
# =============================================================================


@dataclass
class ActionParametersAttrs:
    """Helper dataclass for testing from_attributes on ModelActionParameters."""

    action_name: str | None = None
    action_version: ModelSemVer | None = None
    idempotency_key: str | None = None
    timeout_override_ms: int | None = None
    input_path: str | None = None
    output_path: str | None = None
    format: str | None = None
    validate_input: bool = True
    validate_output: bool = True
    extensions: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Basic Instantiation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersInstantiation:
    """Tests for ModelActionParameters instantiation."""

    def test_create_with_all_fields(self) -> None:
        """Test creating parameters with all fields populated."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        params = ModelActionParameters(
            action_name="transform_data",
            action_version=version,
            idempotency_key="idem-key-12345",
            timeout_override_ms=120,
            input_path="/data/input.json",
            output_path="/data/output.json",
            format="json",
            validate_input=True,
            validate_output=False,
            extensions={"custom_key": "custom_value"},
        )

        assert params.action_name == "transform_data"
        assert params.action_version == version
        assert params.idempotency_key == "idem-key-12345"
        assert params.timeout_override_ms == 120
        assert params.input_path == "/data/input.json"
        assert params.output_path == "/data/output.json"
        assert params.format == "json"
        assert params.validate_input is True
        assert params.validate_output is False
        assert params.extensions == {"custom_key": "custom_value"}

    def test_create_with_partial_fields(self) -> None:
        """Test creating parameters with only some fields."""
        params = ModelActionParameters(
            action_name="simple_action",
            format="yaml",
        )

        assert params.action_name == "simple_action"
        assert params.format == "yaml"
        assert params.action_version is None
        assert params.timeout_override_ms is None
        assert params.validate_input is True  # default

    def test_create_with_no_fields(self) -> None:
        """Test creating parameters with all defaults."""
        params = ModelActionParameters()

        assert params.action_name is None
        assert params.action_version is None
        assert params.idempotency_key is None
        assert params.timeout_override_ms is None
        assert params.input_path is None
        assert params.output_path is None
        assert params.format is None
        assert params.validate_input is True
        assert params.validate_output is True
        assert params.extensions == {}


# =============================================================================
# Default Value Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersDefaults:
    """Tests for ModelActionParameters default values."""

    def test_validate_input_defaults_to_true(self) -> None:
        """Test that validate_input defaults to True."""
        params = ModelActionParameters()
        assert params.validate_input is True

    def test_validate_output_defaults_to_true(self) -> None:
        """Test that validate_output defaults to True."""
        params = ModelActionParameters()
        assert params.validate_output is True

    def test_extensions_defaults_to_empty_dict(self) -> None:
        """Test that extensions defaults to empty dict."""
        params = ModelActionParameters()
        assert params.extensions == {}
        assert isinstance(params.extensions, dict)

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        params = ModelActionParameters()
        assert params.action_name is None
        assert params.action_version is None
        assert params.idempotency_key is None
        assert params.timeout_override_ms is None
        assert params.input_path is None
        assert params.output_path is None
        assert params.format is None


# =============================================================================
# Field Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersValidation:
    """Tests for ModelActionParameters field validation."""

    def test_timeout_override_ms_must_be_positive(self) -> None:
        """Test that timeout_override_ms must be > 0."""
        # Valid positive value
        params = ModelActionParameters(timeout_override_ms=1)
        assert params.timeout_override_ms == 1

        # Invalid (zero)
        with pytest.raises(ValidationError) as exc_info:
            ModelActionParameters(timeout_override_ms=0)
        assert "timeout_override_ms" in str(exc_info.value).lower()

        # Invalid (negative)
        with pytest.raises(ValidationError):
            ModelActionParameters(timeout_override_ms=-1)

    def test_timeout_override_ms_accepts_none(self) -> None:
        """Test that timeout_override_ms accepts None."""
        params = ModelActionParameters(timeout_override_ms=None)
        assert params.timeout_override_ms is None

    def test_action_version_accepts_model_semver(self) -> None:
        """Test that action_version accepts ModelSemVer."""
        version = ModelSemVer(major=2, minor=0, patch=1)
        params = ModelActionParameters(action_version=version)
        assert params.action_version == version
        assert params.action_version.major == 2
        assert params.action_version.minor == 0
        assert params.action_version.patch == 1

    def test_action_version_accepts_dict(self) -> None:
        """Test that action_version accepts dict format."""
        params = ModelActionParameters(
            action_version={"major": 1, "minor": 5, "patch": 0}  # type: ignore[arg-type]
        )
        assert params.action_version is not None
        assert params.action_version.major == 1
        assert params.action_version.minor == 5
        assert params.action_version.patch == 0

    def test_extensions_accepts_various_types(self) -> None:
        """Test that extensions dict accepts various JSON-serializable types."""
        params = ModelActionParameters(
            extensions={
                "string_key": "string_value",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
                "list_key": [1, 2, 3],
                "dict_key": {"nested": "value"},
                "null_key": None,
            }
        )
        assert params.extensions["string_key"] == "string_value"
        assert params.extensions["int_key"] == 42
        assert params.extensions["float_key"] == 3.14
        assert params.extensions["bool_key"] is True
        assert params.extensions["list_key"] == [1, 2, 3]
        assert params.extensions["dict_key"] == {"nested": "value"}
        assert params.extensions["null_key"] is None

    def test_timeout_override_ms_accepts_minimum_value(self) -> None:
        """Test that timeout_override_ms accepts minimum value of 1.

        The minimum valid value is 1 (not 0) because the field uses gt=0.
        """
        params = ModelActionParameters(timeout_override_ms=1)
        assert params.timeout_override_ms == 1

    def test_timeout_override_ms_boundary_validation(self) -> None:
        """Test timeout boundary validation (must be > 0, not >= 0).

        The field uses gt=0 (greater than), not ge=0 (greater than or equal),
        so the minimum valid value is 1, not 0. This is intentional to prevent
        a timeout of 0ms which would cause immediate timeouts.
        """
        # Value of 1 should work (minimum valid)
        params = ModelActionParameters(timeout_override_ms=1)
        assert params.timeout_override_ms == 1

        # Value of 0 should fail (gt=0 constraint)
        with pytest.raises(ValidationError) as exc_info:
            ModelActionParameters(timeout_override_ms=0)
        assert "timeout_override_ms" in str(exc_info.value).lower()


# =============================================================================
# Immutability Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersImmutability:
    """Tests for ModelActionParameters immutability (frozen=True)."""

    def test_cannot_modify_action_name(self) -> None:
        """Test that action_name cannot be modified after creation."""
        params = ModelActionParameters(action_name="original")
        with pytest.raises(ValidationError):
            params.action_name = "modified"  # type: ignore[misc]

    def test_cannot_modify_format(self) -> None:
        """Test that format cannot be modified after creation."""
        params = ModelActionParameters(format="json")
        with pytest.raises(ValidationError):
            params.format = "yaml"  # type: ignore[misc]

    def test_cannot_modify_validate_input(self) -> None:
        """Test that validate_input cannot be modified after creation."""
        params = ModelActionParameters(validate_input=True)
        with pytest.raises(ValidationError):
            params.validate_input = False  # type: ignore[misc]

    def test_cannot_modify_extensions(self) -> None:
        """Test that extensions dict cannot be reassigned."""
        params = ModelActionParameters(extensions={"key": "value"})
        with pytest.raises(ValidationError):
            params.extensions = {"other": "data"}  # type: ignore[misc]


# =============================================================================
# Extra Fields Forbidden Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersExtraForbid:
    """Tests for ModelActionParameters extra='forbid'."""

    def test_extra_fields_raise_error(self) -> None:
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelActionParameters(
                action_name="test",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()


# =============================================================================
# From Attributes Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersFromAttributes:
    """Tests for ModelActionParameters from_attributes=True."""

    def test_create_from_dataclass_with_attributes(self) -> None:
        """Test creating ModelActionParameters from an object with attributes."""
        attrs = ActionParametersAttrs(
            action_name="from_attrs_action",
            format="csv",
            validate_input=False,
        )
        params = ModelActionParameters.model_validate(attrs)
        assert params.action_name == "from_attrs_action"
        assert params.format == "csv"
        assert params.validate_input is False

    def test_create_from_object_with_all_attributes(self) -> None:
        """Test creating from object with all attributes populated."""
        version = ModelSemVer(major=3, minor=1, patch=4)
        attrs = ActionParametersAttrs(
            action_name="full_action",
            action_version=version,
            idempotency_key="idem-full",
            timeout_override_ms=60,
            input_path="/input.json",
            output_path="/output.json",
            format="json",
            validate_input=True,
            validate_output=True,
            extensions={"extra": "data"},
        )
        params = ModelActionParameters.model_validate(attrs)
        assert params.action_name == "full_action"
        assert params.action_version == version
        assert params.extensions == {"extra": "data"}


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersSerialization:
    """Tests for ModelActionParameters serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        params = ModelActionParameters(
            action_name="dump_test",
            action_version=version,
            format="xml",
        )

        data = params.model_dump()
        assert data["action_name"] == "dump_test"
        assert data["action_version"]["major"] == 1
        assert data["format"] == "xml"

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        params = ModelActionParameters(
            action_name="json_test",
            format="json",
        )

        json_str = params.model_dump_json()
        assert isinstance(json_str, str)
        assert "json_test" in json_str
        assert '"format":"json"' in json_str or '"format": "json"' in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate from dictionary."""
        data = {
            "action_name": "from_dict",
            "action_version": {"major": 2, "minor": 1, "patch": 0},
            "format": "yaml",
            "validate_input": False,
        }

        params = ModelActionParameters.model_validate(data)
        assert params.action_name == "from_dict"
        assert params.action_version is not None
        assert params.action_version.major == 2
        assert params.format == "yaml"
        assert params.validate_input is False

    def test_round_trip_serialization(self) -> None:
        """Test full round-trip serialization."""
        original = ModelActionParameters(
            action_name="roundtrip",
            action_version=ModelSemVer(major=1, minor=2, patch=3),
            idempotency_key="idem-roundtrip",
            timeout_override_ms=90,
            input_path="/in.json",
            output_path="/out.json",
            format="json",
            validate_input=True,
            validate_output=False,
            extensions={"key1": "value1", "key2": 123},
        )

        json_str = original.model_dump_json()
        restored = ModelActionParameters.model_validate_json(json_str)

        assert restored == original


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersEdgeCases:
    """Tests for edge cases and additional scenarios."""

    def test_empty_string_action_name(self) -> None:
        """Test that empty string action_name is accepted."""
        params = ModelActionParameters(action_name="")
        assert params.action_name == ""

    def test_empty_string_format(self) -> None:
        """Test that empty string format is accepted."""
        params = ModelActionParameters(format="")
        assert params.format == ""

    def test_empty_extensions_dict(self) -> None:
        """Test that empty extensions dict is valid."""
        params = ModelActionParameters(extensions={})
        assert params.extensions == {}

    def test_large_timeout_value(self) -> None:
        """Test that large timeout values are accepted."""
        params = ModelActionParameters(timeout_override_ms=86400000)  # 24 hours in ms
        assert params.timeout_override_ms == 86400000

    def test_model_is_not_hashable_due_to_dict_field(self) -> None:
        """Test that model is not hashable due to extensions dict field.

        ModelActionParameters has an extensions dict field which makes it
        unhashable, even though the model is frozen. This is expected
        behavior in Pydantic - frozen models with mutable container fields
        (like dict or list) are not hashable.
        """
        params = ModelActionParameters(
            action_name="hash_test",
            format="json",
        )
        # Should NOT be hashable due to dict field
        with pytest.raises(TypeError, match="unhashable type"):
            hash(params)

    def test_equal_params_are_equal(self) -> None:
        """Test that params with same values are equal."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        params1 = ModelActionParameters(
            action_name="same",
            action_version=version,
            format="json",
        )
        params2 = ModelActionParameters(
            action_name="same",
            action_version=version,
            format="json",
        )

        assert params1 == params2

    def test_different_params_are_not_equal(self) -> None:
        """Test that different params are not equal."""
        params1 = ModelActionParameters(action_name="first")
        params2 = ModelActionParameters(action_name="second")

        assert params1 != params2

    def test_model_copy_with_update(self) -> None:
        """Test model_copy with update for creating modified copies."""
        original = ModelActionParameters(
            action_name="original",
            format="json",
            validate_input=True,
        )

        modified = original.model_copy(
            update={"action_name": "modified", "validate_input": False}
        )

        assert modified.action_name == "modified"
        assert modified.validate_input is False
        assert modified.format == "json"  # unchanged
        assert original.action_name == "original"  # Original unchanged

    def test_common_format_values(self) -> None:
        """Test common format values are accepted."""
        formats = ["json", "yaml", "xml", "csv", "protobuf", "msgpack"]
        for fmt in formats:
            params = ModelActionParameters(format=fmt)
            assert params.format == fmt


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelActionParametersIntegration:
    """Integration tests for ModelActionParameters."""

    def test_model_config_is_correct(self) -> None:
        """Verify model configuration is correct."""
        config = ModelActionParameters.model_config
        assert config.get("frozen") is True
        assert config.get("extra") == "forbid"
        assert config.get("from_attributes") is True

    def test_can_be_used_in_dict(self) -> None:
        """Test that params can be stored in dictionary."""
        params = ModelActionParameters(
            action_name="dict_test",
            format="yaml",
        )
        params_dict = {"execution": params}
        assert params_dict["execution"].action_name == "dict_test"
        assert params_dict["execution"].format == "yaml"

    def test_cannot_be_used_in_set_due_to_dict_field(self) -> None:
        """Test that params cannot be stored in set due to unhashable dict field.

        ModelActionParameters has an extensions dict field which makes it
        unhashable, so it cannot be used in sets.
        """
        params1 = ModelActionParameters(action_name="first")

        with pytest.raises(TypeError, match="unhashable type"):
            hash(params1)  # Cannot hash due to dict field

    def test_semver_integration(self) -> None:
        """Test ModelSemVer integration."""
        version = ModelSemVer(major=1, minor=2, patch=3)
        params = ModelActionParameters(
            action_name="semver_test",
            action_version=version,
        )

        assert params.action_version is not None
        assert str(params.action_version) == "1.2.3"
        assert params.action_version.bump_minor() == ModelSemVer(
            major=1, minor=3, patch=0
        )
