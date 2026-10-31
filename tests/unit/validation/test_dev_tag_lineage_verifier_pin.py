# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21676: the tags-not-releases invariant flags a released-package verifier pin.

Operator ruling 2026-10-31, extending the ruling of 2026-10-29T01:50:26Z: the gate installs its
verifier from an omnimarket dev-merge tag, so a caller that passes the receipt gate a verifier
version is the form this must not return in.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.checker_dev_tag_lineage import (
    check_verifier_version_pins,
    load_policy,
)
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage

pytestmark = pytest.mark.unit

_PINNED = """\
name: Repo Evidence Gate
on:
  pull_request_target:
    types: [opened]
jobs:
  repo-evidence:
    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@dev-20261031203936-91354974f1e3
    with:
      evidence-source: caller
      verifier-version: 0.4.320
"""
_TAGGED = _PINNED.replace(
    "verifier-version: 0.4.320", "verifier-tag: dev-20261031203936-91354974f1e3"
)
_REUSABLE = """\
name: receipt-gate
on:
  workflow_call:
    inputs:
      verifier-tag:
        type: string
        default: ""
      verifier-version:
        type: string
        default: "0.4.305"
jobs:
  dod-verify:
    runs-on: ubuntu-latest
    env:
      VERIFIER_VERSION: ${{ inputs.verifier-version }}
    steps:
      - run: echo ok
"""


def _contract():
    return ValidatorDevTagLineage().contract


def _rules(phase: str) -> tuple[str, ...]:
    return tuple(
        rule.rule_id
        for rule in _contract().rules
        if (rule.parameters or {})["phase"] == phase
    )


def test_a_caller_that_passes_a_verifier_version_is_flagged() -> None:
    issues = check_verifier_version_pins(Path("call.yml"), _PINNED, _contract())
    assert [issue.rule_name for issue in issues] == ["verifier_version_pin"]
    assert issues[0].line_number == 10
    assert "line 10" in issues[0].message
    assert "verifier-tag" in issues[0].suggestion


def test_a_caller_that_passes_a_dev_merge_tag_is_clean() -> None:
    assert not check_verifier_version_pins(Path("call.yml"), _TAGGED, _contract())


def test_the_reusable_that_only_declares_the_input_is_clean() -> None:
    assert not check_verifier_version_pins(Path("gate.yml"), _REUSABLE, _contract())


def test_every_pinning_line_is_flagged_in_line_order() -> None:
    text = (
        _PINNED
        + "  another-caller:\n"
        + "    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml@dev-20261031203936-91354974f1e3\n"
        + "    with:\n"
        + "      verifier-version: '0.4.303'\n"
    )
    issues = check_verifier_version_pins(Path("call.yml"), text, _contract())
    assert [issue.line_number for issue in issues] == [10, 14]


@pytest.mark.parametrize(
    "line",
    [
        "      verifier-version: 0.4.320",
        '      verifier-version: "0.4.320"',
        "      verifier-version: '0.4.320'  # pinned",
        '      "verifier-version": 0.4.320',
        "      'verifier-version': 0.4.320",
        "verifier-version: 1",
    ],
)
def test_every_form_of_a_valued_pin_is_flagged(line: str) -> None:
    assert [
        issue.rule_name
        for issue in check_verifier_version_pins(
            Path("call.yml"), f"jobs:\n  a:\n    with:\n{line}\n", _contract()
        )
    ] == ["verifier_version_pin"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name: x\non: push\n",
        "# verifier-version: 0.4.320\n",
        "      # verifier-version: 0.4.320\n",
        "env:\n  VERIFIER_VERSION: ${{ inputs.verifier-version }}\n",
        "inputs:\n  verifier-version:\n    type: string\n",
        "      verifier-versions: 1\n",
        "      verifier-version:  # nothing\n",
    ],
)
def test_declarations_comments_and_reads_are_not_pins(text: str) -> None:
    assert not check_verifier_version_pins(Path("w.yml"), text, _contract())


def test_the_pin_pattern_is_rule_data() -> None:
    contract = _contract()
    row = next(
        rule for rule in contract.rules if rule.rule_id == "verifier_version_pin"
    )
    parameters = dict(row.parameters or {})
    parameters["pin_pattern"] = r"^\s*verifier-tag\s*:\s*[^\s#]"
    changed = contract.model_copy(
        update={
            "rules": [
                item.model_copy(update={"parameters": parameters})
                if item.rule_id == row.rule_id
                else item
                for item in contract.rules
            ]
        }
    )
    assert not check_verifier_version_pins(Path("call.yml"), _PINNED, changed)
    flagged = check_verifier_version_pins(Path("call.yml"), _TAGGED, changed)
    assert [issue.rule_name for issue in flagged] == ["verifier_version_pin"]


def test_the_contract_must_carry_the_rule_row() -> None:
    contract = _contract()
    without = contract.model_copy(
        update={
            "rules": [
                rule
                for rule in contract.rules
                if rule.rule_id != "verifier_version_pin"
            ]
        }
    )
    with pytest.raises(Exception, match="dev_tag_lineage"):
        load_policy(without)


def test_the_rule_is_an_enabled_blocking_invariant() -> None:
    assert "verifier_version_pin" in _rules("invariant")
    assert "verifier_version_pin" not in _rules("identity")


def test_a_directory_scan_finds_the_pinned_caller_under_github_workflows(
    tmp_path: Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "call-repo-evidence-gate.yml").write_text(_PINNED)
    (workflows / "receipt-gate.yml").write_text(_REUSABLE)
    (workflows / "other.yaml").write_text(_TAGGED)
    result = ValidatorDevTagLineage(root=tmp_path, rules=_rules("invariant")).validate(
        [tmp_path]
    )
    assert [issue.rule_name for issue in result.issues] == ["verifier_version_pin"]
    assert str(result.issues[0].file_path).endswith("call-repo-evidence-gate.yml")


def test_a_named_workflow_file_is_judged_and_needs_no_resolver(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    caller = workflows / "call.yml"
    caller.write_text(_PINNED)
    result = ValidatorDevTagLineage(root=tmp_path).validate_file(caller)
    assert [issue.rule_name for issue in result.issues] == ["verifier_version_pin"]


def test_identity_only_selection_leaves_a_workflow_alone(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    caller = workflows / "call.yml"
    caller.write_text(_PINNED)
    result = ValidatorDevTagLineage(
        root=tmp_path, rules=_rules("identity")
    ).validate_file(caller)
    assert result.is_valid


def test_a_workflow_under_tests_is_excluded(tmp_path: Path) -> None:
    fixture = tmp_path / "tests" / ".github" / "workflows"
    fixture.mkdir(parents=True)
    (fixture / "call.yml").write_text(_PINNED)
    result = ValidatorDevTagLineage(root=tmp_path, rules=_rules("invariant")).validate(
        [tmp_path]
    )
    assert result.is_valid
