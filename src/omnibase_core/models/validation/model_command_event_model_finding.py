# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCommandEventModelFinding — finding from the command-category event_model guard (OMN-13028)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelCommandEventModelFinding:
    """A ``handler_routing`` entry whose ``message_category`` is ``command`` but lacks an ``event_model``.

    A command-category handler entry that omits ``event_model`` is the failure mode
    behind OMN-13003 (handler with no event_model) and the ladder layer this guard
    closes. A command message names a typed payload model; without a declared
    ``event_model`` the dispatcher cannot resolve the payload type for the command
    handler, and the node fails closed (or worse, silently degenerates) at runtime.

    This guard makes that contract state mechanically impossible at commit time:
    every ``handler_routing`` entry tagged ``message_category: command`` MUST declare
    a non-empty ``event_model`` (a nested ``{name, module}`` block).
    """

    path: Path
    handler_index: int
    handler_name: str

    def format(self) -> str:
        return (
            f"{self.path}: handlers[{self.handler_index}] "
            f"(handler={self.handler_name}) has message_category=command "
            f"but is missing 'event_model'"
        )
