# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Phase 7 contract YAML schema extensions (OMN-2896).

Tests ModelTieredResolutionConfig, ModelTrustDomainConfig, and their
integration with ModelCapabilityDependency and ModelHandlerContract.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.contracts.model_contract_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.routing.model_tiered_resolution_config import (
    ModelTieredResolutionConfig,
)
from omnibase_core.models.routing.model_trust_domain_config import (
    ModelTrustDomainConfig,
)
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior

# ===========================================================================
# ModelTieredResolutionConfig
# ===========================================================================


@pytest.mark.unit
class TestModelTieredResolutionConfigFrozen:
    """Frozen enforcement tests."""

    def test_frozen_min_tier(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
        )
        with pytest.raises(ValidationError):
            config.min_tier = EnumResolutionTier.ORG_TRUSTED  # type: ignore[misc]

    def test_frozen_max_tier(self) -> None:
        config = ModelTieredResolutionConfig(
            max_tier=EnumResolutionTier.ORG_TRUSTED,
        )
        with pytest.raises(ValidationError):
            config.max_tier = EnumResolutionTier.QUARANTINE  # type: ignore[misc]

    def test_frozen_require_proofs(self) -> None:
        config = ModelTieredResolutionConfig(
            require_proofs=["node_identity"],
        )
        with pytest.raises(ValidationError):
            config.require_proofs = []  # type: ignore[misc]

    def test_frozen_classification(self) -> None:
        config = ModelTieredResolutionConfig(
            classification="internal",
        )
        with pytest.raises(ValidationError):
            config.classification = "public"  # type: ignore[misc]


