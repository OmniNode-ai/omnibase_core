# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Compliance orchestrator node.

Coordinates the contract compliance scan workflow by discovering contracts
and fanning out one check request per discovered contract.

.. versionadded:: OMN-7072
"""

from omnibase_core.nodes.node_compliance_orchestrator.handler import (
    NodeComplianceOrchestrator,
)

__all__ = ["NodeComplianceOrchestrator"]
