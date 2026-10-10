# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: the two ``binds_ac`` refusals ModelTicketContract shares with OCC.

onex_change_control's ``validate-yaml`` validates every ``dod_evidence`` item
that declares ``binds_ac`` against its OCC-local ``ModelDodEvidenceItem``
before handing the contract to this model. That adds two refusals core did not
carry: a ``binds_ac`` entry that is not a bare criterion label, and a check
type outside OCC's eight on an item that declares ``binds_ac``. These tests
pin both on the ticket-contract model, the good forms that still pass, and the
places the rules must not reach (items with no ``binds_ac``, and the goal
contract event models that bind free-form criterion ids).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.ticket.model_contract_dod_item import (
    BINDS_AC_CHECK_TYPE_RULE,
    BINDS_AC_LABEL_RULE,
    ModelContractDodItem,
)
from omnibase_core.models.ticket.model_ticket_contract import ModelTicketContract

_OCC_CHECK_TYPES = (
    "test_exists",
    "test_passes",
    "file_exists",
    "grep",
    "command",
    "endpoint",
    "behavior_proven",
    "semantic_grading",
)


def _item(
    item_id: str = "dod-omn-1-ac1",
    *,
    check_type: str = "test_passes",
    check_value: Any = "uv run pytest tests/unit -q",
    **extra: Any,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id,
        "description": "the gate is wired",
        "source": "manual",
        "checks": [{"check_type": check_type, "check_value": check_value}],
    }
    if check_type == "file_exists":
        # A sole file_exists item is refused by an unrelated core rule.
        item["checks"].append({"check_type": "command", "check_value": "true"})
    item.update(extra)
    return item


def _contract(*items: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-1",
        "title": "binds_ac parity",
        "dod_evidence": list(items),
    }


@pytest.mark.unit
class TestBindsAcLabelRule:
    def test_label_with_trailing_text_is_refused_naming_item_and_rule(self) -> None:
        bad = _item("dod-omn-1-wired", binds_ac=["AC1 -- the gate is wired"])
        with pytest.raises(ValidationError) as excinfo:
            ModelTicketContract.model_validate(_contract(bad))
        message = str(excinfo.value)
        assert BINDS_AC_LABEL_RULE in message
        assert "'dod-omn-1-wired'" in message
        assert "'AC1 -- the gate is wired'" in message

    @pytest.mark.parametrize(
        "entry", ["AC1 -- the gate is wired", "AC1 extra", "criterion-1", "AC", ""]
    )
    def test_non_label_entries_are_refused(self, entry: str) -> None:
        with pytest.raises(ValidationError, match=BINDS_AC_LABEL_RULE):
            ModelTicketContract.model_validate(_contract(_item(binds_ac=[entry])))

    @pytest.mark.parametrize(
        "entry", ["AC1", "ac-1", "DoD2", "DOD 3", "AC_4", "ac.5", "AC12"]
    )
    def test_well_formed_labels_still_pass(self, entry: str) -> None:
        contract = ModelTicketContract.model_validate(
            _contract(_item(binds_ac=[entry]))
        )
        assert contract.dod_evidence[0].binds_ac == (entry,)


@pytest.mark.unit
class TestBindsAcCheckTypeRule:
    def test_command_exit_0_with_binds_ac_is_refused_naming_item_and_rule(
        self,
    ) -> None:
        bad = _item("dod-omn-1-exit", check_type="command_exit_0", binds_ac=["AC1"])
        with pytest.raises(ValidationError) as excinfo:
            ModelTicketContract.model_validate(_contract(bad))
        message = str(excinfo.value)
        assert BINDS_AC_CHECK_TYPE_RULE in message
        assert "'dod-omn-1-exit'" in message
        assert "'command_exit_0'" in message

    @pytest.mark.parametrize(
        "check_type", ["rendered_output", "runtime_sha_match", "disposition"]
    )
    def test_other_core_only_check_types_with_binds_ac_are_refused(
        self, check_type: str
    ) -> None:
        bad = _item(check_type=check_type, binds_ac=["AC1"])
        with pytest.raises(ValidationError, match=BINDS_AC_CHECK_TYPE_RULE):
            ModelTicketContract.model_validate(_contract(bad))

    def test_declared_but_empty_binds_ac_still_meets_the_rule(self) -> None:
        bad = _item(check_type="command_exit_0", binds_ac=[])
        with pytest.raises(ValidationError, match=BINDS_AC_CHECK_TYPE_RULE):
            ModelTicketContract.model_validate(_contract(bad))

    @pytest.mark.parametrize("check_type", _OCC_CHECK_TYPES)
    def test_occ_check_types_with_binds_ac_still_pass(self, check_type: str) -> None:
        check_value: Any = (
            {"pattern": "x", "path": "src/"} if check_type == "grep" else "true"
        )
        contract = ModelTicketContract.model_validate(
            _contract(
                _item(check_type=check_type, check_value=check_value, binds_ac=["AC1"])
            )
        )
        assert contract.dod_evidence[0].checks[0].check_type == check_type

    def test_command_exit_0_without_binds_ac_still_passes(self) -> None:
        contract = ModelTicketContract.model_validate(
            _contract(_item(check_type="command_exit_0"))
        )
        assert contract.dod_evidence[0].checks[0].check_type == "command_exit_0"


@pytest.mark.unit
class TestBindsAcRulesScope:
    def test_every_violating_item_is_named(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            ModelTicketContract.model_validate(
                _contract(
                    _item("dod-a", binds_ac=["AC1 -- text"]),
                    _item("dod-b", check_type="command_exit_0", binds_ac=["AC2"]),
                    _item("dod-c", binds_ac=["AC3"]),
                )
            )
        message = str(excinfo.value)
        assert "'dod-a'" in message
        assert "'dod-b'" in message
        assert "'dod-c'" not in message

    def test_goal_contract_item_model_keeps_free_form_criterion_ids(self) -> None:
        item = ModelContractDodItem.model_validate(
            _item(check_type="disposition", binds_ac=["criterion-goal-contract"])
        )
        assert item.binds_ac == ("criterion-goal-contract",)
