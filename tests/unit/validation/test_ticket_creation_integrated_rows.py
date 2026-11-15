# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The integrated-criterion row of the core ticket create gate (OMN-23411).

A code ticket is done only when it is seen running, so one acceptance criterion must
open with ``integrated:`` and its falsifier must read the running system. These tests
exercise the checker the way a caller does: through the committed contract and the
file validator, with no sibling clone.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation import validator_base
from omnibase_core.validation.checker_ticket_creation import check_ticket_creation
from omnibase_core.validation.validator_ticket_creation import ValidatorTicketCreation

CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "ticket_creation.validation.yaml"
)

GRAMMAR = (
    "- [ ] AC<n>: integrated: <what is true in the running system> -- falsifier: "
    "<command run on a lab host or the dev lane, and the result read back>"
)
PLAIN_CRITERION = (
    "- [ ] AC1: the check works -- falsifier: uv run pytest tests/unit/test_x.py -q"
)
INTEGRATED_CRITERION = (
    "- [ ] AC2: integrated: the gate refuses a bare create in the running ticket node"
    " -- falsifier: onex ticket create on a lab host, refusal read back"
)
INTEGRATED_UNREAD_CRITERION = (
    "- [ ] AC2: integrated: the refusal is reproduced"
    " -- falsifier: uv run pytest tests/unit/test_gate.py -q"
)
UNREAD_FIX = "name the host, lane or running node the falsifier reads, and the read-back it makes"


def _data() -> dict[str, object]:
    loaded = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    assert isinstance(loaded, dict)
    return loaded


def _contract(data: dict[str, object] | None = None) -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(data or _data())


def _payload(description: str) -> dict[str, object]:
    return {
        "title": "Mint the floor ticket",
        "description": description,
        "parentId": "OMN-22847",
        "state": "Backlog",
    }


def _description(*criteria: str) -> str:
    return "Gate: C7\n\n## Acceptance criteria\n" + "\n".join(criteria)


class TestGoldenAdmittedCreate:
    def test_an_integrated_criterion_whose_falsifier_reads_the_running_system_admits(
        self,
    ) -> None:
        description = _description(INTEGRATED_CRITERION)
        assert check_ticket_creation(_payload(description), _contract()).admitted

    def test_the_other_criteria_need_not_read_the_running_system(self) -> None:
        description = _description(PLAIN_CRITERION, INTEGRATED_CRITERION)
        result = check_ticket_creation(_payload(description), _contract())
        assert result.admitted


class TestRefusedCreate:
    def test_no_integrated_criterion_is_refused_with_the_grammar_fix(self) -> None:
        result = check_ticket_creation(
            _payload(_description(PLAIN_CRITERION)), _contract()
        )
        assert result.codes == ("missing_integrated_criterion",)
        finding = result.findings[0]
        assert finding.field == "description"
        assert finding.reason == (
            "no acceptance criterion is an integrated one: a code ticket is done only "
            "when it is seen running, so one criterion must open with 'integrated:' "
            "and name the running system"
        )
        assert finding.fix == f"add '{GRAMMAR}' as the last criterion"

    def test_an_integrated_criterion_whose_falsifier_reads_nothing_running_is_refused(
        self,
    ) -> None:
        result = check_ticket_creation(
            _payload(_description(PLAIN_CRITERION, INTEGRATED_UNREAD_CRITERION)),
            _contract(),
        )
        assert result.codes == ("missing_integrated_criterion",)
        finding = result.findings[0]
        assert finding.field == "description"
        assert finding.reason == (
            "the integrated criterion 'AC2: integrated: the refusal is reproduced "
            "-- falsifier: uv run pytest tests/unit/test_gate.py -q' has a falsifier "
            "that does not read the running system"
        )
        assert finding.fix == UNREAD_FIX


