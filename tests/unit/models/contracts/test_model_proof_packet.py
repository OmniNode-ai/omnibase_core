# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelProofPacket — per-tier required-field enforcement (OMN-13338)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_proof_tier import EnumProofTier
from omnibase_core.models.contracts.ticket.model_proof_packet import (
    ModelProofPacket,
    required_fields_for_tier,
)


def _l0_fields() -> dict[str, Any]:
    return {"pr_url": "https://github.com/o/r/pull/1", "ci_status": "success"}


def _l1_fields() -> dict[str, Any]:
    return {
        **_l0_fields(),
        "merged_pr_url": "https://github.com/o/r/pull/1",
        "test_evidence": "tests/unit/test_x.py::test_y PASSED",
        "verifier": "ci-reviewer-2026-06-19",
    }


def _l2_fields() -> dict[str, Any]:
    return {
        **_l1_fields(),
        "runtime_sha": "a1b2c3d",
        "image_digest": "sha256:" + "a" * 64,
        "correlation_id": "11880229-aaaa-bbbb-cccc-ddddeeeeffff",
        "terminal_event": "onex.evt.x.completed.v1",
        "projection_ref": "projection_x:row-42",
    }


def _l3_fields() -> dict[str, Any]:
    return {
        **_l2_fields(),
        "dashboard_ref": "omnidash/widget/x",
        "network_evidence": "GET /projection/x -> 200",
        "replay_class": "golden-chain-x",
    }


@pytest.mark.unit
class TestProofPacketPerTierConstruction:
    """Each tier constructs when all its cumulative required fields are present."""

    def test_l0_constructs(self) -> None:
        packet = ModelProofPacket(tier=EnumProofTier.L0, **_l0_fields())
        assert packet.tier is EnumProofTier.L0

    def test_l1_constructs(self) -> None:
        packet = ModelProofPacket(tier=EnumProofTier.L1, **_l1_fields())
        assert packet.tier is EnumProofTier.L1

    def test_l2_constructs(self) -> None:
        packet = ModelProofPacket(tier=EnumProofTier.L2, **_l2_fields())
        assert packet.tier is EnumProofTier.L2

    def test_l3_constructs(self) -> None:
        packet = ModelProofPacket(tier=EnumProofTier.L3, **_l3_fields())
        assert packet.tier is EnumProofTier.L3


@pytest.mark.unit
class TestProofPacketTierUnderEvidenced:
    """A tier claim with a missing required field is rejected."""

    def test_l0_missing_ci_status_rejected(self) -> None:
        fields = _l0_fields()
        del fields["ci_status"]
        with pytest.raises(ValidationError, match="ci_status"):
            ModelProofPacket(tier=EnumProofTier.L0, **fields)

    def test_l1_missing_test_evidence_rejected(self) -> None:
        fields = _l1_fields()
        del fields["test_evidence"]
        with pytest.raises(ValidationError, match="test_evidence"):
            ModelProofPacket(tier=EnumProofTier.L1, **fields)

    def test_l1_missing_verifier_rejected(self) -> None:
        fields = _l1_fields()
        del fields["verifier"]
        with pytest.raises(ValidationError, match="verifier"):
            ModelProofPacket(tier=EnumProofTier.L1, **fields)

    def test_l2_claim_with_only_l0_fields_rejected(self) -> None:
        # The discriminating case: claiming L2 while carrying L0-only evidence.
        with pytest.raises(ValidationError, match="runtime_sha"):
            ModelProofPacket(tier=EnumProofTier.L2, **_l0_fields())

    def test_l3_missing_replay_class_rejected(self) -> None:
        fields = _l3_fields()
        del fields["replay_class"]
        with pytest.raises(ValidationError, match="replay_class"):
            ModelProofPacket(tier=EnumProofTier.L3, **fields)

    def test_blank_string_treated_as_missing(self) -> None:
        fields = _l0_fields()
        fields["ci_status"] = "   "
        with pytest.raises(ValidationError, match="ci_status"):
            ModelProofPacket(tier=EnumProofTier.L0, **fields)


@pytest.mark.unit
class TestProofPacketFieldValidators:
    def test_bad_runtime_sha_rejected(self) -> None:
        fields = _l2_fields()
        fields["runtime_sha"] = "zzz"
        with pytest.raises(ValidationError, match="hex git SHA"):
            ModelProofPacket(tier=EnumProofTier.L2, **fields)

    def test_bad_evidence_ticket_rejected(self) -> None:
        fields = _l1_fields()
        fields["evidence_ticket"] = "PROJ-1"
        with pytest.raises(ValidationError, match="evidence_ticket"):
            ModelProofPacket(tier=EnumProofTier.L1, **fields)

    def test_valid_source_fields_accepted(self) -> None:
        fields = _l1_fields()
        fields["evidence_ticket"] = "OMN-13338"
        fields["evidence_source_sha"] = "deadbeef"
        packet = ModelProofPacket(tier=EnumProofTier.L1, **fields)
        assert packet.evidence_ticket == "OMN-13338"

    def test_packet_is_frozen(self) -> None:
        packet = ModelProofPacket(tier=EnumProofTier.L0, **_l0_fields())
        with pytest.raises(ValidationError):
            packet.tier = EnumProofTier.L1  # type: ignore[misc]

    def test_extra_field_rejected(self) -> None:
        fields = _l0_fields()
        fields["rogue"] = "x"
        with pytest.raises(ValidationError):
            ModelProofPacket(tier=EnumProofTier.L0, **fields)


@pytest.mark.unit
class TestRequiredFieldsForTier:
    def test_l0_required_fields(self) -> None:
        assert required_fields_for_tier(EnumProofTier.L0) == ("pr_url", "ci_status")

    def test_cumulative_growth(self) -> None:
        l0 = set(required_fields_for_tier(EnumProofTier.L0))
        l1 = set(required_fields_for_tier(EnumProofTier.L1))
        l2 = set(required_fields_for_tier(EnumProofTier.L2))
        l3 = set(required_fields_for_tier(EnumProofTier.L3))
        assert l0 < l1 < l2 < l3

    def test_l3_includes_customer_fields(self) -> None:
        l3 = required_fields_for_tier(EnumProofTier.L3)
        assert {"dashboard_ref", "network_evidence", "replay_class"} <= set(l3)
