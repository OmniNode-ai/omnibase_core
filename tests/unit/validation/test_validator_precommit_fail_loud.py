# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pre-commit fail-loud meta check in the generic validator format (OMN-22357).

A hook entry must not swallow its failure, a gate script must not exit zero on a
missing prerequisite or a bypass variable, and every hook stage must be installed.
The checker is pure; the validator reads a hook file and the scripts its entries
invoke; every pattern, window, stage and remediation text is a ``parameters`` entry
of a rule row of ``precommit_fail_loud.validation.yaml``. These tests load that
contract, so the values that gate the repository are the values under test.
"""

from __future__ import annotations

import json
import re
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
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    main_for_reference,
)
from omnibase_core.validation.validator_precommit_fail_loud import (
    ValidatorPrecommitFailLoud,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/precommit_fail_loud.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/precommit_fail_loud"
_CANARY_DIR = _ROOT / "tests/fixtures/precommit_fail_loud"
_REFERENCE = (
    "omnibase_core.validation.validator_precommit_fail_loud:ValidatorPrecommitFailLoud"
)
_NO_FINDING_KINDS = {"script_reference"}


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _kind(rule_id: str) -> str:
    rule = next(r for r in _contract().rules if r.rule_id == rule_id)
    return str((rule.parameters or {})["kind"])


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
        parameters.pop(key, None)
    else:
        parameters[key] = cast(RuleParameterValue, value)
    return _with_rule(contract, rule_id, parameters=parameters)


def _issues(
    contract: ModelValidatorSubcontract, path: Path
) -> list[ModelValidationIssue]:
    return list(
        ValidatorPrecommitFailLoud(contract=contract).validate_file(path).issues
    )


def _write(tmp_path: Path, source: str, name: str = ".pre-commit-config.yaml") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _config(entry: str, language: str = "system", extra: str = "") -> str:
    body = "".join(f"          {line}\n" for line in entry.splitlines())
    return (
        "default_install_hook_types: [pre-commit]\n"
        "repos:\n  - repo: local\n    hooks:\n"
        "      - id: gate\n        name: gate\n"
        f"        entry: |\n{body}"
        f"        language: {language}\n{extra}"
    )


_RULES = [
    rule.rule_id
    for rule in _contract().rules
    if (rule.parameters or {})["kind"] not in _NO_FINDING_KINDS
]


# --- AC1: the rules are the contract's rows, the check is a ValidatorBase ------------


@pytest.mark.parametrize("rule_id", _RULES)
def test_precommit_fail_loud_planted_violation_yields_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _issues(_contract(), _FIXTURES / f"violation_{rule_id}.yaml")
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert [issue.code for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_precommit_fail_loud_clean_fixture_yields_no_issue(rule_id: str) -> None:
    assert _issues(_contract(), _FIXTURES / f"clean_{rule_id}.yaml") == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_precommit_fail_loud_disabling_a_rule_row_clears_its_violation(
    rule_id: str,
) -> None:
    contract = _with_rule(_contract(), rule_id, enabled=False)
    assert _issues(contract, _FIXTURES / f"violation_{rule_id}.yaml") == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_precommit_fail_loud_rule_data_decides_what_is_refused(rule_id: str) -> None:
    """Changing the one value a rule row refuses on clears its planted violation."""
    contract = _contract()
    kind = _kind(rule_id)
    if kind == "hook_count_floor":
        changed = _with_parameter(contract, rule_id, "min_hooks", 0 + 1)
        assert _issues(changed, _FIXTURES / f"violation_{rule_id}.yaml")
        lowered = _with_rule(
            contract,
            rule_id,
            parameters={**(_rule_parameters(rule_id)), "min_hooks": 0},
        )
        with pytest.raises(ModelOnexError, match="min_hooks"):
            _issues(lowered, _FIXTURES / f"violation_{rule_id}.yaml")
        return
    if kind == "stage_coverage":
        changed = _with_parameter(
            contract, rule_id, "allowed_uninstalled", ["pre-push"]
        )
    elif kind == "windowed_exit":
        changed = _with_parameter(contract, rule_id, "exit_pattern", r"zzz-never")
    else:
        changed = _with_parameter(contract, rule_id, "pattern", r"zzz-never")
    assert _issues(changed, _FIXTURES / f"violation_{rule_id}.yaml") == []


def _rule_parameters(rule_id: str) -> dict[str, RuleParameterValue]:
    rule = next(r for r in _contract().rules if r.rule_id == rule_id)
    return dict(rule.parameters or {})


def test_precommit_fail_loud_validator_is_a_contract_driven_validator_base() -> None:
    contract = _contract()
    assert contract.validator_id == ValidatorPrecommitFailLoud.validator_id
    assert contract.target_patterns == [
        ".pre-commit-config.yaml",
        ".pre-commit-hooks.yaml",
    ]
    assert ValidatorPrecommitFailLoud().contract.rules == contract.rules


def test_precommit_fail_loud_source_names_no_hook_pattern_or_stage() -> None:
    """No literal rule value lives in code: patterns, stage names and hook ids are data."""
    forbidden = [
        "manual",
        "fail-loud-ok",
        "continue-on-error",
        "set +e",
        "SKIP",
        "BYPASS",
    ]
    forbidden.append("precommit-fail-loud" + "-meta-gate")
    for name in ("checker_precommit_fail_loud.py", "validator_precommit_fail_loud.py"):
        source = (_ROOT / "src/omnibase_core/validation" / name).read_text()
        for word in forbidden:
            assert word not in source, f"{name} names rule data {word!r}"


_OPTIONAL_PARAMETERS = {
    "unless",
    "suppression_marker",
    "allowed_uninstalled",
    "guard_pattern",
}
_REQUIRED_PARAMETERS = [
    (rule.rule_id, key)
    for rule in _contract().rules
    for key in (rule.parameters or {})
    if key not in _OPTIONAL_PARAMETERS
]


@pytest.mark.parametrize(("rule_id", "key"), _REQUIRED_PARAMETERS)
def test_precommit_fail_loud_missing_required_parameter_fails_the_load(
    rule_id: str, key: str
) -> None:
    changed = _with_parameter(_contract(), rule_id, key, None)
    clean = _FIXTURES / "clean_precommit_fail_loud_swallow_or_true.yaml"
    with pytest.raises(ModelOnexError, match=rule_id):
        _issues(changed, clean)


def test_precommit_fail_loud_unknown_kind_and_bad_regex_fail_the_load() -> None:
    rule_id = _RULES[1]
    clean = _FIXTURES / f"clean_{rule_id}.yaml"
    with pytest.raises(ModelOnexError, match="unknown kind"):
        _issues(_with_parameter(_contract(), rule_id, "kind", "other"), clean)
    with pytest.raises(ModelOnexError, match="regular expression"):
        _issues(_with_parameter(_contract(), rule_id, "pattern", "(["), clean)
    with pytest.raises(ModelOnexError, match="read_scripts"):
        _issues(_with_parameter(_contract(), rule_id, "read_scripts", "tree"), clean)


# --- Inherited behaviour of the six copies, as one generic rule ------------------------


def test_precommit_fail_loud_manual_stage_is_admitted_without_justification(
    tmp_path: Path,
) -> None:
    """The copies never auto-install the manual stage and require no reason for it."""
    source = _config("checker", extra="        stages: [manual]\n")
    assert _issues(_contract(), _write(tmp_path, source)) == []


def test_precommit_fail_loud_stage_defaults_to_the_stage_pre_commit_installs(
    tmp_path: Path,
) -> None:
    base = "repos:\n  - repo: local\n    hooks:\n      - id: gate\n        entry: checker\n        language: system\n"
    assert _issues(_contract(), _write(tmp_path, base)) == []
    config = _write(tmp_path, base + "        stages: [pre-push]\n")
    [issue] = _issues(_contract(), config)
    assert "pre-push" in issue.message


def test_precommit_fail_loud_file_no_target_pattern_covers_is_refused_not_passed(
    tmp_path: Path,
) -> None:
    other = _write(tmp_path, _config("checker"), "other.yaml")
    with pytest.raises(ModelOnexError, match="not covered by target_patterns"):
        ValidatorPrecommitFailLoud().validate([other])
    with pytest.raises(ModelOnexError, match="does not exist"):
        ValidatorPrecommitFailLoud().validate([tmp_path / ".pre-commit-config.yaml"])


def test_precommit_fail_loud_exported_hook_list_is_scanned_without_stage_coverage(
    tmp_path: Path,
) -> None:
    exported = (
        "- id: gate\n  name: gate\n  entry: bash -c 'checker || true'\n"
        "  language: system\n  stages: [pre-push]\n"
    )
    [issue] = _issues(_contract(), _write(tmp_path, exported, ".pre-commit-hooks.yaml"))
    assert issue.rule_name == "precommit_fail_loud_swallow_or_true"


def test_precommit_fail_loud_python_language_entries_are_not_shell_scanned(
    tmp_path: Path,
) -> None:
    source = _config("python -m checker || true", language="python")
    assert _issues(_contract(), _write(tmp_path, source)) == []


def test_precommit_fail_loud_args_are_scanned_with_the_entry(tmp_path: Path) -> None:
    source = _config("bash -c", extra="        args: ['checker || true']\n")
    [issue] = _issues(_contract(), _write(tmp_path, source))
    assert issue.rule_name == "precommit_fail_loud_swallow_or_true"


def test_precommit_fail_loud_suppression_marker_skips_the_flagged_line(
    tmp_path: Path,
) -> None:
    flagged = _config("bash -c 'checker || true'")
    assert len(_issues(_contract(), _write(tmp_path, flagged))) == 1
    marker = _rule_parameters("precommit_fail_loud_swallow_or_true")[
        "suppression_marker"
    ]
    reviewed = _config(f"bash -c 'checker || true' # {marker}: reviewed")
    assert _issues(_contract(), _write(tmp_path, reviewed)) == []


def test_precommit_fail_loud_config_with_other_top_level_keys_is_judged(
    tmp_path: Path,
) -> None:
    """One core copy refused any top-level key it did not list; the other five did not."""
    source = "exclude: '^build/'\nminimum_pre_commit_version: '3.0.0'\n" + _config(
        "checker"
    )
    assert _issues(_contract(), _write(tmp_path, source)) == []


@pytest.mark.parametrize(
    "source", ["repos: [\n", "[1]\n", "repos: {a: 1}\n", "repos: [1]\n"]
)
def test_precommit_fail_loud_unreadable_config_is_an_error_not_a_pass(
    tmp_path: Path, source: str
) -> None:
    with pytest.raises(ModelOnexError, match="cannot read hooks"):
        _issues(_contract(), _write(tmp_path, source))


# --- Scripts the entries invoke -------------------------------------------------------


def _script_config(tmp_path: Path, script_text: str | None) -> Path:
    if script_text is not None:
        script = tmp_path / "scripts" / "gate.sh"
        script.parent.mkdir()
        script.write_text(script_text, encoding="utf-8")
    return _write(tmp_path, _config("bash scripts/gate.sh"))


def test_precommit_fail_loud_script_exit_zero_after_not_found_is_refused_by_name(
    tmp_path: Path,
) -> None:
    config = _script_config(
        tmp_path, 'if [ ! -f x ]; then\n  echo "x not found"\n  exit 0\nfi\n'
    )
    [issue] = _issues(_contract(), config)
    assert issue.rule_name == "precommit_fail_loud_exit_zero_on_missing"
    assert "script scripts/gate.sh:3" in issue.message


def test_precommit_fail_loud_script_exit_one_after_not_found_passes(
    tmp_path: Path,
) -> None:
    config = _script_config(
        tmp_path, 'if [ ! -f x ]; then\n  echo "x not found"\n  exit 1\nfi\n'
    )
    assert _issues(_contract(), config) == []


def test_precommit_fail_loud_script_swallow_is_not_an_entry_rule(
    tmp_path: Path,
) -> None:
    """A tolerated command inside a script is a script's business; only the entry is held."""
    config = _script_config(tmp_path, "grep -q x y || true\n")
    assert _issues(_contract(), config) == []


