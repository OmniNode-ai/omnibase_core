# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Dependency provenance in the generic validator format (OMN-22011, plan task T2.3).

One planted fixture per rule (exactly one issue carrying that rule id), one clean fixture
per admitted shape, the rule data mutation and load-failure tests, the purity test of the
checker, the canary through the hook entry, and the wiring of the hook id.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.dep_provenance.model_dep_provenance_rules import (
    ModelDepProvenanceRules,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    main_for_reference,
)
from omnibase_core.validation.checker_dep_provenance import check_dep_provenance
from omnibase_core.validation.validator_dep_provenance import ValidatorDepProvenance
from omnibase_core.validation.validator_first_party_ref import (
    ValidatorFirstPartyRef,
    dev_tag_pattern,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests/fixtures/validation/dep_provenance"
CONTRACT = (
    ROOT / "src/omnibase_core/validation/contracts/dep_provenance.validation.yaml"
)
HOOK_ID = "check-dep-provenance"

CLEAN = sorted(path.name for path in FIXTURES.glob("clean_*"))
PLANTED: dict[str, str] = {
    "violation_rev_pin": "source_shape_not_admitted",
    "violation_branch_pin": "source_shape_not_admitted",
    "violation_release_tag": "source_shape_not_admitted",
    "violation_malformed_dev_tag": "source_shape_not_admitted",
    "violation_dev_tag_with_rev": "source_shape_not_admitted",
    "violation_path_source": "source_shape_not_admitted",
    "violation_subtable_rev": "source_shape_not_admitted",
    "violation_list_of_sources": "source_shape_not_admitted",
    "violation_infra_rev_pin": "source_shape_not_admitted",
    "violation_comment_is_no_exemption": "source_shape_not_admitted",
    "violation_dev_tag_foreign_repo": "dev_tag_foreign_repository",
    "violation_dev_tag_wrong_sibling": "dev_tag_foreign_repository",
    "violation_foreign_git_source": "foreign_git_source",
    "violation_invalid_toml": "invalid_pyproject",
}
RULE_IDS = {
    "source_vocabulary",
    "source_shape_not_admitted",
    "dev_tag_foreign_repository",
    "foreign_git_source",
    "invalid_pyproject",
}


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _staged(case: str, tmp_path: Path) -> Path:
    """Copy a fixture to a path outside tests/ so the contract's exclusions do not apply."""
    target = tmp_path / case / "pyproject.toml"
    target.parent.mkdir(parents=True)
    shutil.copy(FIXTURES / case / "pyproject.toml.txt", target)
    return target


def _validator(contract: ModelValidatorSubcontract | None = None):
    return ValidatorDepProvenance(contract)


def _rule_ids(case: str, tmp_path: Path, contract=None) -> list[str]:
    result = _validator(contract).validate_file(_staged(case, tmp_path))
    return [str(issue.rule_name) for issue in result.issues]


def test_fixture_sets_are_not_empty() -> None:
    assert len(CLEAN) >= 9
    assert set(PLANTED) == {path.name for path in FIXTURES.glob("violation_*")}


@pytest.mark.parametrize("case", CLEAN)
def test_clean_shape_passes(case: str, tmp_path: Path) -> None:
    assert _rule_ids(case, tmp_path) == []


@pytest.mark.parametrize(("case", "rule_id"), sorted(PLANTED.items()))
def test_one_defect_is_one_issue_with_its_rule_id(
    case: str, rule_id: str, tmp_path: Path
) -> None:
    assert _rule_ids(case, tmp_path) == [rule_id]


def test_every_finding_rule_has_a_planted_fixture() -> None:
    assert set(PLANTED.values()) == RULE_IDS - {"source_vocabulary"}


def test_contract_declares_exactly_the_rule_set() -> None:
    assert {rule.rule_id for rule in _contract().rules} == RULE_IDS


@pytest.mark.parametrize("rule_id", sorted(set(PLANTED.values())))
def test_disabling_a_rule_row_silences_its_fixture(
    rule_id: str, tmp_path: Path
) -> None:
    contract = _contract()
    rows = [
        row.model_copy(update={"enabled": False}) if row.rule_id == rule_id else row
        for row in contract.rules
    ]
    muted = contract.model_copy(update={"rules": rows})
    for case, expected in PLANTED.items():
        if expected == rule_id:
            assert rule_id not in _rule_ids(case, tmp_path / rule_id, muted)


def _vocabulary_mutated(contract, **changes):
    rows = []
    for row in contract.rules:
        if row.rule_id == "source_vocabulary":
            row = row.model_copy(update={"parameters": {**row.parameters, **changes}})
        rows.append(row)
    return contract.model_copy(update={"rules": rows})


def test_exempt_packages_is_rule_data(tmp_path: Path) -> None:
    contract = _vocabulary_mutated(_contract(), exempt_packages=["some-lib"])
    assert _rule_ids("violation_foreign_git_source", tmp_path, contract) == []


def test_admitted_shapes_per_package_is_rule_data(tmp_path: Path) -> None:
    rows = [
        "omnibase-core|omnibase_core|registry",
        "omnibase-spi|omnibase_spi|registry,sibling_dev_tag",
    ]
    contract = _vocabulary_mutated(_contract(), packages=rows)
    assert _rule_ids("clean_sibling_dev_tag", tmp_path, contract) == [
        "source_shape_not_admitted"
    ]


def test_governed_package_list_is_rule_data(tmp_path: Path) -> None:
    rows = ["omnibase-spi|omnibase_spi|registry,sibling_dev_tag"]
    contract = _vocabulary_mutated(_contract(), packages=rows)
    assert _rule_ids("violation_rev_pin", tmp_path, contract) == ["foreign_git_source"]


def test_organisation_is_rule_data(tmp_path: Path) -> None:
    contract = _vocabulary_mutated(_contract(), github_org="another-org")
    assert _rule_ids("clean_sibling_dev_tag", tmp_path, contract) == [
        "dev_tag_foreign_repository"
    ]


def test_git_keys_are_rule_data(tmp_path: Path) -> None:
    contract = _vocabulary_mutated(_contract(), git_keys=["git", "branch", "tag"])
    assert _rule_ids("violation_dev_tag_with_rev", tmp_path, contract) == []


def test_message_text_is_rule_data(tmp_path: Path) -> None:
    contract = _contract()
    rows = [
        row.model_copy(
            update={
                "parameters": {**row.parameters, "remediation": "REMEDY-SENTINEL"},
            }
        )
        if row.rule_id == "source_shape_not_admitted"
        else row
        for row in contract.rules
    ]
    muted = contract.model_copy(update={"rules": rows})
    result = _validator(muted).validate_file(_staged("violation_rev_pin", tmp_path))
    assert "REMEDY-SENTINEL" in result.issues[0].message


def test_findings_name_package_line_and_remediation(tmp_path: Path) -> None:
    result = _validator().validate_file(_staged("violation_rev_pin", tmp_path))
    [issue] = result.issues
    assert "omnibase-core" in issue.message
    assert issue.line_number == 7
    assert issue.code == "source_shape_not_admitted"


@pytest.mark.parametrize(
    "change",
    [
        {"drop_rule": "source_vocabulary"},
        {"drop_rule": "invalid_pyproject"},
        {"add_rule": "unknown_rule"},
        {"vocabulary": {"normalize_pattern": "["}},
        {"vocabulary": {"packages": ["not-a-row"]}},
        {"vocabulary": {"packages": ["omnibase-core|omnibase_core|unknown_shape"]}},
        {"vocabulary": {"tag_key": ""}},
        {"finding": ("source_shape_not_admitted", {"message": "{unknown_field}"})},
        {"finding": ("foreign_git_source", {"remediation": ""})},
        {"disable": "source_vocabulary"},
    ],
)
def test_invalid_contract_fails_to_load_rather_than_passing(change: dict) -> None:
    contract = _contract()
    rows = list(contract.rules)
    if "drop_rule" in change:
        rows = [row for row in rows if row.rule_id != change["drop_rule"]]
    if "add_rule" in change:
        rows.append(rows[1].model_copy(update={"rule_id": change["add_rule"]}))
    if "vocabulary" in change:
        rows = [
            row.model_copy(
                update={"parameters": {**row.parameters, **change["vocabulary"]}}
            )
            if row.rule_id == "source_vocabulary"
            else row
            for row in rows
        ]
    if "finding" in change:
        rule_id, extra = change["finding"]
        rows = [
            row.model_copy(update={"parameters": {**row.parameters, **extra}})
            if row.rule_id == rule_id
            else row
            for row in rows
        ]
    if "disable" in change:
        rows = [
            row.model_copy(update={"enabled": False})
            if row.rule_id == change["disable"]
            else row
            for row in rows
        ]
    broken = contract.model_copy(update={"rules": rows})
    with pytest.raises(Exception, match="dep_provenance"):
        ModelDepProvenanceRules.from_contract(broken)


def test_every_vocabulary_key_is_read(tmp_path: Path) -> None:
    """A key the contract carries and the code never reads is data nobody enforces."""
    contract = _contract()
    [vocabulary] = [r for r in contract.rules if r.rule_id == "source_vocabulary"]
    rules = ModelDepProvenanceRules.from_contract(contract)
    assert set(type(rules.vocabulary).model_fields) == set(vocabulary.parameters)


def test_checker_is_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Facts in, issues out: no file read, no clock, no environment."""
    source = (FIXTURES / "violation_rev_pin" / "pyproject.toml.txt").read_text()
    rules = ModelDepProvenanceRules.from_contract(_contract())
    tag_pattern = dev_tag_pattern()

    def refuse(*_args, **_kwargs):
        raise AssertionError("the checker performed I/O")

    monkeypatch.setattr(Path, "read_text", refuse)
    monkeypatch.setattr(Path, "open", refuse)
    monkeypatch.setattr("builtins.open", refuse)
    issues = check_dep_provenance(Path("pyproject.toml"), source, rules, tag_pattern)
    assert [issue.rule_name for issue in issues] == ["source_shape_not_admitted"]


def test_dev_tag_shape_is_the_shared_first_party_pattern() -> None:
    """One definition of the dev-merge tag shape: the first_party_ref contract owns it."""
    assert ValidatorFirstPartyRef().contract is not None
    assert dev_tag_pattern().startswith("^dev-")
    rules = ModelDepProvenanceRules.from_contract(_contract())
    assert "tag_pattern" not in type(rules.vocabulary).model_fields


def test_package_table_covers_every_first_party_sibling() -> None:
    siblings = {
        row.split("=")[0]
        for rule in ValidatorFirstPartyRef().contract.rules
        if rule.rule_id == "wrong_repo"
        for row in rule.parameters["siblings"]
    }
    rules = ModelDepProvenanceRules.from_contract(_contract())
    assert siblings <= {package.name for package in rules.vocabulary.package_rows}


# ---- hook wiring -----------------------------------------------------------------


def _hooks(path: str) -> list[dict]:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_hook_id_is_exported_for_consumers() -> None:
    [hook] = [h for h in _hooks(".pre-commit-hooks.yaml") if h["id"] == HOOK_ID]
    assert hook["language"] == "python"
    assert hook["pass_filenames"] is True
    assert hook["entry"].endswith(
        "runtime_validator_run omnibase_core.validation.validator_dep_provenance:ValidatorDepProvenance"
    )
    assert "pyproject" in hook["files"]


def test_lineage_of_a_dev_tag_is_owned_by_the_dev_tag_lineage_hook() -> None:
    """Tag identity is not copied here: the lineage hook must exist and cover pyproject.toml."""
    rules = ModelDepProvenanceRules.from_contract(_contract())
    lineage = rules.vocabulary.lineage_hook
    [hook] = [h for h in _hooks(".pre-commit-hooks.yaml") if h["id"] == lineage]
    import re

    assert re.search(hook["files"], "pyproject.toml")


def test_core_consumes_its_own_hook_id_not_a_script() -> None:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text("utf-8"))
    [hook] = [
        h
        for repo in config["repos"]
        for h in repo.get("hooks", [])
        if h["id"] == HOOK_ID
    ]
    assert "check_dep_provenance.py" not in hook["entry"]
    assert "validator_dep_provenance:ValidatorDepProvenance" in hook["entry"]
    assert not (ROOT / "scripts/check_dep_provenance.py").exists()


def test_required_workflow_runs_the_validator_not_a_script() -> None:
    text = (ROOT / ".github/workflows/dep-provenance-gate.yml").read_text("utf-8")
    assert "scripts/check_dep_provenance.py" not in text
    assert "validator_dep_provenance:ValidatorDepProvenance" in text


def test_core_own_pyproject_passes_its_own_hook(tmp_path: Path) -> None:
    out = tmp_path / "own.json"
    assert (
        main_for_reference(
            [
                "omnibase_core.validation.validator_dep_provenance:ValidatorDepProvenance",
                str(ROOT / "pyproject.toml"),
                "--report-json",
                str(out),
            ]
        )
        == 0
    )


# ---- canary through the hook entry ------------------------------------------------


def test_canary_is_refused_with_its_rule_id_and_clean_control_passes(
    tmp_path: Path,
) -> None:
    """The hook entry exactly as pre-commit runs it: a planted override is refused, the control passes."""
    entry = "omnibase_core.validation.validator_dep_provenance:ValidatorDepProvenance"
    bad = _staged("violation_rev_pin", tmp_path)
    report = tmp_path / "canary.json"
    assert main_for_reference([entry, str(bad), "--report-json", str(report)]) == 1
    findings = json.loads(report.read_text())["findings"]
    assert [f["rule_id"] for f in findings] == ["source_shape_not_admitted"]
    good = _staged("clean_sibling_dev_tag", tmp_path)
    assert main_for_reference([entry, str(good)]) == 0
