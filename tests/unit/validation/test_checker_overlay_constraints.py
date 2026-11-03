# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the overlay-constraints checker and its generic validator (OMN-22185, AC2).

A contract declares relations between overlay keys. A mutated overlay that violates a relation
is refused with a diagnostic naming the relation; the unmutated overlay passes. The relations
exercised are the lane lander's R1 ``hold_s <= lease_seconds`` and R2 (two minimums of one).
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
from omnibase_core.models.overlay_constraints import (
    ModelOverlayConstraintsCheckInput,
    ModelOverlayConstraintsCheckResult,
    ModelOverlayConstraintsDeclaration,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation import checker_overlay_constraints as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_overlay_constraints import (
    check_overlay_constraints,
)
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_overlay_constraints import (
    ValidatorOverlayConstraints,
)

pytestmark = pytest.mark.unit

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "validation"
    / "overlay_constraints"
    / "lander_contract.yaml"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "overlay_constraints.validation.yaml"
)
PACKAGE_ROOT = Path(validator_base.__file__).parent.parent
PRODUCTION_SOURCES = (
    "validation/checker_overlay_constraints.py",
    "validation/validator_overlay_constraints.py",
    *(
        f"models/overlay_constraints/{path.name}"
        for path in sorted(
            (PACKAGE_ROOT / "models" / "overlay_constraints").glob("*.py")
        )
    ),
)
RULE_IDS = {
    "relation_violated",
    "key_absent",
    "value_not_numeric",
    "relation_malformed",
}


def _document() -> dict[str, Any]:
    loaded = yaml.safe_load(FIXTURE.read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _flat(document: dict[str, Any]) -> dict[str, object]:
    return {
        k: v for keys in document["overlay_values"].values() for k, v in keys.items()
    }


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None] | None = None,
) -> ModelValidatorSubcontract:
    raw = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: rule for rule in copy.deepcopy(raw["rules"])}
    if mutate:
        mutate(rules)
    raw = {**raw, "rules": list(rules.values())}
    return ModelValidatorSubcontract.model_validate(raw)


def check(
    document: dict[str, Any] | None = None,
    *,
    values: dict[str, object] | None = None,
    contract: ModelValidatorSubcontract | None = None,
) -> ModelOverlayConstraintsCheckResult:
    document = document or _document()
    return check_overlay_constraints(
        ModelOverlayConstraintsCheckInput(
            source_name="node/contract.yaml",
            declaration=ModelOverlayConstraintsDeclaration.model_validate(
                document["overlay_constraints"]
            ),
            values=_flat(document) if values is None else values,
            contract=contract or _contract_with(),
        )
    )


def _mutated(**changes: object) -> dict[str, object]:
    values = _flat(_document())
    values.update(changes)
    return values


# --- AC2: the unmutated overlay passes (positive control) ---


def test_overlay_constraints_admits_the_unmutated_overlay() -> None:
    result = check()
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.relations_checked == 3


def test_overlay_constraints_admits_a_hold_exactly_at_the_lease() -> None:
    """The relation is <=, so equality holds."""
    assert check(values=_mutated(run_s=690)).issues == ()


# --- AC2: a mutated overlay violating R1 or R2 is refused naming the relation ---


def test_overlay_constraints_refuses_r1_when_the_hold_exceeds_the_lease() -> None:
    result = check(values=_mutated(run_s=691))
    assert [i.code for i in result.issues] == ["relation_violated"]
    assert result.issues[0].context["relation"] == "R1"
    assert "R1" in result.issues[0].message
    assert "hold_s <= lease_seconds" in result.issues[0].message
    assert "901 <= 900" in result.issues[0].message
    assert result.exit_code == 1


def test_overlay_constraints_refuses_r1_when_the_lease_shrinks() -> None:
    result = check(values=_mutated(lease_seconds=100))
    assert [i.context["relation"] for i in result.issues] == ["R1"]


@pytest.mark.parametrize(
    ("key", "relation"),
    [("permit_min_ladder_steps", "R2a"), ("permit_min_head_dispatches", "R2b")],
)
@pytest.mark.parametrize("bad", [0, -1])
def test_overlay_constraints_refuses_r2_when_a_permit_minimum_is_below_one(
    key: str, relation: str, bad: int
) -> None:
    result = check(values=_mutated(**{key: bad}))
    assert [i.code for i in result.issues] == ["relation_violated"]
    assert result.issues[0].context["relation"] == relation
    assert relation in result.issues[0].message


