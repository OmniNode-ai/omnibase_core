# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Chain scenario schema, checker and validator on the shipped rule data (OMN-22478).

Each rule has a planted fixture that violates only that rule and a clean fixture that
violates none. The generated-test rule is the failing control for "a generated test that
cannot fail is rejected": a kept receipt that stayed green, is missing, or belongs to
another version of the case refuses the node.
"""

from __future__ import annotations

import copy
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_chain_scenario_kind import EnumChainScenarioKind
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_case import (
    ModelChainScenarioCase,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_receipt_set import (
    ModelChainScenarioReceiptSet,
)
from omnibase_core.models.contracts.subcontracts.model_chain_scenario_subcontract import (
    ModelChainScenarioSubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    RuleParameterValue,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
    main,
)
from omnibase_core.validation.checker_chain_scenario import check_chain_scenarios
from omnibase_core.validation.validator_chain_scenario import ValidatorChainScenario

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _ROOT / "src/omnibase_core/validation/contracts/chain_scenario.validation.yaml"
)
_FIXTURES = _ROOT / "tests/fixtures/validation/chain_scenario"
_MARK = "REMEDIATION-MARK"


def _contract() -> ModelValidatorSubcontract:
    data = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
    return ModelValidatorSubcontract.model_validate(data["validation"])


def _with_parameter(
    contract: ModelValidatorSubcontract, rule_id: str, key: str, value: object | None
) -> ModelValidatorSubcontract:
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


def _document(name: str = "clean") -> dict[str, object]:
    loaded: dict[str, object] = yaml.safe_load(
        (_FIXTURES / name / "contract.yaml").read_text(encoding="utf-8")
    )
    return loaded


def _receipts(name: str = "clean") -> ModelChainScenarioReceiptSet | None:
    path = _FIXTURES / name / "chain_scenario_receipts.json"
    if not path.exists():
        return None
    return ModelChainScenarioReceiptSet.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _issues(
    contract: ModelValidatorSubcontract, name: str
) -> list[ModelValidationIssue]:
    key = f"{name}/contract.yaml"
    return check_chain_scenarios(
        {key: _document(name)}, {key: _receipts(name)}, contract.rules
    )


_RULES = [rule.rule_id for rule in _contract().rules]
_PARAMETERS = [
    (rule.rule_id, key)
    for rule in _contract().rules
    for key in sorted(rule.parameters or {})
]


def _block() -> dict[str, object]:
    return cast("dict[str, object]", copy.deepcopy(_document()["chain_scenarios"]))


@pytest.mark.parametrize("rule_id", _RULES)
def test_planted_violation_yields_exactly_one_issue_with_its_rule_id(
    rule_id: str,
) -> None:
    issues = _issues(_contract(), f"violation_{rule_id}")
    assert [issue.code for issue in issues] == [rule_id]
    rule = next(rule for rule in _contract().rules if rule.rule_id == rule_id)
    assert issues[0].message.endswith(f" -- {(rule.parameters or {})['remediation']}")


def test_clean_fixture_yields_no_issue() -> None:
    assert _issues(_contract(), "clean") == []


def test_planted_set_names_every_rule_once() -> None:
    found: Counter[str] = Counter()
    for rule_id in _RULES:
        found.update(str(i.code) for i in _issues(_contract(), f"violation_{rule_id}"))
    assert found == Counter(_RULES)


@pytest.mark.parametrize("rule_id", _RULES)
def test_disabling_a_rule_row_clears_only_that_rules_fixture(rule_id: str) -> None:
    contract = _contract().model_copy(
        update={
            "rules": [
                r.model_copy(update={"enabled": False}) if r.rule_id == rule_id else r
                for r in _contract().rules
            ]
        }
    )
    assert _issues(contract, f"violation_{rule_id}") == []


def test_only_the_undeclared_node_rule_is_a_warning() -> None:
    contract = _contract()
    assert contract.fail_on_error is True
    assert contract.max_violations == 0
    severities = {rule.rule_id: rule.severity for rule in contract.rules}
    undeclared_severity = severities.pop("node_without_scenario_declaration")
    assert undeclared_severity == "warning"
    assert set(severities.values()) == {"error"}


def test_the_validator_cli_refuses_the_planted_set_and_accepts_the_clean_node(
    tmp_path: Path,
) -> None:
    refused = main(
        ValidatorChainScenario,
        [str(_FIXTURES), "--report-json", str(tmp_path / "refused.json")],
        build_validator_container,
    )
    assert refused == 1
    accepted = main(
        ValidatorChainScenario,
        [
            str(_FIXTURES / "clean/contract.yaml"),
            "--report-json",
            str(tmp_path / "ok.json"),
        ],
        build_validator_container,
    )
    assert accepted == 0


@pytest.mark.parametrize(("rule_id", "key"), _PARAMETERS)
def test_a_rule_row_missing_each_required_key_fails_to_load(
    rule_id: str, key: str
) -> None:
    mutated = _with_parameter(_contract(), rule_id, key, None)
    with pytest.raises(ModelOnexError):
        check_chain_scenarios({}, {}, mutated.rules)


def test_remediation_text_comes_from_the_rule_row() -> None:
    mutated = _with_parameter(
        _contract(), "generated_test_cannot_fail", "remediation", _MARK
    )
    issues = _issues(mutated, "violation_generated_test_cannot_fail")
    assert len(issues) == 1 and issues[0].message.endswith(f" -- {_MARK}")


def test_an_unknown_break_name_in_the_rule_row_fails_to_load() -> None:
    mutated = _with_parameter(
        _contract(), "generated_test_cannot_fail", "golden_breaks", ["BOGUS"]
    )
    with pytest.raises(ValueError):
        check_chain_scenarios({}, {}, mutated.rules)


def test_emptying_the_required_break_list_lets_a_green_receipt_through() -> None:
    mutated = _with_parameter(
        _contract(), "generated_test_cannot_fail", "golden_breaks", []
    )
    assert _issues(mutated, "violation_generated_test_cannot_fail") == []


def test_a_missing_receipts_file_refuses_every_required_break() -> None:
    issues = check_chain_scenarios({"c": _document()}, {"c": None}, _contract().rules)
    assert Counter(str(i.code) for i in issues) == Counter(
        {"generated_test_cannot_fail": 4}
    )


def test_a_receipt_for_an_edited_case_is_stale() -> None:
    document = _document()
    block = cast(
        "dict[str, list[dict[str, dict[str, dict[str, str]]]]]",
        document["chain_scenarios"],
    )
    cases = block["cases"]
    cases[0]["input"]["payload"]["row"] = "edited"
    issues = check_chain_scenarios(
        {"c": document}, {"c": _receipts()}, _contract().rules
    )
    assert Counter(str(i.code) for i in issues) == Counter(
        {"generated_test_cannot_fail": 2}
    )
    assert all("different version" in i.message for i in issues)


def test_a_state_update_requires_the_skipped_reducer_update_break() -> None:
    document = _document()
    block = cast("dict[str, list[dict[str, object]]]", document["chain_scenarios"])
    block["bindings"].append(
        {
            "name": "store",
            "target": "ATTRIBUTE",
            "attribute": "_db",
            "role": "REDUCER_STATE",
            "in_memory_factory": "fixture.doubles:RecordingStore",
        }
    )
    block["cases"][0]["state_updates"] = [
        {"binding": "store", "target": "rows", "key": "alpha"}
    ]
    issues = check_chain_scenarios(
        {"c": document}, {"c": _receipts()}, _contract().rules
    )
    codes = Counter(str(i.code) for i in issues)
    assert codes["case_without_named_breaks"] == 1
    assert codes["generated_test_cannot_fail"] >= 1


# --- the schema's own failing controls ------------------------------------------------


def test_the_clean_block_parses_and_pins_each_case_with_a_hash() -> None:
    parsed = ModelChainScenarioSubcontract.model_validate(_block())
    assert [c.kind for c in parsed.cases] == [
        EnumChainScenarioKind.GOLDEN,
        EnumChainScenarioKind.ERROR,
    ]
    assert parsed.cases[0].case_hash() != parsed.cases[1].case_hash()
    without_breaks = parsed.cases[0].model_copy(update={"breaks": ()})
    assert without_breaks.case_hash() == parsed.cases[0].case_hash()


_Mutation = Callable[[dict[str, list[dict[str, dict[str, object]]]]], object]
_BREAKS_THE_SCHEMA: list[_Mutation] = [
    lambda b: b["cases"][1].pop("fault"),
    lambda b: b["cases"][1].pop("ledger_failure_row"),
    lambda b: b["cases"][1].pop("reading"),
    lambda b: b["cases"][1].pop("failure"),
    lambda b: b["cases"][0].update({"reading": "NOT_WORKING"}),
    lambda b: b["cases"][0].update({"fault": {"kind": "BAD_PAYLOAD"}}),
    lambda b: b["cases"][1].update({"failure": "undeclared"}),
    lambda b: cast("dict[str, object]", b["cases"][1]["fault"]).update(
        {"boundary": "nope"}
    ),
    lambda b: b["cases"][1].update({"case_name": b["cases"][0]["case_name"]}),
    lambda b: b["failures"][0].update(
        {"topic": cast("dict[str, object]", b)["success_topic"]}
    ),
    lambda b: b["cases"][0].update({"unknown_field": 1}),
    lambda b: b["cases"][0].pop("oracle"),
]


@pytest.mark.parametrize("mutation", _BREAKS_THE_SCHEMA)
def test_a_scenario_that_breaks_the_schema_does_not_parse(mutation: _Mutation) -> None:
    block = cast("dict[str, list[dict[str, dict[str, object]]]]", _block())
    mutation(block)
    with pytest.raises(ValidationError):
        ModelChainScenarioSubcontract.model_validate(block)


def test_an_error_case_without_a_fault_is_not_an_error_case() -> None:
    case = cast("list[dict[str, object]]", _block()["cases"])[1]
    del case["fault"]
    with pytest.raises(ValidationError, match="an error case declares a fault"):
        ModelChainScenarioCase.model_validate(case)
