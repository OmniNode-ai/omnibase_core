# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelDelegationRuntimeProfile and sub-models.

TDD-first for OMN-10919. Tests cover:
1. Minimal valid profile (required fields only)
2. ModelDelegationSecretRef rejects raw_value
3. extra="forbid" enforcement
4. Full profile with all 8 sub-models populated
5. Frozen immutability
"""

from __future__ import annotations

import pytest
from omnibase_compat.contracts.delegation.model_delegation_dashboard_connection import (
    ModelDelegationDashboardConnection,
)
from omnibase_compat.contracts.delegation.model_delegation_datastore import (
    ModelDelegationDatastore,
)
from omnibase_compat.contracts.delegation.model_delegation_event_bus_endpoint import (
    ModelDelegationEventBusEndpoint,
)
from omnibase_compat.contracts.delegation.model_delegation_llm_backend import (
    ModelDelegationLlmBackend,
)
from omnibase_compat.contracts.delegation.model_delegation_pricing_manifest_ref import (
    ModelDelegationPricingManifestRef,
)
from omnibase_compat.contracts.delegation.model_delegation_projection_api import (
    ModelDelegationProjectionApi,
)
from omnibase_compat.contracts.delegation.model_delegation_runtime_profile import (
    ModelDelegationRuntimeProfile,
)
from omnibase_compat.contracts.delegation.model_delegation_secret_ref import (
    ModelDelegationSecretRef,
)
from omnibase_compat.contracts.delegation.model_delegation_security import (
    ModelDelegationSecurity,
)
from pydantic import ValidationError

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_event_bus() -> ModelDelegationEventBusEndpoint:
    return ModelDelegationEventBusEndpoint(
        provider="redpanda",
        bootstrap_servers=["192.168.86.201:19092"],
        topic_policy_ref="onex.topics.v1",
        consumer_groups=["delegation-consumer-group"],
    )


@pytest.fixture
def minimal_llm_backend() -> ModelDelegationLlmBackend:
    return ModelDelegationLlmBackend(
        bifrost_endpoint_ref="LLM_CODER_URL",
        default_task_model_ref="cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit",
        max_tokens_default=4096,
        max_tokens_hard_limit=32768,
        timeout_ms=30000,
    )


@pytest.fixture
def minimal_profile(
    minimal_event_bus: ModelDelegationEventBusEndpoint,
    minimal_llm_backend: ModelDelegationLlmBackend,
) -> ModelDelegationRuntimeProfile:
    return ModelDelegationRuntimeProfile(
        name="test-delegation-profile",
        version=1,
        runtime_profile="local",
        event_bus=minimal_event_bus,
        llm_backends={"default": minimal_llm_backend},
    )


# =============================================================================
# Test: Minimal valid profile
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestMinimalValidProfile:
    def test_minimal_valid_profile(
        self, minimal_profile: ModelDelegationRuntimeProfile
    ) -> None:
        assert minimal_profile.name == "test-delegation-profile"
        assert minimal_profile.version == 1
        assert minimal_profile.runtime_profile == "local"
        assert minimal_profile.security is None
        assert minimal_profile.pricing is None
        assert minimal_profile.dashboard is None
        assert minimal_profile.datastores is None

    def test_event_bus_fields(
        self, minimal_profile: ModelDelegationRuntimeProfile
    ) -> None:
        eb = minimal_profile.event_bus
        assert eb.provider == "redpanda"
        assert eb.bootstrap_servers == ["192.168.86.201:19092"]
        assert eb.topic_policy_ref == "onex.topics.v1"
        assert eb.consumer_groups == ["delegation-consumer-group"]

    def test_llm_backend_fields(
        self, minimal_profile: ModelDelegationRuntimeProfile
    ) -> None:
        backend = minimal_profile.llm_backends["default"]
        assert backend.bifrost_endpoint_ref == "LLM_CODER_URL"
        assert backend.max_tokens_default == 4096
        assert backend.max_tokens_hard_limit == 32768
        assert backend.timeout_ms == 30000

    def test_event_bus_requires_at_least_one_server(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationEventBusEndpoint(
                provider="redpanda",
                bootstrap_servers=[],  # min_length=1
                topic_policy_ref="ref",
                consumer_groups=[],
            )

    def test_llm_backend_max_tokens_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationLlmBackend(
                bifrost_endpoint_ref="ref",
                default_task_model_ref="model",
                max_tokens_default=0,  # must be ge=1
                max_tokens_hard_limit=1000,
                timeout_ms=1000,
            )

    def test_llm_backend_timeout_ge_1000(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationLlmBackend(
                bifrost_endpoint_ref="ref",
                default_task_model_ref="model",
                max_tokens_default=100,
                max_tokens_hard_limit=1000,
                timeout_ms=999,  # must be ge=1000
            )


# =============================================================================
# Test: ModelDelegationSecretRef rejects raw_value
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestSecretRefContractRejectsRawValue:
    def test_rejects_raw_secret_value(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelDelegationSecretRef(
                ref_name="MY_SECRET",
                raw_value="supersecret",  # must be rejected
            )
        assert (
            "raw_value" in str(exc_info.value).lower()
            or "secret" in str(exc_info.value).lower()
        )

    def test_accepts_ref_name_only(self) -> None:
        secret = ModelDelegationSecretRef(ref_name="MY_SECRET")
        assert secret.ref_name == "MY_SECRET"
        assert secret.raw_value is None

    def test_accepts_none_raw_value(self) -> None:
        secret = ModelDelegationSecretRef(ref_name="MY_SECRET", raw_value=None)
        assert secret.raw_value is None


# =============================================================================
# Test: extra="forbid" enforcement
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestExtraFieldsForbidden:
    def test_profile_rejects_extra_fields(
        self,
        minimal_event_bus: ModelDelegationEventBusEndpoint,
        minimal_llm_backend: ModelDelegationLlmBackend,
    ) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationRuntimeProfile(
                name="test",
                version=1,
                runtime_profile="local",
                event_bus=minimal_event_bus,
                llm_backends={"default": minimal_llm_backend},
                unknown_field="not allowed",  # type: ignore[call-arg]
            )

    def test_event_bus_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationEventBusEndpoint(
                provider="redpanda",
                bootstrap_servers=["host:9092"],
                topic_policy_ref="ref",
                consumer_groups=[],
                unexpected="extra",  # type: ignore[call-arg]
            )

    def test_secret_ref_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationSecretRef(
                ref_name="MY_SECRET",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

    def test_llm_backend_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationLlmBackend(
                bifrost_endpoint_ref="ref",
                default_task_model_ref="model",
                max_tokens_default=100,
                max_tokens_hard_limit=1000,
                timeout_ms=5000,
                mystery_field="nope",  # type: ignore[call-arg]
            )


# =============================================================================
# Test: Full profile with all 8 sub-models
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestFullProfileWithAllSections:
    def test_full_profile_with_all_sections(
        self,
        minimal_event_bus: ModelDelegationEventBusEndpoint,
        minimal_llm_backend: ModelDelegationLlmBackend,
    ) -> None:
        security = ModelDelegationSecurity(
            broker_allowlist_ref="BROKER_ALLOWLIST",
            endpoint_cidr_allowlist_ref="CIDR_ALLOWLIST",
            shared_secret_ref=ModelDelegationSecretRef(ref_name="SHARED_SECRET"),
        )
        pricing = ModelDelegationPricingManifestRef(
            manifest_ref="pricing.v1", version=1
        )
        projection_api = ModelDelegationProjectionApi(
            base_url_ref="PROJECTION_API_URL",
            endpoints={"nodes": "/api/v1/nodes", "events": "/api/v1/events"},
            schema_version="1.0.0",
            freshness_sla_ms=5000,
        )
        dashboard = ModelDelegationDashboardConnection(
            projection_api_ref=projection_api,
            refresh_contract={"interval_ms": 30000},
        )
        datastore = ModelDelegationDatastore(
            projection_database_ref="PROJECTION_DB_URL",
        )

        profile = ModelDelegationRuntimeProfile(
            name="full-delegation-profile",
            version=2,
            runtime_profile="production",
            event_bus=minimal_event_bus,
            llm_backends={"default": minimal_llm_backend, "fast": minimal_llm_backend},
            security=security,
            pricing=pricing,
            dashboard=dashboard,
            datastores={"projection": datastore},
        )

        assert profile.name == "full-delegation-profile"
        assert profile.version == 2
        assert profile.runtime_profile == "production"
        assert profile.security is not None
        assert profile.security.broker_allowlist_ref == "BROKER_ALLOWLIST"
        assert profile.pricing is not None
        assert profile.pricing.manifest_ref == "pricing.v1"
        assert profile.pricing.version == 1
        assert profile.dashboard is not None
        assert profile.dashboard.projection_api_ref.base_url_ref == "PROJECTION_API_URL"
        assert profile.datastores is not None
        assert "projection" in profile.datastores

    def test_pricing_version_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationPricingManifestRef(manifest_ref="pricing.v1", version=0)

    def test_projection_api_freshness_sla_ms(self) -> None:
        api = ModelDelegationProjectionApi(
            base_url_ref="URL_REF",
            endpoints={},
            schema_version="1.0.0",
            freshness_sla_ms=1000,
        )
        assert api.freshness_sla_ms == 1000

    def test_security_shared_secret_ref_type(self) -> None:
        secret = ModelDelegationSecretRef(ref_name="MY_SECRET")
        security = ModelDelegationSecurity(
            broker_allowlist_ref="B",
            endpoint_cidr_allowlist_ref="C",
            shared_secret_ref=secret,
        )
        assert isinstance(security.shared_secret_ref, ModelDelegationSecretRef)
        assert security.shared_secret_ref.ref_name == "MY_SECRET"


# =============================================================================
# Test: Frozen immutability
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestFrozenImmutability:
    def test_profile_is_frozen(
        self, minimal_profile: ModelDelegationRuntimeProfile
    ) -> None:
        with pytest.raises((ValidationError, TypeError)):
            minimal_profile.name = "modified"  # type: ignore[misc]

    def test_event_bus_is_frozen(
        self, minimal_event_bus: ModelDelegationEventBusEndpoint
    ) -> None:
        with pytest.raises((ValidationError, TypeError)):
            minimal_event_bus.provider = "kafka"  # type: ignore[misc]

    def test_secret_ref_is_frozen(self) -> None:
        secret = ModelDelegationSecretRef(ref_name="SECRET_REF")
        with pytest.raises((ValidationError, TypeError)):
            secret.ref_name = "MODIFIED"  # type: ignore[misc]

    def test_llm_backend_is_frozen(
        self, minimal_llm_backend: ModelDelegationLlmBackend
    ) -> None:
        with pytest.raises((ValidationError, TypeError)):
            minimal_llm_backend.timeout_ms = 99999  # type: ignore[misc]

    def test_model_config_frozen_true(self) -> None:
        assert ModelDelegationRuntimeProfile.model_config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        assert ModelDelegationRuntimeProfile.model_config.get("extra") == "forbid"

    def test_model_config_from_attributes(self) -> None:
        assert ModelDelegationRuntimeProfile.model_config.get("from_attributes") is True