@pytest.mark.unit
class TestModelTieredResolutionConfigExtraForbid:
    """extra='forbid' enforcement tests."""

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ModelTieredResolutionConfig(
                bonus_field="bad",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelTieredResolutionConfigDefaults:
    """All-None defaults work correctly."""

    def test_all_defaults(self) -> None:
        config = ModelTieredResolutionConfig()
        assert config.min_tier is None
        assert config.max_tier is None
        assert config.require_proofs == []
        assert config.classification is None

    def test_partial_fields(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
        )
        assert config.min_tier == EnumResolutionTier.LOCAL_EXACT
        assert config.max_tier is None
        assert config.require_proofs == []
        assert config.classification is None


@pytest.mark.unit
class TestModelTieredResolutionConfigSerialization:
    """Serialization round-trip tests."""

    def test_model_dump_round_trip(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
            max_tier=EnumResolutionTier.ORG_TRUSTED,
            require_proofs=["node_identity", "capability_attested"],
            classification="internal",
        )
        data = config.model_dump()
        restored = ModelTieredResolutionConfig.model_validate(data)
        assert restored == config

    def test_json_round_trip(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_COMPATIBLE,
            max_tier=EnumResolutionTier.FEDERATED_TRUSTED,
            require_proofs=["org_membership"],
            classification="confidential",
        )
        json_str = config.model_dump_json()
        restored = ModelTieredResolutionConfig.model_validate_json(json_str)
        assert restored == config

    def test_empty_config_round_trip(self) -> None:
        config = ModelTieredResolutionConfig()
        data = config.model_dump()
        restored = ModelTieredResolutionConfig.model_validate(data)
        assert restored == config

    def test_from_attributes_enabled(self) -> None:
        assert ModelTieredResolutionConfig.model_config.get("from_attributes") is True


@pytest.mark.unit
class TestModelTieredResolutionConfigEnumValues:
    """Enum field validation tests."""

    def test_all_resolution_tiers_accepted_as_min(self) -> None:
        for tier in EnumResolutionTier:
            config = ModelTieredResolutionConfig(min_tier=tier)
            assert config.min_tier is tier

    def test_all_resolution_tiers_accepted_as_max(self) -> None:
        for tier in EnumResolutionTier:
            config = ModelTieredResolutionConfig(max_tier=tier)
            assert config.max_tier is tier

    def test_string_tier_values_accepted(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier="local_exact",  # type: ignore[arg-type]
            max_tier="org_trusted",  # type: ignore[arg-type]
        )
        assert config.min_tier == EnumResolutionTier.LOCAL_EXACT
        assert config.max_tier == EnumResolutionTier.ORG_TRUSTED

    def test_invalid_tier_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelTieredResolutionConfig(
                min_tier="nonexistent_tier",  # type: ignore[arg-type]
            )


# ===========================================================================
# ModelTrustDomainConfig
# ===========================================================================


@pytest.mark.unit
class TestModelTrustDomainConfigFrozen:
    """Frozen enforcement tests."""

    def test_frozen_domain_id(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="local.default",
            tier=EnumResolutionTier.LOCAL_EXACT,
        )
        with pytest.raises(ValidationError):
            config.domain_id = "other.domain"  # type: ignore[misc]

    def test_frozen_tier(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="local.default",
            tier=EnumResolutionTier.LOCAL_EXACT,
        )
        with pytest.raises(ValidationError):
            config.tier = EnumResolutionTier.ORG_TRUSTED  # type: ignore[misc]

    def test_frozen_trust_root_ref(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="org.omninode",
            tier=EnumResolutionTier.ORG_TRUSTED,
            trust_root_ref="secrets://keys/org-trust-root",
        )
        with pytest.raises(ValidationError):
            config.trust_root_ref = None  # type: ignore[misc]


@pytest.mark.unit
class TestModelTrustDomainConfigExtraForbid:
    """extra='forbid' enforcement tests."""

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ModelTrustDomainConfig(
                domain_id="local.default",
                tier=EnumResolutionTier.LOCAL_EXACT,
                bonus="bad",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelTrustDomainConfigSerialization:
    """Serialization round-trip tests."""

    def test_model_dump_round_trip(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="org.omninode",
            tier=EnumResolutionTier.ORG_TRUSTED,
            trust_root_ref="secrets://keys/org-omninode-trust-root",
        )
        data = config.model_dump()
        restored = ModelTrustDomainConfig.model_validate(data)
        assert restored == config

    def test_json_round_trip(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="fed.partner-a",
            tier=EnumResolutionTier.FEDERATED_TRUSTED,
            trust_root_ref="secrets://keys/partner-a-trust-root",
        )
        json_str = config.model_dump_json()
        restored = ModelTrustDomainConfig.model_validate_json(json_str)
        assert restored == config

    def test_no_trust_root_ref_round_trip(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="local.default",
            tier=EnumResolutionTier.LOCAL_EXACT,
        )
        data = config.model_dump()
        restored = ModelTrustDomainConfig.model_validate(data)
        assert restored == config
        assert restored.trust_root_ref is None

    def test_from_attributes_enabled(self) -> None:
        assert ModelTrustDomainConfig.model_config.get("from_attributes") is True


@pytest.mark.unit
class TestModelTrustDomainConfigValidation:
    """Validation tests for domain_id and tier."""

    def test_empty_domain_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelTrustDomainConfig(
                domain_id="",
                tier=EnumResolutionTier.LOCAL_EXACT,
            )

    def test_domain_id_with_empty_segment_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty segment"):
            ModelTrustDomainConfig(
                domain_id="local..default",
                tier=EnumResolutionTier.LOCAL_EXACT,
            )

    def test_domain_id_segment_must_start_with_letter(self) -> None:
        with pytest.raises(ValidationError, match="must start with a letter"):
            ModelTrustDomainConfig(
                domain_id="local.1bad",
                tier=EnumResolutionTier.LOCAL_EXACT,
            )

    def test_valid_domain_id_formats(self) -> None:
        for domain_id in ["local.default", "org.omninode", "fed.partner-a", "single"]:
            config = ModelTrustDomainConfig(
                domain_id=domain_id,
                tier=EnumResolutionTier.LOCAL_EXACT,
            )
            assert config.domain_id == domain_id

    def test_all_tiers_accepted(self) -> None:
        for tier in EnumResolutionTier:
            config = ModelTrustDomainConfig(
                domain_id="test.domain",
                tier=tier,
            )
            assert config.tier is tier

    def test_string_tier_accepted(self) -> None:
        config = ModelTrustDomainConfig(
            domain_id="org.test",
            tier="org_trusted",  # type: ignore[arg-type]
        )
        assert config.tier == EnumResolutionTier.ORG_TRUSTED


# ===========================================================================
# Integration: ModelCapabilityDependency with tiered_resolution
# ===========================================================================


@pytest.mark.unit
class TestCapabilityDependencyTieredResolution:
    """Integration tests for tiered_resolution on ModelCapabilityDependency."""

    def test_dependency_without_tiered_resolution(self) -> None:
        """Existing dependencies parse unchanged (backward compat)."""
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
        )
        assert dep.tiered_resolution is None

    def test_dependency_with_tiered_resolution(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
            max_tier=EnumResolutionTier.ORG_TRUSTED,
            require_proofs=["node_identity", "capability_attested"],
            classification="internal",
        )
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            tiered_resolution=config,
        )
        assert dep.tiered_resolution is not None
        assert dep.tiered_resolution.min_tier == EnumResolutionTier.LOCAL_EXACT
        assert dep.tiered_resolution.max_tier == EnumResolutionTier.ORG_TRUSTED
        assert dep.tiered_resolution.require_proofs == [
            "node_identity",
            "capability_attested",
        ]
        assert dep.tiered_resolution.classification == "internal"

    def test_dependency_with_empty_tiered_resolution(self) -> None:
        config = ModelTieredResolutionConfig()
        dep = ModelCapabilityDependency(
            alias="cache",
            capability="cache.distributed",
            tiered_resolution=config,
        )
        assert dep.tiered_resolution is not None
        assert dep.tiered_resolution.min_tier is None
        assert dep.tiered_resolution.max_tier is None

    def test_dependency_tiered_resolution_round_trip(self) -> None:
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
            max_tier=EnumResolutionTier.FEDERATED_TRUSTED,
            require_proofs=["org_membership"],
            classification="confidential",
        )
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            tiered_resolution=config,
        )
        data = dep.model_dump()
        restored = ModelCapabilityDependency.model_validate(data)
        assert restored == dep
        assert restored.tiered_resolution == config

    def test_dependency_tiered_resolution_from_dict(self) -> None:
        """Simulates YAML loading where tiered_resolution is a dict."""
        data = {
            "alias": "db",
            "capability": "database.relational",
            "tiered_resolution": {
                "min_tier": "local_exact",
                "max_tier": "org_trusted",
                "require_proofs": ["node_identity"],
                "classification": "internal",
            },
        }
        dep = ModelCapabilityDependency.model_validate(data)
        assert dep.tiered_resolution is not None
        assert dep.tiered_resolution.min_tier == EnumResolutionTier.LOCAL_EXACT
        assert dep.tiered_resolution.max_tier == EnumResolutionTier.ORG_TRUSTED


