# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DB table declaration model for contract-first projection nodes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDbTableDeclaration"]


class ModelDbTableDeclaration(BaseModel):
    """Declaration of a DB table owned or accessed by this node."""

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    name: str
    migration: str
    access: Literal["read", "write", "read_write"] = "write"
    database: str = "omnidash_analytics"
    role: str
