# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for external node discovery via Python entry points."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.discovery.discovery_external_nodes import (
    DiscoveredNode,
    discover_external_nodes,
)
from omnibase_core.errors.error_node_discovery import NodeDiscoveryError

_EP_MODULE = "omnibase_core.discovery.discovery_external_nodes.entry_points"


def _make_entry_point(
    name: str,
    dist_name: str = "my-plugin",
    dist_version: str = "1.0.0",
    load_return: object | None = None,
    load_raises: Exception | None = None,
) -> MagicMock:
    """Create a mock entry point with the given properties."""
    ep = MagicMock()
    ep.name = name
    ep.dist = MagicMock()
    ep.dist.name = dist_name
    ep.dist.version = dist_version
    if load_raises is not None:
        ep.load.side_effect = load_raises
    elif load_return is not None:
        ep.load.return_value = load_return
    else:
        # Default: return a valid node class
        node_cls = type("FakeNode", (), {"process": lambda self: None})
        ep.load.return_value = node_cls
    return ep


class TestDiscoverExternalNodes:
    """Tests for discover_external_nodes."""

    @pytest.mark.unit
    def test_discover_returns_empty_when_no_plugins(self) -> None:
        with patch(_EP_MODULE, return_value=[]):
            result = discover_external_nodes()
        assert result == {}

    @pytest.mark.unit
    def test_discover_finds_valid_entry_point(self) -> None:
        node_cls = type("MyNode", (), {"process": lambda self: None})
        ep = _make_entry_point("my_node", load_return=node_cls)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert "my_node" in result
        node = result["my_node"]
        assert isinstance(node, DiscoveredNode)
        assert node.name == "my_node"
        assert node.node_class is node_cls
        assert node.package_name == "my-plugin"
        assert node.package_version == "1.0.0"

    @pytest.mark.unit
    def test_discover_skips_failing_entry_point(self) -> None:
        ep = _make_entry_point(
            "bad_node", load_raises=ImportError("missing dependency")
        )

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert result == {}

    @pytest.mark.unit
    def test_discover_warns_on_duplicate_names(self) -> None:
        node_cls_a = type("NodeA", (), {"process": lambda self: None})
        node_cls_b = type("NodeB", (), {"process": lambda self: None})
        ep_a = _make_entry_point(
            "dup_node", dist_name="plugin-a", load_return=node_cls_a
        )
        ep_b = _make_entry_point(
            "dup_node", dist_name="plugin-b", load_return=node_cls_b
        )

        with patch(_EP_MODULE, return_value=[ep_a, ep_b]):
            result = discover_external_nodes()

        # Should keep first registered
        assert len(result) == 1
        assert result["dup_node"].package_name == "plugin-a"
        assert result["dup_node"].node_class is node_cls_a

    @pytest.mark.unit
    def test_discover_strict_raises_on_duplicate(self) -> None:
        node_cls_a = type("NodeA", (), {"process": lambda self: None})
        node_cls_b = type("NodeB", (), {"process": lambda self: None})
        ep_a = _make_entry_point(
            "dup_node", dist_name="plugin-a", load_return=node_cls_a
        )
        ep_b = _make_entry_point(
            "dup_node", dist_name="plugin-b", load_return=node_cls_b
        )

        with patch(_EP_MODULE, return_value=[ep_a, ep_b]):
            with pytest.raises(NodeDiscoveryError, match="Duplicate entry-point name"):
                discover_external_nodes(strict=True)

    @pytest.mark.unit
    def test_discover_rejects_non_class_entry_point(self) -> None:
        # A function is not a valid node class
        ep = _make_entry_point("func_node", load_return=lambda: None)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert result == {}

    @pytest.mark.unit
    def test_discover_accepts_contract_path_node(self) -> None:
        """A class with contract_path but no process method should be accepted."""
        node_cls = type("ContractNode", (), {"contract_path": "/some/path.yaml"})
        ep = _make_entry_point("contract_node", load_return=node_cls)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert "contract_node" in result

    @pytest.mark.unit
    def test_discover_accepts_onex_node_type_node(self) -> None:
        """A class with __onex_node_type__ but no process method should be accepted."""
        node_cls = type("TypedNode", (), {"__onex_node_type__": "compute"})
        ep = _make_entry_point("typed_node", load_return=node_cls)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert "typed_node" in result

    @pytest.mark.unit
    def test_discover_accepts_handle_node(self) -> None:
        """A class with a handle method (handler-based node) should be accepted."""
        node_cls = type("HandlerNode", (), {"handle": lambda self, msg: None})
        ep = _make_entry_point("handler_node", load_return=node_cls)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert "handler_node" in result
        assert result["handler_node"].node_class is node_cls

    @pytest.mark.unit
    def test_discover_rejects_class_without_process_handle_or_contract(self) -> None:
        """A plain class with no process/handle/contract_path/__onex_node_type__ is rejected."""
        node_cls = type("PlainClass", (), {})
        ep = _make_entry_point("plain_node", load_return=node_cls)

        with patch(_EP_MODULE, return_value=[ep]):
            result = discover_external_nodes()

        assert result == {}
