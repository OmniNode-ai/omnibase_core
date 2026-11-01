# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure diagram-drift checker and generic validator (OMN-21510, task T-G1b).

The cases of the merged omnimarket check (``node_contract_diagram_compute``) run here against
the core checker on a copy of the same plan fixture. All rule data lives in
``validation/contracts/diagram_drift.validation.yaml``; the table-driven mutation test changes
every ``parameters`` key of every rule row in turn and asserts the verdict changes.
"""

from __future__ import annotations

import ast
import builtins
import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_check_input import (
    ModelDiagramDriftCheckInput,
)
from omnibase_core.models.diagram_drift.model_diagram_drift_check_result import (
    ModelDiagramDriftCheckResult,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation import checker_diagram_drift as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_diagram_drift import check_diagram_drift
from omnibase_core.validation.hardcoded_model_config import handler as model_config
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_diagram_drift import ValidatorDiagramDrift
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_url_authority import scan_source
from omnibase_core.validators import contract_config_compliance

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "diagram_drift"
)
PLAN = FIXTURES / "plan_diagrams.txt"
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "diagram_drift.validation.yaml"
)
ANDON = "node_andon_stop_reducer:state_machine"
LEASE = "node_lane_lease_reducer:state_machine"

RULE_IDS = {
    "diagram_differs",
    "diagram_without_fragment",
    "fragment_without_diagram",
    "fragment_refused",
    "duplicate_fragment",
    "missing_contract_line",
    "malformed_marker",
    "view_not_supported",
}

QUOTED_GRAPH = (
    "<!-- contract-fragment: node_q:graph -->\n"
    "```yaml\n"
    "workflow_coordination:\n"
    "  workflow_definition:\n"
    "    workflow_metadata:\n"
    "      workflow_name: q\n"
    "      workflow_version: {major: 1, minor: 0, patch: 0}\n"
    "      version: {major: 1, minor: 0, patch: 0}\n"
    "      description: q\n"
    "      timeout_ms: 1000\n"
    "    execution_graph:\n"
    "      version: {major: 1, minor: 0, patch: 0}\n"
    "      nodes:\n"
    "        - node_id: first\n"
    "          node_type: EFFECT_GENERIC\n"
    '          description: say "hi"\n'
    "          depends_on: []\n"
    "```\n"
    "<!-- diagram-contract: node_q:graph -->\n"
    "```mermaid\n"
    "flowchart TB\n"
    '    first["say #quot;hi#quot;"]\n'
    "```\n"
    "The graph of node_q.\n"
)


@pytest.fixture
def plan_text() -> str:
    return PLAN.read_text(encoding="utf-8")


def _contract() -> ModelValidatorSubcontract:
    return ValidatorDiagramDrift().contract


def check(
    text: str, contract: ModelValidatorSubcontract | None = None
) -> ModelDiagramDriftCheckResult:
    return check_diagram_drift(
        ModelDiagramDriftCheckInput(
            source_name="beta/plans/x.md", text=text, contract=contract or _contract()
        )
    )


def _blocks(text: str, marker: str) -> dict[str, list[str]]:
    """Fenced block bodies by ``node:block`` id, read without the checker."""
    lines = text.splitlines()
    found: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        match = re.match(rf"^<!-- {marker}: (\S+?:\S+?)(?: collapsed)? -->$", line)
        if match:
            start = index + 1
            while not lines[start].startswith("```"):
                start += 1
            end = start + 1
            while not lines[end].startswith("```"):
                end += 1
            found.setdefault(match[1], lines[start + 1 : end])
    return found


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    """The committed contract with ``mutate`` applied to its rules, by rule id."""
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _ctx(issue: Any, key: str) -> str:
    return str(issue.context[key])


def test_the_fixture_copy_of_the_plans_diagrams_passes(plan_text: str) -> None:
    result = check(plan_text)
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.diagrams_checked == 11
    assert result.fragments_found == 10


def test_a_state_diagram_with_one_edge_changed_fails_and_names_the_line(
    plan_text: str,
) -> None:
    old = "    fixed --> open : readback_mismatch\n"
    new = "    fixed --> stale : readback_mismatch\n"
    assert plan_text.count(old) == 1
    expected_line = (
        _blocks(plan_text, "diagram-contract")[ANDON].index(old.rstrip()) + 1
    )

    result = check(plan_text.replace(old, new))

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["diagram_differs"]
    issue = result.issues[0]
    assert _ctx(issue, "contract_id") == ANDON
    assert _ctx(issue, "diagram_line") == str(expected_line)
    assert old.strip() in issue.message
    assert new.strip() in issue.message
    assert f"line {expected_line}" in issue.message
    assert (
        issue.line_number
        == plan_text.replace(old, new).splitlines().index(new.rstrip()) + 1
    )


def test_a_removed_transition_with_the_diagram_left_fails(plan_text: str) -> None:
    removed = (
        "  - version: {major: 1, minor: 0, patch: 0}\n"
        "    transition_name: fixed_to_open_on_readback_mismatch\n"
        "    from_state: fixed\n"
        "    to_state: open\n"
        "    trigger: readback_mismatch\n"
    )
    assert plan_text.count(removed) == 1

    result = check(plan_text.replace(removed, ""))

    assert [issue.code for issue in result.issues] == ["diagram_differs"]
    assert _ctx(result.issues[0], "contract_id") == ANDON
    assert "fixed --> open : readback_mismatch" in result.issues[0].message


def test_a_diagram_with_no_fragment_fails(plan_text: str) -> None:
    fragment = "\n".join(_blocks(plan_text, "contract-fragment")[LEASE]) + "\n"
    marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"
    assert plan_text.count(marker + fragment + "```\n") == 1

    result = check(plan_text.replace(marker + fragment + "```\n", ""))

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["diagram_without_fragment"]
    assert _ctx(result.issues[0], "contract_id") == LEASE


def test_a_fragment_with_no_diagram_fails(plan_text: str) -> None:
    block = _blocks(plan_text, "diagram-contract")[LEASE]
    drawn = (
        f"<!-- diagram-contract: {LEASE} -->\n```mermaid\n"
        + "\n".join(block)
        + "\n```\n"
    )
    assert plan_text.count(drawn) == 1

    result = check(plan_text.replace(drawn, ""))

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["fragment_without_diagram"]
    assert _ctx(result.issues[0], "contract_id") == LEASE


def test_a_fragment_the_core_model_refuses_fails(plan_text: str) -> None:
    broken = plan_text.replace(
        "  initial_state: claimed\n", "  initial_state: no_such_state\n"
    )
    assert broken != plan_text

    result = check(broken)

    assert result.exit_code == 1
    refused = [i for i in result.issues if i.code == "fragment_refused"]
    assert [_ctx(i, "contract_id") for i in refused] == [LEASE]


def test_a_diagram_with_no_line_naming_its_contract_fails(plan_text: str) -> None:
    caption = next(
        line
        for line in plan_text.splitlines()
        if line.startswith("*Figure 10.") and "node_lane_lease_reducer" in line
    )

    result = check(
        plan_text.replace(caption, "*Figure 10. The life of one lane lease.*")
    )

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["missing_contract_line"]
    assert _ctx(result.issues[0], "contract_id") == LEASE


def test_two_fragments_with_one_id_fail(plan_text: str) -> None:
    fragment = "\n".join(_blocks(plan_text, "contract-fragment")[LEASE]) + "\n"
    marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"

    result = check(plan_text + "\n" + marker + fragment + "```\n")

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["duplicate_fragment"]


def test_a_collapsed_view_of_a_state_machine_fails(plan_text: str) -> None:
    marked = plan_text.replace(
        f"<!-- diagram-contract: {LEASE} -->",
        f"<!-- diagram-contract: {LEASE} collapsed -->",
    )

    assert [issue.code for issue in check(marked).issues] == ["view_not_supported"]


def test_a_marker_with_no_block_after_it_fails() -> None:
    result = check("<!-- diagram-contract: node_x:graph -->\nno block follows\n")

    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["malformed_marker"]


def test_a_document_with_no_markers_passes_with_nothing_checked() -> None:
    result = check("# A document with no diagrams\n")

    assert result.exit_code == 0
    assert result.diagrams_checked == 0


@pytest.mark.parametrize("extra", ["", "\n", "\n\n"])
def test_blank_lines_before_the_fence_do_not_matter(plan_text: str, extra: str) -> None:
    marker = f"<!-- diagram-contract: {LEASE} -->\n"
    assert check(plan_text.replace(marker, marker + extra)).exit_code == 0


def test_a_label_with_a_quote_is_drawn_with_the_quote_entity() -> None:
    assert check(QUOTED_GRAPH).issues == ()
    assert [i.code for i in check(QUOTED_GRAPH.replace("#quot;", '"')).issues] == [
        "diagram_differs"
    ]


def _battery(plan_text: str) -> list[str]:
    """The plan and one text per kind of drift, so every parameter has a verdict to move."""
    lease_fragment = "\n".join(_blocks(plan_text, "contract-fragment")[LEASE]) + "\n"
    lease_marker = f"<!-- contract-fragment: {LEASE} -->\n```yaml\n"
    drawn = (
        f"<!-- diagram-contract: {LEASE} -->\n```mermaid\n"
        + "\n".join(_blocks(plan_text, "diagram-contract")[LEASE])
        + "\n```\n"
    )
    caption = next(
        line
        for line in plan_text.splitlines()
        if line.startswith("*Figure 10.") and "node_lane_lease_reducer" in line
    )
    return [
        plan_text,
        QUOTED_GRAPH,
        plan_text.replace(
            "    fixed --> open : readback_mismatch\n",
            "    fixed --> stale : readback_mismatch\n",
        ),
        plan_text.replace(lease_marker + lease_fragment + "```\n", ""),
        plan_text.replace(drawn, ""),
        plan_text.replace(
            "  initial_state: claimed\n", "  initial_state: no_such_state\n"
        ),
        plan_text.replace(caption, "*Figure 10. The life of one lane lease.*"),
        plan_text + "\n" + lease_marker + lease_fragment + "```\n",
        plan_text.replace(
            f"<!-- diagram-contract: {LEASE} -->",
            f"<!-- diagram-contract: {LEASE} collapsed -->",
        ),
        plan_text.replace(f"{LEASE} ", f"{LEASE.rpartition(':')[0]}:graph ").replace(
            f"{LEASE} -->", f"{LEASE.rpartition(':')[0]}:graph -->"
        ),
        plan_text.replace(
            "\n".join(_blocks(plan_text, "diagram-contract")[LEASE]) + "\n```",
            "\n".join(_blocks(plan_text, "diagram-contract")[LEASE][:-1]) + "\n```",
        ),
        "<!-- diagram-contract: node_x:graph -->\nno block follows\n",
        "<!-- contract-fragment: node_x:graph -->\nno block follows\n",
    ]


def _verdicts(
    contract: ModelValidatorSubcontract, battery: list[str]
) -> list[tuple[tuple[str | None, int | None, str], ...]]:
    return [
        tuple((i.code, i.line_number, i.message) for i in check(text, contract).issues)
        for text in battery
    ]


def test_every_rule_fires_somewhere_in_the_battery(plan_text: str) -> None:
    fired = {issue.code for text in _battery(plan_text) for issue in check(text).issues}
    assert fired == RULE_IDS


def test_every_parameter_of_every_rule_row_changes_a_verdict(plan_text: str) -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    battery = _battery(plan_text)
    baseline = _verdicts(_contract(), battery)
    unmoved: list[str] = []
    for rule in data["rules"]:
        keys = [*rule["parameters"], "enabled"]
        for key in keys:
            replacements: list[Any]
            if key == "enabled":
                replacements = [False]
            elif isinstance(rule["parameters"][key], list):
                replacements = [[], [*rule["parameters"][key], "x"]]
            else:
                replacements = ["(?!)", "(?s).+"]
            changed = False
            for replacement in replacements:

                def mutate(
                    rules: dict[str, dict[str, Any]],
                    rule_id: str = rule["rule_id"],
                    key: str = key,
                    replacement: Any = replacement,
                ) -> None:
                    if key == "enabled":
                        rules[rule_id]["enabled"] = replacement
                    else:
                        rules[rule_id]["parameters"][key] = replacement

                try:
                    moved = _verdicts(_contract_with(mutate), battery) != baseline
                except ModelOnexError:
                    moved = True  # a contract the checker refuses to load is no pass
                if moved:
                    changed = True
                    break
            if not changed:
                unmoved.append(f"{rule['rule_id']}.{key}")
    assert unmoved == []


def test_a_fixture_contract_that_removes_one_entry_changes_the_verdict(
    plan_text: str,
) -> None:
    """The ticket's AC3 falsifier: drop the compute node type and the graphs stop matching."""

    def drop_compute(rules: dict[str, dict[str, Any]]) -> None:
        rules["diagram_differs"]["parameters"]["compute_node_type"] = "NOT_A_TYPE"

    assert check(plan_text).issues == ()
    changed = check(plan_text, _contract_with(drop_compute))
    assert {issue.code for issue in changed.issues} == {"diagram_differs"}
    assert {_ctx(i, "contract_id").rpartition(":")[2] for i in changed.issues} == {
        "graph"
    }


