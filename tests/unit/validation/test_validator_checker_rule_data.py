# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""K10 checker_rule_data (OMN-21503): planted violations, clean twins, every rule parameter, purity."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_checker_rule_data_module_fact import (
    ModelCheckerRuleDataModuleFact,
)
from omnibase_core.validation import checker_checker_rule_data as checker
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "validation" / "checker_rule_data"
TABLE = "rule_table_in_checker"
FORMAT = "validator_outside_generic_format"
_T = "violation_rule_table_in_checker"
_F = "violation_validator_outside_generic_format"
_CLEAN_FORMAT = "clean_validator_outside_generic_format/checker_z.py"

# rule_id -> violation fixtures: each yields exactly one issue of that rule
VIOLATIONS: dict[str, list[str]] = {
    TABLE: [
        f"{_T}_cli/handler_x_cli.py",
        f"{_T}_base/x_base.py",
        f"{_T}_prefix/checker_p.py",
        f"{_T}_return/x_return.py",
        f"{_T}_path/validators/gate.py",
    ],
    FORMAT: [
        f"{_F}_cli/handler_x_cli.py",
        f"{_F}_report/handler_y.py",
        f"{_F}_writer/handler_w_cli.py",
    ],
}
CLEANS: dict[str, list[str]] = {
    TABLE: ["clean_rule_table_in_checker/validator_x.py"],
    FORMAT: [
        _CLEAN_FORMAT,
        "clean_validator_outside_generic_format/validator_z.py",
    ],
}
# (rule, parameter) -> (fixture, "clears" | "flags")
CONTROLS: dict[tuple[str, str], tuple[str, str]] = {
    (TABLE, "qualifying_name_prefixes"): (f"{_T}_prefix/checker_p.py", "clears"),
    (TABLE, "qualifying_path_patterns"): (f"{_T}_path/validators/gate.py", "clears"),
    (TABLE, "qualifying_base_names"): (f"{_T}_base/x_base.py", "clears"),
    (TABLE, "qualifying_return_names"): (f"{_T}_return/x_return.py", "clears"),
    (TABLE, "cli_gate_name_pattern"): (f"{_T}_cli/handler_x_cli.py", "clears"),
    (TABLE, "writer_markers"): (f"{_T}_cli/handler_x_cli.py", "clears"),
    (TABLE, "constant_name_pattern"): (f"{_T}_base/x_base.py", "clears"),
    (TABLE, "collection_calls"): (f"{_T}_base/x_base.py", "clears"),
    (TABLE, "min_string_words"): (f"{_T}_cli/handler_x_cli.py", "clears"),
    (FORMAT, "one_off_name_pattern"): (f"{_F}_cli/handler_x_cli.py", "clears"),
    (FORMAT, "one_off_markers"): (f"{_F}_cli/handler_x_cli.py", "clears"),
    (FORMAT, "writer_markers"): (f"{_F}_writer/handler_w_cli.py", "clears"),
    (FORMAT, "report_markers"): (f"{_F}_cli/handler_x_cli.py", "clears"),
    (FORMAT, "report_return_names"): (f"{_F}_report/handler_y.py", "clears"),
    (FORMAT, "checker_prefix"): (_CLEAN_FORMAT, "flags"),
    (FORMAT, "validator_prefix"): (_CLEAN_FORMAT, "flags"),
    (FORMAT, "contract_suffix"): (_CLEAN_FORMAT, "flags"),
}


def _contract() -> ModelValidatorSubcontract:
    contract = ValidatorCheckerRuleData().contract
    # the planted fixtures sit under tests/, which the shipped contract excludes
    return contract.model_copy(update={"exclude_patterns": []})


def _codes(
    fixture: str, rule_id: str, contract: ModelValidatorSubcontract | None = None
) -> list[str]:
    validator = ValidatorCheckerRuleData(contract=contract or _contract())
    issues = validator.validate(FIXTURES / fixture).issues
    return [str(i.code) for i in issues if i.code == rule_id]


def _mutated(rule_id: str, key: str) -> ModelValidatorSubcontract:
    contract = _contract()
    rows = []
    for row in contract.rules:
        if row.rule_id == rule_id and row.parameters and key in row.parameters:
            params = dict(row.parameters)
            current = params[key]
            params[key] = (
                ["(?!)"]
                if isinstance(current, list)
                else 99
                if isinstance(current, int)
                else "(?!)"
            )
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    return contract.model_copy(update={"rules": rows})