def test_precommit_fail_loud_script_is_scanned_once_across_hooks(
    tmp_path: Path,
) -> None:
    script = tmp_path / "scripts" / "gate.sh"
    script.parent.mkdir()
    script.write_text('echo "a not found"\nexit 0\n', encoding="utf-8")
    hook = (
        "      - id: {i}\n        name: {i}\n        entry: bash scripts/gate.sh\n"
        "        language: system\n"
    )
    source = (
        "default_install_hook_types: [pre-commit]\nrepos:\n  - repo: local\n    hooks:\n"
        + hook.format(i="one")
        + hook.format(i="two")
    )
    assert len(_issues(_contract(), _write(tmp_path, source))) == 1


def test_precommit_fail_loud_missing_script_is_not_scanned(tmp_path: Path) -> None:
    assert _issues(_contract(), _script_config(tmp_path, None)) == []


def test_precommit_fail_loud_script_reference_row_decides_which_tokens_are_scripts(
    tmp_path: Path,
) -> None:
    config = _script_config(tmp_path, 'echo "x not found"\nexit 0\n')
    changed = _with_parameter(
        _contract(), "precommit_fail_loud_script_reference", "prefixes", ["tools/"]
    )
    assert _issues(changed, config) == []


# --- The repository's own hook files ----------------------------------------------------


