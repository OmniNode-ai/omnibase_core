# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for tiered resolution routing models."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult
from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints
from omnibase_core.models.routing.model_resolution_route_hop import (
    ModelResolutionRouteHop,
)
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt
from omnibase_core.models.routing.model_tiered_resolution_result import (
    ModelTieredResolutionResult,
)
from omnibase_core.models.routing.model_trust_domain import ModelTrustDomain

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trust_domain(**overrides: object) -> ModelTrustDomain:
    defaults: dict[str, object] = {
        "domain_id": "local.default",
        "tier": EnumResolutionTier.LOCAL_EXACT,
        "trust_root_public_key": "dGVzdC1rZXk=",
        "allowed_capabilities": ["database.*"],
        "policy_bundle_hash": "sha256:abc123",
    }
    defaults.update(overrides)
    return ModelTrustDomain(**defaults)  # type: ignore[arg-type]


def _make_hop_constraints(**overrides: object) -> ModelHopConstraints:
    defaults: dict[str, object] = {}
    defaults.update(overrides)
    return ModelHopConstraints(**defaults)  # type: ignore[arg-type]


def _make_route_hop(**overrides: object) -> ModelResolutionRouteHop:
    defaults: dict[str, object] = {
        "hop_index": 0,
        "adapter_id": "omnibase.adapters.PostgresAdapter",
        "trust_domain": "local.default",
        "tier": EnumResolutionTier.LOCAL_EXACT,
    }
    defaults.update(overrides)
    return ModelResolutionRouteHop(**defaults)  # type: ignore[arg-type]


def _make_tier_attempt(**overrides: object) -> ModelTierAttempt:
    defaults: dict[str, object] = {
        "tier": EnumResolutionTier.LOCAL_EXACT,
        "attempted_at": datetime.now(UTC),
        "candidates_found": 3,
        "candidates_after_trust_filter": 2,
        "duration_ms": 1.5,
    }
    defaults.update(overrides)
    return ModelTierAttempt(**defaults)  # type: ignore[arg-type]


def _make_route_plan(**overrides: object) -> ModelRoutePlan:
    defaults: dict[str, object] = {
        "plan_id": uuid4(),
        "hops": [_make_route_hop()],
        "source_capability": "database.relational",
        "resolved_at": datetime.now(UTC),
        "resolution_tier_used": EnumResolutionTier.LOCAL_EXACT,
        "registry_snapshot_hash": "blake3:abc",
        "policy_bundle_hash": "sha256:def",
        "trust_graph_hash": "sha256:ghi",
    }
    defaults.update(overrides)
    return ModelRoutePlan(**defaults)  # type: ignore[arg-type]


