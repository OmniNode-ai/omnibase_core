# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read port for source-file gathering through the EFFECT node."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)


@runtime_checkable
class SourceFileGatherInterface(Protocol):
    """Observe source files without coupling callers to a filesystem reader."""

    def handle(
        self, request: ModelSourceFileGatherInput
    ) -> ModelSourceFileGatherOutput:
        """Return the gathered source and skipped-file observations."""
        ...
