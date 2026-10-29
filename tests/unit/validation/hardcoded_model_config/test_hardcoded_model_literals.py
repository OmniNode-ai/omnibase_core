# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""K6 families O, G, F, P, S, H and B (OMN-21537, plan task T4.1b)."""

from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.private_vocabulary import ModelPrivateVocabularyResolution
from omnibase_core.models.validation.model_hardcoded_literal_rule_set import (
    ModelHardcodedLiteralRuleSet,
)
from omnibase_core.validation.checker_hardcoded_model_literals import (
    check_text,
    load_rule_set,
    scan_literals,
)
from omnibase_core.validation.hardcoded_model_config import (
    runtime_hardcoded_model_config as runtime,
)
from omnibase_core.validation.hardcoded_model_config.handler import (
    scan,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_hardcoded_model_literals import (
    ValidatorHardcodedModelLiterals,
)

FIXTURES = Path(__file__).parents[3] / "fixtures/validation/hardcoded_model_literals"
ORG = "ExampleOrg"
REPOSITORIES = ("omnibase_core", "omnimarket", "omnibase_spi")
HOSTS = ("h201", "h202")
_FORMS = runtime.load_policy(
    ModelPrivateVocabularyResolution.model_construct(path=None, text=None)
)
RULE_IDS = {
    "O": "literal_operational_number",
    "G": "literal_first_party_url",
    "F": "literal_filesystem_location",
    "P": "literal_repository_list",
    "S": "literal_ruling_stamp",
    "H": "literal_host_list",
    "B": "literal_budget_constant",
}


def _rows() -> list[ModelValidatorRule]:
    return list(ValidatorHardcodedModelLiterals().contract.rules)


def _rule_set(
    rows: list[ModelValidatorRule] | None = None, org: str = ORG
) -> ModelHardcodedLiteralRuleSet:
    return load_rule_set(
        rows or _rows(),
        github_org=org,
        repository_names=REPOSITORIES,
        host_names=HOSTS,
        python_suffixes=_FORMS.python_suffixes,
        slash_comment_suffixes=_FORMS.slash_comment_suffixes,
        no_comment_suffixes=_FORMS.no_comment_suffixes,
        exclude_patterns=ValidatorHardcodedModelLiterals().contract.exclude_patterns,
    )


def _issues(name: str, rows: list[ModelValidatorRule] | None = None) -> list[str]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return [
        i.rule_name or "" for i in check_text(f"src/pkg/{name}", text, _rule_set(rows))
    ]


def _with(rule_id: str, **changes: object) -> list[ModelValidatorRule]:
    rows = []
    for row in _rows():
        if row.rule_id == rule_id:
            row = row.model_copy(
                update={"parameters": {**(row.parameters or {}), **changes}}
            )
        rows.append(row)
    return rows


def _stems(prefix: str) -> list[str]:
    return sorted(p.name for p in FIXTURES.iterdir() if p.name.startswith(prefix))


def _rule_of(name: str) -> str:
    return next(
        rid
        for rid in RULE_IDS.values()
        if name.split(".")[0].startswith(("violation_", "clean_")) and rid in name
    )


@pytest.mark.unit
@pytest.mark.parametrize("name", _stems("violation_"))
def test_families_o_g_f_p_s_h_b_violation_fixture_yields_exactly_one_issue(
    name: str,
) -> None:
    assert _issues(name) == [_rule_of(name)]


@pytest.mark.unit
@pytest.mark.parametrize("name", _stems("clean_"))
def test_families_o_g_f_p_s_h_b_clean_fixture_yields_no_issue(name: str) -> None:
    assert _issues(name) == []


@pytest.mark.unit
def test_families_o_g_f_p_s_h_b_every_rule_has_both_fixtures() -> None:
    for rule_id in RULE_IDS.values():
        assert any(n.startswith(f"violation_{rule_id}") for n in _stems("violation_"))
        assert any(n.startswith(f"clean_{rule_id}") for n in _stems("clean_"))


PLANTED = [
    ("O", "return client.get(timeout=30)"),
    ("O", "_POLL_TIMEOUT_MS = 1000"),
    ("G", 'url = f"https://github.com/{org}/{repo}.git"'),
    ("F", 'def f(root=Path.home() / ".cache" / "x"): ...'),
    ("F", 'REGISTRY_PATH = Path(__file__).parent / "registry.yaml"'),
    ("S", 'RULING = "RULING 2026-10-28T13:32:09Z"'),
    ("H", 'HOSTS = ("h201", "h202")'),
    ("P", 'REPOS = ("omnibase_core", "omnimarket")'),
    ("B", "GH_CALL_BUDGET = 12"),
]


@pytest.mark.unit
@pytest.mark.parametrize(("family", "text"), PLANTED)
def test_families_o_g_f_p_s_h_b_planted_violation_is_refused(
    family: str, text: str
) -> None:
    hits = scan_literals("src/pkg/mod.py", text + "\n", _rule_set())
    assert [h[1] for h in hits] == [family]


@pytest.mark.unit
@pytest.mark.parametrize(("family", "text"), [p for p in PLANTED if p[0] in "OGF"])
def test_families_o_g_f_p_s_h_b_same_text_in_a_comment_passes(
    family: str, text: str
) -> None:
    assert scan_literals("src/pkg/mod.py", "# " + text + "\n", _rule_set()) == []


@pytest.mark.unit
def test_checker_is_pure_facts_in_issues_out(monkeypatch: pytest.MonkeyPatch) -> None:
    rule_set = _rule_set()

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("the checker read the filesystem")

    monkeypatch.setattr(builtins, "open", refuse)
    for attribute in ("read_text", "read_bytes", "open", "exists", "is_file", "stat"):
        monkeypatch.setattr(Path, attribute, refuse)
    issues = check_text("src/pkg/mod.py", "timeout = 30\n", rule_set)
    assert [i.rule_name for i in issues] == [RULE_IDS["O"]]


# Every ``parameters`` key of every rule row, the fixture that key controls, and the
# value that changes that fixture's verdict. ``family`` and the two contract-path keys
# are asserted separately.
MUTATIONS: list[tuple[str, str, str, object]] = [
    ("O", "name_patterns", "violation_literal_operational_number_constant.py", []),
    ("O", "call_names", "violation_literal_operational_number_sleep.py", []),
    ("O", "min_value", "violation_literal_operational_number.py", 10**9),
    ("O", "text_patterns", "violation_literal_operational_number_workflow.yml", []),
    ("G", "hosts", "violation_literal_first_party_url_literal.py", ["other.invalid"]),
    ("G", "scheme_patterns", "violation_literal_first_party_url_literal.py", []),
    ("G", "placeholder_pattern", "violation_literal_first_party_url.py", "NEVER_X"),
    ("F", "home_calls", "violation_literal_filesystem_location.py", []),
    (
        "F",
        "parameter_name_patterns",
        "violation_literal_filesystem_location_dot_directory.py",
        ["^never$"],
    ),
    (
        "F",
        "dot_directory_pattern",
        "violation_literal_filesystem_location_dot_directory.py",
        "^NEVER$",
    ),
    (
        "F",
        "constant_name_patterns",
        "violation_literal_filesystem_location_constant.py",
        ["^never$"],
    ),
    ("F", "anchor_names", "violation_literal_filesystem_location_constant.py", []),
    (
        "F",
        "path_constructors",
        "violation_literal_filesystem_location_constructor.py",
        [],
    ),
    (
        "P",
        "extra_names",
        "mutation_literal_repository_list_extra.py",
        ["extra_one", "extra_two"],
    ),
    ("P", "min_members", "violation_literal_repository_list.py", 3),
    ("S", "stamp_pattern", "violation_literal_ruling_stamp.py", "NEVER_X"),
    ("S", "text_pattern", "violation_literal_ruling_stamp.yml", "NEVER_X"),
    ("H", "min_members", "violation_literal_host_list.py", 3),
    ("B", "name_patterns", "violation_literal_budget_constant.py", ["^NEVER$"]),
    ("B", "min_value", "violation_literal_budget_constant.py", 10**9),
    ("B", "text_pattern", "violation_literal_budget_constant_env.yml", "NEVER_X"),
]


def _row_of(family: str) -> ModelValidatorRule:
    return next(r for r in _rows() if (r.parameters or {})["family"] == family)


@pytest.mark.unit
@pytest.mark.parametrize(("family", "key", "fixture", "mutated"), MUTATIONS)
def test_every_parameters_key_changes_the_verdict_on_its_fixture(
    family: str, key: str, fixture: str, mutated: object
) -> None:
    rule_id = _row_of(family).rule_id
    clean_value = (_row_of(family).parameters or {})[key]
    assert mutated != clean_value
    if fixture.startswith("mutation_literal_repository_list_extra"):
        # the extra names are what makes this fixture a violation
        assert _issues(fixture) == []
        assert _issues(fixture, _with(rule_id, **{key: mutated})) == [rule_id]
        return
    assert _issues(fixture) == [rule_id]
    assert _issues(fixture, _with(rule_id, **{key: mutated})) == []


@pytest.mark.unit
def test_remediation_text_is_the_issue_suggestion_of_its_row() -> None:
    for family, rule_id in RULE_IDS.items():
        fixture = next(n for n in _stems("violation_") if rule_id in n)
        text = (FIXTURES / fixture).read_text(encoding="utf-8")
        marker = f"changed {family}"
        rows = _with(rule_id, remediation=marker)
        [issue] = check_text(f"src/pkg/{fixture}", text, _rule_set(rows))
        assert issue.suggestion == marker


@pytest.mark.unit
def test_mutation_table_covers_every_parameters_key() -> None:
    covered = {(f, k) for f, k, _, _ in MUTATIONS}
    outside_table = {"family", "remediation", "org_contract", "registry_contract"}
    for row in _rows():
        parameters = row.parameters or {}
        for key in parameters:
            if key in outside_table:
                continue
            assert (parameters["family"], key) in covered, (row.rule_id, key)
    assert {k for _, k in covered} <= {
        key for row in _rows() for key in (row.parameters or {})
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    "change",
    [
        {"name_patterns": "not-a-list"},
        {"name_patterns": ["("]},
        {"min_value": "one"},
        {"remediation": ""},
        {"family": ""},
    ],
)
def test_an_invalid_contract_fails_to_load_instead_of_passing(
    change: dict[str, Any],
) -> None:
    with pytest.raises((ModelOnexError, Exception)) as raised:
        load_rule_set(
            _with("literal_operational_number", **change),
            github_org=ORG,
            repository_names=REPOSITORIES,
            host_names=HOSTS,
            python_suffixes=_FORMS.python_suffixes,
            slash_comment_suffixes=_FORMS.slash_comment_suffixes,
            no_comment_suffixes=_FORMS.no_comment_suffixes,
        )
    assert raised.value is not None


@pytest.mark.unit
def test_a_missing_parameters_key_fails_to_load() -> None:
    rows = _rows()
    row = next(r for r in rows if r.rule_id == RULE_IDS["O"])
    parameters = {k: v for k, v in (row.parameters or {}).items() if k != "call_names"}
    rows[rows.index(row)] = row.model_copy(update={"parameters": parameters})
    with pytest.raises(ModelOnexError):
        _rule_set(rows)


@pytest.mark.unit
def test_a_disabled_row_judges_nothing_and_leaves_the_others() -> None:
    for family, rule_id in RULE_IDS.items():
        rows = [
            r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
            for r in _rows()
        ]
        fixture = next(n for n in _stems("violation_") if rule_id in n)
        assert _issues(fixture, rows) == []
        for other_id in set(RULE_IDS.values()) - {rule_id}:
            other = next(n for n in _stems("violation_") if other_id in n)
            assert _issues(other, rows) == [other_id], (family, other_id)


@pytest.mark.unit
def test_families_o_g_f_p_s_h_b_apply_to_source_not_tests_or_docs() -> None:
    policy = _policy()
    literal_rules = _rule_set()
    text = "timeout = 30\n"
    assert [f.family for f in scan("src/pkg/mod.py", text, policy, literal_rules)] == [
        "O"
    ]
    assert scan("tests/unit/test_mod.py", text, policy, literal_rules) == []
    assert scan("docs/guide.md", text, policy, literal_rules) == []
    assert scan("src/pkg/mod.py", text, policy) == []


def _policy() -> ModelHardcodedModelConfigPolicy:
    return runtime.load_policy(_neutral_vocabulary())


def _neutral_vocabulary() -> Any:
    from omnibase_core.models.private_vocabulary import (
        ModelPrivateVocabularyResolution,
    )

    return ModelPrivateVocabularyResolution.model_construct(path=None, text=None)


@pytest.mark.unit
def test_exclude_patterns_keep_rule_data_and_declarations_out_of_scope() -> None:
    rule_set = _rule_set()
    text = "ls_remote_timeout_seconds: 30\n"
    assert scan_literals("src/pkg/other.yaml", text, rule_set) != []
    assert scan_literals("src/omnibase_core/contracts/x.yaml", text, rule_set) == []
    assert scan_literals("src/pkg/nodes/n/contract.yaml", text, rule_set) == []
    assert scan_literals("pyproject.toml", "UV_X_TIMEOUT = 30\n", rule_set) == []


def _contract_root(tmp_path: Path, org: str) -> Path:
    (tmp_path / "contracts").mkdir()
    sibling = yaml.safe_load(
        (
            Path(runtime.__file__).parents[2] / "contracts/internal_sibling_pins.yaml"
        ).read_text()
    )
    sibling["github_org"] = org
    (tmp_path / "contracts/internal_sibling_pins.yaml").write_text(
        yaml.safe_dump(sibling)
    )
    layers = yaml.safe_load(
        (Path(runtime.__file__).parents[2] / "contracts/repo_layers.yaml").read_text()
    )
    (tmp_path / "contracts/repo_layers.yaml").write_text(yaml.safe_dump(layers))
    return tmp_path


@pytest.mark.unit
def test_g_family_reads_github_org_from_the_sibling_pins_contract(
    tmp_path: Path,
) -> None:
    policy = _policy()
    text = 'U = "https://github.com/OrgOne/repo.git"\n'
    one = runtime.load_literal_rule_set(
        policy,
        _contract_root(
            tmp_path / "a" if (tmp_path / "a").mkdir() is None else tmp_path, "OrgOne"
        ),
    )
    other_root = tmp_path / "b"
    other_root.mkdir()
    two = runtime.load_literal_rule_set(policy, _contract_root(other_root, "OrgTwo"))
    assert [h[1] for h in scan_literals("src/pkg/m.py", text, one)] == ["G"]
    assert scan_literals("src/pkg/m.py", text, two) == []


@pytest.mark.unit
def test_policy_and_checker_name_no_organisation() -> None:
    package = Path(runtime.__file__).parents[2]
    real_org = yaml.safe_load(
        (package / "contracts/internal_sibling_pins.yaml").read_text()
    )["github_org"]
    for rel in (
        "validation/hardcoded_model_config/policy.yaml",
        "validation/contracts/hardcoded_model_literals.validation.yaml",
        "validation/checker_hardcoded_model_literals.py",
        "validation/validator_hardcoded_model_literals.py",
    ):
        assert real_org not in (package / rel).read_text(encoding="utf-8"), rel
