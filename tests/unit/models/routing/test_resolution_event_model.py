# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelResolutionEvent (Phase 6 resolution event ledger)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_proof_type import EnumProofType
from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
from omnibase_core.models.routing.model_resolution_event import ModelResolutionEvent
from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof
from omnibase_core.models.routing.model_resolution_route_hop import (
    ModelResolutionRouteHop,
)
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NOW = datetime.now(tz=UTC)


def _make_dependency(**overrides: object) -> ModelCapabilityDependency:
    defaults: dict[str, object] = {
        "alias": "db",
        "capability": "database.relational",
    }
    defaults.update(overrides)
    return ModelCapabilityDependency(**defaults)  # type: ignore[arg-type]


def _make_tier_attempt(**overrides: object) -> ModelTierAttempt:
    defaults: dict[str, object] = {
        "tier": EnumResolutionTier.LOCAL_EXACT,
        "attempted_at": _NOW,
        "candidates_found": 3,
        "candidates_after_trust_filter": 1,
        "duration_ms": 1.5,
    }
    defaults.update(overrides)
    return ModelTierAttempt(**defaults)  # type: ignore[arg-type]


def _make_proof(**overrides: object) -> ModelResolutionProof:
    defaults: dict[str, object] = {
        "proof_type": EnumProofType.NODE_IDENTITY,
        "verified": True,
        "verification_notes": "Key matched trust root",
        "verified_at": _NOW,
    }
    defaults.update(overrides)
    return ModelResolutionProof(**defaults)  # type: ignore[arg-type]


def _make_route_plan(**overrides: object) -> ModelRoutePlan:
    hop = ModelResolutionRouteHop(
        hop_index=0,
        adapter_id="adapter-postgres-local",
        trust_domain="local.default",
        tier=EnumResolutionTier.LOCAL_EXACT,
        required_proofs=["node_identity"],
        constraints=ModelHopConstraints(),
    )
    defaults: dict[str, object] = {
        "plan_id": uuid4(),
        "hops": [hop],
        "source_capability": "database.relational",
        "resolved_at": _NOW,
        "resolution_tier_used": EnumResolutionTier.LOCAL_EXACT,
        "registry_snapshot_hash": "blake3:abc123",
        "policy_bundle_hash": "sha256:def456",
        "trust_graph_hash": "sha256:ghi789",
    }
    defaults.update(overrides)
    return ModelRoutePlan(**defaults)  # type: ignore[arg-type]


def _make_success_event(**overrides: object) -> ModelResolutionEvent:
    defaults: dict[str, object] = {
        "event_id": uuid4(),
        "timestamp": _NOW,
        "dependency": _make_dependency(),
        "registry_snapshot_hash": "blake3:abc123",
        "policy_bundle_hash": "sha256:def456",
        "trust_graph_hash": "sha256:ghi789",
        "route_plan": _make_route_plan(),
        "tier_progression": [_make_tier_attempt()],
        "proofs_attempted": [_make_proof()],
        "success": True,
    }
    defaults.update(overrides)
    return ModelResolutionEvent(**defaults)  # type: ignore[arg-type]


