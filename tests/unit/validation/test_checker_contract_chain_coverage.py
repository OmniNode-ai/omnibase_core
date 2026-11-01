# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-driven coverage, planted golden, and mutants through the real loader."""

from __future__ import annotations

import ast
import builtins
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.validation_report_write.model_validator_runtime_bus import (
    ModelValidatorRuntimeBus,
)
from omnibase_core.models.validation.model_contract_chain_binding import (
    ModelContractChainBinding,
)
from omnibase_core.models.validation.model_contract_chain_facts import (
    ModelContractChainFacts,
)
from omnibase_core.models.validation.model_contract_chain_generated_case import (
    ModelContractChainGeneratedCase,
)
from omnibase_core.models.validation.model_handler_di_module_fact import (
    ModelHandlerDiModuleFact,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    run_validator,
)
from omnibase_core.validation.checker_contract_chain_coverage import (
    build_coverage_table,
    check_contract_chain_coverage,
    derive_obligations,
    generate_cases,
    render_coverage_table,
)
from omnibase_core.validation.checker_handler_di import check_module
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    main as hardcoded_model_config_main,
)
from omnibase_core.validation.validator_contract_chain_coverage import (
    ValidatorContractChainCoverage,
    load_facts,
)
from omnibase_core.validation.validator_contract_walker import load_machines
from omnibase_core.validation.validator_handler_di import ValidatorHandlerDi
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_url_authority import ValidatorUrlAuthority
from omnibase_core.validators.contract_config_compliance import validate_paths
from tests.utils.helpers_contract_chain_coverage import stage_planted

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/contract_chain_coverage"
_CONTRACT = (
    _ROOT
    / "src/omnibase_core/validation/contracts/contract_chain_coverage.validation.yaml"
)


def _contract() -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(
        yaml.safe_load(_CONTRACT.read_text())["validation"]
    )


def _configured(tmp_path: Path) -> ModelValidatorSubcontract:
    """Copy real rule data and mutate test roots, as an external caller would."""
    data = yaml.safe_load(_CONTRACT.read_text())
    data["validation"]["exclude_patterns"] = []
    data["validation"]["rules"][0]["parameters"]["test_roots"] = ["tests"]
    path = tmp_path / "coverage.validation.yaml"
    path.write_text(yaml.safe_dump(data))
    return ModelValidatorSubcontract.model_validate(
        yaml.safe_load(path.read_text())["validation"]
    )


def _copy(
    kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, ModelValidatorSubcontract]:
    root = tmp_path / "corpus"
    shutil.copytree(_FIXTURES / kind, root)
    monkeypatch.chdir(root)
    return root, _configured(tmp_path)


def _parameters(
    contract: ModelValidatorSubcontract, rule_id: str, key: str, value: object | None
) -> ModelValidatorSubcontract:
    rules = []
    for rule in contract.rules:
        if rule.rule_id == rule_id:
            parameters = dict(rule.parameters or {})
            if value is None:
                del parameters[key]
            else:
                parameters[key] = cast(RuleParameterValue, value)
            rule = rule.model_copy(update={"parameters": parameters})
        rules.append(rule)
    return contract.model_copy(update={"rules": rules})


def _remove_binding(path: Path, obligation_ref: str) -> None:
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(d, ast.Call)
            and any(
                isinstance(arg, ast.Constant) and arg.value == obligation_ref
                for arg in d.args
            )
            for d in node.decorator_list
        ):
            first = min(d.lineno for d in node.decorator_list) - 1
            del lines[first : node.end_lineno]
            path.write_text("".join(lines))
            return
    raise AssertionError(f"missing planted binding: {obligation_ref}")


def test_planted_has_exactly_one_per_enabled_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("planted", tmp_path, monkeypatch)
    result = ValidatorContractChainCoverage(contract).validate(root)
    assert Counter(i.code for i in result.issues) == Counter(
        r.rule_id for r in contract.rules if r.enabled
    )
    assert len(result.issues) == 9
    assert all(i.code != "machine_not_executed" for i in result.issues)
    assert [i.code for i in result.issues] == [
        r.rule_id for r in contract.rules if r.enabled
    ]
    for issue in result.issues:
        rule = next(r for r in contract.rules if r.rule_id == issue.code)
        assert issue.rule_name == rule.rule_id
        assert issue.severity == "warning"
        assert issue.message.endswith(f" -- {(rule.parameters or {})['remediation']}")
    assert "ORPHAN" in result.issues[6].message
    assert "SPIN" in result.issues[7].message
    assert "WORK" in result.issues[8].message


