# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerDiagramDrift: the merged check's verdicts on the merged task's fixtures (OMN-21510, T-G1b).

The cases are those of the omnimarket ``test_check_document_diagrams`` module, run against the core
checker with the fixture renderer; the rule-table cases remove or change a contract entry and assert
the verdict of the fixture that entry catches changes.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from omnibase_core.handlers.handler_diagram_drift import HandlerDiagramDrift
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_report import (
    ModelDiagramDriftReport,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_rules import (
    ModelDiagramDriftRules,
)
from tests.unit.handlers.diagram_drift_support.helpers import (
    FIXTURE,
    diagram_blocks,
    fragment_blocks,
)
from tests.unit.handlers.diagram_drift_support.renderer import load_fixture_fragment

ANDON = "node_andon_stop_reducer:state_machine"
LEASE = "node_lane_lease_reducer:state_machine"
CONTRACT_PATH = (
    Path(__file__).parents[3]
    / "src"
    / "omnibase_core"
    / "validation"
    / "contracts"
    / "diagram_drift.validation.yaml"
)

pytestmark = pytest.mark.unit

EDGE_OLD = "    fixed --> open : readback_mismatch\n"
EDGE_NEW = "    fixed --> stale : readback_mismatch\n"


def _contract_data() -> dict[str, object]:
    loaded = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    data = loaded["validation"]
    assert isinstance(data, dict)
    return deepcopy(data)


def rules_from(data: dict[str, object]) -> ModelDiagramDriftRules:
    return ModelDiagramDriftRules.from_contract(
        ModelValidatorSubcontract.model_validate(data)
    )


@pytest.fixture(scope="module")
def rules() -> ModelDiagramDriftRules:
    return rules_from(_contract_data())


@pytest.fixture(scope="module")
def plan_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def check(text: str, rules: ModelDiagramDriftRules) -> ModelDiagramDriftReport:
    return HandlerDiagramDrift().check(text, rules, load_fixture_fragment)


def kinds(report: ModelDiagramDriftReport) -> list[str | None]:
    return [issue.code for issue in report.issues]


def contract_id(report: ModelDiagramDriftReport, index: int = 0) -> str:
    context = report.issues[index].context
    assert context is not None
    return context["contract_id"]


def lease_block(plan_text: str) -> list[str]:
    return next(
        lines
        for node, kind, _, lines in diagram_blocks(plan_text)
        if f"{node}:{kind}" == LEASE
    )


def lease_caption(plan_text: str) -> str:
    return next(
        line
        for line in plan_text.splitlines()
        if line.startswith("*Figure 10.") and "node_lane_lease_reducer" in line
    )


def test_the_fixture_copy_of_the_plans_diagrams_passes(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    result = check(plan_text, rules)
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.diagrams_checked == 11
    assert result.fragments_found == 10


def test_the_fixture_holds_seven_state_machines_and_three_graphs(
    plan_text: str,
) -> None:
    blocks = {key.rpartition(":")[2] for key in fragment_blocks(plan_text)}
    names = [block for _, block, _, _ in diagram_blocks(plan_text)]
    assert blocks == {"state_machine", "graph"}
    assert len(fragment_blocks(plan_text)) == 10
    assert sum(1 for k in fragment_blocks(plan_text) if k.endswith(":graph")) == 3
    assert names.count("state_machine") == 7
    assert names.count("graph") == 4


def test_a_state_diagram_with_one_edge_changed_fails_and_names_the_line(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    assert plan_text.count(EDGE_OLD) == 1
    block = next(
        lines
        for node, kind, _, lines in diagram_blocks(plan_text)
        if f"{node}:{kind}" == ANDON
    )
    expected_line = block.index(EDGE_OLD.rstrip("\n")) + 1

    result = check(plan_text.replace(EDGE_OLD, EDGE_NEW), rules)

    assert result.exit_code == 1
    assert kinds(result) == ["diagram_differs"]
    issue = result.issues[0]
    assert contract_id(result) == ANDON
    assert issue.context is not None
    assert issue.context["diagram_line"] == str(expected_line)
    assert EDGE_OLD.strip() in issue.message
    assert EDGE_NEW.strip() in issue.message
    assert f"line {expected_line}" in issue.message


def test_a_removed_transition_with_the_diagram_left_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    removed = (
        "  - version: {major: 1, minor: 0, patch: 0}\n"
        "    transition_name: fixed_to_open_on_readback_mismatch\n"
        "    from_state: fixed\n"
        "    to_state: open\n"
        "    trigger: readback_mismatch\n"
    )
    assert plan_text.count(removed) == 1

    result = check(plan_text.replace(removed, ""), rules)

    assert result.exit_code == 1
    assert kinds(result) == ["diagram_differs"]
    assert contract_id(result) == ANDON
    assert "fixed --> open : readback_mismatch" in result.issues[0].message


def test_a_diagram_with_no_fragment_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    fragment = fragment_blocks(plan_text)[LEASE]
    marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"
    assert plan_text.count(marker + fragment + "```\n") == 1

    result = check(plan_text.replace(marker + fragment + "```\n", ""), rules)

    assert result.exit_code == 1
    assert kinds(result) == ["diagram_without_fragment"]
    assert contract_id(result) == LEASE


def test_a_fragment_with_no_diagram_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    drawn = (
        f"<!-- diagram-contract: {LEASE} -->\n```mermaid\n"
        + "\n".join(lease_block(plan_text))
        + "\n```\n"
    )
    assert plan_text.count(drawn) == 1

    result = check(plan_text.replace(drawn, ""), rules)

    assert result.exit_code == 1
    assert kinds(result) == ["fragment_without_diagram"]
    assert contract_id(result) == LEASE


def test_a_fragment_the_core_model_refuses_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    broken = plan_text.replace(
        "  initial_state: claimed\n", "  initial_state: no_such_state\n"
    )
    assert broken != plan_text

    result = check(broken, rules)

    assert result.exit_code == 1
    assert "fragment_refused" in set(kinds(result))
    assert contract_id(result, kinds(result).index("fragment_refused")) == LEASE


def test_a_diagram_with_no_line_naming_its_contract_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    result = check(
        plan_text.replace(
            lease_caption(plan_text), "*Figure 10. The life of one lane lease.*"
        ),
        rules,
    )

    assert result.exit_code == 1
    assert kinds(result) == ["missing_contract_line"]
    assert contract_id(result) == LEASE


def test_two_fragments_with_one_id_fail(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    fragment = fragment_blocks(plan_text)[LEASE]
    marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"

    result = check(plan_text + "\n" + marker + fragment + "```\n", rules)

    assert result.exit_code == 1
    assert kinds(result) == ["duplicate_fragment"]


def test_a_collapsed_view_of_a_state_machine_fails(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    marked = plan_text.replace(
        f"<!-- diagram-contract: {LEASE} -->",
        f"<!-- diagram-contract: {LEASE} collapsed -->",
    )

    assert kinds(check(marked, rules)) == ["view_not_supported"]


def test_a_marker_with_no_block_after_it_fails(rules: ModelDiagramDriftRules) -> None:
    result = check("<!-- diagram-contract: node_x:graph -->\nno block follows\n", rules)

    assert result.exit_code == 1
    assert kinds(result) == ["malformed_marker"]


def test_a_document_with_no_markers_passes_with_nothing_checked(
    rules: ModelDiagramDriftRules,
) -> None:
    result = check("# A document with no diagrams\n", rules)

    assert result.exit_code == 0
    assert result.diagrams_checked == 0


@pytest.mark.parametrize("extra", ["", "\n", "\n\n"])
def test_blank_lines_before_the_fence_do_not_matter(
    plan_text: str, extra: str, rules: ModelDiagramDriftRules
) -> None:
    marker = f"<!-- diagram-contract: {LEASE} -->\n"
    assert check(plan_text.replace(marker, marker + extra), rules).exit_code == 0


def test_the_issue_carries_its_document_line_and_rule_name(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    marker = f"<!-- diagram-contract: {LEASE} collapsed -->"
    marked = plan_text.replace(f"<!-- diagram-contract: {LEASE} -->", marker)
    line = marked.splitlines().index(marker) + 1

    issue = check(marked, rules).issues[0]

    assert issue.line_number == line
    assert issue.rule_name == "view_not_supported"


# Configuration: every rule table that was a module constant is the contract's.


def _without_rule(rule_id: str) -> dict[str, object]:
    data = _contract_data()
    entries = data["rules"]
    assert isinstance(entries, list)
    data["rules"] = [e for e in entries if e["rule_id"] != rule_id]
    return data


def _with_parameter(rule_id: str, name: str, value: object) -> dict[str, object]:
    data = _contract_data()
    entries = data["rules"]
    assert isinstance(entries, list)
    for entry in entries:
        if entry["rule_id"] == rule_id:
            entry["parameters"][name] = value
    return data


def test_removing_the_view_not_supported_entry_changes_that_fixtures_verdict(
    plan_text: str,
) -> None:
    marked = plan_text.replace(
        f"<!-- diagram-contract: {LEASE} -->",
        f"<!-- diagram-contract: {LEASE} collapsed -->",
    )
    full = rules_from(_contract_data())
    cut = rules_from(_without_rule("view_not_supported"))

    assert kinds(check(marked, full)) == ["view_not_supported"]
    assert check(marked, cut).issues == ()


def _broken_for(kind: str, plan_text: str) -> str:
    fragment = fragment_blocks(plan_text)[LEASE]
    fragment_marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"
    return {
        "diagram_differs": plan_text.replace(EDGE_OLD, EDGE_NEW),
        "diagram_without_fragment": plan_text.replace(
            fragment_marker + fragment + "```\n", ""
        ),
        "fragment_without_diagram": plan_text.replace(
            f"<!-- diagram-contract: {LEASE} -->\n```mermaid\n"
            + "\n".join(lease_block(plan_text))
            + "\n```\n",
            "",
        ),
        "duplicate_fragment": plan_text + "\n" + fragment_marker + fragment + "```\n",
        "missing_contract_line": plan_text.replace(
            lease_caption(plan_text), "*Figure 10. The life of one lane lease.*"
        ),
        "malformed_marker": "<!-- diagram-contract: node_x:graph -->\nno block\n",
        "fragment_refused": plan_text.replace(
            "  initial_state: claimed\n", "  initial_state: no_such_state\n"
        ),
    }[kind]


@pytest.mark.parametrize(
    "removed",
    [
        "diagram_differs",
        "diagram_without_fragment",
        "fragment_without_diagram",
        "duplicate_fragment",
        "missing_contract_line",
        "malformed_marker",
        "fragment_refused",
    ],
)
def test_removing_one_kind_entry_silences_exactly_that_kind(
    removed: str, plan_text: str
) -> None:
    cut = rules_from(_without_rule(removed))
    broken = _broken_for(removed, plan_text)

    assert broken != plan_text
    assert removed in kinds(check(broken, rules_from(_contract_data())))
    assert removed not in kinds(check(broken, cut))


def test_the_marker_pattern_is_the_contracts(plan_text: str) -> None:
    renamed = _with_parameter(
        "diagram_marker",
        "pattern",
        r"^<!-- drawn-from: ([^:\s]+):(\S+?)(?: (collapsed))? -->$",
    )
    moved = plan_text.replace("<!-- diagram-contract:", "<!-- drawn-from:")

    assert check(moved, rules_from(_contract_data())).diagrams_checked == 0
    assert check(moved, rules_from(renamed)).diagrams_checked == 11


def test_the_full_view_only_kinds_are_the_contracts(plan_text: str) -> None:
    other = _with_parameter("view_support", "full_view_only_kinds", ["graph"])

    assert any(collapsed for _, _, collapsed, _ in diagram_blocks(plan_text))
    assert check(plan_text, rules_from(_contract_data())).issues == ()
    assert kinds(check(plan_text, rules_from(other))) == ["view_not_supported"]


def test_a_contract_missing_a_required_table_is_refused() -> None:
    with pytest.raises(ValueError, match="diagram_marker"):
        rules_from(_without_rule("diagram_marker"))


def test_a_marker_pattern_with_the_wrong_group_count_is_refused() -> None:
    bad = _with_parameter("fragment_marker", "pattern", r"^<!-- x: (\S+) -->$")
    with pytest.raises(ValueError, match="fragment_marker"):
        rules_from(bad)


# Bindings: pure.


def test_the_checker_is_deterministic_byte_for_byte(
    plan_text: str, rules: ModelDiagramDriftRules
) -> None:
    broken = plan_text.replace(EDGE_OLD, EDGE_NEW)
    first = check(broken, rules).model_dump_json()
    second = check(broken, rules).model_dump_json()
    fresh = check(broken, rules_from(_contract_data())).model_dump_json()

    assert first == second == fresh


def test_the_checker_does_no_io(
    plan_text: str,
    rules: ModelDiagramDriftRules,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("the checker touched the filesystem")

    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr("builtins.open", refuse)

    assert check(plan_text, rules).exit_code == 0


def test_no_rule_table_is_a_module_constant_of_the_checker() -> None:
    """The marker patterns and the fence live in the contract only."""
    sources = [
        Path(__file__).parents[3]
        / "src"
        / "omnibase_core"
        / "handlers"
        / "handler_diagram_drift.py",
        Path(__file__).parents[3]
        / "src"
        / "omnibase_core"
        / "models"
        / "diagram_drift"
        / "model_diagram_drift_rules.py",
    ]
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for literal in ("<!--", "```", "(?:", "^<"):
            assert literal not in text, (
                f"{literal!r} is a rule literal in {source.name}"
            )
