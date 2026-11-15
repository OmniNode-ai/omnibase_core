# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One dependency a document declares (OMN-24537)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDependsOnEntry(BaseModel):
    """A kind of dependency, its name and an optional field within it; all free data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(min_length=1, description="Kind of the declared dependency")
    name: str = Field(
        min_length=1, description="Name of the dependency within its kind"
    )
    field: str | None = Field(
        default=None,
        min_length=1,
        description="Field of the named thing the dependency needs, when it needs one",
    )

    def token(self, separator: str) -> str:
        """The dependency as the fact source spells it."""
        if self.field is None:
            return self.name
        return f"{self.name}{separator}{self.field}"

    def label(self, separator: str) -> str:
        """The dependency as one diagnostic word."""
        return f"{self.kind}:{self.token(separator)}"
