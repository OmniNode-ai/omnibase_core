# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the text_file_write EFFECT node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelTextFileWriteInput"]


class ModelTextFileWriteInput(BaseModel):
    """The text to persist and the file location to persist it at."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str
    text: str
