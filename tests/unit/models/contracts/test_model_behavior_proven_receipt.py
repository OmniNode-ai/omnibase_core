# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelBehaviorProvenReceipt (OMN-9278).

behavior_proven is a first-class dod_evidence type proving that a ticket's
handler / pipeline / consumer / effect work was exercised against live
external state, not merely unit-tested. Every receipt records the command
that ran, the query used to inspect live state, the pass/fail assertion,
and the observation timestamp.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_behavior_proven_assertion import (
    EnumBehaviorProvenAssertion,
)
from omnibase_core.models.contracts.ticket.model_behavior_proven_receipt import (
    BEHAVIOR_PROVEN_CHECK_TYPE,
    ModelBehaviorProvenReceipt,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)


def _base_fields() -> dict:
    return {
        "ticket_id": "OMN-9214",
        "evidence_item_id": "dod-behavior-001",
        "command_run": "kcat -P -b 192.168.86.201:19092 -t onex.cmd.merge_sweep.v1",
        "query": "rpk topic consume onex.evt.merge_sweep.completed.v1 --num 1",
        "assertion": EnumBehaviorProvenAssertion.PASSED,
        "observed_at": datetime.now(tz=UTC),
    }


@pytest.mark.unit
class TestModelBehaviorProvenReceiptConstruction:
    def test_minimum_valid_receipt_constructs(self) -> None:
        receipt = ModelBehaviorProvenReceipt(**_base_fields())
        assert receipt.ticket_id == "OMN-9214"
        assert receipt.assertion is EnumBehaviorProvenAssertion.PASSED
        assert receipt.observed_state is None

    def test_full_receipt_with_observed_state(self) -> None:
        fields = _base_fields()
        fields["observed_state"] = '{"offset": 42, "value": "merged"}'
        receipt = ModelBehaviorProvenReceipt(**fields)
        assert receipt.observed_state == '{"offset": 42, "value": "merged"}'

    def test_receipt_is_frozen(self) -> None:
        receipt = ModelBehaviorProvenReceipt(**_base_fields())
        with pytest.raises(ValidationError):
            receipt.assertion = EnumBehaviorProvenAssertion.FAILED  # type: ignore[misc]

    def test_receipt_rejects_extra_fields(self) -> None:
        fields = _base_fields()
        fields["rogue"] = "nope"
        with pytest.raises(ValidationError):
            ModelBehaviorProvenReceipt(**fields)


@pytest.mark.unit
class TestModelBehaviorProvenReceiptValidators:
    @pytest.mark.parametrize(
        "bad_id",
        ["OMN-", "omn-1", "1", "OMN-abc", "OMN1", "", "PROJ-1"],
    )
    def test_invalid_ticket_id_rejected(self, bad_id: str) -> None:
        fields = _base_fields()
        fields["ticket_id"] = bad_id
        with pytest.raises(ValidationError, match="ticket_id"):
            ModelBehaviorProvenReceipt(**fields)

    def test_naive_observed_at_rejected(self) -> None:
        fields = _base_fields()
        fields["observed_at"] = datetime(2026, 4, 20, 12, 0, 0)  # no tzinfo
        with pytest.raises(ValidationError, match="timezone-aware"):
            ModelBehaviorProvenReceipt(**fields)

    def test_non_utc_observed_at_converted_to_utc(self) -> None:
        from datetime import timedelta, timezone

        eastern = timezone(timedelta(hours=-5))
        fields = _base_fields()
        fields["observed_at"] = datetime(2026, 4, 20, 12, 0, 0, tzinfo=eastern)
        receipt = ModelBehaviorProvenReceipt(**fields)
        assert receipt.observed_at.tzinfo is UTC
        assert receipt.observed_at.hour == 17

    def test_empty_command_run_rejected(self) -> None:
        fields = _base_fields()
        fields["command_run"] = ""
        with pytest.raises(ValidationError):
            ModelBehaviorProvenReceipt(**fields)

    def test_empty_query_rejected(self) -> None:
        fields = _base_fields()
        fields["query"] = ""
        with pytest.raises(ValidationError):
            ModelBehaviorProvenReceipt(**fields)


@pytest.mark.unit
class TestBehaviorProvenEvidenceItemIntegration:
    """behavior_proven receipts must be recognizable as check entries on
    ModelDodEvidenceItem so the existing receipt-gate stays backwards-compatible.
    """

    def test_evidence_item_accepts_behavior_proven_check_type(self) -> None:
        item = ModelDodEvidenceItem(
            id="dod-behavior-001",
            description="merge_sweep emits onex.cmd and PR enters queue",
            checks=[
                ModelDodEvidenceCheck(
                    check_type=BEHAVIOR_PROVEN_CHECK_TYPE,
                    check_value="kcat -P ... then rpk topic consume ...",
                ),
            ],
        )
        assert item.checks[0].check_type == "behavior_proven"
        assert BEHAVIOR_PROVEN_CHECK_TYPE == "behavior_proven"

    def test_existing_check_types_still_valid(self) -> None:
        """Migration path: rendered_output / runtime_boot items remain valid."""
        item = ModelDodEvidenceItem(
            id="dod-render-001",
            description="dashboard renders",
            checks=[
                ModelDodEvidenceCheck(
                    check_type="rendered_output",
                    check_value="playwright test tests/dashboard/nodes.spec.ts",
                ),
            ],
        )
        assert item.checks[0].check_type == "rendered_output"


@pytest.mark.unit
class TestBehaviorProvenAssertionEnum:
    def test_enum_values_are_stable_strings(self) -> None:
        assert EnumBehaviorProvenAssertion.PASSED.value == "passed"
        assert EnumBehaviorProvenAssertion.FAILED.value == "failed"

    def test_enum_rejects_unknown_value(self) -> None:
        with pytest.raises(ValueError):
            EnumBehaviorProvenAssertion("maybe")