@pytest.mark.parametrize(
    ("rule_id", "fixture"),
    [(r, f) for r, fixtures in VIOLATIONS.items() for f in fixtures],
)
def test_violation_fixture_yields_exactly_one_issue(rule_id: str, fixture: str) -> None:
    assert _codes(fixture, rule_id) == [rule_id]


@pytest.mark.parametrize(
    ("rule_id", "fixture"),
    [(r, f) for r, fixtures in CLEANS.items() for f in fixtures],
)
def test_clean_fixture_yields_nothing(rule_id: str, fixture: str) -> None:
    assert _codes(fixture, rule_id) == []


def test_planted_remediation_and_allowlist_are_named() -> None:
    cli = ValidatorCheckerRuleData(contract=_contract()).validate(
        FIXTURES / f"{_T}_cli/handler_x_cli.py"
    )
    base = ValidatorCheckerRuleData(contract=_contract()).validate(
        FIXTURES / f"{_T}_base/x_base.py"
    )
    assert [i.message.split()[0] for i in cli.issues] == ["_REMEDIATION"]
    assert [i.message.split()[0] for i in base.issues] == ["INFRA_ALLOWLIST"]


def test_every_parameter_of_every_rule_row_has_a_control() -> None:
    declared = {(r.rule_id, k) for r in _contract().rules for k in (r.parameters or {})}
    assert declared == set(CONTROLS)


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(rule_id: str, key: str) -> None:
    fixture, direction = CONTROLS[(rule_id, key)]
    expected = [] if direction == "clears" else [rule_id]
    assert _codes(fixture, rule_id, _mutated(rule_id, key)) == expected


@pytest.mark.parametrize("rule_id", sorted(VIOLATIONS))
def test_disabling_a_rule_row_clears_its_fixtures(rule_id: str) -> None:
    contract = _contract()
    rows = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    disabled = contract.model_copy(update={"rules": rows})
    for fixture in VIOLATIONS[rule_id]:
        assert _codes(fixture, rule_id, disabled) == []


def test_invalid_contract_fails_instead_of_passing() -> None:
    rows = {
        r.rule_id: r.model_copy(update={"parameters": {}}) for r in _contract().rules
    }
    fact = ModelCheckerRuleDataModuleFact(
        "checker_p.py", "checker_p.py", "X = frozenset({1})\n", frozenset(), frozenset()
    )
    with pytest.raises(ModelOnexError, match="qualifying_name_prefixes"):
        checker.check_module(Path("checker_p.py"), fact, rows)


def test_checker_is_pure_over_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("checker performed I/O")

    rules = {r.rule_id: r for r in _contract().rules}
    fact = ModelCheckerRuleDataModuleFact(
        "checker_p.py",
        "checker_p.py",
        'X = frozenset({"a"})\n',
        frozenset(),
        frozenset(),
    )
    with monkeypatch.context() as patched:
        patched.setattr("builtins.open", refuse)
        patched.setattr(Path, "read_text", refuse)
        patched.setattr(Path, "iterdir", refuse)
        issues = checker.check_module(Path("checker_p.py"), fact, rules)
    assert [i.code for i in issues] == [TABLE]


@pytest.mark.parametrize(
    ("relative", "constants"),
    [
        (
            "src/omnibase_core/validators/contract_config_compliance.py",
            {"INFRA_ALLOWLIST", "_EXCLUDED_PATH_PARTS", "_DEFAULT_SCAN_ROOTS"},
        ),
        (
            "src/omnibase_core/validators/handler_di_gate.py",
            {
                "_EXCLUDED_PATH_PARTS",
                "_CONTAINER_RESOLUTION_ATTRS",
                "_DEFAULT_SCAN_ROOTS",
            },
        ),
    ],
)
def test_reports_the_constants_still_held_by_the_gates(
    relative: str, constants: set[str]
) -> None:
    issues = ValidatorCheckerRuleData().validate(ROOT / relative).issues
    assert {i.message.split()[0] for i in issues} == constants


@pytest.mark.parametrize(
    "module",
    [
        "checker_checker_rule_data",
        "checker_rule_parameters",
        "checker_validator_home",
        "validator_checker_rule_data",
        "validator_validator_home",
    ],
)
def test_the_new_checkers_hold_no_rule_table(module: str) -> None:
    path = ROOT / "src" / "omnibase_core" / "validation" / f"{module}.py"
    assert ValidatorCheckerRuleData().validate(path).issues == []
