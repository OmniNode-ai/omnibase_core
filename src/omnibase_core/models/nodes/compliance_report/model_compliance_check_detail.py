# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Single check detail within a compliance scan."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelComplianceCheckDetail(BaseModel):
    """Single check within a compliance scan for one node."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    check_name: str
    passed: bool
    message: str = ""