# ===========================================================================
# Integration: ModelHandlerContract with trust_domains
# ===========================================================================


def _make_minimal_contract(**overrides: object) -> ModelHandlerContract:
    """Create a minimal valid ModelHandlerContract."""
    defaults: dict[str, object] = {
        "handler_id": "node.test.handler",
        "name": "Test Handler",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "descriptor": ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        ),
        "input_model": "myapp.models.Input",
        "output_model": "myapp.models.Output",
    }
    defaults.update(overrides)
    return ModelHandlerContract(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestHandlerContractTrustDomains:
    """Integration tests for trust_domains on ModelHandlerContract."""

    def test_contract_without_trust_domains(self) -> None:
        """Existing contracts parse unchanged (backward compat)."""
        contract = _make_minimal_contract()
        assert contract.trust_domains is None

    def test_contract_with_trust_domains(self) -> None:
        domains = [
            ModelTrustDomainConfig(
                domain_id="local.default",
                tier=EnumResolutionTier.LOCAL_EXACT,
            ),
            ModelTrustDomainConfig(
                domain_id="org.omninode",
                tier=EnumResolutionTier.ORG_TRUSTED,
                trust_root_ref="secrets://keys/org-omninode-trust-root",
            ),
        ]
        contract = _make_minimal_contract(trust_domains=domains)
        assert contract.trust_domains is not None
        assert len(contract.trust_domains) == 2
        assert contract.trust_domains[0].domain_id == "local.default"
        assert contract.trust_domains[1].trust_root_ref == (
            "secrets://keys/org-omninode-trust-root"
        )

    def test_contract_with_empty_trust_domains_list(self) -> None:
        contract = _make_minimal_contract(trust_domains=[])
        assert contract.trust_domains == []

    def test_contract_trust_domains_round_trip(self) -> None:
        domains = [
            ModelTrustDomainConfig(
                domain_id="local.default",
                tier=EnumResolutionTier.LOCAL_EXACT,
            ),
        ]
        contract = _make_minimal_contract(trust_domains=domains)
        data = contract.model_dump()
        restored = ModelHandlerContract.model_validate(data)
        assert restored == contract
        assert restored.trust_domains is not None
        assert len(restored.trust_domains) == 1

    def test_contract_trust_domains_from_dict(self) -> None:
        """Simulates YAML loading where trust_domains is a list of dicts."""
        data = {
            "handler_id": "node.test.handler",
            "name": "Test Handler",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "descriptor": {
                "node_archetype": "compute",
                "purity": "pure",
                "idempotent": True,
            },
            "input_model": "myapp.models.Input",
            "output_model": "myapp.models.Output",
            "trust_domains": [
                {
                    "domain_id": "local.default",
                    "tier": "local_exact",
                },
                {
                    "domain_id": "org.omninode",
                    "tier": "org_trusted",
                    "trust_root_ref": "secrets://keys/org-omninode-trust-root",
                },
            ],
        }
        contract = ModelHandlerContract.model_validate(data)
        assert contract.trust_domains is not None
        assert len(contract.trust_domains) == 2
        assert contract.trust_domains[0].tier == EnumResolutionTier.LOCAL_EXACT
        assert contract.trust_domains[1].tier == EnumResolutionTier.ORG_TRUSTED


# ===========================================================================
# Full integration: dependency with tiered_resolution + contract trust_domains
# ===========================================================================


@pytest.mark.unit
class TestFullContractYamlIntegration:
    """Full integration tests combining tiered_resolution and trust_domains."""

    def test_full_contract_with_all_new_fields(self) -> None:
        """Contract with both tiered_resolution on deps and trust_domains."""
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
            max_tier=EnumResolutionTier.ORG_TRUSTED,
            require_proofs=["node_identity", "capability_attested"],
            classification="internal",
        )
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            tiered_resolution=config,
        )
        domains = [
            ModelTrustDomainConfig(
                domain_id="local.default",
                tier=EnumResolutionTier.LOCAL_EXACT,
            ),
            ModelTrustDomainConfig(
                domain_id="org.omninode",
                tier=EnumResolutionTier.ORG_TRUSTED,
                trust_root_ref="secrets://keys/org-omninode-trust-root",
            ),
        ]
        contract = _make_minimal_contract(
            capability_inputs=[dep],
            trust_domains=domains,
        )

        assert contract.capability_inputs[0].tiered_resolution is not None
        assert contract.trust_domains is not None
        assert len(contract.trust_domains) == 2

    def test_full_contract_round_trip(self) -> None:
        """Full round-trip including all Phase 7 fields."""
        config = ModelTieredResolutionConfig(
            min_tier=EnumResolutionTier.LOCAL_EXACT,
            max_tier=EnumResolutionTier.ORG_TRUSTED,
            require_proofs=["node_identity"],
            classification="internal",
        )
        dep = ModelCapabilityDependency(
            alias="db",
            capability="database.relational",
            tiered_resolution=config,
        )
        domains = [
            ModelTrustDomainConfig(
                domain_id="local.default",
                tier=EnumResolutionTier.LOCAL_EXACT,
            ),
        ]
        contract = _make_minimal_contract(
            capability_inputs=[dep],
            trust_domains=domains,
        )
        data = contract.model_dump()
        restored = ModelHandlerContract.model_validate(data)
        assert restored == contract
        assert restored.capability_inputs[0].tiered_resolution == config
        assert restored.trust_domains == domains

    def test_full_contract_from_yaml_like_dict(self) -> None:
        """Simulate full YAML-like dict loading with all Phase 7 fields."""
        data = {
            "handler_id": "node.test.handler",
            "name": "Test Handler",
            "contract_version": {"major": 1, "minor": 0, "patch": 0},
            "descriptor": {
                "node_archetype": "compute",
                "purity": "pure",
                "idempotent": True,
            },
            "input_model": "myapp.models.Input",
            "output_model": "myapp.models.Output",
            "capability_inputs": [
                {
                    "alias": "db",
                    "capability": "database.relational",
                    "tiered_resolution": {
                        "min_tier": "local_exact",
                        "max_tier": "org_trusted",
                        "require_proofs": [
                            "node_identity",
                            "capability_attested",
                        ],
                        "classification": "internal",
                    },
                },
            ],
            "trust_domains": [
                {
                    "domain_id": "local.default",
                    "tier": "local_exact",
                },
                {
                    "domain_id": "org.omninode",
                    "tier": "org_trusted",
                    "trust_root_ref": "secrets://keys/org-omninode-trust-root",
                },
            ],
        }
        contract = ModelHandlerContract.model_validate(data)
        assert contract.capability_inputs[0].tiered_resolution is not None
        assert (
            contract.capability_inputs[0].tiered_resolution.min_tier
            == EnumResolutionTier.LOCAL_EXACT
        )
        assert contract.trust_domains is not None
        assert len(contract.trust_domains) == 2
