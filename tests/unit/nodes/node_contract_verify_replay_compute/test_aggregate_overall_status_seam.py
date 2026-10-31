# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The verify-replay node delegates its verdict to the public rule (OMN-21505).

Covers the source seam (the handler calls ``aggregate_overall_status`` and no
longer carries the rule's body) and the binding check: the same statuses give
the same verdict in a direct call and through the node's in-process handler.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path

import pytest

from omnibase_core.enums.enum_check_status import EnumCheckStatus
from omnibase_core.enums.enum_overall_status import (
    EnumOverallStatus,
    aggregate_overall_status,
)
from omnibase_core.enums.enum_verify_tier import EnumVerifyTier
from omnibase_core.models.contract_verify_replay.model_verify_check_result import (
    ModelVerifyCheckResult,
)
from omnibase_core.models.contract_verify_replay.model_verify_replay_input import (
    ModelVerifyReplayInput,
)
from omnibase_core.nodes.node_contract_verify_replay_compute import (
    handler as handler_module,
)
from omnibase_core.nodes.node_contract_verify_replay_compute.handler import (
    NodeContractVerifyReplayCompute,
)

pytestmark = pytest.mark.unit

_ALL_STATUSES = (EnumCheckStatus.PASS, EnumCheckStatus.FAIL, EnumCheckStatus.SKIP)
_COMBINATIONS = [
    combo
    for size in (1, 2, 3)
    for combo in itertools.product(_ALL_STATUSES, repeat=size)
]


def _handler_tree() -> ast.Module:
    return ast.parse(Path(handler_module.__file__ or "").read_text())


def test_handler_calls_the_public_function() -> None:
    """AC2: the handler calls ``aggregate_overall_status``."""
    called = {
        node.func.id
        for node in ast.walk(_handler_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "aggregate_overall_status" in called


def test_handler_no_longer_carries_the_rule_body() -> None:
    """AC2: no private copy of the rule, and no FAIL/SKIP/PASS verdict logic."""
    tree = _handler_tree()
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "_aggregate_overall_status" not in defined
    returned_overall = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "EnumOverallStatus"
    ]
    assert returned_overall == []


@pytest.mark.parametrize(
    "combo",
    _COMBINATIONS,
    ids=lambda combo: "+".join(s.value for s in combo),
)
def test_direct_call_and_node_handler_give_the_same_verdict(
    combo: tuple[EnumCheckStatus, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC4: the same statuses give the same verdict direct and through the node."""
    checks = [
        ModelVerifyCheckResult(check_name=f"check_{i}", status=status)
        for i, status in enumerate(combo)
    ]
    node = NodeContractVerifyReplayCompute()
    monkeypatch.setattr(node, "_tier2_result", lambda _manifest: checks[0])
    monkeypatch.setattr(
        node, "_run_tier1_checks", lambda **_kwargs: list(checks), raising=True
    )
    bundle = _bundle_bytes()

    report = node.handle(
        ModelVerifyReplayInput(package_bytes=bundle, tier=EnumVerifyTier.TIER1_STATIC)
    )

    assert report.overall_status == aggregate_overall_status(combo)
    assert isinstance(report.overall_status, EnumOverallStatus)


def _bundle_bytes() -> bytes:
    from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
    from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
    from omnibase_core.models.contracts.model_profile_reference import (
        ModelProfileReference,
    )
    from omnibase_core.package.service_oncp_builder import OncpBuilder

    builder = OncpBuilder(
        package_id="omninode.test.pkg",
        package_version="1.0.0",
        base_profile_ref="compute_pure",
        base_profile_version="1.0.0",
    )
    builder.add_overlay(
        ModelContractPatch(
            extends=ModelProfileReference(profile="compute_pure", version="1.0.0")
        ),
        scope=EnumOverlayScope.PROJECT,
        overlay_id="base-patch",
    )
    bundle_bytes, _manifest = builder.build_bytes()
    return bundle_bytes
