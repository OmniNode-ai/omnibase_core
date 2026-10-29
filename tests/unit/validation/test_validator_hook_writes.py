# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the hook-writes rule in the generic validator format (OMN-21498, T2.6).

A pre-commit hook must check, never rewrite. The checker is pure; the validator
reads a hook file; every pattern, hook id and remediation text is a ``parameters``
entry of a rule row of ``hook_writes.validation.yaml``. These tests load that
contract, so the values that gate the repository are the values under test.
"""

from __future__ import annotations

import builtins
import json
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
from omnibase_core.models.hook_writes.model_hook_writes_hook import ModelHookWritesHook
from omnibase_core.validation.checker_hook_writes import check_hook_writes
from omnibase_core.validation.validator_hook_writes import ValidatorHookWrites

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _ROOT / "src/omnibase_core/validation/contracts/hook_writes.validation.yaml"
_FIXTURES = _ROOT / "tests/fixtures/validation/hook_writes"
_MARK = "zzz-marker"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_rule(
    contract: ModelValidatorSubcontract, rule_id: str, **changes: object
) -> ModelValidatorSubcontract:
    """The contract with one rule row changed (``parameters`` replaced when given)."""
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
    return list(ValidatorHookWrites(contract=contract).validate_file(path).issues)


def _write(tmp_path: Path, source: str, name: str = ".pre-commit-config.yaml") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _local(*hooks: str) -> str:
    return "repos:\n  - repo: local\n    hooks:\n" + "".join(hooks)


def _hook(hook_id: str, entry: str, extra: str = "") -> str:
    return (
        f"      - id: {hook_id}\n"
        f"        name: {hook_id}\n"
        f"        entry: {json.dumps(entry)}\n"
        "        language: system\n" + extra
    )


_RULES = [rule.rule_id for rule in _contract().rules]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _issues(_contract(), _FIXTURES / f"violation_{rule_id}.yaml")
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert [issue.code for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _issues(_contract(), _FIXTURES / f"clean_{rule_id}.yaml") == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(rule_id: str) -> None:
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _issues(contract, _FIXTURES / f"violation_{rule_id}.yaml") == []


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
    violation = _FIXTURES / f"violation_{rule_id}.yaml"
    clean = _FIXTURES / f"clean_{rule_id}.yaml"
    if key in {"reason", "remediation"}:
        issues = _issues(_with_parameter(contract, rule_id, key, _MARK), violation)
        assert len(issues) == 1 and _MARK in issues[0].message
    elif key in {"pattern", "hook_id"}:
        mutated = _with_parameter(contract, rule_id, key, r"\bnever-matches-zzz\b")
        assert _issues(mutated, violation) == []
    elif key == "unless":
        assert _issues(_with_parameter(contract, rule_id, key, "."), violation) == []
    elif key == "check_only_args":
        source = _local(_hook("planted", "tool", "        args: [--zzz-arg]\n"))
        hook_id = (
            next(r for r in contract.rules if r.rule_id == rule_id).parameters or {}
        )["hook_id"]
        source = source.replace("- id: planted", f"- id: {hook_id}")
        path = _write(tmp_path, source)
        assert len(_issues(contract, path)) == 1
        mutated = _with_parameter(contract, rule_id, key, ["--zzz-arg"])
        assert _issues(mutated, path) == []
    elif key == "min_hooks":
        assert _issues(_with_parameter(contract, rule_id, key, 2), clean) != []
    elif key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _issues(_with_parameter(contract, rule_id, key, "bogus"), violation)
    else:
        pytest.fail(f"no mutation case for parameter {key!r} of {rule_id}")


_OPTIONAL_KEYS = frozenset({"unless", "check_only_args"})


@pytest.mark.parametrize(
    ("rule_id", "key"),
    [case for case in _parameter_cases() if case[1] not in _OPTIONAL_KEYS],
)
def test_a_rule_row_missing_a_required_key_fails_to_load(
    rule_id: str, key: str
) -> None:
    """An invalid contract raises rather than passing (optional keys excepted)."""
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        _issues(mutated, _FIXTURES / f"violation_{rule_id}.yaml")


def test_a_pattern_that_does_not_compile_fails_to_load() -> None:
    mutated = _with_parameter(_contract(), "hook_writes_fix_flag", "pattern", "(")
    with pytest.raises(ModelOnexError, match="regular expression"):
        _issues(mutated, _FIXTURES / "violation_hook_writes_fix_flag.yaml")


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker runs with ``open`` and the Path reads patched to raise."""
    rules = _contract().rules

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    hooks = (ModelHookWritesHook(id="planted", entry="sed -i s/a/b/ f"),)
    issues = check_hook_writes(Path("x.yaml"), hooks, rules)
    assert [i.rule_name for i in issues] == ["hook_writes_in_place_edit"]


