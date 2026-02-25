# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract resolve compute node.

ONEX compute node that wraps ContractMergeEngine to provide the canonical
overlay resolution interface (contract.resolve).

.. versionadded:: OMN-2754
"""

from omnibase_core.nodes.node_contract_resolve_compute.handler import (
    NodeContractResolveCompute,
)

__all__ = ["NodeContractResolveCompute"]
