# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A named class of changed files, selected by repository and path (OMN-21823)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field


class ModelLabReceiptFileClass(BaseModel):
    """One ``<name>::<repository pattern>::<path pattern>`` entry of a contract list."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(description="Class name reported when the class counts")
    repository: re.Pattern[str] = Field(
        description="Selects the repositories the class applies to"
    )
    path: re.Pattern[str] = Field(description="Selects the changed paths in the class")

    def selects(self, repository: str, path: str) -> bool:
        """Whether the class applies to a path of a repository."""
        return (
            self.repository.search(repository) is not None
            and self.path.search(path) is not None
        )
