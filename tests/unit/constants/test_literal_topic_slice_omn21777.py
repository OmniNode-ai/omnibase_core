# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""TopicBase members of the OMN-21777 slice come from packaged YAML, not from Python source."""

import importlib
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from ruamel.yaml import YAML

from omnibase_core.topics import TopicBase
from omnibase_core.validation.validator_contracts_and_di import ValidatorContractsAndDi

topics = importlib.import_module("omnibase_core.topics")

_TOPIC_BASE = Path(topics.__file__).parent / "topic_base_names.yaml"
_SLICE_SIZE = 32
_TOPIC_BASE_FINDINGS_AT_MERGE_BASE = 158


def _declared() -> dict[str, str]:
    with _TOPIC_BASE.open(encoding="utf-8") as handle:
        document = TypeAdapter(dict[str, dict[str, str]]).validate_python(
            YAML(typ="safe").load(handle)
        )
    return document["topics"]


def _literal_topic_values() -> set[str]:
    result = ValidatorContractsAndDi().validate_file(Path(str(topics.__file__)))
    return {i.message.split("'")[1] for i in result.issues if i.code == "literal_topic"}


@pytest.mark.unit
class TestTopicBaseSliceContract:
    def test_members_equal_their_contract_entries(self) -> None:
        declared = _declared()
        assert len(declared) == _SLICE_SIZE
        assert {name: TopicBase[name].value for name in declared} == declared

    def test_wire_values_are_unchanged(self) -> None:
        assert TopicBase.SESSION_STARTED == "onex.evt.omniclaude.session-started.v1"
        assert (
            TopicBase.PROJECTION_COST_TOKEN_USAGE
            == "onex.snapshot.projection.cost.token_usage.v1"
        )
        assert (
            TopicBase.AUDIT_CONTEXT_BUDGET_EXCEEDED
            == "onex.evt.omniclaude.audit-context-budget-exceeded.v1"
        )

    def test_source_holds_none_of_the_slice_literals(self) -> None:
        flagged = _literal_topic_values()
        assert flagged.isdisjoint(_declared().values())
        assert len(flagged) == _TOPIC_BASE_FINDINGS_AT_MERGE_BASE - _SLICE_SIZE
