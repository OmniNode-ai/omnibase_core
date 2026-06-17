# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRuntimeDeploymentProof — runtime deployment proof wire DTO (canonical core home).

Graduated from ``omnibase_compat.contracts.runtime_deployment.wire`` (OMN-13209 /
A2). Mirrors the OCC-owned wire schema
(``onex_change_control/src/onex_change_control/wire_schemas/
runtime_deployment_proof_v1.yaml``, topic
``onex.evt.omnimarket.runtime-deployment-proof.v1``); OCC owns the schema source
of truth, core owns the shared Python authority. The proof is assembled from the
live runtime attestation surfaces plus the per-lane health/ready/digest probe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane

type ProbeStatus = Literal["pass", "fail"]
type DeploymentProofStatus = Literal["success", "failed"]


class ModelRuntimeDeploymentProof(BaseModel):
    """Per-lane runtime deployment proof consumed by the readiness gate.

    ``image_digest`` is the prod-gate authority: production may deploy only the
    digest proven READY in stability-test, so it is a required proof field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Deployment run correlation ID shared by all deployment events.",
    )
    deployment_id: UUID = Field(
        ...,
        description="Stable identifier for the deployment attempt this proof covers.",
    )
    runtime_lane: EnumRuntimeLane = Field(
        ..., description="Runtime lane that was probed."
    )
    source_sha: str = Field(
        ...,
        min_length=1,
        description="Source commit SHA bound to the deployed artifact.",
    )
    image_digest: str = Field(
        ...,
        min_length=1,
        description="Immutable digest of the running container image. Prod-gate authority.",
    )
    compose_project: str = Field(
        ..., min_length=1, description="Compose project that owns the deployed lane."
    )
    health_status: ProbeStatus = Field(
        ..., description="Per-lane /health probe result."
    )
    ready_status: ProbeStatus = Field(..., description="Per-lane /ready probe result.")
    probed_at: datetime = Field(..., description="When the per-lane probe completed.")
    status: DeploymentProofStatus = Field(..., description="Overall proof status.")
    # string-id-ok: promotion_batch_id is a human-readable promotion batch label shared across OCC evidence, not a UUID.
    promotion_batch_id: str | None = Field(
        default=None, description="Promotion batch identifier shared with OCC evidence."
    )
    runtime_addresses: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Probed runtime addresses (main/effects ports) for the lane.",
    )
    topology_manifest_sha256: str | None = Field(
        default=None,
        description="Topology manifest hash from the runtime manifest reducer.",
    )
    package_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Deployed package versions from runtime attestation.",
    )
    runtime_source_hash: str | None = Field(
        default=None,
        description="Runtime source hash from the runtime source attestor.",
    )
    consumer_groups: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Active consumer groups observed on the probed lane.",
    )
    runtime_sweep_input_ref: str | None = Field(
        default=None,
        description="Reference to the runtime sweep input used for classification.",
    )


__all__: list[str] = [
    "DeploymentProofStatus",
    "ModelRuntimeDeploymentProof",
    "ProbeStatus",
]
