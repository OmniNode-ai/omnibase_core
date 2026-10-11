# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeMergeProvenanceObserveEffect -- declarative effect node (OMN-19927).

Reads, through an injected GitHub reader, the merge-group runs and summary-job
conclusions recorded for one commit. All behavior is declared in
``contract.yaml``; no custom logic here.
"""

from __future__ import annotations

from omnibase_core.nodes.node_effect import NodeEffect


class NodeMergeProvenanceObserveEffect(NodeEffect):
    """Declarative effect node for merge-provenance observation."""


__all__ = ["NodeMergeProvenanceObserveEffect"]
