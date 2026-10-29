# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the inline-logic rules in the generic validator format (OMN-21534, K9).

A program written inline in a workflow ``run:`` block or in a contract ``check_value`` is
refused. The checker is pure; the validator reads a workflow or ticket contract; every
pattern, threshold and remediation text is a ``parameters`` entry of a rule row of
``inline_logic.validation.yaml``. These tests load that contract, so the values that gate
the repository are the values under test.
"""

from __future__ import annotations

import builtins
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
from omnibase_core.models.inline_logic.model_inline_logic_check_value import (
    ModelInlineLogicCheckValue,
)
from omnibase_core.models.inline_logic.model_inline_logic_run_step import (
    ModelInlineLogicRunStep,
)
from omnibase_core.validation.checker_inline_logic import check_inline_logic
from omnibase_core.validation.validator_inline_logic import ValidatorInlineLogic

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/inline_logic.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/inline_logic"
_MARK = "zzz-marker"
_NEVER = r"\bnever-matches-zzz\b"
_BIG = 100000


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_rule(
    contract: ModelValidatorSubcontract, rule_id: str, **changes: object
) -> ModelValidatorSubcontract:
    rules = [
        rule.model_copy(update=changes) if rule.rule_id == rule_id else rule
        for rule in contract.rules
    ]
    return contract.model_copy(update={"rules": rules})


def _with_parameter(
    contract: ModelValidatorSubcontract, rule_id: str, key: str, value: object | None
) -> ModelValidatorSubcontract:
    rule = next(r for r in contract.rules if r.rule_id == rule_id)
    parameters = dict(rule.parameters or {})
    if value is None:
        del parameters[key]
    else:
        parameters[key] = cast(RuleParameterValue, value)
    return _with_rule(contract, rule_id, parameters=parameters)


def _issues(
    contract: ModelValidatorSubcontract, path: Path
) -> list[ModelValidationIssue]:
    return list(ValidatorInlineLogic(contract=contract).validate_file(path).issues)


def _fixture(prefix: str, rule_id: str) -> Path:
    return next(_FIXTURES.glob(f"{prefix}_{rule_id}.*"))


def _workflow(run: str, step_shell: str | None = None) -> str:
    shell_line = f"        shell: {step_shell}\n" if step_shell else ""
    body = "".join(f"          {line}\n" for line in run.splitlines())
    return (
        "name: t\non: push\njobs:\n  work:\n    runs-on: x\n    steps:\n"
        f"      - name: s\n{shell_line}        run: |\n{body}"
    )


def _check(value: str) -> str:
    body = "".join(f"          {line}\n" for line in value.splitlines())
    return (
        "ticket_id: OMN-1\ndod_evidence:\n  - id: e1\n    checks:\n"
        f"      - check_type: command\n        check_value: |\n{body}"
    )


def _write(tmp_path: Path, source: str, name: str = "wf.yml") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


_RULES = [rule.rule_id for rule in _contract().rules]


def _rule(rule_id: str) -> dict[str, RuleParameterValue]:
    rule = next(r for r in _contract().rules if r.rule_id == rule_id)
    return dict(rule.parameters or {})


def test_the_contract_holds_the_four_k9_rules() -> None:
    assert _RULES == [
        "inline_python",
        "run_block_length",
        "inline_loop",
        "inline_program",
    ]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _issues(_contract(), _fixture("violation", rule_id))
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert [issue.code for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _issues(_contract(), _fixture("clean", rule_id)) == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(rule_id: str) -> None:
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _issues(contract, _fixture("violation", rule_id)) == []


def test_the_shell_python_matrix_step_is_refused() -> None:
    """AC1, workflow half: a ``run:`` step with ``shell: python`` building a matrix."""
    issues = _issues(_contract(), _fixture("violation", "inline_python"))
    assert len(issues) == 1 and "build matrix" in issues[0].message


def test_the_25_line_python_c_check_value_is_refused() -> None:
    """AC1, contract half: a ``check_value`` holding a 25-line ``python3 -c``."""
    fixture = _fixture("violation", "inline_program")
    value = yaml.safe_load(fixture.read_text(encoding="utf-8"))["dod_evidence"][0][
        "checks"
    ][0]["check_value"]
    assert len(value.strip().splitlines()) == 25
    issues = _issues(_contract(), fixture)
    assert [issue.rule_name for issue in issues] == ["inline_program"]


def _parameter_cases() -> list[tuple[str, str]]:
    return [
        (rule.rule_id, key)
        for rule in _contract().rules
        for key in sorted(rule.parameters or {})
    ]


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_every_parameter_key_changes_the_verdict_it_controls(
    tmp_path: Path, rule_id: str, key: str
) -> None:
    """Mutate each ``parameters`` key of each rule row in turn; the verdict follows."""
    contract = _contract()
    violation = _fixture("violation", rule_id)
    if key in {"reason", "remediation"}:
        issues = _issues(_with_parameter(contract, rule_id, key, _MARK), violation)
        assert len(issues) == 1 and _MARK in issues[0].message
    elif key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _issues(_with_parameter(contract, rule_id, key, "bogus"), violation)
    elif key == "shell_pattern":
        path = _write(tmp_path, _workflow("echo hi", step_shell="python"))
        assert len(_issues(contract, path)) == 1
        assert _issues(_with_parameter(contract, rule_id, key, _NEVER), path) == []
    elif key in {"run_pattern", "program_pattern"}:
        mutated = _with_parameter(contract, rule_id, key, _NEVER)
        if rule_id == "inline_python":
            violation = _write(tmp_path, _workflow("python3 -c 'print(1)'"))
            assert len(_issues(contract, violation)) == 1
        assert _issues(mutated, violation) == []
    elif key == "max_run_lines":
        path = _fixture("clean", rule_id)
        assert _issues(_with_parameter(contract, rule_id, key, 1), path) != []
        assert _issues(_with_parameter(contract, rule_id, key, _BIG), violation) == []
    elif key == "max_inline_chars":
        one_line = _write(tmp_path, _check('python3 -c "print(1)"'), "c.yaml")
        assert _issues(contract, one_line) == []
        assert _issues(_with_parameter(contract, rule_id, key, 5), one_line) != []
        long_value = _write(
            tmp_path, _check("python3 -c '" + "x" * 300 + "'"), "l.yaml"
        )
        assert len(_issues(contract, long_value)) == 1
        assert _issues(_with_parameter(contract, rule_id, key, _BIG), long_value) == []
    elif key == "refuse_newline":
        assert len(_issues(contract, violation)) == 1
        mutated = _with_parameter(contract, rule_id, "max_inline_chars", _BIG)
        assert len(_issues(mutated, violation)) == 1
        mutated = _with_parameter(mutated, rule_id, key, False)
        assert _issues(mutated, violation) == []
    else:
        pytest.fail(f"no mutation case for parameter {key!r} of {rule_id}")


_OPTIONAL_KEYS = {
    "inline_python": {"shell_pattern", "run_pattern"},
    "inline_loop": {"shell_pattern", "run_pattern"},
}


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [
        case
        for case in _parameter_cases()
        if case[1] not in _OPTIONAL_KEYS.get(case[0], set())
    ],
)
def test_a_rule_row_missing_a_required_key_fails_to_load(
    rule_id: str, key: str
) -> None:
    """An invalid contract raises rather than passing."""
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        _issues(mutated, _fixture("violation", rule_id))


@pytest.mark.parametrize("rule_id", ["inline_python", "inline_loop"])
def test_a_signal_row_with_neither_pattern_fails_to_load(rule_id: str) -> None:
    parameters = {
        key: value
        for key, value in _rule(rule_id).items()
        if key not in {"run_pattern", "shell_pattern"}
    }
    contract = _with_rule(_contract(), rule_id, parameters=parameters)
    with pytest.raises(ModelOnexError, match="needs"):
        _issues(contract, _fixture("violation", rule_id))


@pytest.mark.parametrize(
    ("rule_id", "key", "value"),
    [
        ("inline_python", "run_pattern", "("),
        ("inline_python", "shell_pattern", "("),
        ("inline_program", "program_pattern", "("),
        ("run_block_length", "max_run_lines", 0),
        ("run_block_length", "max_run_lines", "many"),
        ("inline_program", "max_inline_chars", 0),
        ("inline_program", "refuse_newline", "yes"),
    ],
)
def test_an_unreadable_parameter_fails_to_load(
    rule_id: str, key: str, value: object
) -> None:
    mutated = _with_parameter(_contract(), rule_id, key, value)
    with pytest.raises(ModelOnexError):
        _issues(mutated, _fixture("violation", rule_id))


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker runs with ``open`` and the Path reads patched to raise."""
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    steps = (
        ModelInlineLogicRunStep.model_validate(
            {"job": "j", "step": "s", "shell": "python", "run": "x = 1"}
        ),
    )
    values = (
        ModelInlineLogicCheckValue(evidence_ref="e", check_value="bash -c 'a\nb'"),
    )
    issues = check_inline_logic(Path("x.yml"), steps, values, rules)
    assert [i.rule_name for i in issues] == ["inline_python", "inline_program"]


