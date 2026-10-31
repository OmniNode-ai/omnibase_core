# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pure lab-receipt checker and generic validator (OMN-21823).

Every rule has a planted violation fixture (exactly one issue with its rule id) and a paired clean
fixture (no issue). The classification fixtures pin which changes run. All rule data lives in
``validation/contracts/lab_receipt.validation.yaml``; the table-driven mutation test changes every
``parameters`` key of every rule row in turn and asserts the verdict changes or the contract is refused.
"""

from __future__ import annotations

import ast
import builtins
import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.enum_lab_receipt_phase import EnumLabReceiptPhase
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_check_input import (
    ModelLabReceiptCheckInput,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_check_result import (
    ModelLabReceiptCheckResult,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_document import (
    ModelLabReceiptDocument,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation import checker_lab_receipt as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_lab_receipt import check_lab_receipt
from omnibase_core.validation.hardcoded_model_config import handler as model_config
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_hardcoded_topics import ValidatorHardcodedTopics
from omnibase_core.validation.validator_lab_receipt import ValidatorLabReceipt
from omnibase_core.validation.validator_url_authority import scan_source
from omnibase_core.validators import contract_config_compliance

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "lab_receipt"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "lab_receipt.validation.yaml"
)
HOOK_MANIFEST = Path(__file__).resolve().parents[3] / ".pre-commit-hooks.yaml"
VALIDATOR_ID = "lab_receipt"

RULE_IDS = {
    "receipt_required",
    "receipt_criterion_missing",
    "receipt_head_mismatch",
    "receipt_field_missing",
    "receipt_installer_undeclared",
    "receipt_revision_not_head",
    "receipt_observation_unproven",
    "receipt_not_on_lab",
    "lab_read_unavailable",
}
# fixture -> (counted classes). Exempt fixtures count nothing and need no receipt.
CLASSIFICATION: dict[str, tuple[str, ...]] = {
    "exempt_docs_only": (),
    "exempt_tests_only": (),
    "exempt_ticket_contract_only": (),
    "exempt_prod_only": (),
    "exempt_markdown_only": (),
    "exempt_status_unlisted": (),
    "counted_operative": ("operative",),
    "counted_deleted_unit": ("host_unit",),
    "counted_unclassified": ("unclassified",),
    "counted_internal_source": ("internal_source",),
    "counted_package_source": ("package_source",),
    "counted_mixed": ("host_unit", "hook"),
}
Verdict = tuple[tuple[str, ...], bool, tuple[str, ...]]


def _fixture_names() -> list[str]:
    return sorted(
        path.stem
        for path in FIXTURES.glob("*.json")
        if not path.name.startswith("golden")
    )


def _document(name: str) -> ModelLabReceiptDocument:
    return ModelLabReceiptDocument.model_validate_json(
        (FIXTURES / f"{name}.json").read_text("utf-8")
    )


def _contract() -> ModelValidatorSubcontract:
    return ValidatorLabReceipt().contract


def _check(
    name: str,
    contract: ModelValidatorSubcontract | None = None,
    phase: EnumLabReceiptPhase | None = None,
) -> ModelLabReceiptCheckResult:
    document = _document(name)
    if phase is not None:
        document = document.model_copy(update={"phase": phase})
    return check_lab_receipt(
        ModelLabReceiptCheckInput(
            source_name=f"checks/{name}.lab-receipt.json",
            document=document,
            contract=contract or _contract(),
        )
    )


def _verdict(name: str, contract: ModelValidatorSubcontract | None = None) -> Verdict:
    result = _check(name, contract)
    return (
        tuple(f"{i.code}: {i.message}" for i in result.issues),
        result.required,
        result.classes,
    )


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    """The committed contract with `mutate` applied to its rules, by rule id."""
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _all_verdicts(
    contract: ModelValidatorSubcontract,
) -> list[tuple[str, Verdict]]:
    return [(name, _verdict(name, contract)) for name in _fixture_names()]


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_violation_fixture_has_exactly_its_one_issue(rule_id: str) -> None:
    result = _check(f"violation_{rule_id}")
    assert [issue.code for issue in result.issues] == [rule_id]
    assert result.exit_code == 1


@pytest.mark.parametrize("rule_id", sorted(RULE_IDS))
def test_each_clean_fixture_yields_no_issue(rule_id: str) -> None:
    result = _check(f"clean_{rule_id}")
    assert result.issues == ()
    assert result.exit_code == 0


@pytest.mark.parametrize(("name", "classes"), sorted(CLASSIFICATION.items()))
def test_classification_fixtures_pin_which_changes_run(
    name: str, classes: tuple[str, ...]
) -> None:
    result = _check(name)
    assert result.classes == classes
    assert result.required is bool(classes)
    assert result.issues == ()


def test_every_fixture_is_pinned_by_a_test() -> None:
    pinned = (
        {f"violation_{r}" for r in RULE_IDS}
        | {f"clean_{r}" for r in RULE_IDS}
        | set(CLASSIFICATION)
    )
    assert set(_fixture_names()) == pinned


def test_golden_report_covers_every_fixture() -> None:
    golden = json.loads((FIXTURES / "golden_lab_receipt.json").read_text("utf-8"))
    actual = {
        name: {
            "issues": [i.code for i in _check(name).issues],
            "required": _check(name).required,
            "classes": list(_check(name).classes),
        }
        for name in _fixture_names()
    }
    assert golden == actual


def test_a_receipt_for_another_head_never_counts() -> None:
    result = _check("clean_receipt_head_mismatch")
    assert result.issues == ()
    mismatch = _check("violation_receipt_head_mismatch").issues[0]
    assert mismatch.context is not None
    assert mismatch.context["detail"] != mismatch.context["head"]


@pytest.mark.parametrize("rule_id", ["receipt_not_on_lab", "lab_read_unavailable"])
def test_present_phase_does_not_judge_the_lab(rule_id: str) -> None:
    present = _check(f"violation_{rule_id}", phase=EnumLabReceiptPhase.PRESENT)
    assert present.issues == ()
    verify = _check(f"violation_{rule_id}", phase=EnumLabReceiptPhase.VERIFY)
    assert [issue.code for issue in verify.issues] == [rule_id]


def test_verify_run_given_no_lab_read_is_refused_not_passed() -> None:
    result = _check("clean_receipt_required", phase=EnumLabReceiptPhase.VERIFY)
    assert result.issues == ()
    assert result.required is False
    refused = _check("violation_lab_read_unavailable")
    assert refused.exit_code == 1
    assert refused.required is True


def test_verify_phase_keeps_every_present_rule() -> None:
    for rule_id in sorted(RULE_IDS - {"receipt_not_on_lab", "lab_read_unavailable"}):
        verify = _check(f"violation_{rule_id}", phase=EnumLabReceiptPhase.VERIFY)
        assert rule_id in [issue.code for issue in verify.issues], rule_id


def test_a_disabled_rule_row_fails_its_fixture() -> None:
    for rule_id in sorted(RULE_IDS):

        def disable(rules: dict[str, dict[str, Any]], rule_id: str = rule_id) -> None:
            rules[rule_id]["enabled"] = False

        result = _check(f"violation_{rule_id}", _contract_with(disable))
        assert rule_id not in [issue.code for issue in result.issues], rule_id


def test_disabling_the_requirement_row_does_not_change_the_classification() -> None:
    def disable(rules: dict[str, dict[str, Any]]) -> None:
        rules["receipt_required"]["enabled"] = False

    result = _check("violation_receipt_required", _contract_with(disable))
    assert result.required is True
    assert result.issues == ()


def test_committed_contract_holds_every_rule_at_error_severity() -> None:
    contract = _contract()
    assert contract.validator_id == VALIDATOR_ID
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    assert all(
        rule.enabled and rule.severity.value == "error" for rule in contract.rules
    )
    assert contract.fail_on_error
    assert not contract.fail_on_warning
    assert contract.max_violations == 0


@pytest.mark.parametrize("fixture", _fixture_names())
def test_cli_exits_non_zero_exactly_on_the_planted_fixtures(
    fixture: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / f"{fixture}.lab-receipt.json").write_text(
        (FIXTURES / f"{fixture}.json").read_text("utf-8"), "utf-8"
    )
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "report.json"
    code = main(
        ValidatorLabReceipt,
        [str(tmp_path), "--report-json", str(report)],
        build_validator_container,
    )
    assert code == (1 if fixture.startswith("violation_") else 0)
    written = json.loads(report.read_text("utf-8"))
    assert written["overall_status"] == ("FAIL" if code else "PASS")


def test_a_malformed_document_is_refused_not_skipped(tmp_path: Path) -> None:
    broken = tmp_path / "broken.lab-receipt.json"
    broken.write_text('{"phase": "present"}', "utf-8")
    with pytest.raises(ModelOnexError, match="cannot read lab-receipt facts"):
        ValidatorLabReceipt().validate_file(broken)
    broken.write_text('{"phase": "later", "facts": {}}', "utf-8")
    with pytest.raises(ModelOnexError, match="cannot read lab-receipt facts"):
        ValidatorLabReceipt().validate_file(broken)


def test_file_validator_reports_issues_at_the_file(tmp_path: Path) -> None:
    good = tmp_path / "good.lab-receipt.json"
    good.write_text(
        (FIXTURES / "clean_receipt_criterion_missing.json").read_text("utf-8")
    )
    bad = tmp_path / "bad.lab-receipt.json"
    bad.write_text(
        (FIXTURES / "violation_receipt_criterion_missing.json").read_text("utf-8")
    )
    validator = ValidatorLabReceipt()
    assert validator.validate_file(good).is_valid
    result = validator.validate_file(bad)
    assert {issue.file_path for issue in result.issues} == {bad}
    assert {issue.code for issue in result.issues} == {"receipt_criterion_missing"}


def test_hook_manifest_exposes_the_validator_by_hook_id() -> None:
    hooks = {
        hook["id"]: hook for hook in yaml.safe_load(HOOK_MANIFEST.read_text("utf-8"))
    }
    hook = hooks["check-lab-receipt"]
    assert hook["entry"].endswith(
        "omnibase_core.validation.validator_lab_receipt:ValidatorLabReceipt"
    )
    assert hook["pass_filenames"] is True


def _mutations(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [[], [*value, "zz::.*::zz"], [*value, "zz"]]
    return ["(?!)", "(?s).+"]


def test_every_parameter_of_every_rule_row_changes_a_verdict_or_is_refused() -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    baseline = _all_verdicts(_contract())
    unmoved: list[str] = []
    for rule in data["rules"]:
        for key in rule["parameters"]:
            changed = False
            for replacement in _mutations(rule["parameters"][key]):

                def mutate(
                    rules: dict[str, dict[str, Any]],
                    rule_id: str = rule["rule_id"],
                    key: str = key,
                    replacement: Any = replacement,
                ) -> None:
                    rules[rule_id]["parameters"][key] = replacement

                try:
                    moved = _all_verdicts(_contract_with(mutate)) != baseline
                except ModelOnexError:
                    moved = True
                if moved:
                    changed = True
                    break
            if not changed:
                unmoved.append(f"{rule['rule_id']}.{key}")
    assert unmoved == []


def test_invalid_contracts_fail_to_load_rather_than_pass() -> None:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    for rule in data["rules"]:
        for key in rule["parameters"]:

            def drop(
                rules: dict[str, dict[str, Any]],
                rule_id: str = rule["rule_id"],
                key: str = key,
            ) -> None:
                del rules[rule_id]["parameters"][key]

            with pytest.raises(ModelOnexError, match=rule["rule_id"]):
                _check("clean_receipt_required", _contract_with(drop))

    def drop_rule(rules: dict[str, dict[str, Any]]) -> None:
        del rules["lab_read_unavailable"]

    with pytest.raises(ModelOnexError, match="lab_read_unavailable"):
        _check("clean_receipt_required", _contract_with(drop_rule))


@pytest.mark.parametrize(
    ("rule_id", "key", "value", "match"),
    [
        ("receipt_required", "runtime_classes", ["tool::.*"], "<class>::<repository>"),
        ("receipt_required", "runtime_classes", ["tool::(::x"], "regular expression"),
        ("receipt_required", "prod_classes", "prod", "list of strings"),
        ("receipt_required", "phases", ["later"], "unknown phase"),
        ("receipt_field_missing", "required_fields", ["colour"], "does not have"),
        (
            "receipt_observation_unproven",
            "refused_patterns",
            ["("],
            "regular expression",
        ),
        ("receipt_criterion_missing", "criterion_pattern", "(", "regular expression"),
        ("receipt_installer_undeclared", "installers", "tool", "list of strings"),
    ],
)
def test_malformed_parameters_are_refused_naming_the_rule(
    rule_id: str, key: str, value: Any, match: str
) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        rules[rule_id]["parameters"][key] = value

    with pytest.raises(ModelOnexError, match=f"{rule_id}.*{match}"):
        _check("clean_receipt_required", _contract_with(mutate))


def test_invalid_contracts_validate_disabled_rows_too() -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        rules["receipt_not_on_lab"]["enabled"] = False
        del rules["receipt_not_on_lab"]["parameters"]["phases"]

    with pytest.raises(ModelOnexError, match="receipt_not_on_lab"):
        _check("clean_receipt_required", _contract_with(mutate))


def test_a_new_file_class_needs_no_code_change() -> None:
    before = Path(checker_module.__file__).read_text("utf-8")
    assert _check("exempt_markdown_only").required is False

    def operative(rules: dict[str, dict[str, Any]]) -> None:
        rules["receipt_required"]["parameters"]["operative_classes"].append(
            r"design_note::.*::(^|/)design\.md$"
        )

    result = _check("exempt_markdown_only", _contract_with(operative))
    assert result.required is True
    assert result.classes == ("design_note",)
    assert Path(checker_module.__file__).read_text("utf-8") == before


def test_the_first_matching_class_wins_in_contract_order() -> None:
    def reorder(rules: dict[str, dict[str, Any]]) -> None:
        params = rules["receipt_required"]["parameters"]
        params["runtime_classes"] = [
            r"everything::.*::.",
            *params["runtime_classes"],
        ]

    assert _check("counted_mixed", _contract_with(reorder)).classes == ("everything",)


def test_checker_reads_no_file_while_open_and_path_reads_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _contract()
    documents = {name: _document(name) for name in _fixture_names()}

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    for name, document in documents.items():
        result = check_lab_receipt(
            ModelLabReceiptCheckInput(
                source_name=f"checks/{name}.lab-receipt.json",
                document=document,
                contract=contract,
            )
        )
        assert result.exit_code == (1 if name.startswith("violation_") else 0)


def test_checker_module_is_pure_and_holds_no_rule_table() -> None:
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported & {
        "os",
        "pathlib",
        "subprocess",
        "socket",
        "time",
        "datetime",
        "random",
        "urllib",
        "logging",
        "yaml",
        "re",
    }
    assigned = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
        and not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
    ]
    assert assigned == []


@pytest.mark.parametrize(
    "relative_path",
    [
        "enums/enum_lab_receipt_phase.py",
        "validation/checker_lab_receipt.py",
        "validation/validator_lab_receipt.py",
        "models/lab_receipt/__init__.py",
        "models/lab_receipt/model_lab_receipt_changed_file.py",
        "models/lab_receipt/model_lab_receipt_check_input.py",
        "models/lab_receipt/model_lab_receipt_check_result.py",
        "models/lab_receipt/model_lab_receipt_criterion.py",
        "models/lab_receipt/model_lab_receipt_document.py",
        "models/lab_receipt/model_lab_receipt_facts.py",
        "models/lab_receipt/model_lab_receipt_file_class.py",
        "models/lab_receipt/model_lab_receipt_lab_read.py",
        "models/lab_receipt/model_lab_receipt_record.py",
        "models/lab_receipt/model_lab_receipt_rules.py",
    ],
)
def test_production_source_has_no_runtime_literals(relative_path: str) -> None:
    """Scan the actual source; absent source must not count as a clean scan."""
    package_root = Path(validator_base.__file__).parent.parent
    path = package_root / relative_path
    source = path.read_text(encoding="utf-8")
    repo_path = f"src/omnibase_core/{relative_path}"
    policy_path = Path(model_config.__file__).with_name("policy.yaml")
    policy = ModelHardcodedModelConfigPolicy.model_validate(
        yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    )

    assert scan_source("omnibase_core", repo_path, source) == []
    assert model_config.scan(repo_path, source, policy) == []
    assert not ValidatorHardcodedTopics().validate_file(path).issues
    if relative_path.startswith("validation/checker_"):
        assert not ValidatorCheckerRuleData().validate_file(path).issues
    assert contract_config_compliance.validate_file(path) == []
