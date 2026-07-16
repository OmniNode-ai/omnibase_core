# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_db_in_orchestrator_check COMPUTE node package (OMN-14694).

Exposes :class:`NodeNoDbInOrchestratorCheckCompute` — keys off each node's
declared archetype (``contract.yaml``) and flags database-driver imports inside
``.py`` modules that sit in an ORCHESTRATOR node package, returning a
``ModelValidationReport``.
"""

from omnibase_core.nodes.node_no_db_in_orchestrator_check_compute.handler import (
    NodeNoDbInOrchestratorCheckCompute,
)

__all__ = ["NodeNoDbInOrchestratorCheckCompute"]