def test_pass_corpus_has_no_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("pass", tmp_path, monkeypatch)
    paths = sorted(root.rglob("contract.yaml"))
    machines, not_armed = load_machines(paths)
    assert not_armed == []
    assert len(machines) == 1
    facts = load_facts(paths, contract)
    assert len(derive_obligations(facts, contract.rules)) == 19
    assert ValidatorContractChainCoverage(contract).validate(root).issues == []
    assert (
        generate_cases(build_coverage_table(facts, contract.rules), contract.rules)
        == ()
    )


class TestAMutantThatArmsAHeldPrFails:
    def test_deleted_transition_binding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, contract = _copy("pass", tmp_path, monkeypatch)
        validator = ValidatorContractChainCoverage(contract)
        assert validator.validate(root).issues == []
        identity = "node_pr_handoff_orchestrator/contract.yaml::transition::waiting_to_refused_on_evaluated_held"
        _remove_binding(root / "tests/test_pr_handoff_chains.py.txt", identity)
        issues = validator.validate(root).issues
        assert [i.code for i in issues] == ["uncovered_transition"]
        assert identity in issues[0].message

    def test_deleted_subscriber(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, contract = _copy("pass", tmp_path, monkeypatch)
        validator = ValidatorContractChainCoverage(contract)
        assert validator.validate(root).issues == []
        path = root / "topic_peers/contract.yaml"
        document = yaml.safe_load(path.read_text())
        document["event_bus"]["subscribe_topics"] = []
        path.write_text(yaml.safe_dump(document))
        assert [i.code for i in validator.validate(root).issues] == ["dead_end_topic"]

    def test_deleted_guard_half(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root, contract = _copy("pass", tmp_path, monkeypatch)
        path = root / "node_pr_handoff_orchestrator/contract.yaml"
        document = yaml.safe_load(path.read_text())
        document["state_machine"]["transitions"][0]["conditions"] = [
            {
                "condition_name": "ready",
                "condition_type": "expression",
                "expression": "ready == true",
            }
        ]
        path.write_text(yaml.safe_dump(document))
        tests = root / "tests/test_pr_handoff_chains.py.txt"
        prefix = "node_pr_handoff_orchestrator/contract.yaml::guard::requested_to_waiting_on_accepted::"
        with tests.open("a") as handle:
            for branch in ("true", "false"):
                handle.write(
                    f'\n@chain_obligation("{prefix}{branch}")\ndef guard_{branch}():\n    pass\n'
                )
        validator = ValidatorContractChainCoverage(contract)
        assert validator.validate(root).issues == []
        _remove_binding(tests, prefix + "false")
        issues = validator.validate(root).issues
        assert [i.code for i in issues] == ["guard_branch_unbound"]
        assert prefix + "false" in issues[0].message


def test_table_generation_and_committed_cases_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("planted", tmp_path, monkeypatch)
    paths = sorted(root.rglob("contract.yaml"))
    facts = load_facts(paths, contract)
    rows = build_coverage_table(facts, contract.rules)
    assert len(rows) == 11
    assert sum(row.location == "MISSING" for row in rows) == 4
    assert any(row.overlays == ("redpanda",) for row in rows)
    assert render_coverage_table(rows) == render_coverage_table(tuple(reversed(rows)))
    cases = generate_cases(rows, contract.rules)
    assert len(cases) == 4
    assert all(case.overlays == ("memory", "redpanda") for case in cases)
    assert all(
        case.kind in ("stub_rows", "node_operation") and isinstance(case.fixture, dict)
        for case in cases
    )
    generated = root / "tests/chains/generated/planted.chains.json"
    generated.parent.mkdir(parents=True)
    generated.write_text(json.dumps([case.model_dump(mode="json") for case in cases]))
    facts = load_facts(paths, contract)
    assert all(
        row.location != "MISSING" for row in build_coverage_table(facts, contract.rules)
    )
    assert [
        binding.line
        for binding in facts.bindings
        if binding.file == generated.relative_to(root).as_posix()
    ] == [1, 2, 3, 4]
    assert [i.code for i in check_contract_chain_coverage(facts, contract.rules)] == [
        "dead_end_topic",
        "orphan_subscription",
        "unreachable_state",
        "dead_state",
        "no_failure_exit",
    ]


def test_first_binding_and_overlay_union_are_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("pass", tmp_path, monkeypatch)
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    identity = derive_obligations(facts, contract.rules)[0].id
    bindings = (
        ModelContractChainBinding(
            obligation_ref=identity, file="a.py", line=9, overlays=("memory",)
        ),
        ModelContractChainBinding(
            obligation_ref=identity, file="a.py", line=2, overlays=("redpanda",)
        ),
    )
    facts = facts.model_copy(update={"bindings": bindings})
    row = next(
        row for row in build_coverage_table(facts, contract.rules) if row.id == identity
    )
    assert row.location == "a.py:2"
    assert row.overlays == ("memory", "redpanda")


_PARAMETERS = [
    (r.rule_id, key) for r in _contract().rules for key in (r.parameters or {})
]


@pytest.mark.parametrize(("rule_id", "key"), _PARAMETERS)
@pytest.mark.parametrize("value", [None, {}])
def test_missing_or_mistyped_parameter_raises_before_empty_facts(
    rule_id: str, key: str, value: object
) -> None:
    contract = _parameters(_enable_evidence(_contract()), rule_id, key, value)
    with pytest.raises(ModelOnexError):
        check_contract_chain_coverage(ModelContractChainFacts(), contract.rules)


def test_common_parameters_drive_scans_templates_and_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("planted", tmp_path, monkeypatch)
    contract = _parameters(
        contract, "uncovered_transition", "marker_name", "other_chain"
    )
    contract = _parameters(
        contract, "uncovered_transition", "overlay_marker_name", "other_bus"
    )
    tests = root / "tests/test_planted_chains.py.txt"
    tests.write_text(
        tests.read_text()
        .replace("chain_obligation", "other_chain")
        .replace("bus_overlay", "other_bus")
    )
    contract = _parameters(
        contract, "uncovered_transition", "missing_marker", "UNBOUND"
    )
    contract = _parameters(
        contract, "uncovered_transition", "overlay_profiles", ["custom"]
    )
    contract = _parameters(
        contract,
        "uncovered_transition",
        "id_template",
        "{owner}::custom::{transition_name}",
    )
    tests.write_text(tests.read_text().replace("::transition::", "::custom::"))
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    rows = build_coverage_table(facts, contract.rules)
    assert sum(row.location == "UNBOUND" for row in rows) == 4
    assert all(
        case.overlays == ("custom",) for case in generate_cases(rows, contract.rules)
    )
    assert any(binding.overlays == ("redpanda",) for binding in facts.bindings)


def test_checker_is_pure_with_open_and_path_reads_patched_to_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("planted", tmp_path, monkeypatch)
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    with (
        patch.object(builtins, "open", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "read_text", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "glob", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "rglob", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "read_bytes", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "open", side_effect=AssertionError("checker I/O")),
        patch.object(Path, "exists", side_effect=AssertionError("checker I/O")),
    ):
        assert len(check_contract_chain_coverage(facts, contract.rules)) == 9
        rows = build_coverage_table(facts, contract.rules)
        assert len(generate_cases(rows, contract.rules)) == 4
        assert render_coverage_table(rows)


def test_report_only_and_exclusions() -> None:
    contract = _contract()
    assert all(rule.severity == "warning" for rule in contract.rules)
    assert [rule.rule_id for rule in contract.rules if not rule.enabled] == [
        "machine_not_executed"
    ]
    assert not contract.fail_on_warning
    validator = ValidatorContractChainCoverage(contract)
    assert validator.validate(_FIXTURES).issues == []


@pytest.mark.parametrize(
    "text", ["name: one\nname: two\n", "not: [valid", "- not-a-mapping\n"]
)
def test_strict_contract_loading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str
) -> None:
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "contract.yaml"
    path.write_text(text)
    with pytest.raises(ModelOnexError):
        ValidatorContractChainCoverage(_contract()).validate(path)


def test_unreadable_input_and_invalid_marker_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("pass", tmp_path, monkeypatch)
    source = root / "tests/test_pr_handoff_chains.py.txt"
    source.write_text("@chain_obligation(dynamic)\ndef example():\n    pass\n")
    with pytest.raises(ModelOnexError, match="literal string"):
        ValidatorContractChainCoverage(contract).validate(root)
    with (
        patch.object(Path, "read_text", side_effect=OSError("unreadable")),
        pytest.raises(ModelOnexError, match="cannot read"),
    ):
        load_facts([root / "node_pr_handoff_orchestrator/contract.yaml"], contract)


def test_generated_case_is_frozen_and_forbids_extra_fields() -> None:
    case = ModelContractChainGeneratedCase(
        kind="stub_rows",
        obligation_ref="id",
        fixture={"nested": [None, True, {"value": 1}]},
    )
    with pytest.raises(ValidationError):
        case.node = "changed"
    with pytest.raises(ValidationError):
        ModelContractChainGeneratedCase.model_validate(
            {**case.model_dump(), "unknown": True}
        )


@pytest.mark.parametrize(
    "source_name",
    ["checker_contract_chain_coverage.py", "validator_contract_chain_coverage.py"],
)
def test_new_sources_have_no_operational_literals(
    source_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)
    path = Path("src/omnibase_core/validation") / source_name
    for validator in (
        ValidatorUrlAuthority(repo_root=_ROOT),
        ValidatorHardcodedTopics(),
    ):
        result = validator.validate([path])
        assert result.metadata is not None and result.metadata.files_processed == 1
        assert result.issues == []
    assert validate_paths([path]) == []
    assert hardcoded_model_config_main([str(path)]) == 0


def test_normalized_runtime_report_and_table_match_golden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "corpus"
    stage_planted(root)
    monkeypatch.chdir(root)
    contract = _contract()
    output = tmp_path / "report.json"
    run_validator(
        build_validator_container(),
        ValidatorContractChainCoverage(contract),
        [root],
        str(output),
        "default",
        "repository",
    )
    report = json.loads(output.read_text())
    report["report_id"] = "<normalised>"
    report["provenance"]["generated_at"] = "<normalised>"
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    actual = {
        "report": report,
        "issues": [
            i.model_dump(mode="json")
            for i in check_contract_chain_coverage(facts, contract.rules)
        ],
        "coverage_table": [
            row.model_dump(mode="json")
            for row in build_coverage_table(facts, contract.rules)
        ],
    }
    golden = json.loads((_FIXTURES / "golden_contract_chain_coverage.json").read_text())
    assert actual == {key: golden[key] for key in actual}


def _enable_evidence(contract: ModelValidatorSubcontract) -> ModelValidatorSubcontract:
    return contract.model_copy(
        update={
            "rules": [
                r.model_copy(update={"enabled": True})
                if r.rule_id == "machine_not_executed"
                else r
                for r in contract.rules
            ]
        }
    )


# Each row owns a mutation, fixture and observable before/after assertion.
# Held execution evidence validates its parameters but deliberately emits nothing.
_PARAMETER_CASES: list[tuple[str, str, object, str, str, object, object]] = [
    (
        "uncovered_transition",
        "id_template",
        "changed::{owner}::{transition_name}",
        "planted",
        "count",
        1,
        6,
    ),
    ("uncovered_transition", "marker_name", "other_chain", "planted", "bindings", 7, 0),
    (
        "uncovered_transition",
        "overlay_marker_name",
        "other_overlay",
        "planted",
        "binding_overlays",
        ("redpanda",),
        (),
    ),
    ("uncovered_transition", "test_roots", ["absent"], "planted", "bindings", 7, 0),
    (
        "uncovered_transition",
        "test_file_globs",
        ["**/*.absent"],
        "planted",
        "bindings",
        7,
        0,
    ),
    (
        "uncovered_transition",
        "test_exclude_patterns",
        ["*.py.txt"],
        "planted",
        "bindings",
        7,
        0,
    ),
    (
        "uncovered_transition",
        "generated_cases_glob",
        "absent/*.json",
        "planted",
        "count",
        0,
        1,
    ),
    ("uncovered_transition", "missing_marker", "UNBOUND", "planted", "unbound", 0, 4),
    (
        "uncovered_transition",
        "overlay_profiles",
        ["custom"],
        "planted",
        "case_overlays",
        ("memory", "redpanda"),
        ("custom",),
    ),
    (
        "uncovered_transition",
        "scenario_kind",
        "stub_rows",
        "planted",
        "case_kind",
        ("node_operation",),
        ("stub_rows",),
    ),
    (
        "uncovered_transition",
        "scenario_node_template",
        "changed",
        "planted",
        "case_node_changed",
        False,
        True,
    ),
    (
        "uncovered_transition",
        "scenario_operation_template",
        "changed",
        "planted",
        "case_operation_changed",
        False,
        True,
    ),
    (
        "uncovered_transition",
        "allowed_differences",
        ["result.timestamp"],
        "planted",
        "case_differences",
        (),
        ("result.timestamp",),
    ),
    ("uncovered_graph_edge", "nodes_path", "elsewhere.nodes", "planted", "count", 1, 0),
    ("uncovered_graph_edge", "node_id_key", "absent", "planted", "count", 1, 0),
    ("uncovered_graph_edge", "dependencies_key", "absent", "planted", "count", 1, 0),
    (
        "uncovered_graph_edge",
        "id_template",
        "changed::{owner}::{from_node}->{to_node}",
        "planted",
        "count",
        1,
        2,
    ),
    ("guard_branch_unbound", "branches", ["yes", "no"], "planted", "count", 1, 2),
    (
        "guard_branch_unbound",
        "id_template",
        "changed::{owner}::{transition_name}::{branch}",
        "planted",
        "count",
        1,
        2,
    ),
    ("loop_exit_unbound", "nodes_path", "elsewhere.nodes", "planted", "count", 1, 0),
    ("loop_exit_unbound", "node_id_key", "absent", "planted", "count", 1, 0),
    ("loop_exit_unbound", "loops_to_path", "absent", "planted", "count", 1, 0),
    (
        "loop_exit_unbound",
        "id_template",
        "changed::{owner}::{node_id}",
        "planted",
        "changed_id",
        False,
        True,
    ),
    (
        "loop_exit_unbound",
        "fsm_id_template",
        "changed::{owner}::{transition_name}",
        "pass",
        "count",
        0,
        2,
    ),
    ("dead_end_topic", "producer_paths", [], "planted", "count", 1, 0),
    ("dead_end_topic", "consumer_paths", [], "pass", "count", 0, 3),
    ("dead_end_topic", "external_consumer_paths", [], "pass", "count", 0, 3),
    ("orphan_subscription", "consumer_paths", [], "planted", "count", 1, 0),
    ("orphan_subscription", "producer_paths", [], "pass", "count", 0, 3),
    ("orphan_subscription", "external_producer_paths", [], "pass", "count", 0, 1),
    ("dead_state", "wildcard_state", "INIT", "planted", "count", 1, 0),
    ("no_failure_exit", "wildcard_state", "INIT", "planted", "count", 1, 0),
    ("machine_not_executed", "evidence_glob", "absent/*.json", "planted", "held", 0, 0),
    ("machine_not_executed", "minimum_executions", 2, "planted", "held", 0, 0),
]
_PARAMETER_CASES += [
    (rule_id, "kind", "unknown", "planted", "raises", None, None)
    for rule_id in (
        "uncovered_transition",
        "uncovered_graph_edge",
        "guard_branch_unbound",
        "loop_exit_unbound",
        "dead_end_topic",
        "orphan_subscription",
        "unreachable_state",
        "dead_state",
        "no_failure_exit",
        "machine_not_executed",
    )
]
_PARAMETER_CASES += [
    (
        rule_id,
        "remediation",
        "Changed remediation.",
        "planted",
        observable,
        before,
        after,
    )
    for rule_id, observable, before, after in (
        ("uncovered_transition", "remediation", False, True),
        ("uncovered_graph_edge", "remediation", False, True),
        ("guard_branch_unbound", "remediation", False, True),
        ("loop_exit_unbound", "remediation", False, True),
        ("dead_end_topic", "remediation", False, True),
        ("orphan_subscription", "remediation", False, True),
        ("unreachable_state", "remediation", False, True),
        ("dead_state", "remediation", False, True),
        ("no_failure_exit", "remediation", False, True),
        ("machine_not_executed", "held", 0, 0),
    )
]


def test_parameter_table_covers_every_key_of_every_rule_row() -> None:
    pairs = [(row[0], row[1]) for row in _PARAMETER_CASES]
    assert len(pairs) == len(set(pairs))
    assert set(pairs) == set(_PARAMETERS)


def _observable(
    root: Path, contract: ModelValidatorSubcontract, rule_id: str, observable: str
) -> object:
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    issues = [
        i
        for i in check_contract_chain_coverage(facts, contract.rules)
        if i.code == rule_id
    ]
    if observable in ("count", "held"):
        return len(issues)
    if observable == "bindings":
        return len(facts.bindings)
    if observable == "binding_overlays":
        return tuple(sorted({o for b in facts.bindings for o in b.overlays}))
    if observable == "changed_id":
        assert issues
        return all("changed::" in i.message for i in issues)
    if observable == "remediation":
        assert issues
        return all(i.message.endswith(" -- Changed remediation.") for i in issues)
    rows = build_coverage_table(facts, contract.rules)
    if observable == "unbound":
        return sum(r.location == "UNBOUND" for r in rows)
    cases = generate_cases(rows, contract.rules)
    assert cases
    if observable == "case_overlays":
        return tuple(sorted({o for c in cases for o in c.overlays}))
    if observable == "case_kind":
        return tuple(sorted({c.kind for c in cases}))
    if observable == "case_node_changed":
        return all(c.node == "changed" for c in cases)
    if observable == "case_operation_changed":
        return all(c.operation == "changed" for c in cases)
    assert observable == "case_differences"
    return tuple(sorted({d for c in cases for d in c.allowed_differences}))


@pytest.mark.parametrize(
    ("rule_id", "key", "value", "fixture", "observable", "before", "after"),
    _PARAMETER_CASES,
    ids=[f"{row[0]}-{row[1]}" for row in _PARAMETER_CASES],
)
def test_parameter_mutation_changes_its_controlled_observable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    rule_id: str,
    key: str,
    value: object,
    fixture: str,
    observable: str,
    before: object,
    after: object,
) -> None:
    root, contract = _copy(fixture, tmp_path, monkeypatch)
    contract = _enable_evidence(contract)
    if key == "generated_cases_glob":
        facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
        cases = generate_cases(
            build_coverage_table(facts, contract.rules), contract.rules
        )
        generated = root / "tests/chains/generated/planted.chains.json"
        generated.parent.mkdir(parents=True)
        generated.write_text(json.dumps([c.model_dump(mode="json") for c in cases]))
    changed = _parameters(contract, rule_id, key, value)
    if observable == "raises":
        assert _observable(root, contract, "machine_not_executed", "held") == 0
        with pytest.raises(ModelOnexError, match="unknown kind"):
            load_facts(sorted(root.rglob("contract.yaml")), changed)
    else:
        assert _observable(root, contract, rule_id, observable) == before
        assert _observable(root, changed, rule_id, observable) == after
        assert before != after or observable == "held"


