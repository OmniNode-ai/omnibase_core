# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""contract.verify.replay compute node package (OMN-2759).

Exposes :class:`NodeContractVerifyReplayCompute` — the tier1 static
verification node for ``.oncp`` contract packages.

.. versionadded:: 0.20.0
"""

from omnibase_core.nodes.node_contract_verify_replay_compute.handler import (
    NodeContractVerifyReplayCompute,
)

__all__ = ["NodeContractVerifyReplayCompute"]
