# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts for the ``no_io_outside_effects`` checker (OMN-21532, K4).

One node contract and, optionally, one Python module found under the contract's
directory. A contract given alone is judged for its own faults; a contract given with
a module is the archetype context the module is judged in. A module given with no contract is one
that no node contract sits above; the ``package_scope`` row says which such modules are judged.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelNoIoOutsideEffectsFacts"]


class ModelNoIoOutsideEffectsFacts(BaseModel):
    """The nearest node contract (none when no node sits above the module) and the module judged."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract: ModelSourceFile | None = None
    module: ModelSourceFile | None = None
