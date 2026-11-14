# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The route rows of the core ticket create gate: create_route and contract_block_edit (OMN-23764).

The checker cannot see who built a payload, so its caller states the route and reads the
switch. These tests exercise the checker the way a caller does: through the committed contract
and the file validator, with no sibling clone.
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
from omnibase_core.validation.validator_ticket_creation import ValidatorTicketCreation

CONTRACT_PATH = (
    Path(validator_base.__file__).parent
    / "contracts"
    / "ticket_creation.validation.yaml"
)

# The admitted create of tests/fixtures/ticket_creation/guard_recorded_verdicts.json.
ADMITTED_CREATE: dict[str, object] = {
    "title": "Mint the floor ticket",
    "description": (
        "Gate: C7\n\n## Acceptance criteria\n"
        "- [ ] AC1: the check works -- falsifier: uv run pytest tests/unit/test_x.py -q"
    ),
    "parentId": "OMN-22847",
    "state": "Backlog",
}

BLOCK = "```yaml onex-ticket-contract\nschema_version: 1.1.0\ncontract_fingerprint: aaaa\n```\n"
BODY = "created-by-lane: lane-a\n\nIn plain terms: x\n\n" + BLOCK


def _data() -> dict[str, object]:
    loaded = yaml.safe_load(CONTRACT_PATH.read_text("utf-8"))["validation"]
    assert isinstance(loaded, dict)
    return loaded


def _contract(data: dict[str, object] | None = None) -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract.model_validate(data or _data())


def _update(**fields: object) -> dict[str, object]:
    return {"id": "OMN-1", **fields}


class TestCreateRouteRefused:
    def test_create_route_refused_for_a_raw_create_with_the_switch_at_refuse(
        self,
    ) -> None:
        result = check_ticket_creation(
            ADMITTED_CREATE, _contract(), route="raw", route_switch="refuse"
        )
        assert result.codes == ("create_route",)
        finding = result.findings[0]
        assert "onex ticket create --draft" in finding.fix

    def test_create_route_refused_control_the_same_payload_is_admitted_without_a_route(
        self,
    ) -> None:
        assert check_ticket_creation(ADMITTED_CREATE, _contract()).admitted

    def test_the_switch_defaults_to_allow(self) -> None:
        assert check_ticket_creation(ADMITTED_CREATE, _contract(), route="raw").admitted
        assert check_ticket_creation(
            ADMITTED_CREATE, _contract(), route="raw", route_switch="allow"
        ).admitted

    def test_a_node_create_is_admitted_with_the_switch_at_refuse(self) -> None:
        assert check_ticket_creation(
            ADMITTED_CREATE, _contract(), route="node", route_switch="refuse"
        ).admitted

    def test_the_switch_is_a_contract_default_a_caller_can_move(self) -> None:
        data = copy.deepcopy(_data())
        rules = data["rules"]
        assert isinstance(rules, list)
        row = next(r for r in rules if r["rule_id"] == "create_route")
        row["parameters"]["switch_default"] = "refuse"
        result = check_ticket_creation(ADMITTED_CREATE, _contract(data), route="raw")
        assert result.codes == ("create_route",)
        assert check_ticket_creation(
            ADMITTED_CREATE, _contract(data), route="raw", route_switch="allow"
        ).admitted

    def test_disabling_the_row_admits_the_raw_create(self) -> None:
        data = copy.deepcopy(_data())
        rules = data["rules"]
        assert isinstance(rules, list)
        next(r for r in rules if r["rule_id"] == "create_route")["enabled"] = False
        assert check_ticket_creation(
            ADMITTED_CREATE, _contract(data), route="raw", route_switch="refuse"
        ).admitted

    @pytest.mark.parametrize(
        ("route", "switch", "field"),
        [("hand", None, "route"), ("raw", "maybe", "route_switch")],
    )
    def test_an_unknown_route_or_switch_is_refused_not_read_as_clean(
        self, route: str, switch: str | None, field: str
    ) -> None:
        result = check_ticket_creation(
            ADMITTED_CREATE, _contract(), route=route, route_switch=switch
        )
        assert result.codes == ("unevaluable",)
        assert result.findings[0].field == field

    def test_a_raw_create_that_breaks_another_rule_reports_both(self) -> None:
        bad = {**ADMITTED_CREATE, "project": "p"}
        result = check_ticket_creation(
            bad, _contract(), route="raw", route_switch="refuse"
        )
        assert result.codes == ("project_set", "create_route")


