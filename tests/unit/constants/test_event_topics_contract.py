# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The core event topics are declared in packaged YAML, not in Python (OMN-21623)."""

from pathlib import Path
from types import ModuleType

import pytest
from pydantic import TypeAdapter
from ruamel.yaml import YAML

from omnibase_core.constants import constants_event_types
from omnibase_core.event_bus.testing import topic_constants
from omnibase_core.validation.validator_contracts_and_di import ValidatorContractsAndDi

_EVENT_TOPICS = Path(constants_event_types.__file__).parent / "event_topics.yaml"
_SUBSTRATE_TOPICS = Path(topic_constants.__file__).parent / "substrate_test_topics.yaml"

# (module, constant name) -> (contract file, contract key)
_BOUND: dict[tuple[ModuleType, str], tuple[Path, str]] = {
    (constants_event_types, f"TOPIC_{key.upper()}"): (_EVENT_TOPICS, key)
    for key in (
        "github_pr_status_event",
        "git_hook_event",
        "linear_snapshot_event",
        "episode_boundary",
        "validation_run_completed_event",
        "validation_run_started_event",
        "validation_violations_batch_event",
        "validation_no_faked_boundary_scan_requested_cmd",
        "validation_no_faked_boundary_scan_completed_event",
        "validation_todo_marker_scan_requested_cmd",
        "validation_todo_marker_scan_completed_event",
        "validation_localhost_url_scan_requested_cmd",
        "validation_localhost_url_scan_completed_event",
        "validation_pin_hygiene_scan_requested_cmd",
        "validation_pin_hygiene_scan_completed_event",
        "validation_doc_content_scan_requested_cmd",
        "validation_doc_content_scan_completed_event",
    )
} | {
    (topic_constants, "SEAM_TEST_TOPIC"): (_SUBSTRATE_TOPICS, "seam_test"),
    (topic_constants, "FIDELITY_JOIN_LEAVE_TOPIC"): (
        _SUBSTRATE_TOPICS,
        "fidelity_join_leave",
    ),
    (topic_constants, "FIDELITY_EARLIEST_TOPIC"): (
        _SUBSTRATE_TOPICS,
        "fidelity_earliest",
    ),
    (topic_constants, "FIDELITY_LATEST_TOPIC"): (_SUBSTRATE_TOPICS, "fidelity_latest"),
    (topic_constants, "FIDELITY_REJOIN_TOPIC"): (_SUBSTRATE_TOPICS, "fidelity_rejoin"),
    (topic_constants, "FIDELITY_REBALANCE_TOPIC"): (
        _SUBSTRATE_TOPICS,
        "fidelity_rebalance",
    ),
}

_REMOVED_UNUSED = (
    "TOPIC_CLI_RUN_NODE_CMD",
    "TOPIC_CLI_RUN_NODE_RESPONSE",
    "TOPIC_VALIDATION_LOCAL_PATH_SCAN_REQUESTED_CMD",
    "TOPIC_VALIDATION_LOCAL_PATH_SCAN_COMPLETED_EVENT",
    "TOPIC_VALIDATION_PRIVATE_IP_SCAN_REQUESTED_CMD",
    "TOPIC_VALIDATION_PRIVATE_IP_SCAN_COMPLETED_EVENT",
    "TOPIC_VALIDATION_HARDCODED_TOPIC_SCAN_REQUESTED_CMD",
    "TOPIC_VALIDATION_HARDCODED_TOPIC_SCAN_COMPLETED_EVENT",
)


def _declared(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as handle:
        document = TypeAdapter(dict[str, dict[str, str]]).validate_python(
            YAML(typ="safe").load(handle)
        )
    return document["topics"]


@pytest.mark.unit
class TestEventTopicsContract:
    @pytest.mark.parametrize("path", [_EVENT_TOPICS, _SUBSTRATE_TOPICS])
    def test_every_contract_entry_is_bound_to_a_constant(self, path: Path) -> None:
        bound = {key for _, (file, key) in _BOUND.items() if file == path}
        assert bound == set(_declared(path))

    @pytest.mark.parametrize(("module", "name"), list(_BOUND))
    def test_constant_equals_its_contract_entry(
        self, module: ModuleType, name: str
    ) -> None:
        path, key = _BOUND[(module, name)]
        assert getattr(module, name) == _declared(path)[key]

    def test_wire_value_is_unchanged(self) -> None:
        assert (
            constants_event_types.TOPIC_GIT_HOOK_EVENT
            == "onex.evt.platform.git-hook.v1"
        )
        assert (
            topic_constants.SEAM_TEST_TOPIC
            == "onex.evt.omnibase-infra.event-bus-substrate-seam-test.v1"
        )

    @pytest.mark.parametrize("name", _REMOVED_UNUSED)
    def test_unused_topic_constant_is_gone(self, name: str) -> None:
        assert not hasattr(constants_event_types, name)

    @pytest.mark.parametrize("module", [constants_event_types, topic_constants])
    def test_source_holds_no_literal_topic_finding(self, module: ModuleType) -> None:
        result = ValidatorContractsAndDi().validate_file(Path(str(module.__file__)))
        assert [i.message for i in result.issues if i.code == "literal_topic"] == []