def _make_base_resolution(**overrides: object) -> ModelResolutionResult:
    defaults: dict[str, object] = {
        "success": True,
    }
    defaults.update(overrides)
    return ModelResolutionResult(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# ModelTrustDomain
# ===========================================================================


@pytest.mark.unit
class TestModelTrustDomain:
    """Tests for ModelTrustDomain."""

    def test_create_with_required_fields(self) -> None:
        td = _make_trust_domain()
        assert td.domain_id == "local.default"
        assert td.tier == EnumResolutionTier.LOCAL_EXACT
        assert td.trust_root_public_key == "dGVzdC1rZXk="
        assert td.allowed_capabilities == ["database.*"]
        assert td.policy_bundle_hash == "sha256:abc123"

    def test_frozen(self) -> None:
        td = _make_trust_domain()
        with pytest.raises(ValidationError):
            td.domain_id = "other"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_trust_domain(unknown_field="bad")

    def test_serialization_round_trip(self) -> None:
        td = _make_trust_domain()
        data = td.model_dump()
        restored = ModelTrustDomain.model_validate(data)
        assert restored == td

    def test_json_round_trip(self) -> None:
        td = _make_trust_domain()
        json_str = td.model_dump_json()
        restored = ModelTrustDomain.model_validate_json(json_str)
        assert restored == td

    def test_empty_domain_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_trust_domain(domain_id="")

    def test_empty_trust_root_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_trust_domain(trust_root_public_key="")

    def test_default_allowed_capabilities_empty(self) -> None:
        td = ModelTrustDomain(
            domain_id="local.default",
            tier=EnumResolutionTier.LOCAL_EXACT,
            trust_root_public_key="dGVzdC1rZXk=",
            policy_bundle_hash="sha256:abc",
        )
        assert td.allowed_capabilities == []

    def test_enum_value_validation(self) -> None:
        """Tier field accepts string values for deserialization."""
        td = ModelTrustDomain.model_validate(
            {
                "domain_id": "org.test",
                "tier": "org_trusted",
                "trust_root_public_key": "a2V5",
                "policy_bundle_hash": "sha256:x",
            }
        )
        assert td.tier == EnumResolutionTier.ORG_TRUSTED

    def test_invalid_tier_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelTrustDomain.model_validate(
                {
                    "domain_id": "org.test",
                    "tier": "nonexistent",
                    "trust_root_public_key": "a2V5",
                    "policy_bundle_hash": "sha256:x",
                }
            )


# ===========================================================================
# ModelHopConstraints
# ===========================================================================


@pytest.mark.unit
class TestModelHopConstraints:
    """Tests for ModelHopConstraints."""

    def test_defaults(self) -> None:
        hc = _make_hop_constraints()
        assert hc.ttl_ms is None
        assert hc.require_encryption is False
        assert hc.classification is None
        assert hc.redaction_policy is None

    def test_all_fields(self) -> None:
        hc = _make_hop_constraints(
            ttl_ms=5000,
            require_encryption=True,
            classification="confidential",
            redaction_policy="pii_masked",
        )
        assert hc.ttl_ms == 5000
        assert hc.require_encryption is True
        assert hc.classification == "confidential"
        assert hc.redaction_policy == "pii_masked"

    def test_frozen(self) -> None:
        hc = _make_hop_constraints()
        with pytest.raises(ValidationError):
            hc.ttl_ms = 1000  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_hop_constraints(extra_field="bad")

    def test_serialization_round_trip(self) -> None:
        hc = _make_hop_constraints(
            ttl_ms=3000, require_encryption=True, classification="internal"
        )
        restored = ModelHopConstraints.model_validate(hc.model_dump())
        assert restored == hc

    def test_negative_ttl_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_hop_constraints(ttl_ms=-1)

    def test_zero_ttl_allowed(self) -> None:
        hc = _make_hop_constraints(ttl_ms=0)
        assert hc.ttl_ms == 0


# ===========================================================================
# ModelResolutionRouteHop
# ===========================================================================


@pytest.mark.unit
class TestModelResolutionRouteHop:
    """Tests for ModelResolutionRouteHop."""

    def test_create_with_required_fields(self) -> None:
        hop = _make_route_hop()
        assert hop.hop_index == 0
        assert hop.adapter_id == "omnibase.adapters.PostgresAdapter"
        assert hop.trust_domain == "local.default"
        assert hop.tier == EnumResolutionTier.LOCAL_EXACT
        assert hop.required_proofs == []
        assert hop.constraints == ModelHopConstraints()

    def test_with_proofs_and_constraints(self) -> None:
        constraints = _make_hop_constraints(require_encryption=True)
        hop = _make_route_hop(
            required_proofs=["node_identity", "capability_attested"],
            constraints=constraints,
        )
        assert hop.required_proofs == ["node_identity", "capability_attested"]
        assert hop.constraints.require_encryption is True

    def test_frozen(self) -> None:
        hop = _make_route_hop()
        with pytest.raises(ValidationError):
            hop.hop_index = 99  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_route_hop(surprise="bad")

    def test_serialization_round_trip(self) -> None:
        hop = _make_route_hop(
            hop_index=2,
            required_proofs=["node_identity"],
            constraints=_make_hop_constraints(ttl_ms=1000),
        )
        restored = ModelResolutionRouteHop.model_validate(hop.model_dump())
        assert restored == hop

    def test_negative_hop_index_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_hop(hop_index=-1)

    def test_empty_adapter_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_hop(adapter_id="")

    def test_empty_trust_domain_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_hop(trust_domain="")


# ===========================================================================
# ModelTierAttempt
# ===========================================================================


@pytest.mark.unit
class TestModelTierAttempt:
    """Tests for ModelTierAttempt."""

    def test_create_successful_attempt(self) -> None:
        ta = _make_tier_attempt()
        assert ta.tier == EnumResolutionTier.LOCAL_EXACT
        assert ta.candidates_found == 3
        assert ta.candidates_after_trust_filter == 2
        assert ta.failure_code is None
        assert ta.failure_reason is None
        assert ta.duration_ms == 1.5

    def test_create_failed_attempt(self) -> None:
        ta = _make_tier_attempt(
            failure_code=EnumResolutionFailureCode.NO_MATCH,
            failure_reason="No providers at this tier",
            candidates_found=0,
            candidates_after_trust_filter=0,
        )
        assert ta.failure_code == EnumResolutionFailureCode.NO_MATCH
        assert ta.failure_reason == "No providers at this tier"

    def test_frozen(self) -> None:
        ta = _make_tier_attempt()
        with pytest.raises(ValidationError):
            ta.tier = EnumResolutionTier.QUARANTINE  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_tier_attempt(extra="bad")

    def test_serialization_round_trip(self) -> None:
        ta = _make_tier_attempt(
            failure_code=EnumResolutionFailureCode.POLICY_DENIED,
            failure_reason="Classification gate blocked",
        )
        restored = ModelTierAttempt.model_validate(ta.model_dump())
        assert restored == ta

    def test_json_round_trip(self) -> None:
        ta = _make_tier_attempt()
        restored = ModelTierAttempt.model_validate_json(ta.model_dump_json())
        assert restored == ta

    def test_negative_candidates_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_tier_attempt(candidates_found=-1)

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_tier_attempt(duration_ms=-0.1)

    def test_zero_duration_allowed(self) -> None:
        ta = _make_tier_attempt(duration_ms=0.0)
        assert ta.duration_ms == 0.0

    def test_failure_code_enum_validation(self) -> None:
        """Failure code accepts string values for deserialization."""
        ta = ModelTierAttempt.model_validate(
            {
                "tier": "local_exact",
                "attempted_at": datetime.now(UTC).isoformat(),
                "candidates_found": 0,
                "candidates_after_trust_filter": 0,
                "failure_code": "no_match",
                "duration_ms": 0.5,
            }
        )
        assert ta.failure_code == EnumResolutionFailureCode.NO_MATCH


# ===========================================================================
# ModelRoutePlan
# ===========================================================================


@pytest.mark.unit
class TestModelRoutePlan:
    """Tests for ModelRoutePlan."""

    def test_create_with_required_fields(self) -> None:
        plan = _make_route_plan()
        assert plan.source_capability == "database.relational"
        assert plan.resolution_tier_used == EnumResolutionTier.LOCAL_EXACT
        assert len(plan.hops) == 1
        assert plan.tier_progression == []

    def test_frozen(self) -> None:
        plan = _make_route_plan()
        with pytest.raises(ValidationError):
            plan.source_capability = "other"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_route_plan(bonus="bad")

    def test_empty_hops_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_plan(hops=[])

    def test_serialization_round_trip(self) -> None:
        plan = _make_route_plan(
            tier_progression=[_make_tier_attempt()],
        )
        restored = ModelRoutePlan.model_validate(plan.model_dump())
        assert restored == plan

    def test_json_round_trip(self) -> None:
        plan = _make_route_plan()
        restored = ModelRoutePlan.model_validate_json(plan.model_dump_json())
        assert restored == plan

    def test_multiple_hops(self) -> None:
        hops = [
            _make_route_hop(hop_index=0),
            _make_route_hop(
                hop_index=1,
                adapter_id="omnibase.adapters.CacheAdapter",
                trust_domain="org.omninode",
                tier=EnumResolutionTier.ORG_TRUSTED,
            ),
        ]
        plan = _make_route_plan(hops=hops)
        assert len(plan.hops) == 2
        assert plan.hops[0].hop_index == 0
        assert plan.hops[1].hop_index == 1

    def test_empty_source_capability_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_plan(source_capability="")

    def test_empty_hash_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_route_plan(registry_snapshot_hash="")


# ===========================================================================
# ModelTieredResolutionResult
# ===========================================================================


@pytest.mark.unit
class TestModelTieredResolutionResult:
    """Tests for ModelTieredResolutionResult."""

    def test_create_successful(self) -> None:
        result = ModelTieredResolutionResult(
            route_plan=_make_route_plan(),
            base_resolution=_make_base_resolution(),
            final_tier=EnumResolutionTier.LOCAL_EXACT,
        )
        assert result.route_plan is not None
        assert result.base_resolution.success is True
        assert result.final_tier == EnumResolutionTier.LOCAL_EXACT
        assert result.fail_closed is True
        assert result.structured_failure is None

    def test_create_failed(self) -> None:
        result = ModelTieredResolutionResult(
            base_resolution=_make_base_resolution(success=False),
            tier_progression=[
                _make_tier_attempt(
                    failure_code=EnumResolutionFailureCode.NO_MATCH,
                ),
            ],
            final_tier=EnumResolutionTier.QUARANTINE,
            structured_failure=EnumResolutionFailureCode.TIER_EXHAUSTED,
        )
        assert result.route_plan is None
        assert result.structured_failure == EnumResolutionFailureCode.TIER_EXHAUSTED
        assert result.fail_closed is True

    def test_frozen(self) -> None:
        result = ModelTieredResolutionResult(
            base_resolution=_make_base_resolution(),
        )
        with pytest.raises(ValidationError):
            result.fail_closed = False  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ModelTieredResolutionResult(
                base_resolution=_make_base_resolution(),
                sneaky="bad",  # type: ignore[call-arg]
            )

    def test_serialization_round_trip(self) -> None:
        result = ModelTieredResolutionResult(
            route_plan=_make_route_plan(),
            base_resolution=_make_base_resolution(),
            tier_progression=[_make_tier_attempt()],
            final_tier=EnumResolutionTier.LOCAL_EXACT,
        )
        restored = ModelTieredResolutionResult.model_validate(result.model_dump())
        assert restored == result

    def test_json_round_trip(self) -> None:
        result = ModelTieredResolutionResult(
            base_resolution=_make_base_resolution(),
            final_tier=EnumResolutionTier.ORG_TRUSTED,
            structured_failure=EnumResolutionFailureCode.POLICY_DENIED,
        )
        restored = ModelTieredResolutionResult.model_validate_json(
            result.model_dump_json()
        )
        assert restored == result

    def test_fail_closed_defaults_true(self) -> None:
        result = ModelTieredResolutionResult(
            base_resolution=_make_base_resolution(),
        )
        assert result.fail_closed is True

    def test_defaults(self) -> None:
        result = ModelTieredResolutionResult(
            base_resolution=_make_base_resolution(),
        )
        assert result.route_plan is None
        assert result.tier_progression == []
        assert result.final_tier is None
        assert result.structured_failure is None
