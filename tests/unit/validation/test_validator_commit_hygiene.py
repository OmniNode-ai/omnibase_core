# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for K8 ``commit_hygiene`` in the generic validator format (OMN-21498).

Four refusals, none of which writes: ``missing_final_newline``,
``extra_final_newline``, ``staged_tmp_file`` and ``ai_coauthor_trailer``. The
checker is pure; the trailer pattern, the refused path pattern and every
remediation text are ``parameters`` entries of the rule rows of
``commit_hygiene.validation.yaml``, which these tests load.
"""

from __future__ import annotations

import builtins
import hashlib
from pathlib import Path
from typing import cast

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_commit_hygiene import check_commit_hygiene
from omnibase_core.validation.validator_commit_hygiene import ValidatorCommitHygiene

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/commit_hygiene.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/commit_hygiene"
_MARK = "zzz-marker"
# The relative path is a fact the hook supplies; two rules judge it.
_FACT_PATH = {
    "staged_tmp_file": ("tmp/scratch.txt", "src/scratch.txt"),
    "ai_coauthor_trailer": (".git/COMMIT_EDITMSG", ".git/COMMIT_EDITMSG"),
}


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_parameter(
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


def _check(
    contract: ModelValidatorSubcontract, rule_id: str, *, planted: bool
) -> list[ModelValidationIssue]:
    prefix = "violation" if planted else "clean"
    path = _FIXTURES / f"{prefix}_{rule_id}.txt"
    default = path.name
    relative = _FACT_PATH.get(rule_id, (default, default))[0 if planted else 1]
    return list(check_commit_hygiene(path, relative, path.read_bytes(), contract.rules))


_RULES = [rule.rule_id for rule in _contract().rules]


def test_the_four_k8_rules_are_the_contracts_rows() -> None:
    assert _RULES == [
        "missing_final_newline",
        "extra_final_newline",
        "staged_tmp_file",
        "ai_coauthor_trailer",
    ]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _check(_contract(), rule_id, planted=True)
    assert [issue.rule_name for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _check(_contract(), rule_id, planted=False) == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(rule_id: str) -> None:
    contract = _contract()
    rules = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    mutated = contract.model_copy(update={"rules": rules})
    assert _check(mutated, rule_id, planted=True) == []


def _parameter_cases() -> list[tuple[str, str]]:
    return [
        (rule.rule_id, key)
        for rule in _contract().rules
        for key in sorted(rule.parameters or {})
    ]


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_every_parameter_key_changes_the_verdict_it_controls(
    rule_id: str, key: str
) -> None:
    contract = _contract()
    if key == "remediation":
        issues = _check(
            _with_parameter(contract, rule_id, key, _MARK), rule_id, planted=True
        )
        assert len(issues) == 1 and _MARK in issues[0].message
    elif key == "path_pattern":
        mutated = _with_parameter(contract, rule_id, key, r"^never-matches-zzz$")
        assert _check(mutated, rule_id, planted=True) == []
    elif key == "line_pattern":
        mutated = _with_parameter(contract, rule_id, key, r"never-matches-zzz")
        assert _check(mutated, rule_id, planted=True) == []
    elif key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _check(
                _with_parameter(contract, rule_id, key, "bogus"), rule_id, planted=True
            )
    else:
        pytest.fail(f"no mutation case for parameter {key!r} of {rule_id}")


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_a_rule_row_missing_a_key_fails_to_load(rule_id: str, key: str) -> None:
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        _check(mutated, rule_id, planted=True)


def test_a_pattern_that_does_not_compile_fails_to_load() -> None:
    mutated = _with_parameter(_contract(), "ai_coauthor_trailer", "line_pattern", "(")
    with pytest.raises(ModelOnexError, match="regular expression"):
        _check(mutated, "ai_coauthor_trailer", planted=True)


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    issues = check_commit_hygiene(Path("a.txt"), "a.txt", b"no newline", rules)
    assert [i.rule_name for i in issues] == ["missing_final_newline"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"", []),
        (b"x\n", []),
        (b"x", ["missing_final_newline"]),
        (b"x\n\n", ["extra_final_newline"]),
        (b"x\n\n\n", ["extra_final_newline"]),
        (b"\x00\x01 binary", []),
    ],
)
def test_final_newline_shapes(content: bytes, expected: list[str]) -> None:
    issues = check_commit_hygiene(Path("a"), "a", content, _contract().rules)
    assert [i.rule_name for i in issues] == expected


@pytest.mark.parametrize(
    ("trailer", "refused"),
    [
        ("Co-Authored-By: Claude <noreply@anthropic.com>", True),
        ("co-authored-by: Claude Opus 5 <noreply@anthropic.com>", True),
        ("Co-Authored-By: A Person <person@example.invalid>", False),
    ],
)
def test_trailer_pattern(trailer: str, refused: bool) -> None:
    message = f"feat: x\n\n{trailer}\n".encode()
    issues = check_commit_hygiene(
        Path("m"), ".git/COMMIT_EDITMSG", message, _contract().rules
    )
    assert bool(issues) is refused
    assert all(issue.line_number == 3 for issue in issues)


def test_tmp_rule_judges_only_the_staged_path() -> None:
    rules = _contract().rules
    assert check_commit_hygiene(Path("x"), "src/tmp/x.txt", b"x\n", rules) == ()
    refused = check_commit_hygiene(Path("x"), "tmp/x.txt", b"x\n", rules)
    assert [i.rule_name for i in refused] == ["staged_tmp_file"]


def test_the_validator_reads_and_never_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "notes.txt"
    target.write_bytes(b"no final newline")
    monkeypatch.chdir(tmp_path)
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    result = ValidatorCommitHygiene().validate_file(target)
    assert [i.rule_name for i in result.issues] == ["missing_final_newline"]
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_planted_fixtures_are_excluded_by_the_contracts_exclude_patterns() -> None:
    validator = ValidatorCommitHygiene(contract=_contract())
    assert validator.validate_file(
        _FIXTURES / "violation_missing_final_newline.txt"
    ).is_valid
