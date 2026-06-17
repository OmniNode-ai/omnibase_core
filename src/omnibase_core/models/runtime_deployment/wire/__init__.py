# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical runtime-deployment wire DTOs (graduated from omnibase_compat, OMN-13209).

OCC owns the schema source of truth
(``onex_change_control/src/onex_change_control/wire_schemas/``); core owns the
shared Python authority for the lane enum and deployment-proof DTO that the
deployment/OCC nodes import. ``EnumRuntimeLane`` is canonically defined in
``omnibase_core.enums.enum_runtime_lane`` and re-exported here for the wire API.
"""

from omnibase_core.enums.enum_runtime_lane import EnumRuntimeLane
from omnibase_core.models.runtime_deployment.wire.model_runtime_deployment_proof import (
    DeploymentProofStatus,
    ModelRuntimeDeploymentProof,
    ProbeStatus,
)

__all__: list[str] = [
    "DeploymentProofStatus",
    "EnumRuntimeLane",
    "ModelRuntimeDeploymentProof",
    "ProbeStatus",
]