def test_overlay_constraints_reports_every_violated_relation() -> None:
    result = check(
        values=_mutated(
            lease_seconds=1, permit_min_ladder_steps=0, permit_min_head_dispatches=0
        )
    )
    assert [i.context["relation"] for i in result.issues] == ["R1", "R2a", "R2b"]


# --- absent and non-numeric keys are refused, never assumed zero ---


def test_overlay_constraints_refuses_an_absent_key_naming_the_relation_and_key() -> (
    None
):
    values = _flat(_document())
    del values["drain_s"]
    result = check(values=values)
    assert [i.code for i in result.issues] == ["key_absent"]
    assert result.issues[0].context["relation"] == "R1"
    assert result.issues[0].context["key"] == "drain_s"
    assert result.relations_checked == 2


@pytest.mark.parametrize("bad", ["600", None, True, [1]])
def test_overlay_constraints_refuses_a_non_numeric_value(bad: object) -> None:
    result = check(values=_mutated(run_s=bad))
    assert [i.code for i in result.issues] == ["value_not_numeric"]
    assert result.issues[0].context["key"] == "run_s"


# --- malformed relations ---


@pytest.mark.parametrize(
    "expression",
    ["hold_s", "hold_s <= lease_seconds <= 5", "hold_s <= lease seconds", "a + <= 2"],
)
def test_overlay_constraints_refuses_a_malformed_relation(expression: str) -> None:
    document = _document()
    document["overlay_constraints"]["relations"][0]["expression"] = expression
    result = check(document)
    assert result.issues[0].code == "relation_malformed"
    assert result.issues[0].context["relation"] == "R1"


def test_overlay_constraints_refuses_a_derived_name_defined_by_another_derived_name() -> (
    None
):
    document = _document()
    document["overlay_constraints"]["derived"]["outer"] = "hold_s + 1"
    document["overlay_constraints"]["relations"][0]["expression"] = (
        "outer <= lease_seconds"
    )
    assert check(document).issues[0].code == "relation_malformed"


def test_overlay_constraints_refuses_duplicate_relation_names() -> None:
    document = _document()
    document["overlay_constraints"]["relations"][1]["relation_name"] = "R1"
    with pytest.raises(ValueError, match="duplicate relation ids"):
        check(document)


def test_overlay_constraints_supports_every_comparison_operator() -> None:
    for operator_text, holds in [
        ("<", True),
        ("<=", True),
        (">", False),
        (">=", False),
        ("==", False),
    ]:
        document = _document()
        document["overlay_constraints"]["relations"] = [
            {"relation_name": "X", "expression": f"drain_s {operator_text} run_s"}
        ]
        assert (check(document).issues == ()) is holds, operator_text


# --- contract data: disabled rows, fail-closed loading ---


def test_overlay_constraints_committed_contract_holds_every_rule_at_error_severity() -> (
    None
):
    contract = _contract_with()
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    assert all(
        rule.enabled and rule.severity.is_error_or_above() for rule in contract.rules
    )


def test_overlay_constraints_disabled_rule_row_silences_its_issue() -> None:
    def disable(rules: dict[str, dict[str, Any]]) -> None:
        rules["relation_violated"]["enabled"] = False

    result = check(values=_mutated(lease_seconds=1), contract=_contract_with(disable))
    assert result.issues == ()
    assert result.exit_code == 0


def test_overlay_constraints_operators_are_contract_data() -> None:
    def narrow(rules: dict[str, dict[str, Any]]) -> None:
        rules["relation_malformed"]["parameters"]["operators"] = [">="]

    result = check(contract=_contract_with(narrow))
    assert result.issues[0].code == "relation_malformed"
    assert result.issues[0].context["relation"] == "R1"


@pytest.mark.parametrize(
    ("rule_id", "name", "value"),
    [
        ("relation_violated", "message", None),
        ("key_absent", "message", ""),
        ("relation_malformed", "operators", []),
        ("relation_malformed", "identifier_pattern", "("),
        ("relation_malformed", "number_pattern", None),
        ("relation_malformed", "sum_separator", None),
    ],
)
def test_overlay_constraints_invalid_contracts_fail_to_load(
    rule_id: str, name: str, value: object
) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        if value is None:
            rules[rule_id]["parameters"].pop(name)
        else:
            rules[rule_id]["parameters"][name] = value

    with pytest.raises(ModelOnexError):
        check(contract=_contract_with(mutate))


