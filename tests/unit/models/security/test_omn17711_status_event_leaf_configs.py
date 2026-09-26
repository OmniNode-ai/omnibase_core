# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fail-closed wire regressions for OMN-17711 security leaf DTOs."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.security.model_compliance_status import ModelComplianceStatus
from omnibase_core.models.security.model_config_validation_result import (
    ModelConfigValidationResult,
)
from omnibase_core.models.security.model_credentialsanalysis import (
    ModelCredentialsAnalysis,
)
from omnibase_core.models.security.model_encryption_algorithm import (
    ModelEncryptionAlgorithm,
)
from omnibase_core.models.security.model_manager_assessment import (
    ModelManagerAssessment,
)
from omnibase_core.models.security.model_mcp_security_summary import (
    ModelMCPSecuritySummary,
)
from omnibase_core.models.security.model_security_event import ModelSecurityEvent
from omnibase_core.models.security.model_signature_chain_summary import (
    ModelSignatureChainSummary,
)


def _event_payload() -> dict[str, object]:
    return {
        "event_id": str(uuid4()),
        "event_type": "authentication_success",
        "timestamp": "2026-09-03T00:00:00Z",
        "envelope_id": str(uuid4()),
        "status": "success",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        pytest.param(ModelComplianceStatus, {}, id="compliance-status"),
        pytest.param(ModelConfigValidationResult, {}, id="config-validation-result"),
        pytest.param(
            ModelEncryptionAlgorithm, {"name": "AES-256-GCM"}, id="encryption-algorithm"
        ),
        pytest.param(
            ModelManagerAssessment,
            {
                "backend_security_level": "high",
                "audit_compliance": "compliant",
                "fallback_resilience": "high",
            },
            id="manager-assessment",
        ),
        pytest.param(
            ModelMCPSecuritySummary,
            {
                "authentication_enabled": True,
                "supported_auth_methods": ["oauth"],
                "available_roles": ["operator"],
                "security_events_count": 1,
                "last_events": [_event_payload()],
            },
            id="mcp-security-summary",
        ),
        pytest.param(ModelSecurityEvent, _event_payload(), id="security-event"),
        pytest.param(
            ModelSignatureChainSummary,
            {
                "chain_id": str(uuid4()),
                "envelope_id": str(uuid4()),
                "signature_count": 1,
                "unique_signers": 1,
                "operations": ["sign"],
                "algorithms": ["ed25519"],
                "has_complete_route": True,
                "validation_status": "valid",
                "trust_level": "high",
                "created_at": "2026-09-03T00:00:00Z",
                "last_modified": "2026-09-03T00:00:00Z",
                "chain_hash": "abc123",
                "compliance_frameworks": ["SOC2"],
            },
            id="signature-chain-summary",
        ),
    ],
)
def test_selected_leaf_models_close_mapping_json_and_schema_boundaries(
    model_type: type[BaseModel], payload: dict[str, object]
) -> None:
    """Every selected leaf rejects unknown wire fields without changing its data."""
    model = model_type.model_validate(payload)
    assert model_type.model_config["extra"] == "forbid"
    assert model_type.model_json_schema()["additionalProperties"] is False
    assert model_type.model_validate_json(model.model_dump_json()) == model
    with pytest.raises(ValidationError) as exc_info:
        model_type.model_validate({**payload, "omn17711_unknown": True})
    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


@pytest.mark.unit
def test_typed_containers_preserve_closed_event_and_assessment_boundaries() -> None:
    """Container contracts retain the selected nested types across JSON round-trips."""
    event = ModelSecurityEvent.model_validate(_event_payload())
    summary = ModelMCPSecuritySummary(
        authentication_enabled=True,
        supported_auth_methods=["oauth"],
        available_roles=["operator"],
        security_events_count=1,
        last_events=[event],
    )
    analysis = ModelCredentialsAnalysis(
        strength_score=80,
        compliance_status="compliant",
        risk_level="low",
        manager_assessment=ModelManagerAssessment(
            backend_security_level="high",
            audit_compliance="compliant",
            fallback_resilience="high",
        ),
    )
    restored_summary = ModelMCPSecuritySummary.model_validate_json(
        summary.model_dump_json()
    )
    restored_analysis = ModelCredentialsAnalysis.model_validate_json(
        analysis.model_dump_json()
    )
    assert restored_summary.last_events == [event]
    assert restored_analysis.manager_assessment == analysis.manager_assessment
