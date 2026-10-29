# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts for the ``no_io_outside_effects`` checker (OMN-21532, K4).

One node contract and, optionally, one Python module found under the contract's
directory. A contract given alone is judged for its own faults; a contract given with
a module is the archetype context the module is judged in.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelNoIoOutsideEffectsFacts"]


class ModelNoIoOutsideEffectsFacts(BaseModel):
    """The nearest node contract and, optionally, the module judged inside its directory."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract: ModelSourceFile
    module: ModelSourceFile | None = None
