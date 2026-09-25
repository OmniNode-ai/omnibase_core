# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract tests for the OMN-17732 security leaf configuration tranche."""

import json

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_latency_level import EnumLatencyLevel
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_backend_capabilities import (
    ModelBackendCapabilities,
)
from omnibase_core.models.security.model_backend_config import ModelBackendConfig
from omnibase_core.models.security.model_backend_config_validation import (
    ModelBackendConfigValidation,
)
from omnibase_core.models.security.model_backend_performance_profile import (
    ModelBackendPerformanceProfile,
)
from omnibase_core.models.security.model_performance_optimization_config import (
    ModelPerformanceOptimizationConfig,
)
from omnibase_core.models.security.model_permission import ModelPermission
from omnibase_core.models.security.model_permission_action import ModelPermissionAction
from omnibase_core.models.security.model_permission_metadata import (
    ModelPermissionMetadata,
)
from omnibase_core.models.security.model_secret_backend import ModelSecretBackend
from omnibase_core.models.security.model_secret_config import ModelSecretConfig

type LeafCase = tuple[type[BaseModel], dict[str, object]]

LEAF_CASES: tuple[LeafCase, ...] = (
    (
        ModelBackendCapabilities,
        {
            "supports_secrets": True,
            "supports_rotation": True,
            "supports_encryption": True,
            "supports_audit": True,
            "supports_versioning": False,
            "supports_access_control": True,
            "production_ready": True,
            "requires_external_service": True,
        },
    ),
    (
        ModelBackendConfigValidation,
        {
            "is_valid": False,
            "issues": ["missing endpoint"],
            "warnings": ["development-only backend"],
            "required_fields_missing": ["endpoint"],
            "suggestions": ["configure endpoint"],
        },
    ),
    (
        ModelBackendPerformanceProfile,
        {
            "latency": "low",
            "throughput": "moderate",
            "scalability": "excellent",
            "overhead": "api_calls",
        },
    ),
    (
        ModelPermissionAction,
        {
            "action_id": "11111111-1111-4111-8111-111111111111",
            "action_name": "Read deployment metadata",
            "action_type": "read",
            "resource_types": ["deployment"],
            "requires_approval": False,
            "risk_level": "low",
            "description": "Read-only deployment inspection",
            "max_frequency_per_hour": 60,
            "cooldown_minutes": 0,
            "audit_required": True,
            "audit_detail_level": "detailed",
        },
    ),
    (
        ModelPerformanceOptimizationConfig,
        {
            "cache_enabled": True,
            "cache_ttl_seconds": 120,
            "connection_pooling": True,
            "max_connections": 20,
            "connection_timeout": 4,
        },
    ),
    (
        ModelPermissionMetadata,
        {
            "tags": ["deployment", "read-only"],
            "category": "operations",
            "priority": 4,
            "source_system": "policy-registry",
            "external_id": "22222222-2222-4222-8222-222222222222",
            "notes": "canonical permission metadata",
        },
    ),
)


class _BackendLeafContainer(BaseModel):
    """Typed representative container for nested-boundary verification."""

    model_config = ConfigDict(extra="forbid")

    capabilities: ModelBackendCapabilities
    config_validation: ModelBackendConfigValidation
    performance_profile: ModelBackendPerformanceProfile
    action: ModelPermissionAction
    optimization: ModelPerformanceOptimizationConfig
    metadata: ModelPermissionMetadata


@pytest.mark.parametrize(("model_type", "payload"), LEAF_CASES)
def test_mapping_and_json_round_trip_preserve_wire_values(
    model_type: type[BaseModel],
    payload: dict[str, object],
) -> None:
    """Declared mapping and JSON payloads retain their exact JSON representation."""
    instance = model_type.model_validate(payload)

    assert instance.model_dump(mode="json") == payload
    assert (
        model_type.model_validate_json(instance.model_dump_json()).model_dump(
            mode="json"
        )
        == payload
    )


@pytest.mark.parametrize(("model_type", "payload"), LEAF_CASES)
def test_unknown_keys_fail_closed_for_mapping_and_json(
    model_type: type[BaseModel],
    payload: dict[str, object],
) -> None:
    """Unknown input is rejected instead of being silently discarded."""
    invalid_payload = {**payload, "omn17732_unknown": True}

    with pytest.raises(ValidationError) as mapping_error:
        model_type.model_validate(invalid_payload)
    assert "extra_forbidden" in {
        error["type"] for error in mapping_error.value.errors()
    }

    with pytest.raises(ValidationError) as json_error:
        model_type.model_validate_json(json.dumps(invalid_payload))
    assert "extra_forbidden" in {error["type"] for error in json_error.value.errors()}


