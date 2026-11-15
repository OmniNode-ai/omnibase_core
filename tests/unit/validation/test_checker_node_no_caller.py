# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the ``node_no_caller`` rule in the generic validator format (OMN-24538, class iv: built and never called).

A node whose name no file outside its own directory mentions, whose subscribed topics no other node
publishes and that no command topic feeds is finished work nobody can reach (a node nothing dispatches).
The red rows are small repositories written to a temporary directory with such a node; the control rows
give the same node a publisher, a reference from another directory, or a command topic, which the rule
admits. The checker is pure (the repository index comes from a callable); the validator scans the tree
once for the contracts and the names files mention, and holds each contract to its entry in a per-file
shrink-only baseline. A contract that does not parse is a finding and a file it cannot read raises, so an
unread input never leaves the index short. These tests load ``node_no_caller.validation.yaml``, so the
values that gate the repository are the values under test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_node_no_caller import (
    RULE_NODE_NO_CALLER,
    check_node_no_caller,
    read_node_facts,
)
from omnibase_core.validation.validator_node_no_caller import ValidatorNodeNoCaller

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/node_no_caller.validation.yaml"
)
_NODE = "src/pkg/nodes/node_orphan/contract.yaml"
_ORPHAN = (
    "name: node_orphan\n"
    "event_bus:\n"
    "  subscribe_topics:\n"
    "    - onex.evt.pkg.thing-ready.v1\n"
)
_PUBLISHER = (
    "name: node_producer\n"
    "event_bus:\n"
    "  publish_topics:\n"
    "    - onex.evt.pkg.thing-ready.v1\n"
)
_COMMAND_FED = (
    "name: node_orphan\n"
    "event_bus:\n"
    "  subscribe_topics:\n"
    "    - onex.cmd.pkg.do-thing.v1\n"
)


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules() -> dict[str, ModelValidatorRule]:
    return {r.rule_id: r for r in _contract().rules}


def _mutated(key: str, value: object) -> dict[str, ModelValidatorRule]:
    rules = _rules()
    row = rules[RULE_NODE_NO_CALLER]
    rules[RULE_NODE_NO_CALLER] = row.model_copy(
        update={"parameters": {**(row.parameters or {}), key: value}}
    )
    return rules


_Index = tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]


def _empty_index() -> _Index:
    return ({}, {})


def _lines(
    source: str,
    index: _Index | None = None,
    rules: dict[str, ModelValidatorRule] | None = None,
) -> list[int]:
    issues = check_node_no_caller(
        Path(_NODE), source, lambda: index or _empty_index(), rules or _rules()
    )
    return [i.line_number or 0 for i in issues]


# --- the contract ---


def test_node_no_caller_the_contract_loads(tmp_path: Path) -> None:
    contract = _contract()
    assert contract.validator_id == RULE_NODE_NO_CALLER
    assert {r.rule_id for r in contract.rules} == {
        RULE_NODE_NO_CALLER,
        "baseline_ratchet",
    }
    assert contract.target_patterns == ["**/contract.yaml"]
    assert ValidatorNodeNoCaller(root=tmp_path, baseline={})


# --- the checker ---


def test_node_no_caller_refuses_a_node_nothing_references_publishes_to_or_feeds() -> (
    None
):
    assert _lines(_ORPHAN) == [1]


def test_node_no_caller_a_publisher_of_its_topic_is_a_caller() -> None:
    index = (
        {"onex.evt.pkg.thing-ready.v1": frozenset({"src/pkg/nodes/node_producer"})},
        {},
    )
    assert _lines(_ORPHAN, index) == []


def test_node_no_caller_its_own_publication_is_not_a_caller() -> None:
    index = (
        {"onex.evt.pkg.thing-ready.v1": frozenset({"src/pkg/nodes/node_orphan"})},
        {},
    )
    assert _lines(_ORPHAN, index) == [1]


def test_node_no_caller_a_reference_from_another_directory_is_a_caller() -> None:
    index = ({}, {"node_orphan": frozenset({"src/pkg/wiring.py"})})
    assert _lines(_ORPHAN, index) == []


def test_node_no_caller_a_reference_inside_its_own_directory_is_not_a_caller() -> None:
    index = (
        {},
        {"node_orphan": frozenset({"src/pkg/nodes/node_orphan/handler.py"})},
    )
    assert _lines(_ORPHAN, index) == [1]


