# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Output model for the text_file_write EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelTextFileWriteOutput"]


class ModelTextFileWriteOutput(BaseModel):
    """Where the text was written and how many bytes it holds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    bytes_written: int
