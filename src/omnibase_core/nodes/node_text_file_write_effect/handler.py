# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeTextFileWriteEffect — UTF-8 text persistence EFFECT handler.

The filesystem write behind the evidence-packet and baseline outputs of the
converted check runtimes. Check runtime packages live under COMPUTE node
packages and the no-io-outside-effects gate forbids a write there, so the write
is this EFFECT node, on the definition-B ``handle(request) -> response`` shape.

Ticket: OMN-21520.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.models.nodes.text_file_write.model_text_file_write_output import (
    ModelTextFileWriteOutput,
)

__all__ = ["NodeTextFileWriteEffect"]


class NodeTextFileWriteEffect:
    """EFFECT handler that writes UTF-8 text to a file, creating parents."""

    def handle(self, request: ModelTextFileWriteInput) -> ModelTextFileWriteOutput:
        """Write ``request.text`` to ``request.path`` and report the byte count."""
        target = Path(request.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = request.text.encode("utf-8")
        target.write_bytes(payload)
        return ModelTextFileWriteOutput(path=request.path, bytes_written=len(payload))
