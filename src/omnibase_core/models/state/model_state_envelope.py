# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""State envelope model for node state persistence.

.. versionadded:: 0.35.1
    Added as part of Local-First Node Runtime (OMN-7061)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelStateEnvelope(BaseModel):
    """Wrapper for persisted state with metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: node_id is a logical node name, not a UUID
    node_id: str
    # string-id-ok: scope_id is a logical scope name (e.g. "default", "run-42")
    scope_id: str = Field(default="default")
    # ONEX_EXCLUDE: dict_str_any — generic state payload, schema enforced by caller
    data: dict[str, Any]
    written_at: datetime
    contract_fingerprint: str = Field(default="")
