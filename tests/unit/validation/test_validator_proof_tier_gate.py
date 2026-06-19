# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the proof-tier gate — reject receipts below required tier (OMN-13338)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.enums.ticket.enum_ticket_class import EnumTicketClass
from omnibase_core.models.contracts.ticket.model_dod_receipt import ModelDodReceipt
from omnibase_core.models.contracts.ticket.model_proof_packet import ModelProofPacket
from omnibase_core.validation.validator_proof_tier_gate import evaluate_proof_tier


def _receipt(packet: ModelProofPacket | None) -> ModelDodReceipt:
    fields: dict[str, Any] = {
        "schema_version": "1.0.0",
        "ticket_id": "OMN-13338",
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "gh pr view --json state -q .state",
        "status": EnumReceiptStatus.PASS,
        "run_timestamp": datetime.now(tz=UTC),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "ci-receipt-gate",
        "verifier": "foreground-receipt-gate-2026-06-19",
        "probe_command": "gh pr view --json state -q .state",
        "probe_stdout": "OPEN\n",
        "proof_packet": packet,
    }
    return ModelDodReceipt(**fields)


def _packet(tier: EnumProofTier) -> ModelProofPacket:
    base: dict[str, Any] = {
        "pr_url": "https://github.com/o/r/pull/1",
        "ci_status": "success",
    }
    if tier.rank >= EnumProofTier.L1.rank:
        base |= {
            "merged_pr_url": "https://github.com/o/r/pull/1",
            "test_evidence": "tests/x.py::test PASSED",
            "verifier": "ci-reviewer",
        }
    if tier.rank >= EnumProofTier.L2.rank:
        base |= {
            "runtime_sha": "a1b2c3d",
            "image_digest": "sha256:" + "a" * 64,
            "correlation_id": "11880229-aaaa-bbbb-cccc-ddddeeeeffff",
            "terminal_event": "onex.evt.x.completed.v1",
            "projection_ref": "projection_x:row-42",
        }
    if tier.rank >= EnumProofTier.L3.rank:
        base |= {
            "dashboard_ref": "omnidash/widget/x",
            "network_evidence": "GET /projection/x -> 200",
            "replay_class": "golden-chain-x",
        }
    return ModelProofPacket(tier=tier, **base)


@pytest.mark.unit
class TestProofTierGatePassesAtOrAbove:
    @pytest.mark.parametrize(
        ("ticket_class", "tier"),
        [
            (EnumTicketClass.DOCS, EnumProofTier.L0),
            (EnumTicketClass.CODE, EnumProofTier.L1),
            (EnumTicketClass.RUNTIME, EnumProofTier.L2),
            (EnumTicketClass.CUSTOMER, EnumProofTier.L3),
        ],
    )
    def test_exact_tier_passes(
        self, ticket_class: EnumTicketClass, tier: EnumProofTier
    ) -> None:
        result = evaluate_proof_tier(_receipt(_packet(tier)), ticket_class)
        assert result.passed
        assert result.actual_tier is tier

    def test_higher_tier_passes(self) -> None:
        # An L3 packet satisfies a RUNTIME (L2) requirement.
        result = evaluate_proof_tier(
            _receipt(_packet(EnumProofTier.L3)), EnumTicketClass.RUNTIME
        )
        assert result.passed


@pytest.mark.unit
class TestProofTierGateRejectsBelow:
    @pytest.mark.parametrize(
        ("ticket_class", "tier"),
        [
            (EnumTicketClass.CODE, EnumProofTier.L0),
            (EnumTicketClass.RUNTIME, EnumProofTier.L1),
            (EnumTicketClass.CUSTOMER, EnumProofTier.L2),
        ],
    )
    def test_below_required_rejected(
        self, ticket_class: EnumTicketClass, tier: EnumProofTier
    ) -> None:
        result = evaluate_proof_tier(_receipt(_packet(tier)), ticket_class)
        assert not result.passed
        assert "PROOF TIER GATE FAILED" in result.reason
        assert result.required_tier is ticket_class.required_tier
        assert result.actual_tier is tier


@pytest.mark.unit
class TestProofTierGateMissingPacket:
    def test_missing_packet_docs_passes_at_floor(self) -> None:
        result = evaluate_proof_tier(_receipt(None), EnumTicketClass.DOCS)
        assert result.passed
        assert result.actual_tier is None

    @pytest.mark.parametrize(
        "ticket_class",
        [EnumTicketClass.CODE, EnumTicketClass.RUNTIME, EnumTicketClass.CUSTOMER],
    )
    def test_missing_packet_above_floor_rejected(
        self, ticket_class: EnumTicketClass
    ) -> None:
        result = evaluate_proof_tier(_receipt(None), ticket_class)
        assert not result.passed
        assert "no proof_packet" in result.reason
        assert result.actual_tier is None
