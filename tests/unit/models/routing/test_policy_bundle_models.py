# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 4 routing models: classification gates, redaction policies, policy bundles."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_classification import EnumClassification
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.routing.model_classification_gate import (
    ModelClassificationGate,
)
from omnibase_core.models.routing.model_policy_bundle import ModelPolicyBundle
from omnibase_core.models.routing.model_redaction_policy import ModelRedactionPolicy
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_trust_policy(**overrides: object) -> ModelTrustPolicy:
    defaults: dict[str, object] = {
        "name": "Test Policy",
        "version": "1.0.0",
        "created_by": "test-suite",
    }
    defaults.update(overrides)
    return ModelTrustPolicy(**defaults)  # type: ignore[arg-type]


def _make_classification_gate(**overrides: object) -> ModelClassificationGate:
    defaults: dict[str, object] = {
        "classification": EnumClassification.INTERNAL,
        "allowed_tiers": [
            EnumResolutionTier.LOCAL_EXACT,
            EnumResolutionTier.LOCAL_COMPATIBLE,
        ],
        "require_encryption": False,
        "require_redaction": False,
    }
    defaults.update(overrides)
    return ModelClassificationGate(**defaults)  # type: ignore[arg-type]


def _make_redaction_policy(**overrides: object) -> ModelRedactionPolicy:
    defaults: dict[str, object] = {
        "policy_name": "pii_masked",
        "rules": {"*.email": "mask", "*.ssn": "hash"},
    }
    defaults.update(overrides)
    return ModelRedactionPolicy(**defaults)  # type: ignore[arg-type]


def _make_policy_bundle(**overrides: object) -> ModelPolicyBundle:
    defaults: dict[str, object] = {
        "bundle_id": uuid4(),
        "trust_policy": _make_trust_policy(),
        "classification_gates": [_make_classification_gate()],
        "redaction_policies": [_make_redaction_policy()],
        "version": "1.0.0",
    }
    defaults.update(overrides)
    return ModelPolicyBundle(**defaults)  # type: ignore[arg-type]


# ===========================================================================
# EnumClassification
# ===========================================================================


@pytest.mark.unit
class TestEnumClassification:
    """Tests for EnumClassification."""

    def test_all_values_present(self) -> None:
        assert EnumClassification.PUBLIC.value == "public"
        assert EnumClassification.INTERNAL.value == "internal"
        assert EnumClassification.CONFIDENTIAL.value == "confidential"
        assert EnumClassification.RESTRICTED.value == "restricted"

    def test_member_count(self) -> None:
        assert len(EnumClassification) == 4

    def test_str_returns_value(self) -> None:
        assert str(EnumClassification.PUBLIC) == "public"
        assert str(EnumClassification.RESTRICTED) == "restricted"

    def test_lookup_by_value(self) -> None:
        assert EnumClassification("public") is EnumClassification.PUBLIC
        assert EnumClassification("restricted") is EnumClassification.RESTRICTED

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumClassification("top_secret")

    def test_unique_values(self) -> None:
        values = [m.value for m in EnumClassification]
        assert len(values) == len(set(values))

    def test_is_string_subclass(self) -> None:
        assert isinstance(EnumClassification.PUBLIC, str)


# ===========================================================================
# ModelClassificationGate
# ===========================================================================


@pytest.mark.unit
class TestModelClassificationGate:
    """Tests for ModelClassificationGate."""

    def test_create_with_required_fields(self) -> None:
        gate = _make_classification_gate()
        assert gate.classification == EnumClassification.INTERNAL
        assert EnumResolutionTier.LOCAL_EXACT in gate.allowed_tiers
        assert EnumResolutionTier.LOCAL_COMPATIBLE in gate.allowed_tiers
        assert gate.require_encryption is False
        assert gate.require_redaction is False
        assert gate.redaction_policy is None

    def test_all_fields(self) -> None:
        gate = _make_classification_gate(
            classification=EnumClassification.CONFIDENTIAL,
            allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
            require_encryption=True,
            require_redaction=True,
            redaction_policy="pii_masked",
        )
        assert gate.classification == EnumClassification.CONFIDENTIAL
        assert gate.allowed_tiers == [EnumResolutionTier.LOCAL_EXACT]
        assert gate.require_encryption is True
        assert gate.require_redaction is True
        assert gate.redaction_policy == "pii_masked"

    def test_frozen(self) -> None:
        gate = _make_classification_gate()
        with pytest.raises(ValidationError):
            gate.classification = EnumClassification.PUBLIC  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_classification_gate(bonus_field="bad")

    def test_serialization_round_trip(self) -> None:
        gate = _make_classification_gate(
            classification=EnumClassification.RESTRICTED,
            allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
            require_encryption=True,
        )
        data = gate.model_dump()
        restored = ModelClassificationGate.model_validate(data)
        assert restored == gate

    def test_json_round_trip(self) -> None:
        gate = _make_classification_gate()
        json_str = gate.model_dump_json()
        restored = ModelClassificationGate.model_validate_json(json_str)
        assert restored == gate

    def test_default_allowed_tiers_empty(self) -> None:
        gate = ModelClassificationGate(
            classification=EnumClassification.PUBLIC,
        )
        assert gate.allowed_tiers == []

    def test_enum_string_deserialization(self) -> None:
        gate = ModelClassificationGate.model_validate(
            {
                "classification": "confidential",
                "allowed_tiers": ["local_exact"],
            }
        )
        assert gate.classification == EnumClassification.CONFIDENTIAL
        assert gate.allowed_tiers == [EnumResolutionTier.LOCAL_EXACT]

    def test_invalid_classification_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelClassificationGate.model_validate({"classification": "top_secret"})

    def test_invalid_tier_in_allowed_tiers_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelClassificationGate.model_validate(
                {
                    "classification": "internal",
                    "allowed_tiers": ["nonexistent_tier"],
                }
            )


