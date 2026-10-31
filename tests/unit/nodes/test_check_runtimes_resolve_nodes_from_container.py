# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Seven check runtimes resolve their nodes from a container instead of building them (OMN-21744).

Each runtime binds its effects and COMPUTE node in one container and resolves every node it
calls from there. The contracts_and_di ``handler_hand_construction`` rule judges the runtime
sources, and each container hands out the node it registered.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_contracts_and_di_facts import (
    ModelContractsAndDiFacts,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.validation.checker_contracts_and_di import check_contracts_and_di
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

pytestmark = pytest.mark.unit

_RULE = "handler_hand_construction"
_FACTS = ModelContractsAndDiFacts(
    repository="omnibase_core",
    tag_source_repositories=frozenset(),
    advanced_sites=frozenset(),
)
_NODES = Path(__file__).resolve().parents[3] / "src/omnibase_core/nodes"
_RUNTIMES = (
    "node_test_root_collection_check_compute.runtime_test_root_collection_check",
    "node_skip_count_ratchet_check_compute.runtime_skip_count_ratchet_check",
    "node_exposed_identifiers_check_compute.runtime_exposed_identifiers_check",
    "node_no_utcnow_check_compute.runtime_no_utcnow_check",
    "node_no_raw_sqlite3_check_compute.runtime_no_raw_sqlite3_check",
    "node_no_io_outside_effects_check_compute.runtime_no_io_outside_effects_check",
    "node_no_hardcoded_ip_check_compute.runtime_no_hardcoded_ip_check",
)


def _findings(relative: Path, text: str) -> list[str]:
    rules = list(ValidatorContractsAndDi().contract.rules)
    return [
        issue.message
        for issue in check_contracts_and_di(relative, text, rules, _FACTS)
        if issue.rule_name == _RULE
    ]


@pytest.mark.parametrize("module", _RUNTIMES)
def test_runtime_source_draws_no_hand_construction_finding(module: str) -> None:
    relative = Path("src/omnibase_core/nodes", *module.split(".")).with_suffix(".py")
    source = (_NODES.parent.parent.parent / relative).read_text(encoding="utf-8")
    assert _findings(relative, source) == []


def test_hand_construction_is_still_refused() -> None:
    """Positive control: the rule fires on the construction the runtimes used to make."""
    findings = _findings(
        Path("src/omnibase_core/nodes/node_x_check_compute/runtime_x.py"),
        "def run():\n    return NodeSourceFileGatherEffect().handle(None)\n",
    )
    assert len(findings) == 1


@pytest.mark.parametrize("module", _RUNTIMES)
def test_runtime_container_hands_out_its_bound_nodes(module: str) -> None:
    runtime = importlib.import_module(f"omnibase_core.nodes.{module}")
    container = runtime._container()
    assert runtime._container() is container
    gather = container.get_service(NodeSourceFileGatherEffect)
    assert isinstance(gather, NodeSourceFileGatherEffect)
    assert container.get_service(NodeSourceFileGatherEffect) is gather
    writer = container.get_service(NodeValidationReportWriteEffect)
    assert isinstance(writer, NodeValidationReportWriteEffect)
