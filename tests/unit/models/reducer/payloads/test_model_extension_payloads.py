# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for PayloadExtension.

This module tests the PayloadExtension model for extension/plugin intents, verifying:
1. Field validation (extension_type, plugin_name, version, data, config, timeout_seconds)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import PayloadExtension


@pytest.mark.unit
class TestPayloadExtensionInstantiation:
    """Test PayloadExtension instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = PayloadExtension(
            extension_type="plugin.transform",
            plugin_name="data-enricher",
        )
        assert payload.extension_type == "plugin.transform"
        assert payload.plugin_name == "data-enricher"
        assert payload.intent_type == "extension"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = PayloadExtension(
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
class TestPayloadExtensionDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'extension'."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        assert payload.intent_type == "extension"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        data = payload.model_dump()
        assert data["intent_type"] == "extension"


@pytest.mark.unit
class TestPayloadExtensionTypeValidation:
    """Test extension_type field validation."""

    def test_extension_type_required(self) -> None:
        """Test that extension_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(plugin_name="test")  # type: ignore[call-arg]
        assert "extension_type" in str(exc_info.value)

    def test_extension_type_min_length(self) -> None:
        """Test extension_type minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type="", plugin_name="test")
        assert "extension_type" in str(exc_info.value)

    def test_extension_type_max_length(self) -> None:
        """Test extension_type maximum length validation."""
        long_type = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type=long_type, plugin_name="test")
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
            payload = PayloadExtension(extension_type=ext_type, plugin_name="test")
            assert payload.extension_type == ext_type

    def test_extension_type_requires_namespace(self) -> None:
        """Test that extension_type requires namespace.name pattern."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type="noDot", plugin_name="test")
        assert "extension_type" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadExtensionPluginNameValidation:
    """Test plugin_name field validation."""

    def test_plugin_name_required(self) -> None:
        """Test that plugin_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type="plugin.test")  # type: ignore[call-arg]
        assert "plugin_name" in str(exc_info.value)

    def test_plugin_name_min_length(self) -> None:
        """Test plugin_name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type="plugin.test", plugin_name="")
        assert "plugin_name" in str(exc_info.value)

    def test_plugin_name_max_length(self) -> None:
        """Test plugin_name maximum length validation."""
        long_name = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(extension_type="plugin.test", plugin_name=long_name)
        assert "plugin_name" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadExtensionDefaultValues:
    """Test default values."""

    def test_default_version(self) -> None:
        """Test default version is None."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        assert payload.version is None

    def test_default_data(self) -> None:
        """Test default data is empty dict."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        assert payload.data == {}

    def test_default_config(self) -> None:
        """Test default config is empty dict."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        assert payload.config == {}

    def test_default_timeout_seconds(self) -> None:
        """Test default timeout_seconds is None."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        assert payload.timeout_seconds is None


@pytest.mark.unit
class TestPayloadExtensionTimeoutValidation:
    """Test timeout_seconds field validation."""

    def test_timeout_minimum(self) -> None:
        """Test timeout_seconds minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=0,
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_timeout_maximum(self) -> None:
        """Test timeout_seconds maximum value."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=3601,
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_valid_timeout_range(self) -> None:
        """Test valid timeout values."""
        for timeout in [1, 60, 3600]:
            payload = PayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                timeout_seconds=timeout,
            )
            assert payload.timeout_seconds == timeout


@pytest.mark.unit
class TestPayloadExtensionVersionValidation:
    """Test version field validation."""

    def test_version_max_length(self) -> None:
        """Test version maximum length validation."""
        long_version = "a" * 33
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                version=long_version,
            )
        assert "version" in str(exc_info.value)


@pytest.mark.unit
class TestPayloadExtensionImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_extension_type(self) -> None:
        """Test that extension_type cannot be modified after creation."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        with pytest.raises(ValidationError):
            payload.extension_type = "webhook.send"  # type: ignore[misc]

    def test_cannot_modify_plugin_name(self) -> None:
        """Test that plugin_name cannot be modified after creation."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        with pytest.raises(ValidationError):
            payload.plugin_name = "new-plugin"  # type: ignore[misc]


@pytest.mark.unit
class TestPayloadExtensionSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = PayloadExtension(
            extension_type="plugin.ml",
            plugin_name="classifier",
            version="1.0.0",
            data={"input": "text"},
            config={"model": "default"},
            timeout_seconds=60,
        )
        data = original.model_dump()
        restored = PayloadExtension.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = PayloadExtension(extension_type="plugin.test", plugin_name="test")
        json_str = original.model_dump_json()
        restored = PayloadExtension.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = PayloadExtension(extension_type="plugin.test", plugin_name="test")
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
class TestPayloadExtensionExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PayloadExtension(
                extension_type="plugin.test",
                plugin_name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)
