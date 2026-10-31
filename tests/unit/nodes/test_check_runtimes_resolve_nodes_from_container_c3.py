# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eight more check runtimes resolve their nodes from a container (OMN-21786).

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
    "node_no_env_fallbacks_check_compute.runtime_no_env_fallbacks_check",
    "node_no_direct_kafka_producer_check_compute.runtime_no_direct_kafka_producer_check",
    "node_markdown_links_check_compute.runtime_markdown_links_check",
    "node_integration_skips_check_compute.runtime_integration_skips_check",
    "node_ai_slop_check_compute.runtime_ai_slop_check",
    "node_topic_names_check_compute.runtime_topic_names_check",
    "node_spdx_headers_check_compute.runtime_spdx_headers_check",
    "node_required_context_producer_check_compute.runtime_required_context_producer_check",
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