@pytest.mark.parametrize("name", [".pre-commit-config.yaml", ".pre-commit-hooks.yaml"])
def test_precommit_fail_loud_repository_hook_files_pass(name: str) -> None:
    assert _issues(_contract(), _ROOT / name) == []


@pytest.mark.parametrize("name", [".pre-commit-config.yaml", ".pre-commit-hooks.yaml"])
def test_precommit_fail_loud_repository_hook_files_planted_swallow_is_refused(
    tmp_path: Path, name: str
) -> None:
    """Positive control for the pass above: the same file with one swallowed entry fails."""
    text = (_ROOT / name).read_text(encoding="utf-8")
    planted = re.sub(
        r"(?m)^(\s*entry: )(\S.*)$", r"\1bash -c '\2 || true'", text, count=1
    )
    assert planted != text
    issues = _issues(_contract(), _write(tmp_path, planted, name))
    assert "precommit_fail_loud_swallow_or_true" in {i.rule_name for i in issues}


def test_precommit_fail_loud_hook_is_registered_and_the_local_script_is_gone() -> None:
    hooks = yaml.safe_load((_ROOT / ".pre-commit-hooks.yaml").read_text())
    [hook] = [h for h in hooks if "ValidatorPrecommitFailLoud" in h.get("entry", "")]
    assert hook["id"] == "precommit-fail-loud-meta-gate"
    assert hook["language"] == "python"
    assert hook["pass_filenames"] is False
    assert hook["always_run"] is True
    assert hook["args"] == [".pre-commit-config.yaml"]
    local = _ROOT / "scripts" / "validation" / ("validate_precommit" + "_fail_loud.py")
    assert not local.exists()
    config = yaml.safe_load((_ROOT / ".pre-commit-config.yaml").read_text())
    local_hooks = [
        h
        for repo in config["repos"]
        if repo["repo"] == "local"
        for h in repo["hooks"]
        if h["id"] == hook["id"]
    ]
    assert [h["entry"].count("ValidatorPrecommitFailLoud") for h in local_hooks] == [1]


