# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelCapabilityView."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelCapabilityView


@pytest.mark.unit
class TestModelCapabilityView:
    """Tests for ModelCapabilityView model."""

    def test_minimal_creation(self) -> None:
        """Test creating with only required fields."""
        cap_id = uuid4()
        view = ModelCapabilityView(
            capability_id=cap_id,
            name="test-capability",
        )
        assert view.capability_id == cap_id
        assert view.name == "test-capability"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        view = ModelCapabilityView(
            capability_id=uuid4(),
            name="test",
        )
        assert view.namespace is None
        assert view.display_name is None
        assert view.version is None
        assert view.description is None
        assert view.category is None
        assert view.is_deprecated is False
        assert view.tags == ()

    def test_full_creation(self) -> None:
        """Test creating with all fields."""
        cap_id = uuid4()
        view = ModelCapabilityView(
            capability_id=cap_id,
            name="database.relational",
            namespace="core",
            display_name="Relational Database",
            version="1.2.0",
            description="Relational database capability",
            category="database",
            is_deprecated=False,
            tags=("production", "stable"),
        )
        assert view.name == "database.relational"
        assert view.namespace == "core"
        assert view.display_name == "Relational Database"
        assert view.tags == ("production", "stable")

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        cap_id = uuid4()
        view = ModelCapabilityView(
            capability_id=cap_id,
            name="test",
            namespace="core",
            tags=("tag1", "tag2"),
        )
        data = view.model_dump()
        restored = ModelCapabilityView.model_validate(data)
        assert restored == view
        assert restored.capability_id == cap_id

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        view = ModelCapabilityView(
            capability_id=uuid4(),
            name="test",
        )
        json_str = view.model_dump_json()
        restored = ModelCapabilityView.model_validate_json(json_str)
        assert restored == view

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        view = ModelCapabilityView(
            capability_id=uuid4(),
            name="test",
        )
        # Pydantic frozen models raise ValidationError on mutation in v2,
        # but may raise TypeError in some edge cases or implementations
        with pytest.raises((ValidationError, TypeError)):
            view.name = "new-name"  # type: ignore[misc]

    def test_uuid_from_string(self) -> None:
        """Test creating with UUID from string."""
        uuid_str = "12345678-1234-1234-1234-123456789012"
        view = ModelCapabilityView(
            capability_id=UUID(uuid_str),
            name="test",
        )
        assert str(view.capability_id) == uuid_str

    def test_deprecated_capability(self) -> None:
        """Test creating a deprecated capability."""
        view = ModelCapabilityView(
            capability_id=uuid4(),
            name="legacy-feature",
            is_deprecated=True,
        )
        assert view.is_deprecated is True

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelCapabilityView(
                capability_id=uuid4(),
                name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelCapabilityView(name="test")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ModelCapabilityView(capability_id=uuid4())  # type: ignore[call-arg]