def test_invalid_contracts_fail_to_load_rather_than_pass(plan_text: str) -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    for rule in data["rules"]:
        for key in rule["parameters"]:

            def drop(
                rules: dict[str, dict[str, Any]],
                rule_id: str = rule["rule_id"],
                key: str = key,
            ) -> None:
                del rules[rule_id]["parameters"][key]

            with pytest.raises(ModelOnexError, match=rule["rule_id"]):
                check(plan_text, _contract_with(drop))

    def drop_rule(rules: dict[str, dict[str, Any]]) -> None:
        del rules["duplicate_fragment"]

    with pytest.raises(ModelOnexError, match="duplicate_fragment"):
        check(plan_text, _contract_with(drop_rule))

    def bad_regex(rules: dict[str, dict[str, Any]]) -> None:
        rules["malformed_marker"]["parameters"]["diagram_marker_pattern"] = "("

    with pytest.raises(ModelOnexError, match="diagram_marker_pattern"):
        check(plan_text, _contract_with(bad_regex))

    def too_few_groups(rules: dict[str, dict[str, Any]]) -> None:
        rules["malformed_marker"]["parameters"]["fragment_marker_pattern"] = "^<!--"

    with pytest.raises(ModelOnexError, match="fragment_marker_pattern"):
        check(plan_text, _contract_with(too_few_groups))


