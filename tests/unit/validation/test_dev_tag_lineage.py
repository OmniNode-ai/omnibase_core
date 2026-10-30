# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Planted rules, unresolved facts, policy and source/lock parsing (OMN-17427)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_dev_tag_lineage_candidate import (
    ModelDevTagLineageCandidate,
)
from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.validation.checker_dev_tag_lineage import (
    check_dev_tag_lineage,
    load_policy,
    normalize,
    parse_candidates,
    parse_lock,
)
from omnibase_core.validation.validator_dev_tag_lineage import ValidatorDevTagLineage

pytestmark = pytest.mark.unit
_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/validation/dev_tag_lineage"
_RULES = (
    "tag_absent",
    "tag_suffix_mismatch",
    "tag_off_branch",
    "declared_version_mismatch",
    "lock_mismatch",
    "lineage_unresolved",
)


def _single(
    values: tuple[ModelDevTagLineageCandidate, ...],
) -> ModelDevTagLineageCandidate:
    """The one candidate a fixture declares."""
    assert len(values) == 1, values
    return values[0]


@pytest.mark.parametrize("rule", _RULES)
@pytest.mark.parametrize("state", ["clean", "violation"])
def test_planted_rules(rule: str, state: str) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    directory = _FIXTURES / f"{state}_{rule}"
    path = directory / "pyproject.toml.txt"
    candidate = _single(parse_candidates(path.read_text(), policy))
    lock = directory / (policy.lock_name + ".txt")
    entries = parse_lock(lock.read_text(), policy) if lock.exists() else None
    table = json.loads((_FIXTURES / "facts.json").read_text())
    facts = ModelDevTagLineageFacts.model_validate(table[directory.name])
    issues = check_dev_tag_lineage(path, candidate, facts, entries, validator.contract)
    assert [issue.rule_name for issue in issues] == (
        [rule] if state == "violation" else []
    )
    assert all(issue.suggestion for issue in issues)


@pytest.mark.parametrize("field", ["tag_exists", "commit", "version", "on_branch"])
def test_each_unresolved_fact_fails_closed(field: str) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    candidate = _single(
        parse_candidates(
            (_FIXTURES / "clean_lineage_unresolved/pyproject.toml.txt").read_text(),
            policy,
        )
    )
    data = {
        "tag_exists": True,
        "commit": "a" * 40,
        "version": "2.3.4",
        "on_branch": True,
        "detail": "partial",
    }
    data[field] = None
    issues = check_dev_tag_lineage(
        Path("pyproject.toml.txt"),
        candidate,
        ModelDevTagLineageFacts.model_validate(data),
        None,
        validator.contract,
    )
    assert [issue.rule_name for issue in issues] == ["lineage_unresolved"]


def test_scope_all_tables_filter_and_normalization() -> None:
    policy = load_policy(ValidatorDevTagLineage().contract)
    text = (_FIXTURES / "clean_tag_absent/pyproject.toml.txt").read_text()
    override = '\n[tool.uv]\noverride-dependencies = ["demo-package==9.8.7"]\n'
    candidate = _single(parse_candidates(text + override, policy, "DEMO.package"))
    assert candidate.declared_specs == ("==9.8.7", "==2.3.4")
    assert candidate.url == "file:///fixture/origin.git"
    assert normalize("Demo_Package", policy) == "demo-package"
    assert not parse_candidates(text, policy, "other")
    for change in (', rev = "abc"', ', branch = "dev"'):
        assert not parse_candidates(
            text.replace("tag = ", change[2:] + ", tag = "), policy
        )
    assert not parse_candidates(
        text.replace("dev-20261029143607-aaaaaaaaaaaa", "dev"), policy
    )
    reordered = policy.model_copy(
        update={"declaration_tables": tuple(reversed(policy.declaration_tables))}
    )
    candidate = _single(parse_candidates(text + override, reordered))
    assert candidate.declared_specs == ("==2.3.4", "==9.8.7")
    assert (
        parse_candidates(
            text.replace("tag = ", "tag = ").replace(
                'git = "file:///fixture/origin.git"', "git = 123"
            ),
            policy,
        )
        == ()
    )


