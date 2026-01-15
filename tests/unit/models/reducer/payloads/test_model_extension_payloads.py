# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelPayloadExtension.

This module tests the ModelPayloadExtension model for extension/plugin intents, verifying:
1. Field validation (extension_type, plugin_name, version, data, config, timeout_seconds)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import ModelPayloadExtension


@pytest.mark.unit
class TestModelPayloadExtensionInstantiation:
    """Test ModelPayloadExtension instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadExtension(
            extension_type="plugin.transform",
            plugin_name="data-enricher",
        )
        assert payload.extension_type == "plugin.transform"
        assert payload.plugin_name == "data-enricher"
        assert payload.intent_type == "extension"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = ModelPayloadExtension(
            extension_type="plugin.ml_inference",
            plugin_name="sentiment-analyzer",
            version="2.1.0",
            data={"text": "This is great!", "model": "bert-base"},
            config={"threshold": 0.8},
            timeout_seconds=30,
        )
        assert payload.extension_type == "plugin.ml_inference"
        assert payload.plugin_name == "sentiment-analyzer"
        assert payload.version == "2.1.0"
        assert payload.data == {"text": "This is great!", "model": "bert-base"}
        assert payload.config == {"threshold": 0.8}
        assert payload.timeout_seconds == 30


@pytest.mark.unit
class TestModelPayloadExtensionDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'extension'."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        assert payload.intent_type == "extension"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        data = payload.model_dump()
        assert data["intent_type"] == "extension"


@pytest.mark.unit
class TestModelPayloadExtensionTypeValidation:
    """Test extension_type field validation."""

    def test_extension_type_required(self) -> None:
        """Test that extension_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE(OMN-1266): Intentionally missing required arg to test validation.
            ModelPayloadExtension(plugin_name="test")  # type: ignore[call-arg]
        assert "extension_type" in str(exc_info.value)

    def test_extension_type_min_length(self) -> None:
        """Test extension_type minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(extension_type="", plugin_name="test")
        assert "extension_type" in str(exc_info.value)

    def test_extension_type_max_length(self) -> None:
        """Test extension_type maximum length validation."""
        long_type = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(extension_type=long_type, plugin_name="test")
        assert "extension_type" in str(exc_info.value)

    def test_extension_type_valid_patterns(self) -> None:
        """Test valid extension_type patterns."""
        valid_types = [
            "plugin.transform",
            "webhook.send",
            "experimental.feature",
            "custom.action",
        ]
        for ext_type in valid_types:
            payload = ModelPayloadExtension(extension_type=ext_type, plugin_name="test")
            assert payload.extension_type == ext_type

    def test_extension_type_requires_namespace(self) -> None:
        """Test that extension_type requires namespace.name pattern."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(extension_type="noDot", plugin_name="test")
        assert "extension_type" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadExtensionPluginNameValidation:
    """Test plugin_name field validation."""

    def test_plugin_name_required(self) -> None:
        """Test that plugin_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE(OMN-1266): Intentionally missing required arg to test validation.
            ModelPayloadExtension(extension_type="plugin.test")  # type: ignore[call-arg]
        assert "plugin_name" in str(exc_info.value)

    def test_plugin_name_min_length(self) -> None:
        """Test plugin_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(extension_type="plugin.test", plugin_name="")
        assert "plugin_name" in str(exc_info.value)

    def test_plugin_name_max_length(self) -> None:
        """Test plugin_name maximum length validation."""
        long_name = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(extension_type="plugin.test", plugin_name=long_name)
        assert "plugin_name" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadExtensionDefaultValues:
    """Test default values."""

    def test_default_version(self) -> None:
        """Test default version is None."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        assert payload.version is None

    def test_default_data(self) -> None:
        """Test default data is empty dict."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        assert payload.data == {}

    def test_default_config(self) -> None:
        """Test default config is empty dict."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        assert payload.config == {}

    def test_default_timeout_seconds(self) -> None:
        """Test default timeout_seconds is None."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        assert payload.timeout_seconds is None

    def test_accepts_explicit_empty_config(self) -> None:
        """Test that explicitly passing empty config dict works."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            config={},
        )
        assert payload.config == {}


@pytest.mark.unit
class TestModelPayloadExtensionTimeoutValidation:
    """Test timeout_seconds field validation."""

    def test_timeout_minimum(self) -> None:
        """Test timeout_seconds minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=0,
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_timeout_maximum(self) -> None:
        """Test timeout_seconds maximum value."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=3601,
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_valid_timeout_range(self) -> None:
        """Test valid timeout values."""
        for timeout in [1, 60, 3600]:
            payload = ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=timeout,
            )
            assert payload.timeout_seconds == timeout


@pytest.mark.unit
class TestModelPayloadExtensionVersionValidation:
    """Test version field validation."""

    def test_version_max_length(self) -> None:
        """Test version maximum length validation."""
        long_version = "a" * 33
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                version=long_version,
            )
        assert "version" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadExtensionImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_extension_type(self) -> None:
        """Test that extension_type cannot be modified after creation."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        with pytest.raises(ValidationError):
            # NOTE(OMN-1266): Intentionally mutating frozen model to test immutability.
            payload.extension_type = "webhook.send"  # type: ignore[misc]

    def test_cannot_modify_plugin_name(self) -> None:
        """Test that plugin_name cannot be modified after creation."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        with pytest.raises(ValidationError):
            # NOTE(OMN-1266): Intentionally mutating frozen model to test immutability.
            payload.plugin_name = "new-plugin"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadExtensionSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelPayloadExtension(
            extension_type="plugin.ml",
            plugin_name="classifier",
            version="1.0.0",
            data={"input": "text"},
            config={"model": "default"},
            timeout_seconds=60,
        )
        data = original.model_dump()
        restored = ModelPayloadExtension.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        json_str = original.model_dump_json()
        restored = ModelPayloadExtension.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test", plugin_name="test"
        )
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "extension_type",
            "plugin_name",
            "version",
            "data",
            "config",
            "timeout_seconds",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestModelPayloadExtensionExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing unknown field to test extra=forbid.
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


# =============================================================================
# JSON Serialization Validation Tests (OMN-1266)
# =============================================================================


@pytest.mark.unit
class TestModelPayloadExtensionJsonValidationAcceptance:
    """Tests for JSON-safety validation - acceptance cases.

    These tests verify that valid JSON-serializable data is accepted
    in the `data` and `config` fields.
    """

    def test_accepts_string_values(self) -> None:
        """Test that string values are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": "string_value"},
        )
        assert payload.data["key"] == "string_value"

    def test_accepts_integer_values(self) -> None:
        """Test that integer values are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": 42},
        )
        assert payload.data["key"] == 42

    def test_accepts_float_values(self) -> None:
        """Test that float values are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": 3.14159},
        )
        assert payload.data["key"] == 3.14159

    def test_accepts_boolean_true(self) -> None:
        """Test that True boolean is accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": True},
        )
        assert payload.data["key"] is True

    def test_accepts_boolean_false(self) -> None:
        """Test that False boolean is accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": False},
        )
        assert payload.data["key"] is False

    def test_accepts_none_values(self) -> None:
        """Test that None values are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"key": None},
        )
        assert payload.data["key"] is None

    def test_accepts_nested_dicts(self) -> None:
        """Test that nested dicts are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"nested": {"deep": {"value": "ok"}}},
        )
        # Safe: mypy cannot track recursive JsonType for nested dict access
        nested = payload.data["nested"]
        assert isinstance(nested, dict)
        deep = nested["deep"]
        assert isinstance(deep, dict)
        assert deep["value"] == "ok"

    def test_accepts_lists(self) -> None:
        """Test that lists are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"list": [1, 2, 3]},
        )
        assert payload.data["list"] == [1, 2, 3]

    def test_accepts_mixed_lists(self) -> None:
        """Test that lists with mixed types are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"mixed": [1, "two", {"three": 3}]},
        )
        assert payload.data["mixed"] == [1, "two", {"three": 3}]

    def test_accepts_complex_nested_structure(self) -> None:
        """Test that complex nested structures are accepted."""
        # NOTE(OMN-1266): mypy cannot infer JsonType for deeply nested literals.
        complex_data: dict[str, object] = {"complex": {"a": [1, {"b": [2, 3]}]}}
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            # NOTE(OMN-1266): mypy cannot infer JsonType for dict[str, object].
            data=complex_data,  # type: ignore[arg-type]
        )
        assert payload.data == complex_data

    def test_accepts_empty_dict(self) -> None:
        """Test that empty dict is accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={},
        )
        assert payload.data == {}

    def test_accepts_empty_nested_structures(self) -> None:
        """Test that empty nested structures are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"empty_dict": {}, "empty_list": []},
        )
        assert payload.data == {"empty_dict": {}, "empty_list": []}

    def test_accepts_deeply_nested_structure(self) -> None:
        """Test that deeply nested structures (5+ levels) are accepted."""
        # NOTE(OMN-1266): mypy cannot infer JsonType for deeply nested literals.
        deep_data: dict[str, object] = {
            "l1": {"l2": {"l3": {"l4": {"l5": {"l6": "deep"}}}}}
        }
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            # NOTE(OMN-1266): mypy cannot infer JsonType for dict[str, object].
            data=deep_data,  # type: ignore[arg-type]
        )
        # Safe: validated at runtime, mypy cannot track recursive JsonType
        # Navigate through levels with isinstance checks for type narrowing
        l1 = payload.data["l1"]
        assert isinstance(l1, dict)
        l2 = l1["l2"]
        assert isinstance(l2, dict)
        l3 = l2["l3"]
        assert isinstance(l3, dict)
        l4 = l3["l4"]
        assert isinstance(l4, dict)
        l5 = l4["l5"]
        assert isinstance(l5, dict)
        assert l5["l6"] == "deep"

    def test_accepts_large_list(self) -> None:
        """Test that large lists are accepted."""
        # NOTE(OMN-1266): mypy sees list[int] as incompatible with list[JsonType],
        # but int is a JsonType primitive, so this is valid at runtime.
        large_list: list[int] = list(range(1000))
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            # NOTE(OMN-1266): mypy sees list[int] as incompatible with JsonType.
            data={"large": large_list},  # type: ignore[dict-item]
        )
        large_value = payload.data["large"]
        assert isinstance(large_value, list)
        assert len(large_value) == 1000

    def test_accepts_all_primitive_types_together(self) -> None:
        """Test that all primitive types work together."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={
                "string": "value",
                "int": 42,
                "float": 3.14,
                "bool_true": True,
                "bool_false": False,
                "null": None,
            },
        )
        assert payload.data["string"] == "value"
        assert payload.data["int"] == 42
        assert payload.data["float"] == 3.14
        assert payload.data["bool_true"] is True
        assert payload.data["bool_false"] is False
        assert payload.data["null"] is None

    def test_accepts_config_field_json_values(self) -> None:
        """Test that config field also accepts JSON values."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            config={"threshold": 0.8, "options": ["a", "b"]},
        )
        assert payload.config["threshold"] == 0.8
        assert payload.config["options"] == ["a", "b"]