class TestExemptDescriptions:
    def test_an_epic_line_is_exempt(self) -> None:
        description = (
            "Gate: C7\nissue_class: epic\n\n## Acceptance criteria\n" + PLAIN_CRITERION
        )
        payload = {
            "title": "Mint the floor ticket",
            "description": description,
            "state": "Backlog",
        }
        assert check_ticket_creation(payload, _contract()).admitted

    def test_a_proof_class_of_code_only_is_exempt(self) -> None:
        description = (
            "Gate: C7\n\nProof class: code-only\n\n## Acceptance criteria\n"
            + PLAIN_CRITERION
        )
        assert check_ticket_creation(_payload(description), _contract()).admitted

    def test_the_parent_criterion_binding_form_is_not_exempt(self) -> None:
        description = (
            "Gate: OMN-22478 AC-1\n\n## Acceptance criteria\n" + PLAIN_CRITERION
        )
        result = check_ticket_creation(_payload(description), _contract())
        assert result.codes == ("missing_integrated_criterion",)

    def test_a_parent_criterion_create_with_no_criteria_is_left_to_the_other_rules(
        self,
    ) -> None:
        result = check_ticket_creation(
            _payload("Gate: OMN-22478 AC-1\n\nNo list here."), _contract()
        )
        assert "missing_integrated_criterion" not in result.codes


class TestTheRefusalComesFromTheRow:
    def test_disabling_the_row_admits_the_same_payload(self) -> None:
        payload = _payload(_description(PLAIN_CRITERION))
        enabled = check_ticket_creation(payload, _contract())
        assert enabled.codes == ("missing_integrated_criterion",)
        data = copy.deepcopy(_data())
        rules = data["rules"]
        assert isinstance(rules, list)
        row = next(r for r in rules if r["rule_id"] == "missing_integrated_criterion")
        row["enabled"] = False
        assert check_ticket_creation(payload, _contract(data)).admitted


class TestThroughTheFileValidator:
    """The shape the dev-lane run uses: one payload read by the installed validator."""

    def _issues(
        self, tmp_path: Path, document: dict[str, object]
    ) -> list[ModelValidationIssue]:
        doc = tmp_path / "integrated.ticket-creation-payload.json"
        doc.write_text(json.dumps(document), encoding="utf-8")
        validator = ValidatorTicketCreation()
        return list(validator._validate_file(doc, validator._load_contract()))

    def test_an_integrated_create_yields_no_issues(self, tmp_path: Path) -> None:
        description = _description(PLAIN_CRITERION, INTEGRATED_CRITERION)
        assert self._issues(tmp_path, {"tool_input": _payload(description)}) == []

    @pytest.mark.parametrize(
        ("criteria", "fragment"),
        [
            pytest.param(
                (PLAIN_CRITERION,),
                "no acceptance criterion is an integrated one",
                id="missing",
            ),
            pytest.param(
                (PLAIN_CRITERION, INTEGRATED_UNREAD_CRITERION),
                "does not read the running system",
                id="unread",
            ),
        ],
    )
    def test_the_refusals_travel_the_whole_chain(
        self, tmp_path: Path, criteria: tuple[str, ...], fragment: str
    ) -> None:
        issues = self._issues(
            tmp_path, {"tool_input": _payload(_description(*criteria))}
        )
        assert [i.code for i in issues] == ["missing_integrated_criterion"]
        assert fragment in issues[0].message


class TestTheTicketNodePayloadShape:
    """The seam with the ticket node: the payload its handler builds, with a lane context."""

    def _node_payload(self, criteria: tuple[str, ...]) -> dict[str, object]:
        description = (
            "created-by-lane: lane-a\n\nGate: OMN-22478 AC-1\n\n## Acceptance criteria\n"
            + "\n".join(criteria)
        )
        return {
            "title": "Mint the floor ticket",
            "description": description,
            "parentId": "OMN-22847",
            "state": "Backlog",
            "labels": ["lane-created"],
        }

    def test_a_node_create_without_an_integrated_criterion_is_refused_alone(
        self,
    ) -> None:
        result = check_ticket_creation(
            self._node_payload((PLAIN_CRITERION,)),
            _contract(),
            lane="lane-a",
            route="node",
            route_switch="refuse",
        )
        assert result.codes == ("missing_integrated_criterion",)

    def test_a_node_create_with_an_integrated_criterion_is_admitted(self) -> None:
        result = check_ticket_creation(
            self._node_payload((PLAIN_CRITERION, INTEGRATED_CRITERION)),
            _contract(),
            lane="lane-a",
            route="node",
            route_switch="refuse",
        )
        assert result.admitted
