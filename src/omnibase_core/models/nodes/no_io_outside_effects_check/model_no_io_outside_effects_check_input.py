# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the no_io_outside_effects_check COMPUTE node.

The request carries an intermixed set of ``(path, source)`` pairs: both
``contract.yaml`` files (from which the node archetype is read) AND the
``.py`` modules co-located with them. The COMPUTE partitions them by path,
keys off the archetype declared in each contract, and only scans for forbidden
I/O surfaces in the Python modules that sit in a **non-EFFECT** node package —
so the caller does not pre-decide which files matter; the pure handler does,
from the contract seam. See OMN-14694 (WS8 seed) / OMN-14662 (archetype-purity
collapse), epic OMN-2362.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelNoIoOutsideEffectsCheckInput"]


class ModelNoIoOutsideEffectsCheckInput(BaseModel):
    """Request to check non-EFFECT node packages for forbidden I/O surfaces.

    ``files`` mixes ``contract.yaml`` pairs (archetype source of truth) with
    the ``.py`` modules to be scanned. The reused ``ModelSourceFile`` shape
    keeps content inline so the handler never touches the filesystem — reads
    happen at the paired EFFECT boundary (``node_source_file_gather_effect``)
    or the CLI runtime.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