def test_invalid_contracts_validate_disabled_rows_too(plan_text: str) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        rules["view_not_supported"]["enabled"] = False
        del rules["view_not_supported"]["parameters"]["message"]

    with pytest.raises(ModelOnexError, match="view_not_supported"):
        check(plan_text, _contract_with(mutate))


def test_a_disabled_rule_row_silences_its_issue(plan_text: str) -> None:
    for text in _battery(plan_text):
        for rule_id in {issue.code for issue in check(text).issues}:

            def disable(
                rules: dict[str, dict[str, Any]], rule_id: str = rule_id
            ) -> None:
                rules[rule_id]["enabled"] = False

            silenced = check(text, _contract_with(disable))
            assert rule_id not in {issue.code for issue in silenced.issues}


def test_committed_contract_holds_every_rule_at_error_severity() -> None:
    contract = _contract()
    assert contract.validator_id == "diagram_drift"
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    assert all(
        rule.enabled and rule.severity.value == "error" for rule in contract.rules
    )
    assert contract.fail_on_error
    assert not contract.fail_on_warning
    assert contract.max_violations == 0


def test_checker_reads_no_file_while_open_and_path_reads_raise(
    monkeypatch: pytest.MonkeyPatch, plan_text: str
) -> None:
    contract = _contract()
    texts = _battery(plan_text)

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    assert check(texts[0], contract).issues == ()
    assert check(texts[2], contract).exit_code == 1


