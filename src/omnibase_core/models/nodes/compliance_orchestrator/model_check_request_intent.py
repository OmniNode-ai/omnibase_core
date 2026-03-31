# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent to request a compliance check for a single contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelCheckRequestIntent"]


class ModelCheckRequestIntent(BaseModel):
    """Intent to request a compliance check for a single contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contract_path: str
    node_id: str
    run_id: str
