# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the contracts-and-DI rules in the generic validator format (OMN-21623).

RULING 2026-10-29T01:06:13Z: dependencies live in contracts and overlays, no value is
hard-coded, and an in-memory default is only injected through DI. Each rule row of
``contracts_and_di.validation.yaml`` has a planted ``violation_<rule>`` fixture that must
yield exactly one issue of that rule and a ``clean_<rule>`` fixture that must yield none.
The tests load the shipped contract, so the values under test are the values the
validator runs with.
"""

from __future__ import annotations

import builtins
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_contracts_and_di_facts import (
    ModelContractsAndDiFacts,
)
from omnibase_core.validation.checker_contracts_and_di import check_contracts_and_di
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "tests/fixtures/validation/contracts_and_di"
_CLEAN_SITE = Path(".github/workflows/clean.yml")
_FACTS = ModelContractsAndDiFacts(
    repository="consumer",
    tag_source_repositories=frozenset({"omnibase_core", "omnibase_spi"}),
    advanced_sites=frozenset({f"omnibase_core>consumer:{_CLEAN_SITE.as_posix()}"}),
)
_PLANTED_WORKFLOW = _FIXTURES / "violation_first_party_workflow_pin.yml.txt"


def _contract() -> ModelValidatorSubcontract:
    return ValidatorContractsAndDi().contract


def _rules() -> list[ModelValidatorRule]:
    return list(_contract().rules)


def _rule_ids() -> list[str]:
    return [rule.rule_id for rule in _rules() if rule.enabled]


def _site(fixture: Path) -> Path:
    """The repository-relative path a fixture stands for."""
    name = fixture.name
    if name.endswith(".py.txt"):
        return Path("src/pkg/module.py")
    if name.endswith(".toml.txt"):
        return Path("pyproject.toml")
    if "workflow_pin" in name:
        return (
            _CLEAN_SITE
            if name.startswith("clean_")
            else Path(".github/workflows/caller.yml")
        )
    return Path("config/settings.yaml")


def _fixtures(prefix: str, rule_id: str) -> list[Path]:
    """Fixtures of one rule; per_principal_block also plants a per-host mapping."""
    stems = {rule_id}
    if rule_id == "per_principal_block":
        stems.add("per_host_settings")
    return sorted(
        path
        for path in _FIXTURES.iterdir()
        if any(path.name.startswith(f"{prefix}_{stem}.") for stem in stems)
    )


def _check(fixture: Path, rules: list[ModelValidatorRule]) -> list[str]:
    issues = check_contracts_and_di(
        _site(fixture), fixture.read_text(encoding="utf-8"), rules, _FACTS
    )
    return [issue.rule_name or "" for issue in issues]


@pytest.mark.parametrize("rule_id", _rule_ids())
def test_every_enabled_rule_has_planted_and_clean_fixtures(rule_id: str) -> None:
    assert _fixtures("violation", rule_id), f"no violation fixture for {rule_id}"
    assert _fixtures("clean", rule_id), f"no clean fixture for {rule_id}"


@pytest.mark.parametrize("rule_id", _rule_ids())
def test_violation_fixture_yields_exactly_one_issue_of_its_rule(rule_id: str) -> None:
    for fixture in _fixtures("violation", rule_id):
        assert _check(fixture, _rules()) == [rule_id], fixture.name


@pytest.mark.parametrize("rule_id", _rule_ids())
def test_clean_fixture_yields_no_issue(rule_id: str) -> None:
    for fixture in _fixtures("clean", rule_id):
        assert _check(fixture, _rules()) == [], fixture.name


@pytest.mark.parametrize("rule_id", _rule_ids())
def test_disabling_a_row_stops_its_violation_from_failing(rule_id: str) -> None:
    rules = [
        rule.model_copy(update={"enabled": False}) if rule.rule_id == rule_id else rule
        for rule in _rules()
    ]
    for fixture in _fixtures("violation", rule_id):
        if rule_id == "unparseable_file":
            with pytest.raises(ModelOnexError):
                _check(fixture, rules)
        else:
            assert rule_id not in _check(fixture, rules), fixture.name


def _parameter_cases() -> list[tuple[str, str]]:
    return [
        (rule.rule_id, key)
        for rule in _rules()
        if rule.enabled
        for key in sorted(rule.parameters or {})
    ]


@pytest.mark.parametrize(("rule_id", "key"), _parameter_cases())
def test_a_row_missing_any_parameter_fails_to_load(rule_id: str, key: str) -> None:
    rules = []
    for rule in _rules():
        if rule.rule_id == rule_id:
            parameters = dict(rule.parameters or {})
            del parameters[key]
            rule = rule.model_copy(update={"parameters": parameters})
        rules.append(rule)
    with pytest.raises(ModelOnexError):
        _check(_FIXTURES / "clean_literal_ip.py.txt", rules)


def test_an_unknown_kind_fails_to_load() -> None:
    rules = [
        rule.model_copy(
            update={"parameters": {**(rule.parameters or {}), "kind": "nope"}}
        )
        if rule.rule_id == "literal_ip"
        else rule
        for rule in _rules()
    ]
    with pytest.raises(ModelOnexError):
        _check(_FIXTURES / "clean_literal_ip.py.txt", rules)


def test_the_pin_is_judged_by_the_pinned_repository_tag_source() -> None:
    facts = _FACTS.model_copy(update={"tag_source_repositories": frozenset()})
    issues = check_contracts_and_di(
        Path(".github/workflows/caller.yml"),
        _PLANTED_WORKFLOW.read_text(encoding="utf-8"),
        _rules(),
        facts,
    )
    assert issues == ()


def test_the_checker_performs_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = {
        fixture: fixture.read_text(encoding="utf-8")
        for fixture in sorted(_FIXTURES.iterdir())
    }
    rules = _rules()

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    for fixture, text in texts.items():
        check_contracts_and_di(_site(fixture), text, rules, _FACTS)


def _workspace(tmp_path: Path, listed: bool) -> Path:
    """A workspace: the pinned repository's tag source and manifest, and a consumer."""
    core = tmp_path / "omnibase_core"
    (core / ".github/workflows").mkdir(parents=True)
    (core / ".github/workflows/dev-merge-tag.yml").write_text("name: tag\n")
    (core / "docs").mkdir()
    site = "    pin_sites:\n      - path: .github/workflows/caller.yml\n"
    (core / "docs/downstream-repos.yaml").write_text(
        "version: 1\nrepos:\n  - name: consumer\n"
        + (site if listed else "    pin_sites: []\n")
    )
    consumer = tmp_path / "consumer"
    (consumer / ".git").mkdir(parents=True)
    (consumer / ".github/workflows").mkdir(parents=True)
    caller = consumer / ".github/workflows/caller.yml"
    caller.write_text(_PLANTED_WORKFLOW.read_text(encoding="utf-8"))
    return caller


def test_validator_reads_the_advancer_manifest_from_the_workspace(
    tmp_path: Path,
) -> None:
    caller = _workspace(tmp_path, listed=False)
    result = ValidatorContractsAndDi().validate([caller])
    assert [issue.rule_name for issue in result.issues] == ["first_party_workflow_pin"]


def test_a_pin_site_the_manifest_lists_passes(tmp_path: Path) -> None:
    caller = _workspace(tmp_path, listed=True)
    assert ValidatorContractsAndDi().validate([caller]).issues == []


def test_injected_workspace_roots_replace_the_default(tmp_path: Path) -> None:
    caller = _workspace(tmp_path, listed=False)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    validator = ValidatorContractsAndDi(workspace_roots=[elsewhere])
    assert validator.validate([caller]).issues == []


def test_the_contract_holds_no_suppression_comment() -> None:
    contract = _contract()
    assert list(contract.suppression_comments) == []
    assert contract.max_violations == 0