def test_checker_module_is_pure_and_holds_no_rule_table() -> None:
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    # ``yaml`` only parses the fragment text it is given; it opens nothing.
    assert not imported & {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "time",
        "datetime",
        "random",
        "urllib",
        "logging",
    }
    assigned = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
        and not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
    ]
    assert assigned == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "validation/checker_diagram_drift.py",
        "validation/validator_diagram_drift.py",
        "models/diagram_drift/__init__.py",
        "models/diagram_drift/model_diagram_drift_check_input.py",
        "models/diagram_drift/model_diagram_drift_check_result.py",
        "models/diagram_drift/model_diagram_drift_rules.py",
        "models/diagram_drift/model_diagram_block.py",
        "models/diagram_drift/model_diagram_fragment.py",
    ],
)
def test_production_source_has_no_runtime_literals(relative_path: str) -> None:
    """Scan the actual source; absent source must not count as a clean scan."""
    package_root = Path(validator_base.__file__).parent.parent
    path = package_root / relative_path
    source = path.read_text(encoding="utf-8")
    repo_path = f"src/omnibase_core/{relative_path}"
    policy_path = Path(model_config.__file__).with_name("policy.yaml")
    policy = ModelHardcodedModelConfigPolicy.model_validate(
        yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    )

    assert scan_source("omnibase_core", repo_path, source) == []
    assert model_config.scan(repo_path, source, policy) == []
    assert not ValidatorHardcodedTopics().validate_file(path).issues
    assert not ValidatorCheckerRuleData().validate_file(path).issues
    assert contract_config_compliance.validate_file(path) == []


