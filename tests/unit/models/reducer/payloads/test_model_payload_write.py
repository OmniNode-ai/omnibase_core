# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelPayloadWrite.

This module tests the ModelPayloadWrite model for file/storage write intents, verifying:
1. Field validation (path, content, content_type, etc.)
2. Discriminator value
3. Serialization/deserialization
4. Immutability
5. Default values
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.reducer.payloads import ModelPayloadWrite


@pytest.mark.unit
class TestModelPayloadWriteInstantiation:
    """Test ModelPayloadWrite instantiation."""

    def test_create_with_required_fields(self) -> None:
        """Test creating payload with required fields only."""
        payload = ModelPayloadWrite(path="/test/path", content="test content")
        assert payload.path == "/test/path"
        assert payload.content == "test content"
        assert payload.intent_type == "write"

    def test_create_with_all_fields(self) -> None:
        """Test creating payload with all fields."""
        payload = ModelPayloadWrite(
            path="/test/path",
            content="test content",
            content_type="application/json",
            encoding="utf-8",
            create_dirs=False,
            overwrite=False,
            metadata={"key": "value"},
        )
        assert payload.path == "/test/path"
        assert payload.content == "test content"
        assert payload.content_type == "application/json"
        assert payload.encoding == "utf-8"
        assert payload.create_dirs is False
        assert payload.overwrite is False
        assert payload.metadata == {"key": "value"}


@pytest.mark.unit
class TestModelPayloadWriteDiscriminator:
    """Test discriminator field."""

    def test_intent_type_value(self) -> None:
        """Test that intent_type is 'write'."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.intent_type == "write"

    def test_intent_type_in_serialization(self) -> None:
        """Test that intent_type is included in serialization."""
        payload = ModelPayloadWrite(path="/test", content="data")
        data = payload.model_dump()
        assert data["intent_type"] == "write"


@pytest.mark.unit
class TestModelPayloadWriteDefaultValues:
    """Test default values."""

    def test_default_content_type(self) -> None:
        """Test default content_type is text/plain."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.content_type == "text/plain"

    def test_default_encoding(self) -> None:
        """Test default encoding is utf-8."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.encoding == "utf-8"

    def test_default_create_dirs(self) -> None:
        """Test default create_dirs is True."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.create_dirs is True

    def test_default_overwrite(self) -> None:
        """Test default overwrite is True."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.overwrite is True

    def test_default_metadata(self) -> None:
        """Test default metadata is empty dict."""
        payload = ModelPayloadWrite(path="/test", content="data")
        assert payload.metadata == {}


@pytest.mark.unit
class TestModelPayloadWriteValidation:
    """Test field validation."""

    def test_path_required(self) -> None:
        """Test that path is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(content="data")  # type: ignore[call-arg]
        assert "path" in str(exc_info.value)

    def test_content_required(self) -> None:
        """Test that content is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(path="/test")  # type: ignore[call-arg]
        assert "content" in str(exc_info.value)

    def test_path_min_length(self) -> None:
        """Test path minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(path="", content="data")
        assert "path" in str(exc_info.value)

    def test_path_max_length(self) -> None:
        """Test path maximum length validation."""
        long_path = "a" * 1025
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(path=long_path, content="data")
        assert "path" in str(exc_info.value)

    def test_content_type_max_length(self) -> None:
        """Test content_type maximum length validation."""
        long_content_type = "a" * 129
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(
                path="/test", content="data", content_type=long_content_type
            )
        assert "content_type" in str(exc_info.value)

    def test_encoding_max_length(self) -> None:
        """Test encoding maximum length validation."""
        long_encoding = "a" * 33
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(path="/test", content="data", encoding=long_encoding)
        assert "encoding" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadWriteImmutability:
    """Test frozen/immutability."""

    def test_cannot_modify_path(self) -> None:
        """Test that path cannot be modified after creation."""
        payload = ModelPayloadWrite(path="/test", content="data")
        with pytest.raises(ValidationError):
            payload.path = "/new/path"  # type: ignore[misc]

    def test_cannot_modify_content(self) -> None:
        """Test that content cannot be modified after creation."""
        payload = ModelPayloadWrite(path="/test", content="data")
        with pytest.raises(ValidationError):
            payload.content = "new content"  # type: ignore[misc]

    def test_cannot_modify_content_type(self) -> None:
        """Test that content_type cannot be modified after creation."""
        payload = ModelPayloadWrite(path="/test", content="data")
        with pytest.raises(ValidationError):
            payload.content_type = "application/json"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPayloadWriteSerialization:
    """Test serialization/deserialization."""

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelPayloadWrite(
            path="/test/path",
            content="test content",
            content_type="application/json",
            metadata={"key": "value"},
        )
        data = original.model_dump()
        restored = ModelPayloadWrite.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip serialization."""
        original = ModelPayloadWrite(path="/test", content="data")
        json_str = original.model_dump_json()
        restored = ModelPayloadWrite.model_validate_json(json_str)
        assert restored == original

    def test_serialization_includes_all_fields(self) -> None:
        """Test that serialization includes all fields."""
        payload = ModelPayloadWrite(path="/test", content="data")
        data = payload.model_dump()
        expected_keys = {
            "intent_type",
            "path",
            "content",
            "content_type",
            "encoding",
            "create_dirs",
            "overwrite",
            "metadata",
        }
        assert set(data.keys()) == expected_keys


@pytest.mark.unit
class TestModelPayloadWriteExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_field(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPayloadWrite(
                path="/test",
                content="data",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelPayloadWriteFromAttributes:
    """Test from_attributes functionality."""

    def test_from_object_with_attributes(self) -> None:
        """Test creating from an object with matching attributes."""

        class MockWriteRequest:
            intent_type = "write"
            path = "/mock/path"
            content = "mock content"
            content_type = "text/plain"
            encoding = "utf-8"
            create_dirs = True
            overwrite = True
            metadata: dict[str, str] = {}

        obj = MockWriteRequest()
        payload = ModelPayloadWrite.model_validate(obj)
        assert payload.path == "/mock/path"
        assert payload.content == "mock content"
