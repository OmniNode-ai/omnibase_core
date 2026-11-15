# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the depends-on checker and its generic validator (OMN-24537).

A contract, ticket contract or unit declaration may declare what it depends on (an overlay key, a
sibling ticket, a service, the replacement of something it retires). The caller supplies the facts;
a declared dependency absent from them is refused, and so is a kind with no facts. The two recorded
examples must be refused without their dependency and admitted with it: the weekly coding test
trigger without its overlay row (fixture ``contract_eval_tracking.yaml``) and a lab fill ticket
whose prerequisite had no pull request (fixture ``ticket_contract_prerequisite.yaml``).
"""

from __future__ import annotations

import ast
import builtins
import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.depends_on import (
    ModelDependsOnCheckInput,
    ModelDependsOnCheckResult,
    ModelDependsOnFacts,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation import checker_depends_on as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_depends_on import check_depends_on
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_depends_on import ValidatorDependsOn

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2] / "fixtures" / "validation" / "depends_on"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent / "contracts" / "depends_on.validation.yaml"
)
PACKAGE_ROOT = Path(validator_base.__file__).parent.parent
PRODUCTION_SOURCES = (
    "validation/checker_depends_on.py",
    "validation/validator_depends_on.py",
    *(
        f"models/depends_on/{path.name}"
        for path in sorted((PACKAGE_ROOT / "models" / "depends_on").glob("*.py"))
    ),
)
RULE_IDS = {
    "dependency_absent",
    "dependency_malformed",
    "dependency_kind_unknown",
    "facts_unsupplied",
}


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    return ModelValidatorSubcontract.model_validate(data)


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    data = copy.deepcopy(yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"])
    rules = {rule["rule_id"]: rule for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _facts(name: str) -> ModelDependsOnFacts:
    return ModelDependsOnFacts.model_validate(
        yaml.safe_load((FIXTURES / name).read_text("utf-8"))
    )


def check(
    document: str,
    facts: str | None,
    source: str = "contract.yaml",
    contract: ModelValidatorSubcontract | None = None,
) -> ModelDependsOnCheckResult:
    return check_depends_on(
        ModelDependsOnCheckInput(
            source_name=source,
            text=(FIXTURES / document).read_text("utf-8"),
            facts=None if facts is None else _facts(facts),
            contract=contract or _contract(),
        )
    )


# --- AC1: a declared dependency absent from the facts is refused; present, it passes ---


def test_absent_dependency_is_refused_for_the_recorded_scheduled_node() -> None:
    """The weekly coding test trigger without its overlay row (the NodeOverlayNotFoundError evidence)."""
    result = check("contract_eval_tracking.yaml", "facts_without_overlay.yaml")
    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["dependency_absent"]
    assert "overlay_key:node_eval_tracking_schedule_compute" in result.issues[0].message
    assert result.dependencies_checked == 1


def test_present_dependency_passes_for_the_recorded_scheduled_node() -> None:
    result = check("contract_eval_tracking.yaml", "facts_with_overlay.yaml")
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.dependencies_checked == 1


def test_absent_dependency_is_refused_for_the_recorded_ticket_prerequisite() -> None:
    """The lab fill sent a ticket while its prerequisite had no pull request."""
    result = check(
        "ticket_contract_prerequisite.yaml",
        "facts_ticket_absent.yaml",
        source="contracts/OMN-23773.yaml",
    )
    assert [issue.code for issue in result.issues] == ["dependency_absent"]
    assert "sibling_ticket:OMN-23760" in result.issues[0].message


def test_present_dependency_passes_for_the_recorded_ticket_prerequisite() -> None:
    result = check(
        "ticket_contract_prerequisite.yaml",
        "facts_ticket_present.yaml",
        source="contracts/OMN-23773.yaml",
    )
    assert result.issues == ()


def test_overlay_key_with_field_is_judged_by_name_and_field() -> None:
    with_field = check("contract_overlay_field.yaml", "facts_with_overlay.yaml")
    assert with_field.issues == ()
    without_field = check("contract_overlay_field.yaml", "facts_without_overlay.yaml")
    assert "node_factory_floor_publish_effect:limits" in without_field.issues[0].message


def test_dependency_under_metadata_is_read() -> None:
    """The eval tracking fixture declares under metadata, a ticket fixture under context."""
    assert check("contract_eval_tracking.yaml", "facts_without_overlay.yaml").issues
    assert check("ticket_contract_prerequisite.yaml", "facts_ticket_absent.yaml").issues


def test_an_existing_depends_on_key_of_another_shape_is_not_read() -> None:
    """Existing contracts use depends_on for node names; the declaration key is a different, unused one."""
    result = check("contract_other_depends_on.yaml", None)
    assert result.issues == ()
    assert result.dependencies_checked == 0


def test_malformed_entry_is_refused_not_skipped() -> None:
    result = check("contract_malformed.yaml", "facts_with_overlay.yaml")
    assert [issue.code for issue in result.issues] == ["dependency_malformed"]
    assert result.dependencies_checked == 0


def test_unknown_kind_is_refused() -> None:
    result = check("contract_unknown_kind.yaml", "facts_with_overlay.yaml")
    assert [issue.code for issue in result.issues] == ["dependency_kind_unknown"]
    assert "moon_phase" in result.issues[0].message


def test_unsupplied_facts_are_refused_never_assumed_present() -> None:
    none_given = check("contract_eval_tracking.yaml", None)
    assert [issue.code for issue in none_given.issues] == ["facts_unsupplied"]
    other_kind = check("ticket_contract_prerequisite.yaml", "facts_with_overlay.yaml")
    assert [issue.code for issue in other_kind.issues] == ["facts_unsupplied"]


def test_document_without_declaration_passes() -> None:
    result = check("contract_no_declaration.yaml", None)
    assert result.issues == ()
    assert result.dependencies_checked == 0


def test_text_that_is_not_a_mapping_declares_nothing() -> None:
    result = check_depends_on(
        ModelDependsOnCheckInput(
            source_name="contract.yaml",
            text="- just\n- a list\n",
            facts=None,
            contract=_contract(),
        )
    )
    assert result.issues == ()


def test_disabled_rule_is_silent() -> None:
    def disable(rules: dict[str, dict[str, Any]]) -> None:
        rules["dependency_absent"]["enabled"] = False

    result = check(
        "contract_eval_tracking.yaml",
        "facts_without_overlay.yaml",
        contract=_contract_with(disable),
    )
    assert result.issues == ()


def test_committed_contract_holds_every_rule_at_error_severity() -> None:
    contract = _contract()
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    assert all(
        rule.severity.is_error_or_above() and rule.enabled for rule in contract.rules
    )


def test_kinds_and_locations_are_contract_data() -> None:
    def narrow(rules: dict[str, dict[str, Any]]) -> None:
        rules["dependency_kind_unknown"]["parameters"]["kinds"] = ["service"]
        rules["dependency_absent"]["parameters"]["declaration_keys"] = ["needs"]

    contract = _contract_with(narrow)
    assert (
        check(
            "contract_eval_tracking.yaml",
            "facts_without_overlay.yaml",
            contract=contract,
        ).issues
        == ()
    )
    result = check(
        "contract_overlay_field.yaml", "facts_with_overlay.yaml", contract=contract
    )
    assert result.issues == ()


@pytest.mark.parametrize(
    ("rule_id", "name", "value"),
    [
        ("dependency_absent", "declaration_keys", []),
        ("dependency_absent", "field_separator", None),
        ("dependency_kind_unknown", "kinds", "overlay_key"),
        ("facts_unsupplied", "facts_file_path", 3),
    ],
)
def test_invalid_contracts_fail_to_load(rule_id: str, name: str, value: object) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        if value is None:
            rules[rule_id]["parameters"].pop(name)
        else:
            rules[rule_id]["parameters"][name] = value

    with pytest.raises(ModelOnexError):
        check(
            "contract_eval_tracking.yaml",
            "facts_with_overlay.yaml",
            contract=_contract_with(mutate),
        )


def test_a_missing_rule_fails_to_load() -> None:
    def drop(rules: dict[str, dict[str, Any]]) -> None:
        rules.pop("facts_unsupplied")

    with pytest.raises(ModelOnexError, match="required rule is absent"):
        check(
            "contract_eval_tracking.yaml",
            "facts_with_overlay.yaml",
            contract=_contract_with(drop),
        )


# --- generic, pure, no kind name or repository name in code ---


def test_checker_reads_no_file(monkeypatch: pytest.MonkeyPatch) -> None:
    document = (FIXTURES / "contract_eval_tracking.yaml").read_text("utf-8")
    facts, contract = _facts("facts_without_overlay.yaml"), _contract()

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    result = check_depends_on(
        ModelDependsOnCheckInput(
            source_name="contract.yaml", text=document, facts=facts, contract=contract
        )
    )
    assert result.exit_code == 1


def test_no_hardcoded_kind_repository_or_ticket_in_production_source() -> None:
    forbidden = re.compile(
        r"OmniNode|omnibase|omnimarket|overlay_key|sibling_ticket|replacement"
        r"|OMN-\d+|\.github|overlay",
        re.IGNORECASE,
    )
    offenders: list[str] = []
    for relative in PRODUCTION_SOURCES:
        tree = ast.parse((PACKAGE_ROOT / relative).read_text("utf-8"))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
                and forbidden.search(node.value)
            ):
                offenders.append(f"{relative}:{node.lineno}: {node.value!r}")
    assert len(PRODUCTION_SOURCES) >= 8
    assert offenders == []


def test_no_hardcoded_rule_tables_k10_clean() -> None:
    pair = (
        PACKAGE_ROOT / "validation" / "checker_depends_on.py",
        PACKAGE_ROOT / "validation" / "validator_depends_on.py",
    )
    assert all(path.is_file() for path in pair)
    assert ValidatorCheckerRuleData().validate(list(pair)).issues == []
    tree = ast.parse(Path(checker_module.__file__).read_text("utf-8"))
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


# --- the generic file validator reads the facts file the contract names ---


def _facts_path() -> str:
    params = {rule.rule_id: rule.parameters or {} for rule in _contract().rules}
    return str(params["facts_unsupplied"]["facts_file_path"])


def _declaring_file(tmp_path: Path, facts: str | None) -> Path:
    path = tmp_path / "contract.yaml"
    path.write_text(
        (FIXTURES / "contract_eval_tracking.yaml").read_text("utf-8"), "utf-8"
    )
    if facts is not None:
        facts_file = tmp_path / _facts_path()
        facts_file.parent.mkdir(parents=True, exist_ok=True)
        facts_file.write_text((FIXTURES / facts).read_text("utf-8"), "utf-8")
    return path


def test_validator_refuses_through_the_runtime_entry_when_the_fact_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _declaring_file(tmp_path, "facts_without_overlay.yaml")
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "report.json"
    exit_code = main(
        ValidatorDependsOn,
        [str(target), "--report-json", str(report_path)],
        build_validator_container,
    )
    report = json.loads(report_path.read_text("utf-8"))
    assert exit_code == 1
    assert [finding["rule_id"] for finding in report["findings"]] == [
        "dependency_absent"
    ]


def test_validator_reads_facts_from_the_path_the_contract_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _declaring_file(tmp_path, "facts_with_overlay.yaml")
    monkeypatch.chdir(tmp_path)
    assert ValidatorDependsOn().validate_file(target).issues == []


def test_validator_with_no_facts_file_refuses_declared_dependency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _declaring_file(tmp_path, None)
    monkeypatch.chdir(tmp_path)
    issues = ValidatorDependsOn().validate_file(target).issues
    assert [issue.code for issue in issues] == ["facts_unsupplied"]


def test_validator_with_a_malformed_facts_file_raises_never_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = _declaring_file(tmp_path, None)
    facts_file = tmp_path / _facts_path()
    facts_file.parent.mkdir(parents=True, exist_ok=True)
    facts_file.write_text("present: [not, a, mapping]\n", "utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        ValidatorDependsOn().validate_file(target)