@pytest.mark.parametrize(
    "entry",
    [
        "uv run ruff format --force-exclude",
        "uv run ruff check --force-exclude --fix --exit-non-zero-on-fix",
        "perl -i -ne 'print unless /x/'",
        "sed -i 's/a/b/' file.txt",
        'bash -c "rm -rf tmp/* 2>/dev/null || true"',
        "git add -A",
        "prettier --write",
    ],
)
def test_writing_entry_is_refused(tmp_path: Path, entry: str) -> None:
    issues = _issues(_contract(), _write(tmp_path, _local(_hook("some-hook", entry))))
    assert issues
    assert all("some-hook" in issue.message for issue in issues)


@pytest.mark.parametrize(
    "entry",
    [
        "uv run ruff format --force-exclude --check",
        "uv run ruff format --diff",
        "uv run ruff check --force-exclude",
        "uv run ruff check --no-fix",
        "mixed-line-ending --fix=no",
        "uv run mypy src/",
        "grep -n TODO file.txt",
    ],
)
def test_checking_entry_passes(tmp_path: Path, entry: str) -> None:
    path = _write(tmp_path, _local(_hook("some-hook", entry)))
    assert _issues(_contract(), path) == []


def test_args_are_part_of_the_command(tmp_path: Path) -> None:
    source = _local(
        _hook("fmt", "ruff", "        args: [format]\n"),
        _hook("lint", "ruff", "        args: [check, --fix]\n"),
        _hook("lint-ok", "ruff", "        args: [check]\n"),
    )
    messages = [i.message for i in _issues(_contract(), _write(tmp_path, source))]
    assert len(messages) == 2
    assert any("hook fmt:" in m for m in messages)
    assert any("hook lint:" in m for m in messages)


def test_temp_dir_writer_is_not_a_tracked_file_writer(tmp_path: Path) -> None:
    entry = (
        'bash -c \'base=$(mktemp -d); trap "rm -rf \\"$base\\"" EXIT; '
        'git archive HEAD .github | tar -x -C "$base"\''
    )
    assert (
        _issues(_contract(), _write(tmp_path, _local(_hook("temp-only", entry)))) == []
    )


def test_exported_hook_list_is_read(tmp_path: Path) -> None:
    source = (
        "- id: exported-writer\n  entry: perl -i -pe 's/a/b/'\n  language: system\n"
        "- id: exported-checker\n  entry: grep -n x\n  language: system\n"
    )
    issues = _issues(_contract(), _write(tmp_path, source, ".pre-commit-hooks.yaml"))
    assert len(issues) == 1
    assert "exported-writer" in issues[0].message


@pytest.mark.parametrize("source", ["repos: [unclosed", "just a string"])
def test_unreadable_hook_file_raises(tmp_path: Path, source: str) -> None:
    with pytest.raises(ModelOnexError):
        _issues(_contract(), _write(tmp_path, source))


def test_scan_set_is_rule_data() -> None:
    assert _contract().target_patterns == [
        ".pre-commit-config.yaml",
        ".pre-commit-hooks.yaml",
    ]


def test_this_repositorys_own_hook_files_have_no_writer() -> None:
    """AC1: the repository's config and published hooks contain no hook whose entry writes."""
    for name in (".pre-commit-config.yaml", ".pre-commit-hooks.yaml"):
        assert _issues(_contract(), _ROOT / name) == [], name
