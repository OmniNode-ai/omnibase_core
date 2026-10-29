# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture files and rule parameters of the binding conformance validator entry (OMN-21514).

A ``violation_<rule>.py`` fixture yields exactly one issue with that rule id; a ``clean_*.py`` fixture
yields none; and changing any ``parameters`` key of a rule row changes the verdict on the fixture that
row catches.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_binding_conformance import (
    ValidatorBindingConformance,
)

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "validation"
    / "binding_conformance"
    / "handlers"
)
VIOLATIONS = ("env_read", "path_literal", "url_literal")
# The shipped contract excludes test trees, and the fixtures live in one.
NEVER_MATCHES = "(?!)"


def _materialise(name: str, directory: Path) -> Path:
    """Copy ``<name>.py.txt`` to a handler path; the fixtures are text so no repo hook reads them as code."""
    handlers = directory / "handlers"
    handlers.mkdir(exist_ok=True)
    target = handlers / name
    target.write_text(
        (FIXTURES / f"{name}.txt").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return target


def _entry(
    contract: ModelValidatorSubcontract | None = None,
) -> ValidatorBindingConformance:
    shipped = contract or ValidatorBindingConformance().contract
    return ValidatorBindingConformance(
        contract=shipped.model_copy(update={"exclude_patterns": []})
    )


@pytest.mark.parametrize("rule", VIOLATIONS)
def test_a_violation_fixture_yields_exactly_one_issue_with_its_rule(
    rule: str, tmp_path: Path
) -> None:
    result = _entry().validate_file(_materialise(f"violation_{rule}.py", tmp_path))
    assert [issue.code for issue in result.issues] == [rule]


def test_the_clean_fixture_yields_no_issue(tmp_path: Path) -> None:
    result = _entry().validate_file(_materialise("clean_handler.py", tmp_path))
    assert result.issues == []
    assert result.is_valid is True


def _with_parameters(
    contract: ModelValidatorSubcontract, rule_id: str, parameters: dict[str, object]
) -> ModelValidatorSubcontract:
    rules = [
        rule.model_copy(update={"parameters": parameters})
        if rule.rule_id == rule_id
        else rule
        for rule in contract.rules
    ]
    return contract.model_copy(update={"rules": rules})


def _parameter_rows() -> list[tuple[str, str, object]]:
    contract = ValidatorBindingConformance().contract
    return [
        (rule.rule_id, key, value)
        for rule in contract.rules
        for key, value in (rule.parameters or {}).items()
    ]


def _mutated(value: object) -> object:
    return [] if isinstance(value, list) else NEVER_MATCHES


@pytest.mark.parametrize(("rule_id", "key", "value"), _parameter_rows())
def test_every_parameter_of_every_rule_changes_the_verdict_it_governs(
    rule_id: str, key: str, value: object, tmp_path: Path
) -> None:
    shipped = ValidatorBindingConformance().contract
    rule: ModelValidatorRule = next(r for r in shipped.rules if r.rule_id == rule_id)
    parameters = {**(rule.parameters or {}), key: _mutated(value)}
    fixture = _materialise(f"violation_{rule_id}.py", tmp_path)
    if isinstance(value, list):
        # An emptied name list is refused, which is a changed verdict as well.
        with pytest.raises(Exception, match=key):
            _entry(_with_parameters(shipped, rule_id, parameters)).validate_file(
                fixture
            )
        return
    mutated = _entry(_with_parameters(shipped, rule_id, parameters))
    assert mutated.validate_file(fixture).issues == []


def test_the_parameter_table_covers_every_literal_rule() -> None:
    assert {row[0] for row in _parameter_rows()} == set(VIOLATIONS)
