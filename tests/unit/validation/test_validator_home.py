# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""K7 validator_home (OMN-21503): planted violations, clean twins, every rule parameter, pure checker."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_validator_home_hook_fact import (
    ModelValidatorHomeHookFact,
)
from omnibase_core.validation import checker_validator_home as checker
from omnibase_core.validation.validator_validator_home import ValidatorValidatorHome

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "validator_home"
)
NODE_ROOT = "violation_validator_node_outside_core"
HOOKS = ".pre-commit-config.yaml"

# rule_id -> violation fixtures (each yields exactly one issue with that rule_id)
VIOLATIONS: dict[str, list[str]] = {
    "local_hook_definition": [
        f"violation_local_hook_definition.{HOOKS.lstrip('.')}",
        f"violation_local_hook_definition_inline.{HOOKS.lstrip('.')}",
    ],
    "repo_script_hook": [f"violation_repo_script_hook.{HOOKS.lstrip('.')}"],
    "pytest_hook": [f"violation_pytest_hook.{HOOKS.lstrip('.')}"],
    "validator_node_outside_core": [
        f"{NODE_ROOT}/node_x_compute/contract.yaml",
        f"{NODE_ROOT}_by_name/node_x_check_compute/contract.yaml",
        f"{NODE_ROOT}_with_predicate/node_y_compute/contract.yaml",
    ],
    "config_pinning_test": ["violation_config_pinning_test.test_x.py"],
}
CLEANS: dict[str, str] = {
    "local_hook_definition": f"clean_local_hook_definition.{HOOKS.lstrip('.')}",
    "repo_script_hook": f"clean_repo_script_hook.{HOOKS.lstrip('.')}",
    "pytest_hook": f"clean_pytest_hook.{HOOKS.lstrip('.')}",
    "validator_node_outside_core": "clean_validator_node_outside_core/node_z_compute/contract.yaml",
    "config_pinning_test": "clean_config_pinning_test.test_x.py",
}

# (rule_id, parameter) -> (fixture the parameter controls, whether mutating it
# makes a violation disappear ("clears"), a clean fixture violate ("flags") or the
# fixture fall to another rule, named).
# config_name_patterns is held by all three hook rows, so it is mutated in all.
_HOOK = f"violation_{{}}.{HOOKS.lstrip('.')}"
CONTROLS: dict[tuple[str, str], tuple[str, str]] = {
    ("validator_node_outside_core", "contract_name_patterns"): (
        VIOLATIONS["validator_node_outside_core"][0],
        "clears",
    ),
    ("validator_node_outside_core", "validator_output_models"): (
        VIOLATIONS["validator_node_outside_core"][0],
        "clears",
    ),
    ("validator_node_outside_core", "validator_node_patterns"): (
        VIOLATIONS["validator_node_outside_core"][1],
        "clears",
    ),
    ("validator_node_outside_core", "core_checker_import_patterns"): (
        CLEANS["validator_node_outside_core"],
        "flags",
    ),
    ("validator_node_outside_core", "predicate_patterns"): (
        VIOLATIONS["validator_node_outside_core"][2],
        "clears",
    ),
    ("local_hook_definition", "config_name_patterns"): (
        VIOLATIONS["local_hook_definition"][0],
        "clears",
    ),
    ("local_hook_definition", "local_repo_value"): (
        VIOLATIONS["local_hook_definition"][0],
        "clears",
    ),
    ("local_hook_definition", "local_languages"): (
        VIOLATIONS["local_hook_definition"][0],
        "clears",
    ),
    ("local_hook_definition", "inline_shell_patterns"): (
        VIOLATIONS["local_hook_definition"][1],
        "clears",
    ),
    ("repo_script_hook", "config_name_patterns"): (
        VIOLATIONS["repo_script_hook"][0],
        "clears",
    ),
    ("repo_script_hook", "script_entry_patterns"): (
        VIOLATIONS["repo_script_hook"][0],
        "clears",
    ),
    ("pytest_hook", "config_name_patterns"): (
        VIOLATIONS["pytest_hook"][0],
        "clears",
    ),
    # a hook that stops being a pytest hook is still a local system hook
    ("pytest_hook", "pytest_entry_patterns"): (
        VIOLATIONS["pytest_hook"][0],
        "local_hook_definition",
    ),
    ("config_pinning_test", "test_name_patterns"): (
        VIOLATIONS["config_pinning_test"][0],
        "clears",
    ),
    ("config_pinning_test", "config_path_patterns"): (
        VIOLATIONS["config_pinning_test"][0],
        "clears",
    ),
    ("config_pinning_test", "text_assertion_patterns"): (
        VIOLATIONS["config_pinning_test"][0],
        "clears",
    ),
    ("config_pinning_test", "canary_patterns"): (
        CLEANS["config_pinning_test"],
        "flags",
    ),
}
SHARED_KEYS = frozenset({"config_name_patterns"})
NEVER_MATCHES = "(?!)"


