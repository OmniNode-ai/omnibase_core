# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelNodeView."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard import ModelNodeView


class TestModelNodeView:
    """Tests for ModelNodeView model."""

    def test_minimal_creation(self) -> None:
        """Test creating with only required fields."""
        view = ModelNodeView(
            node_id="node-001",
            name="compute-node",
        )
        assert view.node_id == "node-001"
        assert view.name == "compute-node"

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        view = ModelNodeView(
            node_id="n1",
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
        view = ModelNodeView(
            node_id="node-001",
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
        assert view.node_kind == "COMPUTE"
        assert view.capabilities == ("transform", "filter", "aggregate")

    def test_roundtrip_serialization(self) -> None:
        """Test model_dump and model_validate roundtrip."""
        view = ModelNodeView(
            node_id="n1",
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
            node_id="n1",
            name="test",
        )
        json_str = view.model_dump_json()
        restored = ModelNodeView.model_validate_json(json_str)
        assert restored == view

    def test_frozen_model(self) -> None:
        """Test that model is frozen."""
        view = ModelNodeView(
            node_id="n1",
            name="test",
        )
        with pytest.raises(ValidationError):
            view.name = "new-name"  # type: ignore[misc]

    def test_empty_node_id_raises(self) -> None:
        """Test that empty node_id raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(
                node_id="",
                name="test",
            )

    def test_empty_name_raises(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(
                node_id="n1",
                name="",
            )

    def test_get_display_name_with_display_name(self) -> None:
        """Test get_display_name returns display_name when set."""
        view = ModelNodeView(
            node_id="n1",
            name="internal-name",
            display_name="Pretty Name",
        )
        assert view.get_display_name() == "Pretty Name"

    def test_get_display_name_fallback(self) -> None:
        """Test get_display_name falls back to name when display_name is None."""
        view = ModelNodeView(
            node_id="n1",
            name="internal-name",
        )
        assert view.get_display_name() == "internal-name"

    def test_get_qualified_id_with_namespace(self) -> None:
        """Test get_qualified_id with namespace."""
        view = ModelNodeView(
            node_id="node-001",
            name="test",
            namespace="onex.compute",
        )
        assert view.get_qualified_id() == "onex.compute/node-001"

    def test_get_qualified_id_without_namespace(self) -> None:
        """Test get_qualified_id without namespace."""
        view = ModelNodeView(
            node_id="node-001",
            name="test",
        )
        assert view.get_qualified_id() == "node-001"

    def test_inactive_unhealthy_node(self) -> None:
        """Test creating an inactive and unhealthy node."""
        view = ModelNodeView(
            node_id="n1",
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
                node_id="n1",
                name="test",
                unknown_field="value",  # type: ignore[call-arg]
            )

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeView(name="test")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ModelNodeView(node_id="n1")  # type: ignore[call-arg]