@pytest.mark.parametrize(("model_type", "payload"), LEAF_CASES)
def test_schema_declares_closed_world_boundary(
    model_type: type[BaseModel],
    payload: dict[str, object],
) -> None:
    """The generated schema exposes the same closed-world input contract."""
    del payload

    assert model_type.model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize(
    ("model_type", "field_name", "new_value"),
    [
        (ModelBackendCapabilities, "production_ready", True),
        (ModelBackendConfigValidation, "is_valid", False),
        (ModelBackendPerformanceProfile, "latency", EnumLatencyLevel.HIGH),
        (ModelPermissionAction, "risk_level", "high"),
        (ModelPerformanceOptimizationConfig, "cache_enabled", False),
        (ModelPermissionMetadata, "priority", 7),
    ],
)
def test_existing_mutability_is_preserved(
    model_type: type[BaseModel],
    field_name: str,
    new_value: object,
) -> None:
    """Adding an input boundary does not freeze the existing mutable DTOs."""
    payload_by_model = dict(LEAF_CASES)
    instance = model_type.model_validate(payload_by_model[model_type])

    setattr(instance, field_name, new_value)

    assert getattr(instance, field_name) == new_value


def test_mutable_defaults_remain_instance_local() -> None:
    """List defaults retain Pydantic's per-instance isolation."""
    first = ModelBackendConfigValidation()
    second = ModelBackendConfigValidation()

    first.issues.append("first-only")

    assert first.issues == ["first-only"]
    assert second.issues == []


def test_nested_unknown_key_is_rejected_by_typed_container() -> None:
    """A typed container cannot hide unknown data inside a selected leaf."""
    payloads = dict(LEAF_CASES)
    container_payload: dict[str, object] = {
        "capabilities": {
            **payloads[ModelBackendCapabilities],
            "omn17732_nested_unknown": True,
        },
        "config_validation": payloads[ModelBackendConfigValidation],
        "performance_profile": payloads[ModelBackendPerformanceProfile],
        "action": payloads[ModelPermissionAction],
        "optimization": payloads[ModelPerformanceOptimizationConfig],
        "metadata": payloads[ModelPermissionMetadata],
    }

    with pytest.raises(ValidationError) as error:
        _BackendLeafContainer.model_validate(container_payload)

    assert any(
        item["type"] == "extra_forbidden"
        and item["loc"] == ("capabilities", "omn17732_nested_unknown")
        for item in error.value.errors()
    )


def test_real_backend_callers_return_closed_leaf_models() -> None:
    """Canonical backend helpers still construct each leaf with declared fields."""
    backend = ModelSecretBackend.create_vault()

    capabilities = backend.get_backend_capabilities()
    config_validation = backend.validate_config(
        ModelBackendConfig(vault_url="https://vault.example")
    )
    performance_profile = backend.get_performance_profile()

    assert isinstance(capabilities, ModelBackendCapabilities)
    assert isinstance(config_validation, ModelBackendConfigValidation)
    assert isinstance(performance_profile, ModelBackendPerformanceProfile)
    assert config_validation.required_fields_missing == ["vault_token"]


def test_real_secret_config_caller_returns_closed_optimization_model() -> None:
    """Secret configuration preserves the optimization result API."""
    config = ModelSecretConfig(backend=ModelSecretBackend.create_environment())

    optimization = config.get_performance_optimization_config()

    assert isinstance(optimization, ModelPerformanceOptimizationConfig)


def test_permission_metadata_real_container_and_action_public_api() -> None:
    """Permission metadata and action retain their canonical integration surfaces."""
    permission = ModelPermission(
        version=ModelSemVer(major=1, minor=0, patch=0),
        name="read_deployment_metadata",
        resource="deployments/metadata",
        action="read",
        metadata=ModelPermissionMetadata(tags=["scope"]),
    )
    action = ModelPermissionAction.model_validate(
        next(
            payload
            for model_type, payload in LEAF_CASES
            if model_type is ModelPermissionAction
        )
    )

    assert isinstance(permission.metadata, ModelPermissionMetadata)
    assert permission.metadata.tags == ["scope"]
    assert action.action_type == "read"
