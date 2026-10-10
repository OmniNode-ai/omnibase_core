# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Code Entity Bridge Compute — thin declarative COMPUTE node shell.

Bridges AST-extracted code_entities to learned_patterns that context
injection can query and use.

All derivation logic is in handlers/handler_bridge.py.

Ticket: OMN-7863
"""

from __future__ import annotations

from typing import ClassVar

from omniintelligence.nodes.node_code_entity_bridge_compute.handlers import (
    handle_code_entity_bridge,
)
from omniintelligence.nodes.node_code_entity_bridge_compute.models import (
    ModelCodeEntityBridgeInput,
    ModelCodeEntityBridgeOutput,
)


class NodeCodeEntityBridgeCompute:
    """Thin declarative shell for code entity → learned pattern derivation.

    All business logic is delegated to handle_code_entity_bridge.
    """

    is_stub: ClassVar[bool] = True

    def compute(
        self, input_data: ModelCodeEntityBridgeInput
    ) -> ModelCodeEntityBridgeOutput:
        """Derive learned patterns from code entities by delegating to handler."""
        return handle_code_entity_bridge(input_data)


__all__ = ["NodeCodeEntityBridgeCompute"]
