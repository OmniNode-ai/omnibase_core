# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The revision a runtime is serving for one name (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHotloadServedEntry"]


class ModelHotloadServedEntry(BaseModel):
    """The hash and version currently wired for one name (plan section 3.2).

    A reader that needs the served revision's declarations joins this name and
    content hash to the registry's revisions topic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registry_version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