def test_overlay_constraints_a_missing_rule_fails_to_load() -> None:
    def drop(rules: dict[str, dict[str, Any]]) -> None:
        rules.pop("key_absent")

    with pytest.raises(ModelOnexError, match="required rule is absent"):
        check(contract=_contract_with(drop))


def test_overlay_constraints_a_non_comparison_operator_fails_loudly() -> None:
    def swap(rules: dict[str, dict[str, Any]]) -> None:
        rules["relation_malformed"]["parameters"]["operators"] = ["<=", "@"]

    document = _document()
    document["overlay_constraints"]["relations"][0]["expression"] = (
        "hold_s @ lease_seconds"
    )
    with pytest.raises(ModelOnexError, match="comparison operator"):
        check(document, contract=_contract_with(swap))


# --- generic, pure, no repository name or overlay key in code ---


def test_overlay_constraints_checker_reads_no_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document, contract, values = (
        _document(),
        _contract_with(),
        _mutated(lease_seconds=1),
    )

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    assert check(document, values=values, contract=contract).exit_code == 1


def test_overlay_constraints_no_hardcoded_overlay_key_or_repository_name() -> None:
    forbidden = re.compile(
        r"OmniNode|omnibase|omnimarket|lander|lease|hold_s|permit|_s\b|permit_min",
        re.IGNORECASE,
    )
    offenders: list[str] = []
    for relative in PRODUCTION_SOURCES:
        source = (PACKAGE_ROOT / relative).read_text("utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if forbidden.search(node.value):
                    offenders.append(f"{relative}:{node.lineno}: {node.value!r}")
    assert len(PRODUCTION_SOURCES) >= 8
    assert offenders == []


def test_overlay_constraints_no_hardcoded_positive_control() -> None:
    """The scan above finds a planted overlay key and repository name."""
    planted = 'X = "omnibase_infra"\nY = "hold_s"\n'
    found = [
        node.value
        for node in ast.walk(ast.parse(planted))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.search(r"omnibase|hold_s", node.value)
    ]
    assert found == ["omnibase_infra", "hold_s"]


def test_overlay_constraints_no_hardcoded_rule_tables_k10_clean() -> None:
    triple = (
        PACKAGE_ROOT / "validation" / "checker_overlay_constraints.py",
        PACKAGE_ROOT / "validation" / "validator_overlay_constraints.py",
        CONTRACT_PATH,
    )
    assert all(path.is_file() for path in triple)
    assert ValidatorCheckerRuleData().validate(list(triple[:2])).issues == []
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
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


# --- the generic file validator reads the block and values from one contract file ---


def _write(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(document), "utf-8")
    return path


def test_overlay_constraints_validator_refuses_a_mutated_overlay_through_the_runtime_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document()
    document["overlay_values"]["landing_controller"]["lease_seconds"] = 100
    path = _write(tmp_path, document)
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "report.json"
    exit_code = main(
        ValidatorOverlayConstraints,
        [str(path), "--report-json", str(report_path)],
        build_validator_container,
    )
    report = json.loads(report_path.read_text("utf-8"))
    assert exit_code == 1
    assert [f["rule_id"] for f in report["findings"]] == ["relation_violated"]
    assert "R1" in report["findings"][0]["message"]


def test_overlay_constraints_validator_admits_the_unmutated_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, _document())
    monkeypatch.chdir(tmp_path)
    assert ValidatorOverlayConstraints().validate_file(path).issues == []


def test_overlay_constraints_validator_does_not_judge_a_contract_without_the_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, {"name": "node_x", "overlay_values": {"o": {"k": 1}}})
    monkeypatch.chdir(tmp_path)
    assert ValidatorOverlayConstraints().validate_file(path).issues == []


def test_overlay_constraints_validator_with_no_values_refuses_every_named_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document()
    del document["overlay_values"]
    path = _write(tmp_path, document)
    monkeypatch.chdir(tmp_path)
    issues = ValidatorOverlayConstraints().validate_file(path).issues
    assert {i.code for i in issues} == {"key_absent"}
    assert {i.context["relation"] for i in issues} == {"R1", "R2a", "R2b"}


def test_overlay_constraints_validator_refuses_a_key_set_to_two_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = _document()
    document["overlay_values"]["landing_controller"]["run_s"] = 1
    path = _write(tmp_path, document)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ModelOnexError, match="two different values"):
        ValidatorOverlayConstraints().validate_file(path)
