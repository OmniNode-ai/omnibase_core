# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for graduated runtime-deployment wire DTOs (OMN-13209 / A2).

The lane enum and deployment-proof DTO graduated from
``omnibase_compat.contracts.runtime_deployment.wire`` to this canonical core home.
These tests pin the enum values and the proof DTO's required-field / immutability
contract so downstream nodes can rely on a single authority.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime_deployment.wire import (
    EnumRuntimeLane,
    ModelRuntimeDeploymentProof,
)


@pytest.mark.unit
def test_enum_runtime_lane_values() -> None:
    """Lane enum values match the OCC wire schema and live .201 lanes."""
    assert EnumRuntimeLane.DEV == "dev"
    assert EnumRuntimeLane.STABILITY_TEST == "stability-test"
    assert EnumRuntimeLane.PROD == "prod"
    assert {lane.value for lane in EnumRuntimeLane} == {
        "dev",
        "stability-test",
        "prod",
    }


@pytest.mark.unit
def test_deployment_proof_round_trip() -> None:
    """A fully populated proof round-trips through model_validate(model_dump())."""
    proof = ModelRuntimeDeploymentProof(
        correlation_id=uuid.uuid4(),
        deployment_id=uuid.uuid4(),
        runtime_lane=EnumRuntimeLane.STABILITY_TEST,
        source_sha="abc123",
        image_digest="sha256:deadbeef",
        compose_project="omnibase-infra-stability-test",
        health_status="pass",
        ready_status="pass",
        probed_at=datetime.now(UTC),
        status="success",
    )
    restored = ModelRuntimeDeploymentProof.model_validate(proof.model_dump())
    assert restored == proof
    assert restored.runtime_lane is EnumRuntimeLane.STABILITY_TEST


@pytest.mark.unit
def test_deployment_proof_is_frozen() -> None:
    """The proof DTO is immutable (frozen)."""
    proof = ModelRuntimeDeploymentProof(
        correlation_id=uuid.uuid4(),
        deployment_id=uuid.uuid4(),
        runtime_lane=EnumRuntimeLane.PROD,
        source_sha="abc123",
        image_digest="sha256:deadbeef",
        compose_project="omnibase-infra-prod",
        health_status="pass",
        ready_status="pass",
        probed_at=datetime.now(UTC),
        status="success",
    )
    with pytest.raises(ValidationError):
        proof.source_sha = "mutated"  # type: ignore[misc]


@pytest.mark.unit
def test_deployment_proof_rejects_extra_fields() -> None:
    """The proof DTO forbids unknown fields (extra='forbid')."""
    with pytest.raises(ValidationError):
        ModelRuntimeDeploymentProof(
            correlation_id=uuid.uuid4(),
            deployment_id=uuid.uuid4(),
            runtime_lane=EnumRuntimeLane.DEV,
            source_sha="abc123",
            image_digest="sha256:deadbeef",
            compose_project="omnibase-infra",
            health_status="pass",
            ready_status="pass",
            probed_at=datetime.now(UTC),
            status="success",
            unexpected="boom",  # type: ignore[call-arg]
        )
