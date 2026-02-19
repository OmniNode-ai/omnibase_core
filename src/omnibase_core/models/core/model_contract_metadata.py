# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, Field


class ModelContractMetadata(BaseModel):
    """Metadata section of the contract."""

    dependencies: dict[str, list[str]] | None = Field(
        default=None,
        description="Tool dependencies",
    )
    related_docs: dict[str, list[str]] | None = Field(
        default=None,
        description="Related documentation",
    )
    consumers: dict[str, list[str]] | None = Field(
        default=None,
        description="Known consumers of this tool",
    )