@pytest.mark.parametrize(
    ("spec", "admitted"),
    [
        ("", True),
        ("==2.3.4", True),
        (">=2.3.0,<3.0", True),
        (">=2.3.4", True),
        ("~=2.3.0", True),
        ("==2.3.*", True),
        ("===2.3.4", True),
        ("==2.3.4,<3", True),
        ("==2.3.5", False),
        (">=3.0,<4.0", False),
        ("!=2.3.4", False),
        (">=not-a-version", False),
        ("not a specifier", False),
    ],
)
def test_pep440_declarations_admit_the_tag_version(spec: str, admitted: bool) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    text = (
        (_FIXTURES / "clean_tag_absent/pyproject.toml.txt")
        .read_text()
        .replace("==2.3.4", spec)
    )
    candidate = _single(parse_candidates(text, policy))
    facts = ModelDevTagLineageFacts(
        tag_exists=True, commit="a" * 40, version="2.3.4", on_branch=True, detail="ok"
    )
    issues = check_dev_tag_lineage(
        Path("pyproject.toml.txt"), candidate, facts, None, validator.contract
    )
    assert [issue.rule_name for issue in issues] == (
        [] if admitted else ["declared_version_mismatch"]
    )


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("clean_declared_version_mismatch", []),
        ("clean_declared_version_range", []),
        ("violation_declared_version_mismatch", ["declared_version_mismatch"]),
        ("violation_declared_version_missing", ["declared_version_mismatch"]),
    ],
)
def test_declared_version_planted_exact_range_and_missing(
    fixture: str, expected: list[str]
) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    path = _FIXTURES / fixture / "pyproject.toml.txt"
    candidate = _single(parse_candidates(path.read_text(), policy))
    table = json.loads((_FIXTURES / "facts.json").read_text())
    issues = check_dev_tag_lineage(
        path,
        candidate,
        ModelDevTagLineageFacts.model_validate(table[fixture]),
        None,
        validator.contract,
    )
    assert [issue.rule_name for issue in issues] == expected


@pytest.mark.parametrize(
    ("project_spec", "overrides", "admitted"),
    [
        (">=2.3.0,<3.0", ["==2.3.4"], True),
        (">=3.0,<4.0", ["==2.3.4"], False),
        (">=2.3.0,<3.0", ["==2.3.5"], False),
        (">=2.3.0,<3.0", ["==2.3.4", ">=3.0,<4.0"], False),
        (">=2.3.0,<3.0", [">=invalid"], False),
    ],
)
def test_every_declaration_in_every_table_must_admit(
    project_spec: str, overrides: list[str], admitted: bool
) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    text = (
        (_FIXTURES / "clean_tag_absent/pyproject.toml.txt")
        .read_text()
        .replace("==2.3.4", project_spec)
    )
    text += (
        "\n[tool.uv]\noverride-dependencies = "
        + json.dumps(["demo-package" + spec for spec in overrides])
        + "\n"
    )
    candidate = _single(parse_candidates(text, policy))
    facts = ModelDevTagLineageFacts(
        tag_exists=True, commit="a" * 40, version="2.3.4", on_branch=True, detail="ok"
    )
    issues = check_dev_tag_lineage(
        Path("pyproject.toml"), candidate, facts, None, validator.contract
    )
    assert [issue.rule_name for issue in issues] == (
        [] if admitted else ["declared_version_mismatch"]
    )


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "version", "tag", "commit", "malformed_url"]
)
def test_lock_identity_requires_exactly_one_matching_entry(change: str) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    directory = _FIXTURES / "clean_lock_mismatch"
    candidate = _single(
        parse_candidates((directory / "pyproject.toml.txt").read_text(), policy)
    )
    lock = (directory / "uv.lock.txt").read_text()
    if change == "missing":
        lock = "version = 1"
    elif change == "duplicate":
        lock += lock[lock.index("[[package]]") :]
    elif change == "version":
        lock = lock.replace("2.3.4", "2.3.5")
    elif change == "tag":
        lock = lock.replace("tag=dev-", "tag=bad-")
    elif change == "commit":
        lock = lock.replace("#" + "a" * 40, "#" + "b" * 40)
    else:
        lock = lock.replace("file:///fixture/origin.git", "https://[invalid")
    facts = ModelDevTagLineageFacts(
        tag_exists=True, commit="a" * 40, version="2.3.4", on_branch=True, detail="ok"
    )
    issues = check_dev_tag_lineage(
        Path("pyproject.toml.txt"),
        candidate,
        facts,
        parse_lock(lock, policy),
        validator.contract,
    )
    assert [issue.rule_name for issue in issues] == ["lock_mismatch"]


