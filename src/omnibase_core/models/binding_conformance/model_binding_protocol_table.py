# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The caller's protocol table: which protocols exist and which node declares which."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.models.binding_conformance.model_binding_node_row import (
    ModelBindingNodeRow,
)
from omnibase_core.models.binding_conformance.model_binding_protocol import (
    ModelBindingProtocol,
)


class ModelBindingProtocolTable(BaseModel):
    """Data supplied by the caller; the node holds no row and no protocol of its own."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    protocols: tuple[ModelBindingProtocol, ...]
    rows: tuple[ModelBindingNodeRow, ...]

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        codes = [p.code for p in self.protocols]
        refs = [p.protocol for p in self.protocols]
        if len(set(codes)) != len(codes):
            raise ValueError("a protocol code appears twice in the table")
        if len(set(refs)) != len(refs):
            raise ValueError("a protocol import path appears twice in the table")
        nodes = [r.node for r in self.rows]
        if len(set(nodes)) != len(nodes):
            raise ValueError("a node has two rows in the table")
        for row in self.rows:
            unknown = sorted(set(row.protocols) - set(codes))
            if unknown:
                raise ValueError(f"row of {row.node} names unknown protocol {unknown}")
            if len(set(row.protocols)) != len(row.protocols):
                raise ValueError(f"row of {row.node} repeats a protocol")
        return self
