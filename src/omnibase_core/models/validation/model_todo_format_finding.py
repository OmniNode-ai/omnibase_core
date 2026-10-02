# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelTodoFormatFinding — finding from the ticket-format hook (OMN-20068)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelTodoFormatFinding(BaseModel):
    """A comment containing an unfinished-work marker without a ticket reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"
