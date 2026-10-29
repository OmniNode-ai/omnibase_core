# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The files whose unfinished-work markers are checked (OMN-20068)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelTodoFormatRequest"]


class ModelTodoFormatRequest(BaseModel):
    """The files whose unfinished-work markers are checked (OMN-20068)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    paths: tuple[str, ...]
