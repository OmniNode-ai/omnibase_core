# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dev merge tag names supplied for one internal sibling repository."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelSiblingDevTags"]


class ModelSiblingDevTags(BaseModel):
    """A sibling repository's tag inventory for the pure staleness check."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    repo: str
    tags: tuple[str, ...]