def _make_failure_event(**overrides: object) -> ModelResolutionEvent:
    defaults: dict[str, object] = {
        "event_id": uuid4(),
        "timestamp": _NOW,
        "dependency": _make_dependency(),
        "registry_snapshot_hash": "blake3:abc123",
        "policy_bundle_hash": "sha256:def456",
        "trust_graph_hash": "sha256:ghi789",
        "route_plan": None,
        "tier_progression": [
            _make_tier_attempt(
                failure_code=EnumResolutionFailureCode.NO_MATCH,
                failure_reason="No providers at local_exact tier",
            ),
            _make_tier_attempt(
                tier=EnumResolutionTier.ORG_TRUSTED,
                failure_code=EnumResolutionFailureCode.TIER_EXHAUSTED,
                failure_reason="All tiers exhausted",
            ),
        ],
        "proofs_attempted": [],
        "success": False,
        "failure_code": EnumResolutionFailureCode.TIER_EXHAUSTED,
        "failure_reason": "All configured tiers exhausted without resolution",
    }
    defaults.update(overrides)
    return ModelResolutionEvent(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# ModelResolutionEvent
# ===========================================================================


@pytest.mark.unit
class TestModelResolutionEventFrozen:
    """Frozen enforcement tests."""

    def test_frozen_event_id(self) -> None:
        event = _make_success_event()
        with pytest.raises(ValidationError):
            event.event_id = uuid4()  # type: ignore[misc]

    def test_frozen_success(self) -> None:
        event = _make_success_event()
        with pytest.raises(ValidationError):
            event.success = False  # type: ignore[misc]

    def test_frozen_timestamp(self) -> None:
        event = _make_success_event()
        with pytest.raises(ValidationError):
            event.timestamp = _NOW  # type: ignore[misc]

    def test_frozen_failure_code(self) -> None:
        event = _make_failure_event()
        with pytest.raises(ValidationError):
            event.failure_code = None  # type: ignore[misc]


@pytest.mark.unit
class TestModelResolutionEventExtraForbid:
    """extra='forbid' enforcement tests."""

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_success_event(bonus_field="bad")

    def test_unknown_kwarg_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_failure_event(metadata={"key": "val"})


@pytest.mark.unit
class TestModelResolutionEventSerialization:
    """Serialization round-trip tests."""

    def test_model_dump_round_trip_success(self) -> None:
        event = _make_success_event()
        data = event.model_dump()
        restored = ModelResolutionEvent.model_validate(data)
        assert restored == event

    def test_model_dump_round_trip_failure(self) -> None:
        event = _make_failure_event()
        data = event.model_dump()
        restored = ModelResolutionEvent.model_validate(data)
        assert restored == event

    def test_json_round_trip_success(self) -> None:
        event = _make_success_event()
        json_str = event.model_dump_json()
        restored = ModelResolutionEvent.model_validate_json(json_str)
        assert restored == event

    def test_json_round_trip_failure(self) -> None:
        event = _make_failure_event()
        json_str = event.model_dump_json()
        restored = ModelResolutionEvent.model_validate_json(json_str)
        assert restored == event

    def test_datetime_serializes_to_iso_format(self) -> None:
        event = _make_success_event()
        data = event.model_dump(mode="json")
        # Pydantic serializes datetime as ISO 8601 string in JSON mode
        assert isinstance(data["timestamp"], str)
        # Should be parseable back
        parsed = datetime.fromisoformat(data["timestamp"])
        assert parsed == event.timestamp


@pytest.mark.unit
class TestModelResolutionEventSuccess:
    """Tests for successful resolution events."""

    def test_success_event_has_route_plan(self) -> None:
        event = _make_success_event()
        assert event.success is True
        assert event.route_plan is not None
        assert event.failure_code is None
        assert event.failure_reason is None

    def test_success_event_has_dependency(self) -> None:
        event = _make_success_event()
        assert event.dependency.alias == "db"
        assert event.dependency.capability == "database.relational"

    def test_success_event_has_hashes(self) -> None:
        event = _make_success_event()
        assert event.registry_snapshot_hash == "blake3:abc123"
        assert event.policy_bundle_hash == "sha256:def456"
        assert event.trust_graph_hash == "sha256:ghi789"

    def test_success_event_has_tier_progression(self) -> None:
        event = _make_success_event()
        assert len(event.tier_progression) == 1
        assert event.tier_progression[0].tier == EnumResolutionTier.LOCAL_EXACT

    def test_success_event_has_proofs(self) -> None:
        event = _make_success_event()
        assert len(event.proofs_attempted) == 1
        assert event.proofs_attempted[0].verified is True

    def test_success_event_with_empty_proofs(self) -> None:
        event = _make_success_event(proofs_attempted=[])
        assert event.success is True
        assert event.proofs_attempted == []

    def test_success_event_with_multiple_tier_attempts(self) -> None:
        attempts = [
            _make_tier_attempt(
                tier=EnumResolutionTier.LOCAL_EXACT,
                candidates_found=0,
                candidates_after_trust_filter=0,
                failure_code=EnumResolutionFailureCode.NO_MATCH,
                failure_reason="No providers at local_exact",
            ),
            _make_tier_attempt(
                tier=EnumResolutionTier.LOCAL_COMPATIBLE,
                candidates_found=2,
                candidates_after_trust_filter=1,
            ),
        ]
        event = _make_success_event(tier_progression=attempts)
        assert len(event.tier_progression) == 2
        assert (
            event.tier_progression[0].failure_code == EnumResolutionFailureCode.NO_MATCH
        )
        assert event.tier_progression[1].failure_code is None


@pytest.mark.unit
class TestModelResolutionEventFailure:
    """Tests for failed resolution events."""

    def test_failure_event_no_route_plan(self) -> None:
        event = _make_failure_event()
        assert event.success is False
        assert event.route_plan is None
        assert event.failure_code == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert event.failure_reason is not None

    def test_failure_event_has_tier_progression(self) -> None:
        event = _make_failure_event()
        assert len(event.tier_progression) == 2

    def test_failure_event_empty_proofs(self) -> None:
        event = _make_failure_event()
        assert event.proofs_attempted == []

    def test_failure_with_attestation_invalid(self) -> None:
        event = _make_failure_event(
            failure_code=EnumResolutionFailureCode.ATTESTATION_INVALID,
            failure_reason="Token signature verification failed",
        )
        assert event.failure_code == EnumResolutionFailureCode.ATTESTATION_INVALID

    def test_failure_with_policy_denied(self) -> None:
        event = _make_failure_event(
            failure_code=EnumResolutionFailureCode.POLICY_DENIED,
            failure_reason="Classification gate blocked federated tier",
        )
        assert event.failure_code == EnumResolutionFailureCode.POLICY_DENIED

    def test_all_failure_codes_accepted(self) -> None:
        for code in EnumResolutionFailureCode:
            event = _make_failure_event(
                failure_code=code,
                failure_reason=f"Failed with {code.value}",
            )
            assert event.failure_code is code


@pytest.mark.unit
class TestModelResolutionEventValidation:
    """Validation and edge-case tests."""

    def test_empty_registry_snapshot_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_success_event(registry_snapshot_hash="")

    def test_empty_policy_bundle_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_success_event(policy_bundle_hash="")

    def test_empty_trust_graph_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_success_event(trust_graph_hash="")

    def test_default_lists_are_empty(self) -> None:
        event = ModelResolutionEvent(
            event_id=uuid4(),
            timestamp=_NOW,
            dependency=_make_dependency(),
            registry_snapshot_hash="blake3:abc",
            policy_bundle_hash="sha256:def",
            trust_graph_hash="sha256:ghi",
            success=True,
        )
        assert event.tier_progression == []
        assert event.proofs_attempted == []

    def test_default_optional_fields_are_none(self) -> None:
        event = ModelResolutionEvent(
            event_id=uuid4(),
            timestamp=_NOW,
            dependency=_make_dependency(),
            registry_snapshot_hash="blake3:abc",
            policy_bundle_hash="sha256:def",
            trust_graph_hash="sha256:ghi",
            success=False,
        )
        assert event.route_plan is None
        assert event.failure_code is None
        assert event.failure_reason is None

    def test_from_attributes_enabled(self) -> None:
        """Verify from_attributes=True for pytest-xdist compatibility."""
        assert ModelResolutionEvent.model_config.get("from_attributes") is True
