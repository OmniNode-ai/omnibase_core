# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelCapabilityProvided."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)


@pytest.mark.unit
class TestModelCapabilityProvided:
    """Tests for ModelCapabilityProvided model."""

    @pytest.mark.unit
    def test_valid_capability(self) -> None:
        """Test creating a valid capability."""
        cap = ModelCapabilityProvided(name="event_emit")
        assert cap.name == "event_emit"
        assert cap.version is None
        assert cap.description is None

    @pytest.mark.unit
    def test_full_capability(self) -> None:
        """Test creating a capability with all fields."""
        cap = ModelCapabilityProvided(
            name="http_response",
            version="1.0.0",
            description="Provides HTTP response handling",
        )
        assert cap.name == "http_response"
        assert cap.version == "1.0.0"
        assert cap.description == "Provides HTTP response handling"

    @pytest.mark.unit
    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError):
            ModelCapabilityProvided()  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_empty_name_rejected(self) -> None:
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityProvided(name="")

    @pytest.mark.unit
    def test_name_validation_valid_names(self) -> None:
        """Test name validation with valid names."""
        valid_names = [
            "event_emit",
            "http_response",
            "logging",
            "capability123",
            "my_cap_v2",
        ]
        for name in valid_names:
            cap = ModelCapabilityProvided(name=name)
            assert cap.name == name

    @pytest.mark.unit
    def test_name_validation_invalid_names(self) -> None:
        """Test name validation with invalid names."""
        invalid_names = [
            "event-emit",  # Contains dash
            "capability.name",  # Contains dot
            "capability name",  # Contains space
            "cap@test",  # Contains special char
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                ModelCapabilityProvided(name=name)

    @pytest.mark.unit
    def test_matches_exact(self) -> None:
        """Test matches method with exact match."""
        cap = ModelCapabilityProvided(name="event_emit")
        assert cap.matches("event_emit") is True
        assert cap.matches("other") is False

    @pytest.mark.unit
    def test_matches_case_insensitive(self) -> None:
        """Test matches method is case-insensitive."""
        cap = ModelCapabilityProvided(name="event_emit")
        assert cap.matches("EVENT_EMIT") is True
        assert cap.matches("Event_Emit") is True

    @pytest.mark.unit
    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelCapabilityProvided(
                name="test",
                extra="not_allowed",  # type: ignore[call-arg]
            )

    @pytest.mark.unit
    def test_frozen_model(self) -> None:
        """Test that the model is immutable."""
        cap = ModelCapabilityProvided(name="test")
        with pytest.raises(ValidationError):
            cap.name = "changed"  # type: ignore[misc]

    @pytest.mark.unit
    def test_repr_without_version(self) -> None:
        """Test string representation without version."""
        cap = ModelCapabilityProvided(name="event_emit")
        repr_str = repr(cap)
        assert "event_emit" in repr_str
        assert "version" not in repr_str

    @pytest.mark.unit
    def test_repr_with_version(self) -> None:
        """Test string representation with version."""
        cap = ModelCapabilityProvided(name="event_emit", version="1.0.0")
        repr_str = repr(cap)
        assert "event_emit" in repr_str
        assert "1.0.0" in repr_str

    @pytest.mark.unit
    def test_equality(self) -> None:
        """Test equality comparison."""
        cap1 = ModelCapabilityProvided(name="test", version="1.0.0")
        cap2 = ModelCapabilityProvided(name="test", version="1.0.0")
        cap3 = ModelCapabilityProvided(name="other", version="1.0.0")
        assert cap1 == cap2
        assert cap1 != cap3

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "name": "event_emit",
            "version": "1.0.0",
            "description": "Test capability",
        }
        cap = ModelCapabilityProvided.model_validate(data)
        assert cap.name == "event_emit"
        assert cap.version == "1.0.0"
        assert cap.description == "Test capability"

    @pytest.mark.unit
    def test_to_dict(self) -> None:
        """Test serializing to dictionary."""
        cap = ModelCapabilityProvided(
            name="test",
            version="1.0.0",
            description="Test",
        )
        data = cap.model_dump()
        assert data["name"] == "test"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test"

    @pytest.mark.unit
    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is stripped from name."""
        cap = ModelCapabilityProvided(name="  event_emit  ")
        assert cap.name == "event_emit"

    @pytest.mark.unit
    def test_name_normalized_to_lowercase(self) -> None:
        """Test that capability names are normalized to lowercase."""
        cap = ModelCapabilityProvided(name="EventEmit")
        assert cap.name == "eventemit"

        cap2 = ModelCapabilityProvided(name="HTTP_Response")
        assert cap2.name == "http_response"

        cap3 = ModelCapabilityProvided(name="ALLCAPS")
        assert cap3.name == "allcaps"

    @pytest.mark.unit
    def test_mixed_case_with_underscores(self) -> None:
        """Test names with mixed case and underscores."""
        cap = ModelCapabilityProvided(name="My_Event_Emit")
        assert cap.name == "my_event_emit"
