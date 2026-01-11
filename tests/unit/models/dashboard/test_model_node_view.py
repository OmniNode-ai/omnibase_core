# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelNodeView."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelNodeView


@pytest.mark.unit
class TestModelNodeView:
    """Tests for ModelNodeView model."""

    def test_minimal_creation(self) -> None:
        """Test creating with only required fields."""
        node_uuid = uuid4()
        view = ModelNodeView(
            node_id=node_uuid,
            name="compute-node",
        )
        assert view.node_id == node_uuid
        assert view.name == "compute-node"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="test",
        )
        assert view.namespace is None
        assert view.display_name is None
        assert view.node_kind is None
        assert view.node_type is None
        assert view.version is None
        assert view.description is None
        assert view.status is None
        assert view.health_status is None
        assert view.is_active is True
        assert view.is_healthy is True
        assert view.capabilities == ()

    def test_full_creation(self) -> None:
        """Test creating with all fields."""
        node_uuid = uuid4()
        view = ModelNodeView(
            node_id=node_uuid,
            name="data-processor",
            namespace="processing",
            display_name="Data Processor",
            node_kind="COMPUTE",
            node_type="TRANSFORMER",
            version="2.0.0",
            description="Processes data streams",
            status="active",
            health_status="healthy",
            is_active=True,
            is_healthy=True,
            capabilities=("transform", "filter", "aggregate"),
        )
        assert view.node_id == node_uuid
        assert view.node_kind == "COMPUTE"
        assert view.capabilities == ("transform", "filter", "aggregate")

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="test",
            namespace="core",
            capabilities=("cap1", "cap2"),
        )
        data = view.model_dump()
        restored = ModelNodeView.model_validate(data)
        assert restored == view

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="test",
        )
        json_str = view.model_dump_json()
        restored = ModelNodeView.model_validate_json(json_str)
        assert restored == view

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="test",
        )
        # Pydantic frozen models raise ValidationError on mutation in v2,
        # but may raise TypeError in some edge cases or implementations
        with pytest.raises((ValidationError, TypeError)):
            view.name = "new-name"  # type: ignore[misc]

    def test_invalid_node_id_raises(self) -> None:
        """Test that invalid node_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(
                node_id="not-a-valid-uuid",  # type: ignore[arg-type]
                name="test",
            )

    def test_empty_name_raises(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(
                node_id=uuid4(),
                name="",
            )

    def test_get_display_name_with_display_name(self) -> None:
        """Test get_display_name returns display_name when set."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="internal-name",
            display_name="Pretty Name",
        )
        assert view.get_display_name() == "Pretty Name"

    def test_get_display_name_fallback(self) -> None:
        """Test get_display_name falls back to name when display_name is None."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="internal-name",
        )
        assert view.get_display_name() == "internal-name"

    def test_get_qualified_id_with_namespace(self) -> None:
        """Test get_qualified_id with namespace."""
        node_uuid = UUID("12345678-1234-5678-1234-567812345678")
        view = ModelNodeView(
            node_id=node_uuid,
            name="test",
            namespace="onex.compute",
        )
        assert (
            view.get_qualified_id()
            == "onex.compute/12345678-1234-5678-1234-567812345678"
        )

    def test_get_qualified_id_without_namespace(self) -> None:
        """Test get_qualified_id without namespace."""
        node_uuid = UUID("12345678-1234-5678-1234-567812345678")
        view = ModelNodeView(
            node_id=node_uuid,
            name="test",
        )
        assert view.get_qualified_id() == "12345678-1234-5678-1234-567812345678"

    def test_inactive_unhealthy_node(self) -> None:
        """Test creating an inactive and unhealthy node."""
        view = ModelNodeView(
            node_id=uuid4(),
            name="broken-node",
            is_active=False,
            is_healthy=False,
            status="stopped",
            health_status="critical",
        )
        assert view.is_active is False
        assert view.is_healthy is False
        assert view.status == "stopped"
        assert view.health_status == "critical"

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelNodeView(
                node_id=uuid4(),
                name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(name="test")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ModelNodeView(node_id=uuid4())  # type: ignore[call-arg]

    def test_node_id_is_uuid_type(self) -> None:
        """Test that node_id is of UUID type, matching architecture pattern."""
        node_uuid = uuid4()
        view = ModelNodeView(
            node_id=node_uuid,
            name="test",
        )
        assert isinstance(view.node_id, UUID)
        assert view.node_id == node_uuid

    def test_string_uuid_coercion(self) -> None:
        """Test that string UUIDs are coerced to UUID type."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        view = ModelNodeView(
            node_id=uuid_str,  # type: ignore[arg-type]
            name="test",
        )
        assert isinstance(view.node_id, UUID)
        assert str(view.node_id) == uuid_str
