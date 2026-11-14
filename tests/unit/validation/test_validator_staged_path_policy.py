# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ``staged_path_policy``: hooks no-env-file and no-planning-docs (OMN-22012).

The two hooks were a shell script and an inline ``bash -c`` command; they now run
``ValidatorStagedPathPolicy`` through the generic validator runtime with their hook
ids unchanged. Every refused pattern and remediation text is a rule-row parameter
of ``staged_path_policy.validation.yaml``, which these tests load.
"""

from __future__ import annotations

import builtins
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_commit_hygiene import check_commit_hygiene
from omnibase_core.validation.validator_staged_path_policy import (
    ValidatorStagedPathPolicy,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/staged_path_policy.validation.yaml"
)
_HOOK_ENTRY = (
    "omnibase_core.validation.validator_staged_path_policy:ValidatorStagedPathPolicy"
)


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _rules_fired(relative: str, contract: ModelValidatorSubcontract) -> list[str]:
    issues = check_commit_hygiene(Path(relative), relative, b"", contract.rules)
    return [issue.rule_name for issue in issues]


def test_the_rule_rows_are_the_two_hooks() -> None:
    assert [rule.rule_id for rule in _contract().rules] == [
        "env_file_staged",
        "planning_doc_staged",
    ]


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        (".env", ["env_file_staged"]),
        ("sub/.env.local", ["env_file_staged"]),
        (".env_prod", ["env_file_staged"]),
        ("docs/plans/2026-plan.md", ["planning_doc_staged"]),
        (".env.example", []),
        ("deploy/.env.example", []),
        (".envrc", []),
        ("src/env.py", []),
        ("docs/guide.md", []),
        ("sub/docs/plans/x.md", []),
    ],
)
def test_each_path_fires_exactly_its_rule(relative: str, expected: list[str]) -> None:
    assert _rules_fired(relative, _contract()) == expected


@pytest.mark.parametrize(
    ("rule_id", "relative"),
    [("env_file_staged", ".env"), ("planning_doc_staged", "docs/plans/p.md")],
)
def test_disabling_a_row_admits_its_path(rule_id: str, relative: str) -> None:
    contract = _contract()
    rules = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    assert _rules_fired(relative, contract.model_copy(update={"rules": rules})) == []


@pytest.mark.parametrize(
    ("rule_id", "relative", "key", "value"),
    [
        ("env_file_staged", ".env", "path_pattern", r"^nothing$"),
        ("env_file_staged", ".env", "exclude_path_pattern", r"\.env"),
        ("planning_doc_staged", "docs/plans/p.md", "path_pattern", r"^nothing$"),
    ],
)
def test_pattern_parameters_drive_the_verdict(
    rule_id: str, relative: str, key: str, value: str
) -> None:
    contract = _contract()
    rules = []
    for rule in contract.rules:
        if rule.rule_id == rule_id:
            rule = rule.model_copy(
                update={"parameters": {**(rule.parameters or {}), key: value}}
            )
        rules.append(rule)
    assert _rules_fired(relative, contract.model_copy(update={"rules": rules})) == []


def test_validator_never_reads_the_staged_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = tmp_path / ".env"
    secret.write_text("TOKEN=x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def _refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the staged file was read")

    validator = ValidatorStagedPathPolicy(contract=_contract())
    contract = _contract()
    monkeypatch.setattr(Path, "read_bytes", _refuse)
    monkeypatch.setattr(Path, "read_text", _refuse)
    monkeypatch.setattr(builtins, "open", _refuse)
    issues = validator._validate_file(secret, contract)
    assert [issue.rule_name for issue in issues] == ["env_file_staged"]


def test_a_row_of_another_kind_fails_to_load(tmp_path: Path) -> None:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    data["validation"]["rules"][0]["parameters"]["kind"] = "final_newline_missing"
    mutated = tmp_path / "staged_path_policy.validation.yaml"
    mutated.write_text(yaml.safe_dump(data), encoding="utf-8")

    class _Mutated(ValidatorStagedPathPolicy):
        def _get_contract_path(self) -> Path:
            return mutated

    with pytest.raises(ModelOnexError, match="judges paths only"):
        _ = _Mutated().contract


@pytest.mark.parametrize(
    ("relative", "exit_code"),
    [(".env", 1), ("docs/plans/p.md", 1), (".env.example", 0), ("ok.txt", 0)],
)
def test_the_hook_entry_refuses_and_admits(
    tmp_path: Path, relative: str, exit_code: int
) -> None:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x\n", encoding="utf-8")
    env = scrub_git_location_env()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run",
            _HOOK_ENTRY,
            "--report-json",
            str(tmp_path / "report.json"),
            relative,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert completed.returncode == exit_code, completed.stdout + completed.stderr
    if exit_code:
        assert completed.stdout.count("[ERROR]") == 1


@pytest.mark.parametrize("hook_id", ["no-env-file", "no-planning-docs"])
def test_both_hook_ids_run_the_validator(hook_id: str) -> None:
    config = yaml.safe_load(
        (_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hooks = {
        hook["id"]: hook
        for repo in config["repos"]
        for hook in repo["hooks"]
        if "id" in hook
    }
    hook = hooks[hook_id]
    assert _HOOK_ENTRY in hook["entry"]
    assert "runtime_validator_run" in hook["entry"]
    assert hook["pass_filenames"] is True
    assert "always_run" not in hook