def test_runtime_resolves_the_report_writer_and_the_bus_from_the_container(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, contract = _copy("planted", tmp_path, monkeypatch)
    container = build_validator_container()
    resolved: list[type] = []
    inner = container.get_service

    def spy(protocol_type: type, service_name: str | None = None) -> object:
        resolved.append(protocol_type)
        return inner(protocol_type, service_name)

    monkeypatch.setattr(container, "get_service", spy)
    result = run_validator(
        container,
        ValidatorContractChainCoverage(contract),
        [root],
        str(tmp_path / "report.json"),
        "default",
        "repository",
    )
    assert len(result.issues) == 9
    assert resolved == [NodeValidationReportWriteEffect, ModelValidatorRuntimeBus]


def test_checker_has_no_yaml_loader() -> None:
    source = (
        _CONTRACT.parent.parent / "checker_contract_chain_coverage.py"
    ).read_text()
    for token in ("safe_load", "yaml.", "open(", "read_text"):
        assert token not in source


def test_runtime_module_has_no_call_site_construction() -> None:
    """Run the K1 call_site_construction scanner present on this base, without its path filter."""
    path = _CONTRACT.parent.parent / "validator_contract_chain_coverage.py"
    rule = next(
        r
        for r in ValidatorHandlerDi().contract.rules
        if r.rule_id == "call_site_construction"
    )
    fact = ModelHandlerDiModuleFact(
        path.relative_to(_ROOT).as_posix(), path.read_text()
    )
    assert check_module(fact, {rule.rule_id: rule}) == ()
    calls = [
        n.func for n in ast.walk(ast.parse(fact.source)) if isinstance(n, ast.Call)
    ]
    assert not any(
        isinstance(n, ast.Name)
        and n.id in {"ModelONEXContainer", "build_validator_container"}
        for n in calls
    )


def test_severity() -> None:
    data = yaml.safe_load(_CONTRACT.read_text())["validation"]
    assert data["fail_on_warning"] is False
    for row in data["rules"]:
        assert row["severity"] == "warning"
        assert not any(k.startswith("severity_") for k in row)


@pytest.mark.parametrize("fixture", ["planted", "pass"])
def test_coverage_table_publishes_fixture_denominators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixture: str
) -> None:
    """Publish per-kind denominators; comparison with omnimarket's old scripts is follow-up work."""
    root, contract = _copy(fixture, tmp_path, monkeypatch)
    facts = load_facts(sorted(root.rglob("contract.yaml")), contract)
    counts = Counter(
        row.kind.value for row in build_coverage_table(facts, contract.rules)
    )
    golden = json.loads((_FIXTURES / "golden_contract_chain_coverage.json").read_text())
    assert dict(sorted(counts.items())) == golden["denominators"][fixture]
