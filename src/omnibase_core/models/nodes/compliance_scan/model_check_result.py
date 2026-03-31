# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result model for a single compliance check."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelCheckResult"]


class ModelCheckResult(BaseModel):
    """Result of a single compliance check."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    check_id: int
    check_name: str
    check_class: str
    passed: bool
    message: str = ""
