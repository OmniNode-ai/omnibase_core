# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for canonical PR OCC metadata stamp parser/renderer (OMN-14188)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_pr_evidence_source_kind import EnumPrEvidenceSourceKind
from omnibase_core.models.validation.model_pr_occ_metadata_stamp import (
    ModelPrOccMetadataStamp,
)
from omnibase_core.validation.pr_occ_metadata_stamp import (
    parse_pr_occ_metadata_stamp,
    render_pr_occ_metadata_stamp,
)


@pytest.mark.unit
class TestParsePrOccMetadataStamp:
    def test_parses_occ_source_ticket_and_metadata(self) -> None:
        stamp = parse_pr_occ_metadata_stamp(
            "Closes OMN-14188\n\nEvidence-Ticket: OMN-14188\n"
            "Evidence-Source: OCC#3762\n",
            repo="omnibase_core",
            pr_number=1407,
            head_sha="a" * 40,
        )

        assert stamp.repo == "omnibase_core"
        assert stamp.pr_number == 1407
        assert stamp.head_sha == "a" * 40
        assert stamp.evidence_tickets == ("OMN-14188",)
        assert stamp.evidence_source is not None
        assert stamp.evidence_source.kind is EnumPrEvidenceSourceKind.OCC_PR
        assert stamp.evidence_source.occ_pr_number == 3762

    def test_parses_sha_source(self) -> None:
        stamp = parse_pr_occ_metadata_stamp(
            "Evidence-Ticket: OMN-14188\nEvidence-Source: abc1234\n"
        )

        assert stamp.evidence_source is not None
        assert stamp.evidence_source.kind is EnumPrEvidenceSourceKind.COMMIT_SHA
        assert stamp.evidence_source.commit_sha == "abc1234"

    def test_preserves_human_sections_and_marks_stamp_section(self) -> None:
        body = (
            "# Summary\n"
            "Human prose.\n\n"
            "## Evidence\n"
            "Evidence-Ticket: OMN-14188\n"
            "Evidence-Source: OCC#3762\n\n"
            "## Test plan\n"
            "- pytest\n"
        )

        stamp = parse_pr_occ_metadata_stamp(body)

        assert [section.heading for section in stamp.body_sections] == [
            "Summary",
            "Evidence",
            "Test plan",
        ]
        assert [section.is_stamp_section for section in stamp.body_sections] == [
            False,
            True,
            False,
        ]
        assert "".join(section.content for section in stamp.body_sections) == body

    def test_parses_skip_token_allowlist_binding(self) -> None:
        stamp = parse_pr_occ_metadata_stamp(
            "[skip-receipt-gate: appr-123]\n# skip-token-allowed: receipt-456\n"
        )

        assert len(stamp.skip_tokens) == 1
        token = stamp.skip_tokens[0]
        assert token.gate_name == "receipt-gate"
        assert token.reason == "appr-123"
        assert token.allowlist_receipt_id == "receipt-456"

    def test_invalid_evidence_source_is_not_typed_as_source(self) -> None:
        stamp = parse_pr_occ_metadata_stamp("Evidence-Source: OCC# nope\n")

        assert stamp.evidence_source is None
        assert stamp.body_sections[0].is_stamp_section is True


@pytest.mark.unit
class TestRenderPrOccMetadataStamp:
    def test_renders_canonical_block_after_human_body(self) -> None:
        parsed = parse_pr_occ_metadata_stamp("# Summary\nKeep this.\n")
        stamp = ModelPrOccMetadataStamp(
            evidence_tickets=("OMN-14188",),
            evidence_source=parsed.evidence_source,
            body_sections=parsed.body_sections,
        )
        stamp = stamp.model_copy(
            update={
                "evidence_source": {
                    "kind": "occ_pr",
                    "occ_pr_number": 3762,
                }
            }
        )
        stamp = ModelPrOccMetadataStamp.model_validate(stamp.model_dump())

        assert render_pr_occ_metadata_stamp(stamp) == (
            "# Summary\nKeep this.\n\n"
            "Evidence-Ticket: OMN-14188\n"
            "Evidence-Source: OCC#3762\n"
        )

    def test_replaces_existing_stamp_section_idempotently(self) -> None:
        body = (
            "# Summary\n"
            "Keep this.\n\n"
            "## Evidence\n"
            "Evidence-Ticket: OMN-OLD\n"
            "Evidence-Source: OCC#1\n\n"
            "## Test plan\n"
            "- pytest\n"
        )
        stamp = parse_pr_occ_metadata_stamp(body)
        updated = stamp.model_copy(update={"evidence_tickets": ("OMN-14188",)})
        updated = ModelPrOccMetadataStamp.model_validate(
            {
                **updated.model_dump(),
                "evidence_source": {"kind": "occ_pr", "occ_pr_number": 3762},
            }
        )

        rendered = render_pr_occ_metadata_stamp(updated)

        assert "OMN-OLD" not in rendered
        assert rendered == (
            "# Summary\nKeep this.\n\n"
            "## Test plan\n- pytest\n\n"
            "Evidence-Ticket: OMN-14188\n"
            "Evidence-Source: OCC#3762\n"
        )
        assert (
            render_pr_occ_metadata_stamp(parse_pr_occ_metadata_stamp(rendered))
            == rendered
        )

    def test_empty_stamp_preserves_body_verbatim(self) -> None:
        body = "Summary only.\n\n"
        assert render_pr_occ_metadata_stamp(parse_pr_occ_metadata_stamp(body)) == body

    def test_renders_skip_token_with_allowlist(self) -> None:
        stamp = parse_pr_occ_metadata_stamp(
            "Evidence-Ticket: OMN-14188\n"
            "[skip-receipt-gate: appr-123]\n"
            "# skip-token-allowed: receipt-456\n"
        )

        assert render_pr_occ_metadata_stamp(stamp) == (
            "Evidence-Ticket: OMN-14188\n"
            "[skip-receipt-gate: appr-123]\n"
            "# skip-token-allowed: receipt-456\n"
        )
