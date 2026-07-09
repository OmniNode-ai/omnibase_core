# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPrOccMetadataStamp (OMN-14187)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind
from omnibase_core.models.validation.model_pr_body_section import ModelPrBodySection
from omnibase_core.models.validation.model_pr_evidence_source import (
    ModelPrEvidenceSource,
)
from omnibase_core.models.validation.model_pr_occ_metadata_stamp import (
    ModelPrOccMetadataStamp,
)
from omnibase_core.models.validation.model_pr_receipt_gate_skip_token import (
    ModelPrReceiptGateSkipToken,
)

_VALID_SHA_40 = "a" * 40


@pytest.mark.unit
class TestModelPrOccMetadataStampTickets:
    def test_ticket_order_preserved_not_sorted(self) -> None:
        stamp = ModelPrOccMetadataStamp(
            evidence_tickets=("OMN-456", "OMN-123"),
        )
        # Order preserved as given (NOT sorted to OMN-123, OMN-456).
        assert stamp.evidence_tickets == ("OMN-456", "OMN-123")
        assert stamp.model_dump()["evidence_tickets"] == ("OMN-456", "OMN-123")

    def test_ticket_dedupe_preserves_first_occurrence(self) -> None:
        stamp = ModelPrOccMetadataStamp(
            evidence_tickets=("OMN-123", "OMN-456", "OMN-123"),
        )
        assert stamp.evidence_tickets == ("OMN-123", "OMN-456")

    def test_ticket_case_normalized(self) -> None:
        stamp = ModelPrOccMetadataStamp(evidence_tickets=("omn-123", "OMN-123"))
        # Case-normalized then de-duped -> a single canonical entry.
        assert stamp.evidence_tickets == ("OMN-123",)

    @pytest.mark.parametrize("bad_ticket", ["JIRA-123", "OMN-abc", "omn123"])
    def test_malformed_ticket_raises(self, bad_ticket: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelPrOccMetadataStamp(evidence_tickets=(bad_ticket,))
        assert "OMN-<n>" in str(exc_info.value)

    def test_bare_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrOccMetadataStamp(evidence_tickets="OMN-123")  # type: ignore[arg-type]

    def test_empty_tickets_default(self) -> None:
        stamp = ModelPrOccMetadataStamp()
        assert stamp.evidence_tickets == ()


@pytest.mark.unit
class TestModelPrOccMetadataStampFields:
    def test_defaults(self) -> None:
        stamp = ModelPrOccMetadataStamp()
        assert stamp.repo == ""
        assert stamp.pr_number is None
        assert stamp.head_sha is None
        assert stamp.evidence_source is None
        assert stamp.evidence_tickets == ()
        assert stamp.skip_tokens == ()
        assert stamp.body_sections == ()

    def test_pr_number_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrOccMetadataStamp(pr_number=0)

    def test_invalid_head_sha_raises(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrOccMetadataStamp(head_sha="not-a-sha")

    def test_valid_head_sha(self) -> None:
        stamp = ModelPrOccMetadataStamp(head_sha=_VALID_SHA_40)
        assert stamp.head_sha == _VALID_SHA_40

    def test_frozen_attribute_mutation_raises(self) -> None:
        stamp = ModelPrOccMetadataStamp(repo="omnibase_core")
        with pytest.raises(ValidationError):
            stamp.repo = "other"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrOccMetadataStamp(unexpected="x")  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelPrOccMetadataStampComposition:
    @staticmethod
    def _full_stamp() -> ModelPrOccMetadataStamp:
        return ModelPrOccMetadataStamp(
            repo="omnibase_core",
            pr_number=1774,
            head_sha=_VALID_SHA_40,
            evidence_source=ModelPrEvidenceSource(
                kind=EnumPrEvidenceSourceKind.OCC_PR, occ_pr_number=42
            ),
            evidence_tickets=("OMN-14187", "OMN-14180"),
            skip_tokens=(
                ModelPrReceiptGateSkipToken(gate_name="receipt-gate", reason="r"),
            ),
            body_sections=(
                ModelPrBodySection(heading=None, content="intro\n"),
                ModelPrBodySection(
                    heading="Evidence-Source",
                    content="Evidence-Source: OCC#42\n",
                    is_stamp_section=True,
                ),
            ),
        )

    def test_nested_roundtrip_model_dump(self) -> None:
        stamp = self._full_stamp()
        restored = ModelPrOccMetadataStamp.model_validate(stamp.model_dump())
        assert restored == stamp

    def test_nested_roundtrip_model_dump_json(self) -> None:
        stamp = self._full_stamp()
        restored = ModelPrOccMetadataStamp.model_validate_json(stamp.model_dump_json())
        assert restored == stamp

    def test_as_dict_ticket_order_preserved(self) -> None:
        stamp = self._full_stamp()
        assert stamp.as_dict()["evidence_tickets"] == ["OMN-14187", "OMN-14180"]

    def test_to_json_deterministic_byte_identical(self) -> None:
        stamp = self._full_stamp()
        assert stamp.to_json() == stamp.to_json()

    def test_to_json_is_sorted_keys(self) -> None:
        stamp = self._full_stamp()
        payload = stamp.to_json()
        # sort_keys=True => top-level keys emitted in sorted order.
        parsed = json.loads(payload)
        assert list(parsed.keys()) == sorted(parsed.keys())
        # Nested evidence_source composed cleanly.
        assert parsed["evidence_source"]["kind"] == "occ_pr"
