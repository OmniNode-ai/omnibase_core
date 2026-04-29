# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Database table reference model for contract dependency tracking."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelDbTableRef(BaseModel):
    """A database table reference with access mode."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    access: str  # "read", "write", "read_write"
