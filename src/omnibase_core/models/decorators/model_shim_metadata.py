# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelShimMetadata — data attached to @shim-decorated callables (OMN-4418)."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelShimMetadata"]


class ModelShimMetadata(BaseModel):
    """Metadata attached to a @shim-decorated callable.

    Read at commit-time by the pre-commit hook and at scan-time by
    node_shim_scanner to detect expired or expiring shims.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    expires_on: datetime.date
    reason: str
    replacement: str
