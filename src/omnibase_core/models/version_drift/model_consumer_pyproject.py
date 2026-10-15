# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One registry consumer's pyproject.toml as read at its origin branch (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelConsumerPyproject"]


class ModelConsumerPyproject(BaseModel):
    """A consumer repository and the pyproject text read from it.

    Attributes:
        repo: The consumer's name as declared in ``contracts/repo_layers.yaml``.
        ref: The ref the text was read at (for example ``origin/dev``).
        pyproject: The file's text, or None when it could not be read. An
            unreadable consumer is never assumed compatible.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    pyproject: str | None = None
