# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the pin needs/provides checker and its generic validator (OMN-21879, task T-A3).

A verifier version declares what it needs from its environment and a caller declares what it
provides; both declarations are data. A pin whose needs are not all provided is refused, as is
a pinned version with no needs declaration. The reconstructed caller pin move of the
deadlocked verifier (fixture ``pin_move_5489.diff``) must be refused.
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
from omnibase_core.models.pin_needs_provides import (
    ModelPinNeedsDeclaration,
    ModelPinNeedsProvidesCheckInput,
    ModelPinNeedsProvidesCheckResult,
    ModelPinProvidesDeclaration,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation import checker_pin_needs_provides as checker_module
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_pin_needs_provides import check_pin_needs_provides
from omnibase_core.validation.validator_checker_rule_data import (
    ValidatorCheckerRuleData,
)
from omnibase_core.validation.validator_pin_needs_provides import (
    ValidatorPinNeedsProvides,
)

pytestmark = pytest.mark.unit

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "validation"
    / "pin_needs_provides"
)
CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "pin_needs_provides.validation.yaml"
)
PACKAGE_ROOT = Path(validator_base.__file__).parent.parent
PRODUCTION_SOURCES = (
    "validation/checker_pin_needs_provides.py",
    "validation/validator_pin_needs_provides.py",
    *(
        f"models/pin_needs_provides/{path.name}"
        for path in sorted(
            (PACKAGE_ROOT / "models" / "pin_needs_provides").glob("*.py")
        )
    ),
)
RULE_IDS = {"need_not_provided", "needs_undeclared", "provides_undeclared"}
CALLER = ".github/workflows/call-repo-evidence-gate.yml"
CALLER_TEXT = (
    "jobs:\n"
    "  repo-evidence:\n"
    "    uses: OmniNode-ai/omnibase_core/.github/workflows/receipt-gate.yml"
    "@dev-20261031120000-000000000000 # pinned\n"
    "    with:\n"
    "      evidence-source: caller\n"
    '      verifier-version: "{version}"\n'
)


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    return ModelValidatorSubcontract.model_validate(data)