# --- AC2: the canary defect, through the hook entry as pre-commit runs it ---------------


def _hook_run(args: list[str]) -> int:
    """Run the hook entry as pre-commit does: real runtime, in-memory bus."""
    return main_for_reference([_REFERENCE, *args])


def test_precommit_fail_loud_canary_named_off_pattern_is_not_a_silent_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The canary run on its own file name must not print PASS having checked nothing."""
    out = tmp_path / "report.json"
    canary = _CANARY_DIR / "canary_swallowed_failure.yaml"
    assert _hook_run([str(canary), "--report-json", str(out)]) == 1
    captured = capsys.readouterr()
    assert "PASS" not in captured.out
    assert "not covered by target_patterns" in captured.err


@pytest.mark.parametrize("relative", [False, True])
def test_precommit_fail_loud_canary_swallowed_failure_refused_converged_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".pre-commit-config.yaml"
    target = config.name if relative else str(config)

    config.write_text((_CANARY_DIR / "canary_swallowed_failure.yaml").read_text())
    out = tmp_path / "canary.json"
    assert _hook_run([target, "--report-json", str(out)]) == 1
    [finding] = json.loads(out.read_text())["findings"]
    assert finding["rule_id"] == "precommit_fail_loud_swallow_or_true"
    assert finding["severity"] == "FAIL"
    assert finding["location"].endswith(".pre-commit-config.yaml")

    config.write_text((_CANARY_DIR / "converged_fail_loud.yaml").read_text())
    assert _hook_run([target, "--report-json", str(out)]) == 0
    assert json.loads(out.read_text())["findings"] == []


def test_precommit_fail_loud_canary_missing_target_is_an_error(tmp_path: Path) -> None:
    assert _hook_run([str(tmp_path / ".pre-commit-config.yaml")]) == 1