def _base_contract() -> ModelValidatorSubcontract:
    contract = ValidatorValidatorHome().contract
    # the planted fixtures sit under tests/fixtures, which the shipped contract excludes
    return contract.model_copy(update={"exclude_patterns": []})


def _codes(
    fixture: str, contract: ModelValidatorSubcontract | None = None
) -> list[str]:
    validator = ValidatorValidatorHome(contract=contract or _base_contract())
    return [str(i.code) for i in validator.validate(FIXTURES / fixture).issues]


def _mutated(rule_id: str, key: str) -> ModelValidatorSubcontract:
    contract = _base_contract()
    rows = []
    for row in contract.rules:
        holds = row.parameters is not None and key in row.parameters
        if holds and (row.rule_id == rule_id or key in SHARED_KEYS):
            assert row.parameters is not None
            params = dict(row.parameters)
            params[key] = (
                [NEVER_MATCHES] if isinstance(params[key], list) else NEVER_MATCHES
            )
            row = row.model_copy(update={"parameters": params})
        rows.append(row)
    return contract.model_copy(update={"rules": rows})


@pytest.mark.parametrize(
    ("rule_id", "fixture"),
    [(r, f) for r, fixtures in VIOLATIONS.items() for f in fixtures],
)
def test_violation_fixture_yields_exactly_its_rule(rule_id: str, fixture: str) -> None:
    assert _codes(fixture) == [rule_id]


@pytest.mark.parametrize(("rule_id", "fixture"), sorted(CLEANS.items()))
def test_clean_fixture_yields_nothing(rule_id: str, fixture: str) -> None:
    assert _codes(fixture) == []


def test_every_parameter_of_every_rule_row_has_a_control() -> None:
    declared = {
        (row.rule_id, key)
        for row in _base_contract().rules
        for key in (row.parameters or {})
    }
    assert declared == set(CONTROLS)


@pytest.mark.parametrize(("rule_id", "key"), sorted(CONTROLS))
def test_mutating_a_parameter_changes_the_verdict(rule_id: str, key: str) -> None:
    fixture, direction = CONTROLS[(rule_id, key)]
    expected = {"clears": [], "flags": [rule_id]}.get(direction, [direction])
    assert _codes(fixture, _mutated(rule_id, key)) == expected


@pytest.mark.parametrize("rule_id", sorted(VIOLATIONS))
def test_disabling_a_rule_row_clears_its_fixtures(rule_id: str) -> None:
    contract = _base_contract()
    rows = [
        r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
        for r in contract.rules
    ]
    disabled = contract.model_copy(update={"rules": rows})
    for fixture in VIOLATIONS[rule_id]:
        assert rule_id not in _codes(fixture, disabled)


def test_invalid_contract_fails_instead_of_passing() -> None:
    contract = _base_contract()
    rows = [
        r.model_copy(update={"parameters": {}}) if r.rule_id == "pytest_hook" else r
        for r in contract.rules
    ]
    broken = contract.model_copy(update={"rules": rows})
    with pytest.raises(ModelOnexError, match="pytest_entry_patterns"):
        checker.check_hooks(
            Path("x"),
            (ModelValidatorHomeHookFact("h", "local", "system", "pytest"),),
            {r.rule_id: r for r in broken.rules},
        )


def test_checker_is_pure_over_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: object, **_k: object) -> None:
        raise AssertionError("checker performed I/O")

    rules = {r.rule_id: r for r in _base_contract().rules}
    hook = ModelValidatorHomeHookFact("h", "local", "pygrep", "x")
    with monkeypatch.context() as patched:
        patched.setattr("builtins.open", refuse)
        patched.setattr(Path, "read_text", refuse)
        patched.setattr(Path, "read_bytes", refuse)
        issues = checker.check_hooks(Path("c"), (hook,), rules)
    assert [i.code for i in issues] == ["local_hook_definition"]


def test_shipped_contract_excludes_the_planted_fixtures() -> None:
    result = ValidatorValidatorHome().validate(FIXTURES)
    assert result.issues == []
