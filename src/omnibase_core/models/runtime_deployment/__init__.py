# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime deployment wire DTOs (canonical, graduated from omnibase_compat).

OMN-13209 (A2): the runtime-deployment lane enum and deployment-proof wire DTO
graduate from the transient ``omnibase_compat.contracts.runtime_deployment.wire``
mirror to this canonical core home now that >=2 repos import them. OCC remains the
schema source of truth (``onex_change_control`` wire schemas); core owns the
shared Python authority that downstream nodes import.
"""