@pytest.mark.parametrize(
    "run",
    [
        "python3 -c 'print(1)'",
        "uv run python -c 'print(1)'",
        "python3 - <<'PY'\nprint(1)\nPY",
        "python <<EOF\nprint(1)\nEOF",
    ],
)
def test_python_in_a_run_block_is_refused(tmp_path: Path, run: str) -> None:
    issues = _issues(_contract(), _write(tmp_path, _workflow(run)))
    assert [i.rule_name for i in issues] == ["inline_python"]


@pytest.mark.parametrize(
    "run",
    [
        "uv run python -m pytest tests/",
        "python3 scripts/tool.py --flag",
        "uv run onex run-node node_x",
        "echo for the record",
    ],
)
def test_a_named_command_in_a_run_block_passes(tmp_path: Path, run: str) -> None:
    assert _issues(_contract(), _write(tmp_path, _workflow(run))) == []


@pytest.mark.parametrize(
    "keyword", ["for i in 1 2; do", "while true; do", "until x; do"]
)
def test_loops_in_a_run_block_are_refused(tmp_path: Path, keyword: str) -> None:
    issues = _issues(_contract(), _write(tmp_path, _workflow(f"{keyword}\n  :\ndone")))
    assert [i.rule_name for i in issues] == ["inline_loop"]