def _contract_with(
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> ModelValidatorSubcontract:
    data = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    rules = {rule["rule_id"]: copy.deepcopy(rule) for rule in data["rules"]}
    mutate(rules)
    data["rules"] = list(rules.values())
    return ModelValidatorSubcontract.model_validate(data)


def _needs(name: str = "pin_needs.yaml") -> ModelPinNeedsDeclaration:
    return ModelPinNeedsDeclaration.model_validate(
        yaml.safe_load((FIXTURES / name).read_text("utf-8"))
    )


def _provides(name: str = "pin_provides.yaml") -> ModelPinProvidesDeclaration:
    return ModelPinProvidesDeclaration.model_validate(
        yaml.safe_load((FIXTURES / name).read_text("utf-8"))
    )


def check(
    text: str,
    source_name: str = CALLER,
    needs: ModelPinNeedsDeclaration | None = None,
    provides: ModelPinProvidesDeclaration | None = None,
    contract: ModelValidatorSubcontract | None = None,
) -> ModelPinNeedsProvidesCheckResult:
    return check_pin_needs_provides(
        ModelPinNeedsProvidesCheckInput(
            source_name=source_name,
            text=text,
            needs=needs if needs is not None else _needs(),
            provides=provides if provides is not None else _provides(),
            contract=contract if contract is not None else _contract(),
        )
    )


def _diff() -> str:
    return (FIXTURES / "pin_move_5489.diff").read_text("utf-8")


# --- AC1: a need the caller does not provide is refused; the recorded pin move is refused ---


def test_pin_needs_provides_refuses_the_recorded_pin_move_fixture() -> None:
    result = check(_diff(), source_name="pin_move_5489.diff")
    assert result.exit_code == 1
    assert [issue.code for issue in result.issues] == ["need_not_provided"]
    issue = result.issues[0]
    assert issue.context["caller"] == CALLER
    assert issue.context["version"] == "0.4.320"
    assert "which needs secret:LINEAR_API_KEY;" in issue.message
    # The line number is the diff line of the added pin.
    added = _diff().splitlines().index('+      verifier-version: "0.4.320"') + 1
    assert issue.line_number == added
    # Only added lines are judged: the removed pin and the context pin are not.
    assert result.pins_checked == 1


def test_pin_needs_provides_refuses_a_caller_file_pinning_a_version_with_an_unprovided_need() -> (
    None
):
    result = check(CALLER_TEXT.format(version="0.4.320"))
    assert [issue.code for issue in result.issues] == ["need_not_provided"]
    assert result.issues[0].line_number == 6
    assert result.pins_checked == 2


def test_pin_needs_provides_reports_every_unprovided_need() -> None:
    needs = ModelPinNeedsDeclaration.model_validate(
        {
            "verifiers": [
                {
                    "verifier_name": "v",
                    "pin_keys": ["verifier-version"],
                    "versions": [
                        {
                            "version": "9",
                            "needs": [
                                {"kind": "secret", "name": "A"},
                                {"kind": "env", "name": "B"},
                            ],
                        }
                    ],
                }
            ]
        }
    )
    provides = ModelPinProvidesDeclaration.model_validate(
        {"callers": [{"caller": CALLER, "provides": [{"kind": "env", "name": "A"}]}]}
    )
    result = check('verifier-version: "9"\n', needs=needs, provides=provides)
    assert [
        issue.message.split("which needs ")[1].split(";")[0] for issue in result.issues
    ] == [
        "secret:A",
        "env:B",
    ]


# --- AC2: a caller providing every need is admitted; an undeclared verifier is refused ---


def test_pin_needs_provides_admits_a_caller_that_provides_every_need() -> None:
    linear = _provides("pin_provides_linear.yaml")
    assert check(_diff(), "pin_move_5489.diff", provides=linear).issues == ()
    result = check(CALLER_TEXT.format(version="0.4.320"), provides=linear)
    assert result.issues == ()
    assert result.exit_code == 0
    assert result.pins_checked == 2


def test_pin_needs_provides_admits_the_previous_pin_that_needs_nothing() -> None:
    assert check(CALLER_TEXT.format(version="0.4.319")).issues == ()


def test_pin_needs_provides_refuses_a_planted_verifier_with_no_needs_declaration() -> (
    None
):
    planted = _needs("pin_needs_planted_undeclared.yaml")
    linear = _provides("pin_provides_linear.yaml")
    result = check(
        CALLER_TEXT.format(version="0.4.321"), needs=planted, provides=linear
    )
    assert result.exit_code == 1
    assert [(issue.code, issue.context["verifier"]) for issue in result.issues] == [
        ("needs_undeclared", "receipt-gate-reusable"),
        ("needs_undeclared", "caller-evidence-verifier"),
    ]


def test_pin_needs_provides_refuses_a_version_absent_from_the_declaration() -> None:
    result = check(CALLER_TEXT.format(version="0.4.999"))
    assert [issue.code for issue in result.issues] == ["needs_undeclared"]
    assert result.issues[0].context["version"] == "0.4.999"


def test_pin_needs_provides_refuses_a_caller_with_no_provides_declaration() -> None:
    nobody = ModelPinProvidesDeclaration.model_validate({"callers": []})
    absent = ModelPinProvidesDeclaration.model_validate(
        {"callers": [{"caller": CALLER}]}
    )
    for provides in (nobody, absent):
        result = check(CALLER_TEXT.format(version="0.4.319"), provides=provides)
        assert {issue.code for issue in result.issues} == {"provides_undeclared"}
        assert len(result.issues) == 2


def test_pin_needs_provides_ignores_keys_no_declared_verifier_names() -> None:
    result = check("name: x\non:\n  push:\njobs: {}\n      - uses: other/thing@v1\n")
    assert result.issues == ()
    assert result.pins_checked == 0


def test_pin_needs_provides_judges_each_file_of_a_multi_file_diff_as_its_own_caller() -> (
    None
):
    other = "+++ b/.github/workflows/other-caller.yml\n+  verifier-version: '0.4.320'\n"
    result = check(_diff() + other, "pin_move_5489.diff")
    assert [(issue.code, issue.context["caller"]) for issue in result.issues] == [
        ("need_not_provided", CALLER),
        ("provides_undeclared", ".github/workflows/other-caller.yml"),
    ]


def test_pin_needs_provides_refuses_contradictory_declarations() -> None:
    with pytest.raises(ValueError, match="selects both"):
        ModelPinNeedsDeclaration.model_validate(
            {
                "verifiers": [
                    {"verifier_name": "a", "pin_keys": ["k"]},
                    {"verifier_name": "b", "pin_keys": ["k"]},
                ]
            }
        )
    with pytest.raises(ValueError, match="declared twice"):
        ModelPinProvidesDeclaration.model_validate(
            {"callers": [{"caller": "c", "provides": []}, {"caller": "c"}]}
        )
    with pytest.raises(ValueError):
        ModelPinNeedsDeclaration.model_validate({"verifiers": [], "extra": 1})


# --- the contract is data and fails closed ---


def test_pin_needs_provides_committed_contract_holds_every_rule_at_error_severity() -> (
    None
):
    contract = _contract()
    assert contract.validator_id == "pin_needs_provides"
    assert {rule.rule_id for rule in contract.rules} == RULE_IDS
    assert all(
        rule.enabled and rule.severity.value == "error" for rule in contract.rules
    )
    assert contract.fail_on_error
    assert contract.max_violations == 0


def test_pin_needs_provides_disabled_rule_row_silences_its_issue() -> None:
    def disable(rules: dict[str, dict[str, Any]]) -> None:
        rules["need_not_provided"]["enabled"] = False

    assert (
        check(_diff(), "pin_move_5489.diff", contract=_contract_with(disable)).issues
        == ()
    )


def test_pin_needs_provides_pin_syntax_is_contract_data() -> None:
    """Removing the pin pattern that reads a key: value pin stops the fixture being judged."""

    def drop_key_value(rules: dict[str, dict[str, Any]]) -> None:
        rules["need_not_provided"]["parameters"]["pin_patterns"] = rules[
            "need_not_provided"
        ]["parameters"]["pin_patterns"][1:]

    result = check(
        _diff(), "pin_move_5489.diff", contract=_contract_with(drop_key_value)
    )
    assert result.issues == ()
    assert result.pins_checked == 0


def test_pin_needs_provides_diff_selection_is_contract_data() -> None:
    def never_diff(rules: dict[str, dict[str, Any]]) -> None:
        rules["need_not_provided"]["parameters"]["diff_source_pattern"] = r"\.never$"

    # Judged as a whole file, the removed pin and the context pin are read; the added
    # line, which starts with the diff prefix, is not.
    result = check(_diff(), "pin_move_5489.diff", contract=_contract_with(never_diff))
    assert result.pins_checked == 2
    # Read whole, the diff file is itself the caller, and it declares no provides.
    assert {issue.code for issue in result.issues} == {"provides_undeclared"}


@pytest.mark.parametrize(
    ("rule_id", "name", "value"),
    [
        ("need_not_provided", "pin_patterns", []),
        ("need_not_provided", "pin_patterns", ["(?P<pin_key>x)"]),
        ("need_not_provided", "pin_patterns", ["("]),
        ("need_not_provided", "diff_file_pattern", "no-group"),
        ("need_not_provided", "added_line_prefix", ""),
        ("need_not_provided", "message", None),
        ("needs_undeclared", "needs_declaration_path", None),
        ("provides_undeclared", "provides_declaration_path", 3),
    ],
)
def test_pin_needs_provides_invalid_contracts_fail_to_load(
    rule_id: str, name: str, value: object
) -> None:
    def mutate(rules: dict[str, dict[str, Any]]) -> None:
        if value is None:
            rules[rule_id]["parameters"].pop(name)
        else:
            rules[rule_id]["parameters"][name] = value

    with pytest.raises(ModelOnexError):
        check(_diff(), "pin_move_5489.diff", contract=_contract_with(mutate))


def test_pin_needs_provides_a_missing_rule_fails_to_load() -> None:
    def drop(rules: dict[str, dict[str, Any]]) -> None:
        rules.pop("provides_undeclared")

    with pytest.raises(ModelOnexError, match="required rule is absent"):
        check(_diff(), "pin_move_5489.diff", contract=_contract_with(drop))


# --- AC3: generic, pure, no repository name or pin value in code ---


def test_pin_needs_provides_checker_reads_no_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    needs, provides, contract, diff = _needs(), _provides(), _contract(), _diff()

    def refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the checker read a file")

    monkeypatch.setattr(builtins, "open", refuse)
    for name in ("read_text", "read_bytes", "open", "exists", "is_file", "iterdir"):
        monkeypatch.setattr(Path, name, refuse)
    result = check(diff, "pin_move_5489.diff", needs, provides, contract)
    assert result.exit_code == 1


def test_pin_needs_provides_no_hardcoded_repository_name_or_pin_value() -> None:
    """No string in the production source names a repository, a pin value or a need."""
    forbidden = re.compile(
        r"OmniNode|omnibase|omnimarket|onex_change_control|knowledge_base"
        r"|\d+\.\d+\.\d+|dev-\d{14}-[0-9a-f]{12}|\b[0-9a-f]{40}\b"
        r"|LINEAR|verifier-version|verifier-tag|receipt-gate|\.github",
        re.IGNORECASE,
    )
    offenders: list[str] = []
    for relative in PRODUCTION_SOURCES:
        source = (PACKAGE_ROOT / relative).read_text("utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if forbidden.search(node.value):
                    offenders.append(f"{relative}:{node.lineno}: {node.value!r}")
    assert len(PRODUCTION_SOURCES) >= 10
    assert offenders == []


def test_pin_needs_provides_no_hardcoded_positive_control() -> None:
    """The scan above finds a planted pin value and repository name."""
    planted = 'X = "omnibase_infra"\nY = "0.4.320"\n'
    found = [
        node.value
        for node in ast.walk(ast.parse(planted))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.search(r"omnibase|\d+\.\d+\.\d+", node.value)
    ]
    assert found == ["omnibase_infra", "0.4.320"]


def test_pin_needs_provides_no_hardcoded_rule_tables_k10_clean() -> None:
    triple = (
        PACKAGE_ROOT / "validation" / "checker_pin_needs_provides.py",
        PACKAGE_ROOT / "validation" / "validator_pin_needs_provides.py",
        CONTRACT_PATH,
    )
    assert all(path.is_file() for path in triple)
    assert ValidatorCheckerRuleData().validate(list(triple[:2])).issues == []
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


# --- the generic file validator reads the declarations named by the contract ---


def _repo(tmp_path: Path, needs: str, provides: str) -> Path:
    contract = _contract()
    params = {rule.rule_id: rule.parameters or {} for rule in contract.rules}
    needs_path = tmp_path / str(params["needs_undeclared"]["needs_declaration_path"])
    provides_path = tmp_path / str(
        params["provides_undeclared"]["provides_declaration_path"]
    )
    needs_path.parent.mkdir(parents=True, exist_ok=True)
    provides_path.parent.mkdir(parents=True, exist_ok=True)
    needs_path.write_text((FIXTURES / needs).read_text("utf-8"), "utf-8")
    provides_path.write_text((FIXTURES / provides).read_text("utf-8"), "utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "call-repo-evidence-gate.yml").write_text(
        CALLER_TEXT.format(version="0.4.320"), "utf-8"
    )
    return workflows / "call-repo-evidence-gate.yml"


def test_pin_needs_provides_validator_refuses_through_the_runtime_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = _repo(tmp_path, "pin_needs.yaml", "pin_provides.yaml")
    monkeypatch.chdir(tmp_path)
    report_path = tmp_path / "report.json"
    exit_code = main(
        ValidatorPinNeedsProvides,
        [str(caller), "--report-json", str(report_path)],
        build_validator_container,
    )
    expected = [
        {"message": issue.message, "rule_id": issue.code}
        for issue in check(caller.read_text("utf-8")).issues
    ]
    report = json.loads(report_path.read_text("utf-8"))
    found = [
        {"message": finding["message"], "rule_id": finding["rule_id"]}
        for finding in report["findings"]
    ]
    assert exit_code == 1
    assert len(expected) == 1
    assert found == expected


def test_pin_needs_provides_validator_admits_a_providing_caller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = _repo(tmp_path, "pin_needs.yaml", "pin_provides_linear.yaml")
    monkeypatch.chdir(tmp_path)
    assert ValidatorPinNeedsProvides().validate_file(caller).issues == []


def test_pin_needs_provides_validator_with_no_needs_file_knows_no_verifier_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository with no needs declaration names no verifier pin key, so nothing is judged."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    caller = workflows / "call.yml"
    caller.write_text(CALLER_TEXT.format(version="0.4.320"), "utf-8")
    monkeypatch.chdir(tmp_path)
    assert ValidatorPinNeedsProvides().validate_file(caller).issues == []


def test_pin_needs_provides_validator_with_no_provides_file_refuses_every_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = _repo(tmp_path, "pin_needs.yaml", "pin_provides.yaml")
    params = {rule.rule_id: rule.parameters or {} for rule in _contract().rules}
    (
        tmp_path / str(params["provides_undeclared"]["provides_declaration_path"])
    ).unlink()
    monkeypatch.chdir(tmp_path)
    issues = ValidatorPinNeedsProvides().validate_file(caller).issues
    assert [issue.code for issue in issues] == ["provides_undeclared"] * 2