@pytest.mark.unit
class TestModelPayloadExtensionJsonValidationRejection:
    """Tests for JSON-safety validation - rejection cases.

    These tests verify that non-JSON-serializable types are rejected
    with appropriate error messages including key-paths.
    """

    def test_rejects_datetime(self) -> None:
        """Test that datetime objects are rejected."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"timestamp": datetime.now()},
            )
        error_str = str(exc_info.value)
        assert "timestamp" in error_str
        assert "datetime" in error_str

    def test_rejects_uuid(self) -> None:
        """Test that UUID objects are rejected."""
        from uuid import uuid4

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"id": uuid4()},
            )
        error_str = str(exc_info.value)
        assert "id" in error_str
        assert "UUID" in error_str

    def test_rejects_path(self) -> None:
        """Test that Path objects are rejected."""
        from pathlib import Path

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"path": Path("/tmp/file")},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "path" in error_str
        # Path type varies by platform (PosixPath, WindowsPath, PurePath)
        assert "Path" in error_str

    def test_rejects_bytes(self) -> None:
        """Test that bytes objects are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"binary": b"some bytes"},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "binary" in error_str
        assert "bytes" in error_str

    def test_rejects_set(self) -> None:
        """Test that set objects are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"items": {1, 2, 3}},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "items" in error_str
        assert "set" in error_str

    def test_rejects_custom_object(self) -> None:
        """Test that custom objects are rejected."""

        class CustomClass:
            pass

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"obj": CustomClass()},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "obj" in error_str
        assert "CustomClass" in error_str

    def test_rejects_nested_datetime_with_path(self) -> None:
        """Test that nested datetime includes key-path in error."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"a": {"b": {"c": datetime.now()}}},
            )
        error_str = str(exc_info.value)
        # Error should mention the path
        assert "a.b.c" in error_str or ("a" in error_str and "b" in error_str)
        assert "datetime" in error_str

    def test_rejects_datetime_in_list_with_index_path(self) -> None:
        """Test that datetime in list includes index path in error."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"list": [1, 2, datetime.now()]},
            )
        error_str = str(exc_info.value)
        # Error should mention the list and index
        assert "list" in error_str
        assert "[2]" in error_str or "2" in error_str
        assert "datetime" in error_str

    def test_rejects_deeply_nested_invalid_value(self) -> None:
        """Test that deeply nested invalid value includes full path."""
        from uuid import uuid4

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"l1": {"l2": {"l3": [{"l4": uuid4()}]}}},
            )
        error_str = str(exc_info.value)
        assert "UUID" in error_str
        # Should include path elements
        assert "l1" in error_str

    def test_rejects_config_field_non_json_values(self) -> None:
        """Test that config field also rejects non-JSON values."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                config={"timestamp": datetime.now()},
            )
        error_str = str(exc_info.value)
        assert "timestamp" in error_str
        assert "datetime" in error_str

    def test_rejects_tuple(self) -> None:
        """Test that tuple objects are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"coords": (1, 2, 3)},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "coords" in error_str
        assert "tuple" in error_str

    def test_rejects_frozenset(self) -> None:
        """Test that frozenset objects are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"frozen": frozenset([1, 2, 3])},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "frozen" in error_str
        assert "frozenset" in error_str

    def test_rejects_complex_number(self) -> None:
        """Test that complex numbers are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"complex_num": complex(1, 2)},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "complex_num" in error_str
        assert "complex" in error_str

    def test_rejects_infinity(self) -> None:
        """Test that infinity values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"value": float("inf")},
            )
        error_str = str(exc_info.value)
        assert "value" in error_str
        assert "inf" in error_str.lower() or "finite" in error_str.lower()

    def test_rejects_negative_infinity(self) -> None:
        """Test that negative infinity values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"value": float("-inf")},
            )
        error_str = str(exc_info.value)
        assert "value" in error_str

    def test_rejects_nan(self) -> None:
        """Test that NaN values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"value": float("nan")},
            )
        error_str = str(exc_info.value)
        assert "value" in error_str
        assert "nan" in error_str.lower() or "finite" in error_str.lower()

    def test_rejects_non_string_dict_keys(self) -> None:
        """Test that non-string dict keys are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={123: "value"},  # type: ignore[dict-item]
            )
        error_str = str(exc_info.value)
        assert "non-string key" in error_str
        assert "int" in error_str


@pytest.mark.unit
class TestModelPayloadExtensionJsonValidationErrorMessages:
    """Tests for JSON-safety validation error messages.

    These tests verify that error messages are clear, actionable,
    and include the key-path to the invalid value.
    """

    def test_error_message_includes_key_path(self) -> None:
        """Test that error message includes the key-path."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"nested": {"deep": {"bad": datetime.now()}}},
            )
        error_str = str(exc_info.value)
        # Should include path information
        assert "nested.deep.bad" in error_str

    def test_error_message_includes_type_name(self) -> None:
        """Test that error message includes the type name."""
        from uuid import uuid4

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"id": uuid4()},
            )
        error_str = str(exc_info.value)
        assert "UUID" in error_str

    def test_error_message_suggests_conversion(self) -> None:
        """Test that error message suggests how to fix the issue."""
        from datetime import datetime

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"ts": datetime.now()},
            )
        error_str = str(exc_info.value)
        # Should suggest conversion methods
        assert "isoformat" in error_str or "Convert" in error_str

    def test_error_message_for_list_index(self) -> None:
        """Test that error message includes list index in path."""
        from pathlib import Path

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                # NOTE(OMN-1266): Intentionally passing invalid type to test rejection.
                data={"items": ["a", "b", Path("/tmp")]},  # type: ignore[list-item]
            )
        error_str = str(exc_info.value)
        # Should include list index
        assert "items[2]" in error_str

    def test_error_message_for_mixed_nesting(self) -> None:
        """Test error message for mixed dict/list nesting."""
        from uuid import uuid4

        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"users": [{"id": uuid4()}]},
            )
        error_str = str(exc_info.value)
        # Should include both dict key and list index
        assert "users" in error_str
        assert "[0]" in error_str
        assert "id" in error_str


