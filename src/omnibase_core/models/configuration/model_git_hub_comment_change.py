# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGitHubCommentChange model."""

from pydantic import BaseModel, Field


class ModelGitHubCommentChange(BaseModel):
    """Represents a change to a GitHub comment field."""

    from_: str | None = Field(default=None, alias="from", description="Previous value")
