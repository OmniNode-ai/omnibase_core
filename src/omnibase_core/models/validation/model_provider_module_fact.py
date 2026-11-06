# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What one module of a provider package offers to its importers (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelProviderModuleFact"]


class ModelProviderModuleFact(BaseModel):
    """One importable module of a provider tree.

    Attributes:
        module: The dotted module name.
        names: The names bound at the module's top level.
        opaque: True when static reading cannot list its names: a star import, a
            module-level ``__getattr__``, or a source that does not parse. Any name
            imported from an opaque module counts as present.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module: str = Field(min_length=1)
    names: frozenset[str] = Field(default_factory=frozenset)
    opaque: bool = False