def test_the_default_shell_of_a_job_is_the_steps_shell(tmp_path: Path) -> None:
    source = (
        "name: t\non: push\njobs:\n  work:\n    runs-on: x\n"
        "    defaults:\n      run:\n        shell: python\n"
        "    steps:\n      - run: x = 1\n"
    )
    issues = _issues(_contract(), _write(tmp_path, source))
    assert [i.rule_name for i in issues] == ["inline_python"]


def test_a_short_bash_c_check_value_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _check("bash -c 'test -f a'"), "c.yaml")
    assert _issues(_contract(), path) == []


def test_a_multi_line_value_without_a_program_passes(tmp_path: Path) -> None:
    path = _write(tmp_path, _check("uv run pytest a \\\n  b -q"), "c.yaml")
    assert _issues(_contract(), path) == []


@pytest.mark.parametrize("source", ["jobs: [unclosed", "just a string", "other: 1\n"])
def test_unreadable_file_raises(tmp_path: Path, source: str) -> None:
    with pytest.raises(ModelOnexError):
        _issues(_contract(), _write(tmp_path, source))


def test_scan_set_is_rule_data() -> None:
    contract = _contract()
    assert contract.target_patterns == [
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        "contracts/OMN-*.yaml",
    ]
    assert "tests/fixtures/validation/inline_logic/**" in contract.exclude_patterns


def test_the_k9_rule_ids_are_the_rule_table_of_the_contract() -> None:
    assert _rule("run_block_length")["max_run_lines"] == 15
    assert _rule("inline_program")["max_inline_chars"] == 200
