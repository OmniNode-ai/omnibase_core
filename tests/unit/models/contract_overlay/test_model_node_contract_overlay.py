# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-22469: a node's contract overlay, read through one registered resolver and merged over its contract.

Failure modes, one case or more each:
  (1) no resolver installed, or two, lets a caller fall back to the packaged contract silently
  (2) a resolver that answers the wrong type, or has no resolve method, is trusted
  (3) the merge puts the packaged value over the overlay's
  (4) a nested mapping in the overlay replaces the whole packaged mapping instead of merging into it
  (5) merging mutates the packaged contract the caller still holds
  (6) a node with no overlay changes the contract
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from omnibase_core.models.contract_overlay import model_node_contract_overlay as module
from omnibase_core.models.contract_overlay.model_node_contract_overlay import (
    NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP,
    ModelNodeContractOverlay,
)
from omnibase_core.models.contract_overlay.model_node_contract_overlay_resolution_error import (
    ModelNodeContractOverlayResolutionError,
)


class _EntryPoint:
    def __init__(self, name: str, target: object) -> None:
        self.name = name
        self.value = f"fixture:{name}"
        self._target = target

    def load(self) -> object:
        return self._target


class _Resolver:
    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.asked: list[str] = []

    def resolve_contract_overlay(self, node_id: str) -> object:
        self.asked.append(node_id)
        return self.answer


def _install(monkeypatch: pytest.MonkeyPatch, *targets: object) -> None:
    points = [_EntryPoint(f"p{i}", t) for i, t in enumerate(targets)]

    def fake_entry_points(*, group: str) -> list[_EntryPoint]:
        assert group == NODE_CONTRACT_OVERLAY_RESOLVER_ENTRY_POINT_GROUP
        return points

    monkeypatch.setattr(module, "entry_points", fake_entry_points)


def _overlay(contract: dict[str, Any]) -> ModelNodeContractOverlay:
    return ModelNodeContractOverlay(
        node_id="node_x",
        overlay_path=Path("/cfg/node_x/overlay.yaml"),
        contract=contract,
    )


def test_no_resolver_installed_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch)
    with pytest.raises(
        ModelNodeContractOverlayResolutionError,
        match="no node contract overlay resolver",
    ):
        ModelNodeContractOverlay.for_node("node_x")


def test_two_resolvers_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _Resolver(_overlay({})), _Resolver(_overlay({})))
    with pytest.raises(ModelNodeContractOverlayResolutionError, match="more than one"):
        ModelNodeContractOverlay.for_node("node_x")


def test_resolver_without_method_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, object())
    with pytest.raises(
        ModelNodeContractOverlayResolutionError, match="does not provide"
    ):
        ModelNodeContractOverlay.for_node("node_x")


def test_resolver_answering_wrong_type_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _Resolver({"contract": {}}))
    with pytest.raises(ModelNodeContractOverlayResolutionError, match="answered dict"):
        ModelNodeContractOverlay.for_node("node_x")


def test_for_node_returns_the_resolver_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = _Resolver(_overlay({"switch": True}))
    _install(monkeypatch, resolver)
    assert ModelNodeContractOverlay.for_node("node_x").contract == {"switch": True}
    assert resolver.asked == ["node_x"]


def test_overlay_key_wins_over_packaged() -> None:
    packaged = {"switch": False, "name": "node_x"}
    assert _overlay({"switch": True}).merged_into(packaged) == {
        "switch": True,
        "name": "node_x",
    }


def test_nested_mappings_merge_instead_of_replacing() -> None:
    packaged = {"writer": {"table": "t", "stamp_uuid": False}}
    merged = _overlay({"writer": {"stamp_uuid": True}}).merged_into(packaged)
    assert merged == {"writer": {"table": "t", "stamp_uuid": True}}


def test_merge_leaves_the_packaged_contract_unchanged() -> None:
    packaged = {"writer": {"stamp_uuid": False}}
    _overlay({"writer": {"stamp_uuid": True}}).merged_into(packaged)
    assert packaged == {"writer": {"stamp_uuid": False}}


def test_node_with_no_overlay_keeps_the_contract() -> None:
    packaged = {"writer": {"stamp_uuid": False}}
    absent = ModelNodeContractOverlay(node_id="node_x", overlay_path=None, contract={})
    assert absent.merged_into(packaged) == packaged