def test_node_no_caller_a_reference_by_directory_name_is_a_caller() -> None:
    source = _ORPHAN.replace("node_orphan", "orphan")
    index = ({}, {"node_orphan": frozenset({"src/pkg/wiring.py"})})
    assert _lines(source, index) == []


def test_node_no_caller_a_command_topic_is_fed_from_outside() -> None:
    assert _lines(_COMMAND_FED) == []


def test_node_no_caller_the_annotated_name_line_is_admitted() -> None:
    assert (
        _lines(
            _ORPHAN.replace(
                "name: node_orphan",
                "name: node_orphan  # " + "failopen" + "-ok: wired next",
            )
        )
        == []
    )


def test_node_no_caller_an_unparseable_contract_is_a_finding_never_clean() -> None:
    assert _lines("name: [unclosed\n") == [1]
    assert _lines("- just\n- a list\n") == [1]


def test_node_no_caller_the_index_is_not_built_for_an_unparseable_contract() -> None:
    def explode() -> _Index:
        raise AssertionError("index built")

    issues = check_node_no_caller(Path(_NODE), "name: [unclosed\n", explode, _rules())
    assert len(issues) == 1


def test_node_no_caller_reads_the_name_and_topics_of_a_contract() -> None:
    facts = read_node_facts(Path(_NODE), _PUBLISHER, _rules())
    assert facts == (
        "node_producer",
        (),
        ("onex.evt.pkg.thing-ready.v1",),
    )
    assert read_node_facts(Path(_NODE), "event_bus: {}\n", _rules()) == (
        "node_orphan",
        (),
        (),
    )


def test_node_no_caller_message_carries_the_reason_the_node_and_remediation() -> None:
    params = _rules()[RULE_NODE_NO_CALLER].parameters or {}
    issues = check_node_no_caller(Path(_NODE), _ORPHAN, _empty_index, _rules())
    message = issues[0].message
    assert str(params["reason"]) in message and "node_orphan" in message
    assert str(params["remediation"]) in message


def test_node_no_caller_disabled_row_is_not_run() -> None:
    rules = _rules()
    rules[RULE_NODE_NO_CALLER] = rules[RULE_NODE_NO_CALLER].model_copy(
        update={"enabled": False}
    )
    assert _lines(_ORPHAN, rules=rules) == []


_PARAMETER_KEYS = [
    "contract_file",
    "name_keys",
    "events_key",
    "subscribe_key",
    "publish_key",
    "external_feed_pattern",
    "scanned_extensions",
    "excluded_dir_names",
    "catalog_file_node_threshold",
    "name_token_patterns",
    "name_token_strip",
    "comment_prefix",
    "annotation_marker",
    "reason",
    "remediation",
]


def test_node_no_caller_every_parameter_key_is_exercised_by_the_table() -> None:
    assert set(_rules()[RULE_NODE_NO_CALLER].parameters or {}) == set(_PARAMETER_KEYS)


@pytest.mark.parametrize("key", _PARAMETER_KEYS)
def test_node_no_caller_a_missing_parameter_fails_the_load(key: str) -> None:
    row = _rules()[RULE_NODE_NO_CALLER]
    stripped = {k: v for k, v in (row.parameters or {}).items() if k != key}
    rules = _rules()
    rules[RULE_NODE_NO_CALLER] = row.model_copy(update={"parameters": stripped})
    with pytest.raises(ModelOnexError):
        check_node_no_caller(Path(_NODE), "", _empty_index, rules)


def test_node_no_caller_mutating_the_external_feed_pattern_changes_the_verdict() -> (
    None
):
    assert _lines(_COMMAND_FED) == []
    assert _lines(_COMMAND_FED, rules=_mutated("external_feed_pattern", "^zzz")) == [1]


def test_node_no_caller_mutating_the_name_keys_changes_the_name_read() -> None:
    facts = read_node_facts(Path(_NODE), _ORPHAN, _mutated("name_keys", ["zzz"]))
    # falls back to the directory name
    assert facts == ("node_orphan", ("onex.evt.pkg.thing-ready.v1",), ())


# --- the validator: it scans the tree once and holds each contract to its baseline entry ---


