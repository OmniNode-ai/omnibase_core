# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2026 OmniNode Team
"""Declarative EFFECT node for checkpoint filesystem I/O.

Owns all read/write/list operations on checkpoint YAML files.
All behavior is defined in contract.yaml and delegated to handlers.

Ticket: OMN-2143
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes.node_effect import NodeEffect

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeCheckpointEffect(NodeEffect):
    """Declarative effect node for checkpoint persistence.

    Handlers:
        - ``HandlerCheckpointWrite``: Writes a phase checkpoint to disk.
        - ``HandlerCheckpointRead``: Reads a checkpoint for pipeline resume.
        - ``HandlerCheckpointList``: Lists available checkpoints for a ticket/run.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the checkpoint effect node."""
        super().__init__(container)