# ===========================================================================
# ModelRedactionPolicy
# ===========================================================================


@pytest.mark.unit
class TestModelRedactionPolicy:
    """Tests for ModelRedactionPolicy."""

    def test_create_with_required_fields(self) -> None:
        policy = _make_redaction_policy()
        assert policy.policy_name == "pii_masked"
        assert policy.rules == {"*.email": "mask", "*.ssn": "hash"}

    def test_frozen(self) -> None:
        policy = _make_redaction_policy()
        with pytest.raises(ValidationError):
            policy.policy_name = "other"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_redaction_policy(extra_field="bad")

    def test_serialization_round_trip(self) -> None:
        policy = _make_redaction_policy()
        data = policy.model_dump()
        restored = ModelRedactionPolicy.model_validate(data)
        assert restored == policy

    def test_json_round_trip(self) -> None:
        policy = _make_redaction_policy()
        json_str = policy.model_dump_json()
        restored = ModelRedactionPolicy.model_validate_json(json_str)
        assert restored == policy

    def test_empty_policy_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_redaction_policy(policy_name="")

    def test_empty_rules_allowed(self) -> None:
        policy = ModelRedactionPolicy(policy_name="no_rules")
        assert policy.rules == {}

    def test_single_rule(self) -> None:
        policy = _make_redaction_policy(rules={"*.phone": "remove"})
        assert policy.rules == {"*.phone": "remove"}


# ===========================================================================
# ModelPolicyBundle
# ===========================================================================


@pytest.mark.unit
class TestModelPolicyBundle:
    """Tests for ModelPolicyBundle."""

    def test_create_with_required_fields(self) -> None:
        bundle = _make_policy_bundle()
        assert bundle.trust_policy.name == "Test Policy"
        assert len(bundle.classification_gates) == 1
        assert len(bundle.redaction_policies) == 1
        assert bundle.version == "1.0.0"

    def test_frozen(self) -> None:
        bundle = _make_policy_bundle()
        with pytest.raises(ValidationError):
            bundle.version = "2.0.0"  # type: ignore[misc]

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            _make_policy_bundle(sneaky="bad")

    def test_serialization_round_trip(self) -> None:
        bundle = _make_policy_bundle()
        data = bundle.model_dump()
        restored = ModelPolicyBundle.model_validate(data)
        assert restored == bundle

    def test_json_round_trip(self) -> None:
        bundle = _make_policy_bundle()
        json_str = bundle.model_dump_json()
        restored = ModelPolicyBundle.model_validate_json(json_str)
        assert restored == bundle

    def test_compute_hash_determinism(self) -> None:
        """Same bundle contents always produce the same hash."""
        bundle = _make_policy_bundle()

        hash1 = bundle.compute_hash()
        hash2 = bundle.compute_hash()

        assert hash1 == hash2
        assert hash1.startswith("sha256:")

    def test_compute_hash_changes_with_content(self) -> None:
        """Different bundle contents produce different hashes."""
        bundle1 = _make_policy_bundle(version="1.0.0")
        bundle2 = _make_policy_bundle(version="2.0.0")

        assert bundle1.compute_hash() != bundle2.compute_hash()

    def test_compute_hash_format(self) -> None:
        bundle = _make_policy_bundle()
        h = bundle.compute_hash()
        assert h.startswith("sha256:")
        # SHA-256 hex digest is 64 characters
        assert len(h.split(":")[1]) == 64

    def test_empty_gates_and_policies(self) -> None:
        bundle = _make_policy_bundle(
            classification_gates=[],
            redaction_policies=[],
        )
        assert bundle.classification_gates == []
        assert bundle.redaction_policies == []
        assert bundle.compute_hash().startswith("sha256:")

    def test_empty_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_policy_bundle(version="")

    def test_multiple_gates(self) -> None:
        gates = [
            _make_classification_gate(classification=EnumClassification.PUBLIC),
            _make_classification_gate(
                classification=EnumClassification.RESTRICTED,
                allowed_tiers=[EnumResolutionTier.LOCAL_EXACT],
                require_encryption=True,
            ),
        ]
        bundle = _make_policy_bundle(classification_gates=gates)
        assert len(bundle.classification_gates) == 2

    def test_multiple_redaction_policies(self) -> None:
        policies = [
            _make_redaction_policy(policy_name="pii_masked"),
            _make_redaction_policy(
                policy_name="full_redact",
                rules={"*": "remove"},
            ),
        ]
        bundle = _make_policy_bundle(redaction_policies=policies)
        assert len(bundle.redaction_policies) == 2

    def test_default_bundle_id_generated(self) -> None:
        bundle = ModelPolicyBundle(
            trust_policy=_make_trust_policy(),
            version="1.0.0",
        )
        assert bundle.bundle_id is not None