def _tree(tmp_path: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _validator(tmp_path: Path, baseline: dict[str, int]) -> ValidatorNodeNoCaller:
    return ValidatorNodeNoCaller(
        root=tmp_path, baseline=baseline, baseline_path="baseline.txt"
    )


def test_node_no_caller_validator_refuses_a_node_nothing_calls(tmp_path: Path) -> None:
    _tree(tmp_path, {_NODE: _ORPHAN, "src/pkg/other.py": "x = 1\n"})
    result = _validator(tmp_path, {}).validate([tmp_path / _NODE])
    assert not result.is_valid
    assert [i.line_number for i in result.issues] == [1]


def test_node_no_caller_validator_control_a_file_in_another_directory_names_it(
    tmp_path: Path,
) -> None:
    _tree(
        tmp_path,
        {_NODE: _ORPHAN, "src/pkg/wiring.py": "from pkg.nodes import node_orphan\n"},
    )
    assert _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_control_another_node_publishes_its_topic(
    tmp_path: Path,
) -> None:
    _tree(
        tmp_path,
        {_NODE: _ORPHAN, "src/pkg/nodes/node_producer/contract.yaml": _PUBLISHER},
    )
    assert _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_a_dotted_name_is_found_in_a_module_path(
    tmp_path: Path,
) -> None:
    source = _ORPHAN.replace("node_orphan", "pkg.orphan.node")
    _tree(tmp_path, {_NODE: source, "src/pkg/wiring.py": "import pkg.orphan.node\n"})
    assert _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_a_catalog_file_is_never_a_caller(
    tmp_path: Path,
) -> None:
    others = {
        f"src/pkg/nodes/node_n{i}/contract.yaml": f"name: node_n{i}\n"
        for i in range(30)
    }
    catalog = "\n".join(f"node_n{i}" for i in range(30)) + "\nnode_orphan\n"
    _tree(tmp_path, {_NODE: _ORPHAN, **others, "pyproject.toml": catalog})
    assert not _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid
    _tree(tmp_path, {"pyproject.toml": "node_orphan\nnode_n1\n"})
    assert _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_a_fixture_directory_is_not_scanned(
    tmp_path: Path,
) -> None:
    _tree(tmp_path, {_NODE: _ORPHAN, "tests/fixtures/wiring.py": "node_orphan\n"})
    assert not _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_an_unparseable_contract_elsewhere_raises(
    tmp_path: Path,
) -> None:
    _tree(
        tmp_path,
        {
            _NODE: _ORPHAN,
            "src/pkg/nodes/node_broken/contract.yaml": "name: [unclosed\n",
        },
    )
    with pytest.raises(ModelOnexError) as excinfo:
        _validator(tmp_path, {}).validate([tmp_path / _NODE])
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 file")
def test_node_no_caller_validator_a_file_that_cannot_be_read_raises(
    tmp_path: Path,
) -> None:
    _tree(tmp_path, {_NODE: _ORPHAN, "src/pkg/wiring.py": "node_orphan\n"})
    unreadable = tmp_path / "src/pkg/wiring.py"
    unreadable.chmod(0o000)
    try:
        with pytest.raises(ModelOnexError) as excinfo:
            _validator(tmp_path, {}).validate([tmp_path / _NODE])
    finally:
        unreadable.chmod(0o644)
    assert excinfo.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


def test_node_no_caller_validator_admits_a_baselined_node_and_refuses_a_new_one(
    tmp_path: Path,
) -> None:
    second = "src/pkg/nodes/node_second/contract.yaml"
    _tree(
        tmp_path,
        {_NODE: _ORPHAN, second: _ORPHAN.replace("node_orphan", "node_second")},
    )
    baseline = {_NODE: 1}
    assert _validator(tmp_path, baseline).validate([tmp_path / _NODE]).is_valid
    assert not _validator(tmp_path, baseline).validate([tmp_path / second]).is_valid


def test_node_no_caller_validator_the_ratchet_directory_is_not_scanned(
    tmp_path: Path,
) -> None:
    """The baseline names the baselined node by path; that must not make it a called node."""
    _tree(
        tmp_path,
        {_NODE: _ORPHAN, ".onex_ratchets/node_no_caller_ratchet.yaml": f"{_NODE}: 1\n"},
    )
    assert not _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid


def test_node_no_caller_validator_a_ticket_contract_naming_the_node_is_not_a_caller(
    tmp_path: Path,
) -> None:
    """A ticket's evidence file names the node it checks; that must not make the node called."""
    _tree(tmp_path, {_NODE: _ORPHAN, "contracts/OMN-1.yaml": "check: node_orphan\n"})
    assert not _validator(tmp_path, {}).validate([tmp_path / _NODE]).is_valid
