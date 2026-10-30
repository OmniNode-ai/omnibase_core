# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the handler-shape checker in the generic validator format (OMN-21536, K3).

Every handler class is judged, bound by a contract or not. The checker is pure;
the validator reads a module; every pattern, name list, threshold and remediation text
is a ``parameters`` entry of a rule row of ``handler_shape.validation.yaml``. These
tests load that contract, so the values that gate the repository are the values under
test.
"""

from __future__ import annotations

import builtins
import shutil
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
from omnibase_core.validation.checker_handler_shape import check_handler_shape
from omnibase_core.validation.validator_handler_shape import (
    ValidatorHandlerShape,
    module_facts,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/handler_shape.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/handler_shape"
_NODES = _ROOT / "src/omnibase_core"
_MARK = "zzz-marker"
_NEVER = "zzz-never-matches"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_parameter(
    contract: ModelValidatorSubcontract, rule_id: str, key: str, value: object | None
) -> ModelValidatorSubcontract:
    """The contract with one parameter of one rule row changed (removed when None)."""
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


def _with_enabled(
    contract: ModelValidatorSubcontract, rule_id: str, enabled: bool
) -> ModelValidatorSubcontract:
    rules = [
        rule.model_copy(update={"enabled": enabled})
        if rule.rule_id == rule_id
        else rule
        for rule in contract.rules
    ]
    return contract.model_copy(update={"rules": rules})


def _issues(
    contract: ModelValidatorSubcontract, path: Path
) -> list[ModelValidationIssue]:
    return list(ValidatorHandlerShape(contract=contract).validate_file(path).issues)


def _staged(tmp_path: Path, fixture: str, rule_id: str) -> Path:
    """Copy a fixture to a ``handler_*.py`` name, the file pattern a handler module has."""
    target = tmp_path / f"handler_{rule_id}.py"
    shutil.copy(_FIXTURES / f"{fixture}_{rule_id}.py", target)
    return target


def _source(tmp_path: Path, source: str, name: str = "handler_planted.py") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


_RULES = [rule.rule_id for rule in _contract().rules]


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    tmp_path: Path, rule_id: str
) -> None:
    issues = _issues(_contract(), _staged(tmp_path, "violation", rule_id))
    assert [issue.rule_name for issue in issues] == [rule_id]
    assert [issue.code for issue in issues] == [rule_id]


@pytest.mark.parametrize("rule_id", _RULES)
def test_clean_fixture_yields_no_issue(tmp_path: Path, rule_id: str) -> None:
    assert _issues(_contract(), _staged(tmp_path, "clean", rule_id)) == []


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_fails_that_rules_fixture(
    tmp_path: Path, rule_id: str
) -> None:
    """Disabling a rule row removes exactly that rule's finding, and no other rule's."""
    contract = _with_enabled(_contract(), rule_id, False)
    assert _issues(contract, _staged(tmp_path, "violation", rule_id)) == []
    for other in _RULES:
        if other != rule_id:
            assert len(_issues(contract, _staged(tmp_path, "violation", other))) == 1


def test_a_handler_class_no_contract_binds_is_classified(tmp_path: Path) -> None:
    """AC1: a bare module holding a class, with no node and no contract beside it."""
    path = _source(
        tmp_path,
        "class HandlerProbe:\n    def handle(self, probes, pins, local_backends):\n        return None\n",
        "unbound.py",
    )
    issues = _issues(_contract(), path)
    assert [issue.rule_name for issue in issues] == ["noncanonical_handle"]
    assert issues[0].line_number == 2


_TYPED = "class HandlerA:\n    def handle(self, thing: ModelThing) -> None: ...\n"
_REQUEST = "class HandlerA:\n    def handle(self, thing: ThingRequest) -> None: ...\n"
_PROBE = "class HandlerA:\n    def handle(self, probe) -> None: ...\n"
_ENVELOPE_FN = "from x import ModelEventEnvelope\n\n\ndef use(value: ModelEventEnvelope) -> None: ...\n"
_ENVELOPE_PREFIX = (
    "from x import ModelEventEnvelope\n\n\nclass HandlerA:\n    "
    "def use(self) -> ModelEventEnvelope: ...\n"
)
_ENVELOPE_HANDLE = (
    "from x import ModelEventEnvelope\n\n\nclass Plain:\n    "
    "def handle(self, request: ModelEventEnvelope) -> None: ...\n"
)
_MUTATES_PREFIX = "class HandlerA:\n    def record(self, item: str) -> None:\n        self._items.append(item)\n"

# (rule, key) -> (source, staged name, value that flips the verdict, issues before)
_CASES: dict[tuple[str, str], tuple[str, str, object, int]] = {
    ("noncanonical_handle", "handle_method_name"): (
        _PROBE,
        "handler_a.py",
        _NEVER,
        1,
    ),
    ("noncanonical_handle", "magic_param_names"): (
        _PROBE,
        "handler_a.py",
        ["probe"],
        1,
    ),
    ("noncanonical_handle", "non_model_annotations"): (
        _TYPED,
        "handler_a.py",
        ["ModelThing"],
        0,
    ),
    ("noncanonical_handle", "non_model_substrings"): (
        _TYPED,
        "handler_a.py",
        ["Thing"],
        0,
    ),
    ("noncanonical_handle", "model_annotation_markers"): (
        _TYPED,
        "handler_a.py",
        [_NEVER],
        0,
    ),
    ("noncanonical_handle", "model_annotation_suffixes"): (
        _REQUEST,
        "handler_a.py",
        [_NEVER],
        0,
    ),
    ("module_function_handler", "handler_file_pattern"): (
        "def gather() -> None: ...\n",
        "handler_a.py",
        _NEVER,
        1,
    ),
    ("module_function_handler", "private_function_prefix"): (
        "def gather() -> None: ...\n",
        "handler_a.py",
        "g",
        1,
    ),
    ("module_function_handler", "min_public_functions"): (
        "def gather() -> None: ...\n",
        "handler_a.py",
        2,
        1,
    ),
    ("envelope_in_core", "handler_file_pattern"): (
        _ENVELOPE_FN,
        "handler_a.py",
        _NEVER,
        1,
    ),
    ("envelope_in_core", "handler_class_prefixes"): (
        _ENVELOPE_PREFIX,
        "plain.py",
        [_NEVER],
        1,
    ),
    ("envelope_in_core", "handle_method_name"): (
        _ENVELOPE_HANDLE,
        "plain.py",
        _NEVER,
        1,
    ),
    ("envelope_in_core", "forbidden_names"): (
        _ENVELOPE_FN,
        "handler_a.py",
        [_NEVER],
        1,
    ),
    ("mutating_public_method", "handle_method_name"): (
        _MUTATES_PREFIX,
        "plain.py",
        "record",
        1,
    ),
    ("mutating_public_method", "handler_class_prefixes"): (
        _MUTATES_PREFIX,
        "plain.py",
        [_NEVER],
        1,
    ),
    ("mutating_public_method", "private_method_prefix"): (
        _MUTATES_PREFIX,
        "plain.py",
        "rec",
        1,
    ),
    ("mutating_public_method", "exempt_method_names"): (
        _MUTATES_PREFIX,
        "plain.py",
        ["record"],
        1,
    ),
    ("mutating_public_method", "mutating_call_names"): (
        _MUTATES_PREFIX,
        "plain.py",
        [_NEVER],
        1,
    ),
}
_TEXT_KEYS = frozenset({"kind", "remediation"})


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
    if key == "remediation":
        issues = _issues(
            _with_parameter(contract, rule_id, key, _MARK),
            _staged(tmp_path, "violation", rule_id),
        )
        assert len(issues) == 1 and _MARK in issues[0].message
        return
    if key == "kind":
        with pytest.raises(ModelOnexError, match="unknown kind"):
            _issues(
                _with_parameter(contract, rule_id, key, "bogus"),
                _staged(tmp_path, "violation", rule_id),
            )
        return
    source, name, flipped, before = _CASES[(rule_id, key)]
    path = _source(tmp_path, source, name)
    mutated = _with_parameter(contract, rule_id, key, flipped)
    own = [i for i in _issues(contract, path) if i.rule_name == rule_id]
    after = [i for i in _issues(mutated, path) if i.rule_name == rule_id]
    assert len(own) == before
    assert len(after) != len(own)


def test_every_parameter_key_has_a_mutation_case() -> None:
    covered = set(_CASES) | {
        (rule_id, key) for rule_id, key in _parameter_cases() if key in _TEXT_KEYS
    }
    assert covered == set(_parameter_cases())


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_a_rule_row_missing_a_key_fails_to_load(
    tmp_path: Path, rule_id: str, key: str
) -> None:
    """An invalid contract raises rather than passing, on a file that has no handler."""
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        _issues(mutated, _source(tmp_path, "x = 1\n", "empty.py"))


def test_a_pattern_that_does_not_compile_fails_to_load(tmp_path: Path) -> None:
    mutated = _with_parameter(
        _contract(), "module_function_handler", "handler_file_pattern", "("
    )
    with pytest.raises(ModelOnexError, match="regular expression"):
        _issues(mutated, _source(tmp_path, "x = 1\n"))


def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """The checker runs with ``open`` and the Path reads patched to raise."""
    rules = _contract().rules
    facts = module_facts(
        "handler_planted.py", _TYPED.replace("thing: ModelThing", "a, b")
    )

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker performed I/O")

    for name in ("read_text", "read_bytes", "open"):
        monkeypatch.setattr(Path, name, refuse)
    monkeypatch.setattr(builtins, "open", refuse)
    issues = check_handler_shape(facts, rules)
    assert [i.rule_name for i in issues] == ["noncanonical_handle"]


def test_scan_set_is_rule_data() -> None:
    assert "**/handlers/**/*.py" in _contract().target_patterns


def test_node_packages_of_this_repository_hold_no_misshapen_handler() -> None:
    """The hook's scope: every module under a ``nodes/`` package is judged and clean."""
    validator = ValidatorHandlerShape()
    targets = sorted(_NODES.glob("**/nodes/**/*.py"))
    assert targets
    assert validator.validate(targets).issues == []
