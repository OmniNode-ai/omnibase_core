# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parity of the core ticket-creation validator with the omniclaude guard it replaces (OMN-22850).

``guard_recorded_verdicts.json`` holds payloads and the verdict the guard itself returned for
each: exit 0 (admitted) or exit 3 with its finding codes and fields, one case per refusal code
plus the accepted shapes. The recording ran the guard script on the lab host against the
omniclaude head the fixture names; this test replays the same payloads through the core checker
and the file validator and asserts equal verdicts. The recording is a fixture rather than a
live run so the test needs no sibling clone and never skips.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_ticket_creation import check_ticket_creation
from omnibase_core.validation.validator_ticket_creation import (
    ValidatorTicketCreation,
    ledger_line_lookup,
)

CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "ticket_creation.validation.yaml"
)
RECORDED = json.loads(
    (
        Path(__file__).parents[2]
        / "fixtures"
        / "ticket_creation"
        / "guard_recorded_verdicts.json"
    ).read_text("utf-8")
)
CASES = RECORDED["cases"]
LEDGER_NAME = "ROLLING_WORK_LEDGER.md"


def _data() -> dict[str, object]:
    loaded = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    assert isinstance(loaded, dict)
    return loaded


def _contract(data: dict[str, object] | None = None) -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(data or _data())


def _ledger(tmp_path: Path) -> Path:
    ledger = tmp_path / LEDGER_NAME
    ledger.write_text("\n".join(RECORDED["ledger_lines"]) + "\n", encoding="utf-8")
    return ledger


def _verdict(
    case: dict[str, object], contract: ModelValidatorSubcontract, ledger: Path
) -> tuple[bool, list[tuple[str, str]]]:
    lane = case["lane"]
    assert lane is None or isinstance(lane, str)
    result = check_ticket_creation(
        case["tool_input"],
        contract,
        lane=lane,
        ledger_line_exists=ledger_line_lookup(ledger),
    )
    return result.admitted, [(f.code, f.field) for f in result.findings]


def _guard(case: dict[str, object]) -> tuple[bool, list[tuple[str, str]]]:
    guard = case["guard"]
    assert isinstance(guard, dict)
    return guard["exit"] == 0, [(code, field) for code, field in guard["findings"]]


def _mismatches(data: dict[str, object], ledger: Path) -> list[str]:
    contract = _contract(data)
    return [
        str(case["name"])
        for case in CASES
        if _verdict(case, contract, ledger) != _guard(case)
    ]


def _rules(data: dict[str, object]) -> list[dict[str, object]]:
    rules = data["rules"]
    assert isinstance(rules, list)
    return rules


def _rule(data: dict[str, object], rule_id: str) -> dict[str, object]:
    return next(r for r in _rules(data) if r["rule_id"] == rule_id)


def _params(row: dict[str, object]) -> dict[str, list[str]]:
    params = row["parameters"]
    assert isinstance(params, dict)
    return params


class TestParityWithTheGuard:
    @pytest.mark.parametrize("case", CASES, ids=[str(c["name"]) for c in CASES])
    def test_equal_verdict(self, case: dict[str, object], tmp_path: Path) -> None:
        assert _verdict(case, _contract(), _ledger(tmp_path)) == _guard(case)

    def test_every_refusal_code_and_an_accepted_shape_is_recorded(self) -> None:
        codes = {code for case in CASES for code, _field in _guard(case)[1]}
        rules = {r["rule_id"] for r in _rules(_data())}
        findings = codes | {"criterion_text_unreadable"}
        assert codes <= rules
        assert {
            "missing_parent",
            "project_set",
            "missing_gate_line",
            "residual_title",
            "missing_probe_line",
            "malformed_probe_line",
            "unfalsified_criterion",
            "merge_state_falsifier_on_behaviour_criterion",
            "missing_acceptance_criteria",
            "unlabelled_criteria",
            "missing_diagnosis",
            "unresolvable_diagnosis",
            "lane_identity_missing",
            "lane_label_missing",
            "lane_stamp_missing",
            "unevaluable",
        } <= findings
        assert any(_guard(case)[0] for case in CASES)

    def test_the_file_validator_reads_the_same_verdict(self, tmp_path: Path) -> None:
        ledger = _ledger(tmp_path)
        validator = ValidatorTicketCreation()
        contract = validator._load_contract()
        for case in CASES:
            doc = tmp_path / "payload.ticket-creation-payload.json"
            doc.write_text(
                json.dumps(
                    {
                        "tool_input": case["tool_input"],
                        "lane": case["lane"],
                        "ledger_path": str(ledger),
                    }
                ),
                encoding="utf-8",
            )
            issues = validator._validate_file(doc, contract)
            admitted, findings = _guard(case)
            assert [i.code for i in issues] == [code for code, _f in findings], case[
                "name"
            ]
            assert (not issues) == admitted


class TestFailingControl:
    """Each control drops one thing the guard enforces and shows the parity read going red."""

    def test_the_unmodified_contract_has_no_mismatch(self, tmp_path: Path) -> None:
        assert _mismatches(_data(), _ledger(tmp_path)) == []

    @pytest.mark.parametrize(
        "code",
        sorted({code for case in CASES for code, _f in _guard(case)[1]}),
    )
    def test_dropping_a_rule_is_a_mismatch(self, code: str, tmp_path: Path) -> None:
        data = copy.deepcopy(_data())
        _rule(data, code)["enabled"] = False
        broken = _mismatches(data, _ledger(tmp_path))
        assert broken, f"dropping {code} left every recorded verdict equal"
        expected = {
            str(case["name"])
            for case in CASES
            if any(c == code for c, _f in _guard(case)[1])
        }
        assert expected <= set(broken)

    def test_dropping_a_vocabulary_entry_is_a_mismatch(self, tmp_path: Path) -> None:
        data = copy.deepcopy(_data())
        row = _rule(data, "binding_grammar")
        params = _params(row)
        params["criterion_ids"] = [i for i in params["criterion_ids"] if i != "C7"]
        assert "admitted" in _mismatches(data, _ledger(tmp_path))


class TestUpdatesAndContract:
    def test_an_update_that_writes_the_description_is_refused_not_assumed_clean(
        self,
    ) -> None:
        result = check_ticket_creation({"id": "OMN-1", "description": "x"}, _contract())
        assert result.codes == ("criterion_text_unreadable",)

    def test_a_contract_with_a_missing_row_refuses_instead_of_admitting(self) -> None:
        data = copy.deepcopy(_data())
        data["rules"] = [r for r in _rules(data) if r["rule_id"] != "project_set"]
        with pytest.raises(Exception, match="project_set"):
            check_ticket_creation(
                {"title": "t", "description": "d", "parentId": "OMN-1", "project": "p"},
                _contract(data),
            )
