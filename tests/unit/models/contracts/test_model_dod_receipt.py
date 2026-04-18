# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDodReceipt — the receipt-gate proof artifact."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt


def _base_fields() -> dict:
    return {
        "ticket_id": "OMN-9084",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "gh pr view --json state -q .state",
        "status": EnumReceiptStatus.PASS,
        "run_timestamp": datetime.now(tz=UTC),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "ci-receipt-gate",
    }


@pytest.mark.unit
class TestModelDodReceiptConstruction:
    def test_minimum_valid_receipt_constructs(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.ticket_id == "OMN-9084"
        assert receipt.status is EnumReceiptStatus.PASS
        assert receipt.actual_output is None
        assert receipt.exit_code is None

    def test_full_receipt_with_all_fields(self) -> None:
        fields = _base_fields()
        fields.update(
            actual_output="OPEN",
            exit_code=0,
            duration_ms=123,
            pr_number=1349,
        )
        receipt = ModelDodReceipt(**fields)
        assert receipt.actual_output == "OPEN"
        assert receipt.exit_code == 0
        assert receipt.duration_ms == 123
        assert receipt.pr_number == 1349

    def test_receipt_is_frozen(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        with pytest.raises(ValidationError):
            receipt.status = EnumReceiptStatus.FAIL  # type: ignore[misc]

    def test_receipt_rejects_extra_fields(self) -> None:
        fields = _base_fields()
        fields["rogue_field"] = "not allowed"
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptTicketIdValidator:
    def test_valid_ticket_id_passes(self) -> None:
        ModelDodReceipt(**_base_fields())

    @pytest.mark.parametrize(
        "bad_id",
        ["OMN-", "omn-9084", "9084", "OMN-abc", "OMN9084", "", "PROJ-1"],
    )
    def test_invalid_ticket_id_rejected(self, bad_id: str) -> None:
        fields = _base_fields()
        fields["ticket_id"] = bad_id
        with pytest.raises(ValidationError, match="ticket_id"):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptCommitShaValidator:
    def test_valid_sha_short_passes(self) -> None:
        fields = _base_fields()
        fields["commit_sha"] = "a1b2c3d"
        ModelDodReceipt(**fields)

    def test_valid_sha_full_passes(self) -> None:
        fields = _base_fields()
        fields["commit_sha"] = "a" * 40
        ModelDodReceipt(**fields)

    @pytest.mark.parametrize(
        "bad_sha",
        ["a1b2c3", "zzzzzzz", "A1B2C3D", "a" * 41, "", "not-a-sha"],
    )
    def test_invalid_sha_rejected(self, bad_sha: str) -> None:
        fields = _base_fields()
        fields["commit_sha"] = bad_sha
        with pytest.raises(ValidationError, match="commit_sha"):
            ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptTimestampValidator:
    def test_naive_datetime_rejected(self) -> None:
        fields = _base_fields()
        fields["run_timestamp"] = datetime(2026, 4, 17, 20, 0, 0)  # no tz
        with pytest.raises(ValidationError, match="timezone-aware"):
            ModelDodReceipt(**fields)

    def test_non_utc_tz_normalized_to_utc(self) -> None:
        from datetime import timezone

        eastern = timezone(timedelta(hours=-5))
        fields = _base_fields()
        fields["run_timestamp"] = datetime(2026, 4, 17, 15, 0, 0, tzinfo=eastern)
        receipt = ModelDodReceipt(**fields)
        assert receipt.run_timestamp.tzinfo is UTC
        assert receipt.run_timestamp.hour == 20  # 15 EST → 20 UTC


@pytest.mark.unit
class TestModelDodReceiptDurationValidator:
    def test_negative_duration_rejected(self) -> None:
        fields = _base_fields()
        fields["duration_ms"] = -1
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)

    def test_zero_duration_allowed(self) -> None:
        fields = _base_fields()
        fields["duration_ms"] = 0
        ModelDodReceipt(**fields)


@pytest.mark.unit
class TestModelDodReceiptStatusEnum:
    def test_pass_status(self) -> None:
        receipt = ModelDodReceipt(**_base_fields())
        assert receipt.status is EnumReceiptStatus.PASS

    def test_fail_status(self) -> None:
        fields = _base_fields()
        fields["status"] = EnumReceiptStatus.FAIL
        receipt = ModelDodReceipt(**fields)
        assert receipt.status is EnumReceiptStatus.FAIL

    def test_arbitrary_string_status_rejected(self) -> None:
        fields = _base_fields()
        fields["status"] = "MAYBE"
        with pytest.raises(ValidationError):
            ModelDodReceipt(**fields)
