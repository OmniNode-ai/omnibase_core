# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for ModelDirectivePayloadBase.

This module tests the base class for all directive payloads, verifying:
1. ConfigDict settings (frozen, extra="forbid", from_attributes)
2. Base class inheritance behavior
3. Immutability constraints
4. Extra field rejection
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
    ModelDirectivePayloadBase,
)


@pytest.mark.unit
class TestModelDirectivePayloadBaseConfiguration:
    """Test ModelDirectivePayloadBase configuration settings."""

    def test_model_config_frozen(self) -> None:
        """Test that model is configured as frozen."""
        config = ModelDirectivePayloadBase.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Test that model forbids extra fields."""
        config = ModelDirectivePayloadBase.model_config
        assert config.get("extra") == "forbid"

    def test_model_config_from_attributes(self) -> None:
        """Test that model allows from_attributes."""
        config = ModelDirectivePayloadBase.model_config
        assert config.get("from_attributes") is True


@pytest.mark.unit
class TestModelDirectivePayloadBaseInstantiation:
    """Test ModelDirectivePayloadBase instantiation."""

    def test_instantiate_empty_base_class(self) -> None:
        """Test that base class can be instantiated with no fields."""
        payload = ModelDirectivePayloadBase()
        assert payload is not None

    def test_base_class_has_no_fields(self) -> None:
        """Test that base class defines no additional fields."""
        payload = ModelDirectivePayloadBase()
        # model_dump should return empty dict for base class
        data = payload.model_dump()
        assert data == {}


@pytest.mark.unit
class TestModelDirectivePayloadBaseImmutability:
    """Test ModelDirectivePayloadBase immutability (frozen)."""

    def test_base_class_is_frozen(self) -> None:
        """Test that base class instances are immutable."""
        payload = ModelDirectivePayloadBase()
        with pytest.raises(ValidationError):
            payload.__pydantic_validator__.validate_assignment(payload, "__dict__", {})

    def test_cannot_add_attributes_after_creation(self) -> None:
        """Test that new attributes cannot be added after creation."""
        payload = ModelDirectivePayloadBase()
        # Frozen models raise ValidationError when trying to set attributes
        with pytest.raises(ValidationError):
            payload.new_attribute = "value"  # type: ignore[attr-defined]


@pytest.mark.unit
class TestModelDirectivePayloadBaseExtraFieldsRejected:
    """Test that extra fields are rejected."""

    def test_reject_extra_fields_on_construction(self) -> None:
        """Test that extra fields are rejected during construction."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDirectivePayloadBase(unknown_field="value")  # type: ignore[call-arg]
        assert "extra_forbidden" in str(exc_info.value)

    def test_reject_multiple_extra_fields(self) -> None:
        """Test that multiple extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDirectivePayloadBase(  # type: ignore[call-arg]
                field1="value1",
                field2="value2",
            )
        assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
class TestModelDirectivePayloadBaseSerialization:
    """Test ModelDirectivePayloadBase serialization."""

    def test_model_dump_empty(self) -> None:
        """Test model_dump returns empty dict."""
        payload = ModelDirectivePayloadBase()
        assert payload.model_dump() == {}

    def test_model_dump_json_empty(self) -> None:
        """Test model_dump_json returns empty object."""
        payload = ModelDirectivePayloadBase()
        json_str = payload.model_dump_json()
        assert json_str == "{}"

    def test_roundtrip_serialization(self) -> None:
        """Test roundtrip serialization."""
        original = ModelDirectivePayloadBase()
        data = original.model_dump()
        restored = ModelDirectivePayloadBase.model_validate(data)
        assert original == restored


@pytest.mark.unit
class TestModelDirectivePayloadBaseFromAttributes:
    """Test from_attributes functionality for pytest-xdist compatibility."""

    def test_from_object_with_attributes(self) -> None:
        """Test creating from an object with matching attributes."""

        class MockObject:
            pass

        obj = MockObject()
        payload = ModelDirectivePayloadBase.model_validate(obj)
        assert payload is not None

    def test_from_dict(self) -> None:
        """Test creating from dict."""
        payload = ModelDirectivePayloadBase.model_validate({})
        assert payload is not None