def test_results_are_byte_identical_in_process_and_through_the_runtime_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, plan_text: str
) -> None:
    """The local in-process entry of the generic runtime reports what the checker returns."""
    drifted = plan_text.replace(
        "    fixed --> open : readback_mismatch\n",
        "    fixed --> stale : readback_mismatch\n",
    ).replace(
        "<!-- diagram-contract: node_wip_gate_reducer:state_machine -->",
        "<!-- diagram-contract: node_wip_gate_reducer:state_machine collapsed -->",
    )
    plans = tmp_path / "beta" / "plans"
    plans.mkdir(parents=True)
    (plans / "drifted.md").write_text(drifted, "utf-8")
    (plans / "clean.md").write_text(plan_text, "utf-8")
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "report.json"

    exit_code = main(
        ValidatorDiagramDrift,
        [str(tmp_path), "--report-json", str(report_path)],
        build_validator_container,
    )

    expected = [
        {
            "location": f"beta/plans/drifted.md:{issue.line_number}",
            "message": issue.message,
            "rule_id": issue.code,
        }
        for issue in check_diagram_drift(
            ModelDiagramDriftCheckInput(
                source_name="beta/plans/drifted.md",
                text=drifted,
                contract=_contract(),
            )
        ).issues
    ]
    report = json.loads(report_path.read_text("utf-8"))
    found = [
        {
            "location": finding["location"],
            "message": finding["message"],
            "rule_id": finding["rule_id"],
        }
        for finding in report["findings"]
    ]
    assert exit_code == 1
    assert len(expected) == 2
    assert json.dumps(found, sort_keys=True) == json.dumps(expected, sort_keys=True)