@pytest.mark.unit
class TestModelPayloadExtensionJsonValidationEdgeCases:
    """Tests for JSON-safety validation edge cases."""

    def test_accepts_negative_numbers(self) -> None:
        """Test that negative numbers are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"negative_int": -42, "negative_float": -3.14},
        )
        assert payload.data["negative_int"] == -42
        assert payload.data["negative_float"] == -3.14

    def test_accepts_zero(self) -> None:
        """Test that zero values are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"zero_int": 0, "zero_float": 0.0},
        )
        assert payload.data["zero_int"] == 0
        assert payload.data["zero_float"] == 0.0

    def test_accepts_empty_string(self) -> None:
        """Test that empty string is accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"empty": ""},
        )
        assert payload.data["empty"] == ""

    def test_accepts_unicode_strings(self) -> None:
        """Test that unicode strings are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"unicode": "Hello, world!"},
        )
        assert payload.data["unicode"] == "Hello, world!"

    def test_accepts_scientific_notation(self) -> None:
        """Test that scientific notation floats are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"scientific": 1.23e-4},
        )
        assert payload.data["scientific"] == 1.23e-4

    def test_accepts_large_integers(self) -> None:
        """Test that large integers are accepted."""
        large_int = 10**100
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"large": large_int},
        )
        assert payload.data["large"] == large_int

    def test_accepts_special_string_characters(self) -> None:
        """Test that strings with special characters are accepted."""
        payload = ModelPayloadExtension(
            extension_type="plugin.test",
            plugin_name="test",
            data={"special": 'quotes"and\\backslashes\nand\tnewlines'},
        )
        assert "quotes" in str(payload.data["special"])

    def test_first_invalid_value_reported(self) -> None:
        """Test that the first invalid value is reported when multiple exist."""
        from datetime import datetime
        from uuid import uuid4

        # When multiple invalid values exist, at least one should be reported
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                data={"dt": datetime.now(), "uuid": uuid4()},
            )
        error_str = str(exc_info.value)
        # Should report at least one
        assert "datetime" in error_str or "UUID" in error_str