def test_validator_requires_resolver_and_calls_once_per_candidate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text((_FIXTURES / "clean_tag_absent/pyproject.toml.txt").read_text())
    with pytest.raises(Exception, match="needs the resolver"):
        ValidatorDevTagLineage(root=tmp_path).validate(tmp_path)
    calls = []

    def resolve(request):
        calls.append(request)
        return ModelDevTagLineageFacts(tag_exists=False, detail="absent")

    result = ValidatorDevTagLineage(root=tmp_path, resolver=resolve).validate(
        [tmp_path, path]
    )
    assert len(calls) == 1
    assert [issue.rule_name for issue in result.issues] == ["tag_absent"]
    assert (
        ValidatorDevTagLineage(root=tmp_path, package="other")
        .validate(tmp_path)
        .is_valid
    )


def test_models_are_frozen_and_forbid_extra_fields() -> None:
    facts = ModelDevTagLineageFacts(detail="unresolved")
    with pytest.raises(ValidationError):
        facts.detail = "mutated"
    with pytest.raises(ValidationError):
        ModelDevTagLineageFacts.model_validate({"detail": "x", "extra": True})


def test_rule_policy_changes_decisions_and_messages() -> None:
    validator = ValidatorDevTagLineage()
    rule = next(
        rule
        for rule in validator.contract.rules
        if rule.rule_id == "lineage_unresolved"
    )
    parameters = dict(rule.parameters or {})
    parameters["tag_pattern"] = "^custom$"
    contract = validator.contract.model_copy(
        update={
            "rules": [
                item.model_copy(update={"parameters": parameters})
                if item.rule_id == rule.rule_id
                else item
                for item in validator.contract.rules
            ]
        }
    )
    text = (_FIXTURES / "clean_tag_absent/pyproject.toml.txt").read_text()
    assert parse_candidates(text, load_policy(contract)) == ()
    assert (
        len(
            parse_candidates(
                text.replace("dev-20261029143607-aaaaaaaaaaaa", "custom"),
                load_policy(contract),
            )
        )
        == 1
    )


def test_lock_only_target_checks_its_adjacent_project(tmp_path: Path) -> None:
    directory = _FIXTURES / "clean_lock_mismatch"
    (tmp_path / "pyproject.toml").write_text(
        (directory / "pyproject.toml.txt").read_text()
    )
    lock = tmp_path / "uv.lock"
    lock.write_text((directory / "uv.lock.txt").read_text())
    validator = ValidatorDevTagLineage(
        root=tmp_path,
        resolver=lambda request: ModelDevTagLineageFacts(
            tag_exists=True,
            commit="a" * 40,
            version="2.3.4",
            on_branch=True,
            detail="ok",
        ),
    )
    assert validator.validate([lock]).is_valid
    lock.write_text(lock.read_text().replace("2.3.4", "9.9.9"))
    assert [issue.rule_name for issue in validator.validate([lock]).issues] == [
        "lock_mismatch"
    ]


def test_invalid_or_weakened_contract_fails_closed() -> None:
    validator = ValidatorDevTagLineage()
    for contract in (
        validator.contract.model_copy(update={"rules": []}),
        validator.contract.model_copy(update={"fail_on_error": False}),
        validator.contract.model_copy(
            update={
                "rules": [
                    rule.model_copy(update={"enabled": False})
                    for rule in validator.contract.rules
                ]
            }
        ),
    ):
        with pytest.raises(Exception, match="dev_tag_lineage"):
            load_policy(contract)


@pytest.mark.parametrize(
    ("second_spec", "expected"),
    [
        (">=2.3.0,<3.0", []),
        (">=3.0,<4.0", ["declared_version_mismatch"]),
        (">=invalid", ["declared_version_mismatch"]),
    ],
)
def test_every_optional_dependency_declaration_must_admit(
    second_spec: str, expected: list[str]
) -> None:
    validator = ValidatorDevTagLineage()
    policy = load_policy(validator.contract)
    text = (
        _FIXTURES / "violation_declared_version_missing/pyproject.toml.txt"
    ).read_text()
    text += f'\n[project.optional-dependencies]\nfeature = ["demo-package>=2.3.0"]\nfull = ["Demo_Package{second_spec}"]\n'
    candidate = _single(parse_candidates(text, policy))
    assert candidate.declared_specs == (">=2.3.0", second_spec)
    facts = ModelDevTagLineageFacts(
        tag_exists=True, commit="a" * 40, version="2.3.4", on_branch=True, detail="ok"
    )
    issues = check_dev_tag_lineage(
        Path("pyproject.toml"), candidate, facts, None, validator.contract
    )
    assert [issue.rule_name for issue in issues] == expected