class TestContractBlockEdit:
    def test_contract_block_edit_refused_for_a_full_description_that_changes_the_block(
        self,
    ) -> None:
        edited = BODY.replace("aaaa", "bbbb")
        result = check_ticket_creation(
            _update(description=edited),
            _contract(),
            route="raw",
            current_description=BODY,
        )
        assert result.codes == ("contract_block_edit", "criterion_text_unreadable")
        assert "onex ticket sync" in result.findings[0].fix

    def test_contract_block_edit_refused_for_a_replace_patch_inside_the_block(
        self,
    ) -> None:
        patch = [
            {
                "op": "replace",
                "old_string": "contract_fingerprint: aaaa",
                "new_string": "contract_fingerprint: bbbb",
            }
        ]
        result = check_ticket_creation(
            _update(patch=patch), _contract(), route="raw", current_description=BODY
        )
        assert "contract_block_edit" in result.codes

    def test_contract_block_edit_refused_when_a_patch_deletes_the_block(self) -> None:
        patch = [{"op": "replace", "old_string": BLOCK, "new_string": ""}]
        result = check_ticket_creation(
            _update(patch=patch), _contract(), current_description=BODY
        )
        assert "contract_block_edit" in result.codes

    def test_contract_block_edit_refused_when_a_block_is_written_into_a_blockless_body(
        self,
    ) -> None:
        patch = [{"op": "append", "text": BLOCK}]
        result = check_ticket_creation(
            _update(patch=patch),
            _contract(),
            current_description="created-by-lane: lane-a\n",
        )
        assert "contract_block_edit" in result.codes

    def test_contract_block_edit_refused_whatever_the_switch(self) -> None:
        for switch in ("allow", "refuse"):
            result = check_ticket_creation(
                _update(description=BODY.replace("aaaa", "bbbb")),
                _contract(),
                route="raw",
                route_switch=switch,
                current_description=BODY,
            )
            assert "contract_block_edit" in result.codes

    def test_a_patch_outside_the_block_is_not_a_block_edit(self) -> None:
        patch = [
            {
                "op": "replace",
                "old_string": "In plain terms: x",
                "new_string": "In plain terms: y",
            }
        ]
        result = check_ticket_creation(
            _update(patch=patch), _contract(), route="raw", current_description=BODY
        )
        assert result.codes == ("criterion_text_unreadable",)

    def test_the_node_route_may_change_the_block(self) -> None:
        result = check_ticket_creation(
            _update(description=BODY.replace("aaaa", "bbbb")),
            _contract(),
            route="node",
            current_description=BODY,
        )
        assert result.codes == ("criterion_text_unreadable",)

    def test_an_unresolvable_patch_is_not_judged_a_block_edit_and_stays_refused(
        self,
    ) -> None:
        patch = [{"op": "replace", "old_string": "no such text", "new_string": "x"}]
        result = check_ticket_creation(
            _update(patch=patch), _contract(), route="raw", current_description=BODY
        )
        assert result.codes == ("criterion_text_unreadable",)

    def test_an_update_without_the_current_body_is_unchanged(self) -> None:
        result = check_ticket_creation(
            _update(description=BODY.replace("aaaa", "bbbb")), _contract()
        )
        assert result.codes == ("criterion_text_unreadable",)

    def test_a_state_only_update_is_admitted(self) -> None:
        assert check_ticket_creation(
            _update(state="Done"), _contract(), route="raw", current_description=BODY
        ).admitted


class TestRecordedPayloadThroughTheFileValidator:
    """The shape the dev-lane run uses: one recorded payload read by the installed validator."""

    def _issues(self, tmp_path: Path, document: dict[str, object]) -> list[str]:
        doc = tmp_path / "recorded.ticket-creation-payload.json"
        doc.write_text(json.dumps(document), encoding="utf-8")
        validator = ValidatorTicketCreation()
        return [
            i.code for i in validator._validate_file(doc, validator._load_contract())
        ]

    def test_a_recorded_raw_payload_yields_create_route(self, tmp_path: Path) -> None:
        issues = self._issues(
            tmp_path,
            {"tool_input": ADMITTED_CREATE, "route": "raw", "route_switch": "refuse"},
        )
        assert issues == ["create_route"]

    def test_a_recorded_block_edit_yields_contract_block_edit(
        self, tmp_path: Path
    ) -> None:
        issues = self._issues(
            tmp_path,
            {
                "tool_input": _update(description=BODY.replace("aaaa", "bbbb")),
                "route": "raw",
                "current_description": BODY,
            },
        )
        assert issues[0] == "contract_block_edit"

    def test_a_document_without_a_route_is_judged_as_before(
        self, tmp_path: Path
    ) -> None:
        assert self._issues(tmp_path, {"tool_input": ADMITTED_CREATE}) == []
