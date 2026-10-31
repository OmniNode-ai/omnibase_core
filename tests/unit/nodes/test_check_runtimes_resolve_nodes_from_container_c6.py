# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Five more check runtimes resolve their nodes from a container (OMN-21726).

Each runtime binds its effects and COMPUTE node in one container and resolves every node it
calls from there. The contracts_and_di ``handler_hand_construction`` rule judges the runtime
sources, and each container hands out the nodes it registered.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from omnibase_core.models.validation.model_contracts_and_di_facts import (
    ModelContractsAndDiFacts,
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
_ROOT = Path(__file__).resolve().parents[3]
_RUNTIMES = (
    "node_hardcoded_topic_check_compute.runtime_hardcoded_topic_check",
    "node_local_paths_check_compute.runtime_local_paths_check",
    "node_no_untyped_metadata_check_compute.runtime_no_untyped_metadata_check",
    "node_precommit_interpreter_check_compute.runtime_precommit_interpreter_check",
    "node_private_ip_check_compute.runtime_private_ip_check",
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
    assert _findings(relative, (_ROOT / relative).read_text(encoding="utf-8")) == []


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
    writer = container.get_service(NodeValidationReportWriteEffect)
    assert isinstance(writer, NodeValidationReportWriteEffect)
    assert container.get_service(NodeValidationReportWriteEffect) is writer
