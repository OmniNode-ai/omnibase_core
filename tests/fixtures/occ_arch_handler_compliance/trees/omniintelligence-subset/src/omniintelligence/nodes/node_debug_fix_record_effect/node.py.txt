# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Debug Fix Record Effect Node — declarative shell.

Ticket: OMN-3556
"""

from __future__ import annotations

from omnibase_core.nodes.node_effect import NodeEffect


class NodeDebugFixRecordEffect(NodeEffect):
    """Declarative effect node for debug fix record creation.

    Consumes ci-recovery-detected.v1 events. Finds the open TriggerRecord for
    the repo+branch, inserts a FixRecord, and atomically marks the TriggerRecord
    resolved. Emits debug-fix-record-created.v1 on success.

    This node is a thin shell following the ONEX declarative pattern.
    All routing and execution logic is driven by contract.yaml.
    """

    # Pure declarative shell - all behavior defined in contract.yaml


__all__ = ["NodeDebugFixRecordEffect"]
