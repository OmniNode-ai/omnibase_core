# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A column referenced from Python SQL that no migration declares."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelColumnViolation"]


class ModelColumnViolation(BaseModel):
    """The table, the missing column and the Python file that referenced it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    table: str
    column: str
    python_file: str
    repo: str
