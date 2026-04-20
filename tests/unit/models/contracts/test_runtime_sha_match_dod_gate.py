# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TDD tests for runtime_sha_match DoD gate (OMN-9356).

Root cause addressed: tickets marked Done with code on main but runtime
not redeployed (OMN-9321 class, 5-day-stale runtime).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_dod_evidence_check import (
    ModelDodEvidenceCheck,
)
from omnibase_core.models.contracts.ticket.model_dod_evidence_item import (
    ModelDodEvidenceItem,
)
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_runtime_sha_classify_result import (
    ModelRuntimeShaClassifyResult,
)
from omnibase_core.models.contracts.ticket.model_runtime_sha_match_output import (
    ModelRuntimeShaMatchOutput,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.runtime_sha_match import (
    CHECK_TYPE_RUNTIME_SHA_MATCH,
    assert_runtime_sha_receipts_present,
    classify_runtime_sha_match_receipt,
)

pytestmark = pytest.mark.unit

_PROBE_CMD = "ssh jonah@192.168.86.201 git -C /opt/omninode/runtime rev-parse HEAD"  # onex-allow-internal-ip: test fixture only


def _base_receipt(
    *,
    check_type: str = CHECK_TYPE_RUNTIME_SHA_MATCH,
    status: EnumReceiptStatus = EnumReceiptStatus.PASS,
    actual_output: str | None = None,
) -> ModelDodReceipt:
    return ModelDodReceipt(
        ticket_id="OMN-9356",
        evidence_item_id="dod-sha-001",
        check_type=check_type,
        check_value=_PROBE_CMD,
        status=status,
        run_timestamp=datetime.now(tz=UTC),
        commit_sha="a1b2c3d4e5f6",  # pragma: allowlist secret
        runner="integration-sweep-verifier",
        actual_output=actual_output,
    )


def _make_evidence_items(
    check_type: str = CHECK_TYPE_RUNTIME_SHA_MATCH,
) -> list[ModelDodEvidenceItem]:
    return [
        ModelDodEvidenceItem(
            id="dod-sha-001",
            description="Runtime SHA matches merge SHA",
            checks=[
                ModelDodEvidenceCheck(check_type=check_type, check_value=_PROBE_CMD)
            ],
        )
    ]


def _make_output_json(
    *,
    runtime_host: str = "192.168.86.201",  # onex-allow-internal-ip: test fixture only
    deployed_sha: str = "abc123def456",  # pragma: allowlist secret
    merge_sha: str = "abc123def456",  # pragma: allowlist secret
    match: bool = True,
) -> str:
    return json.dumps(
        {
            "runtime_host": runtime_host,
            "deployed_sha": deployed_sha,
            "merge_sha": merge_sha,
            "match": match,
        }
    )


class TestCheckTypeConstant:
    def test_check_type_value(self) -> None:
        assert CHECK_TYPE_RUNTIME_SHA_MATCH == "runtime_sha_match"


class TestModelRuntimeShaMatchOutput:
    def test_valid_matching_sha(self) -> None:
        out = ModelRuntimeShaMatchOutput(
            runtime_host="192.168.86.201",
            deployed_sha="abc123def456",
            merge_sha="abc123def456",
            match=True,
        )
        assert out.match is True

    def test_valid_mismatched_sha(self) -> None:
        out = ModelRuntimeShaMatchOutput(
            runtime_host="192.168.86.201",
            deployed_sha="aaaaaaaaaaaa",
            merge_sha="bbbbbbbbbbbb",
            match=False,
        )
        assert out.match is False

    def test_missing_runtime_host_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelRuntimeShaMatchOutput(
                deployed_sha="abc123",
                merge_sha="abc123",
                match=True,
            )

    def test_missing_deployed_sha_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelRuntimeShaMatchOutput(
                runtime_host="192.168.86.201",
                merge_sha="abc123",
                match=True,
            )

    def test_is_frozen(self) -> None:
        out = ModelRuntimeShaMatchOutput(
            runtime_host="192.168.86.201",
            deployed_sha="abc123",
            merge_sha="abc123",
            match=True,
        )
        with pytest.raises(ValidationError):
            out.match = False  # type: ignore[misc]


class TestModelRuntimeShaClassifyResult:
    def test_constructs_with_required_fields(self) -> None:
        result = ModelRuntimeShaClassifyResult(
            valid=True, blocking=False, reason="PASS"
        )
        assert result.valid is True
        assert result.blocking is False
        assert result.reason == "PASS"

    def test_is_frozen(self) -> None:
        result = ModelRuntimeShaClassifyResult(
            valid=True, blocking=False, reason="PASS"
        )
        with pytest.raises(ValidationError):
            result.blocking = True  # type: ignore[misc]


class TestClassifyRuntimeShaMatchReceipt:
    def test_pass_receipt_with_matching_sha_is_not_blocking(self) -> None:
        receipt = _base_receipt(
            status=EnumReceiptStatus.PASS,
            actual_output=_make_output_json(match=True),
        )
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.valid is True
        assert result.blocking is False

    def test_fail_receipt_is_blocking(self) -> None:
        receipt = _base_receipt(
            status=EnumReceiptStatus.FAIL,
            actual_output=_make_output_json(match=False),
        )
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.valid is True
        assert result.blocking is True

    def test_pass_receipt_with_mismatch_sha_is_blocking(self) -> None:
        """Receipt says PASS but SHA mismatch in actual_output — classifier catches the lie."""
        receipt = _base_receipt(
            status=EnumReceiptStatus.PASS,
            actual_output=_make_output_json(
                deployed_sha="aaaaaaaaaaaa",
                merge_sha="bbbbbbbbbbbb",
                match=False,
            ),
        )
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.blocking is True
        assert "mismatch" in result.reason.lower()

    def test_pass_receipt_with_missing_output_is_blocking(self) -> None:
        receipt = _base_receipt(status=EnumReceiptStatus.PASS, actual_output=None)
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.blocking is True
        assert "actual_output" in result.reason.lower()

    def test_pass_receipt_with_malformed_output_is_blocking(self) -> None:
        receipt = _base_receipt(status=EnumReceiptStatus.PASS, actual_output="not-json")
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.blocking is True

    def test_wrong_check_type_raises_onex_error(self) -> None:
        receipt = _base_receipt(check_type="command")
        with pytest.raises(ModelOnexError):
            classify_runtime_sha_match_receipt(receipt)

    def test_pass_receipt_with_valid_output_reason(self) -> None:
        receipt = _base_receipt(
            status=EnumReceiptStatus.PASS,
            actual_output=_make_output_json(
                deployed_sha="deadbeef1234",  # pragma: allowlist secret
                merge_sha="deadbeef1234",  # pragma: allowlist secret
                match=True,
            ),
        )
        result = classify_runtime_sha_match_receipt(receipt)
        assert result.valid is True
        assert result.blocking is False
        assert result.reason == "PASS: deployed_sha matches merge_sha"


class TestDodGuardBlocksWithoutRuntimeShaReceipt:
    """Guard: a ticket contract with runtime_sha_match evidence cannot close Done without PASS receipt."""

    def test_missing_receipt_raises_on_done_transition(self) -> None:
        with pytest.raises(ModelOnexError):
            assert_runtime_sha_receipts_present(
                ticket_id="OMN-9356",
                evidence_items=_make_evidence_items(),
                receipts=[],
            )

    def test_pass_receipt_clears_guard(self) -> None:
        receipt = ModelDodReceipt(
            ticket_id="OMN-9356",
            evidence_item_id="dod-sha-001",
            check_type="runtime_sha_match",
            check_value=_PROBE_CMD,
            status=EnumReceiptStatus.PASS,
            run_timestamp=datetime.now(tz=UTC),
            commit_sha="abc123def456",  # pragma: allowlist secret
            runner="ci",
            actual_output=_make_output_json(
                deployed_sha="abc123def456",
                merge_sha="abc123def456",
                match=True,
            ),
        )
        # Must not raise
        assert_runtime_sha_receipts_present(
            ticket_id="OMN-9356",
            evidence_items=_make_evidence_items(),
            receipts=[receipt],
        )

    def test_fail_receipt_still_blocks(self) -> None:
        receipt = ModelDodReceipt(
            ticket_id="OMN-9356",
            evidence_item_id="dod-sha-001",
            check_type="runtime_sha_match",
            check_value=_PROBE_CMD,
            status=EnumReceiptStatus.FAIL,
            run_timestamp=datetime.now(tz=UTC),
            commit_sha="abc123def456",  # pragma: allowlist secret
            runner="ci",
            actual_output=_make_output_json(
                deployed_sha="aaaaaaaaaaaa",
                merge_sha="bbbbbbbbbbbb",
                match=False,
            ),
        )
        with pytest.raises(ModelOnexError):
            assert_runtime_sha_receipts_present(
                ticket_id="OMN-9356",
                evidence_items=_make_evidence_items(),
                receipts=[receipt],
            )

    def test_no_sha_evidence_items_does_not_raise(self) -> None:
        items = _make_evidence_items(check_type="command")
        # No runtime_sha_match checks — guard should not block
        assert_runtime_sha_receipts_present(
            ticket_id="OMN-9356",
            evidence_items=items,
            receipts=[],
        )

    def test_duplicate_sha_checks_on_same_item_raises(self) -> None:
        item = ModelDodEvidenceItem(
            id="dod-sha-dup",
            description="Duplicate SHA checks",
            checks=[
                ModelDodEvidenceCheck(
                    check_type=CHECK_TYPE_RUNTIME_SHA_MATCH, check_value=_PROBE_CMD
                ),
                ModelDodEvidenceCheck(
                    check_type=CHECK_TYPE_RUNTIME_SHA_MATCH,
                    check_value=_PROBE_CMD + " --extra",
                ),
            ],
        )
        with pytest.raises(ModelOnexError):
            assert_runtime_sha_receipts_present(
                ticket_id="OMN-9356",
                evidence_items=[item],
                receipts=[],
            )
