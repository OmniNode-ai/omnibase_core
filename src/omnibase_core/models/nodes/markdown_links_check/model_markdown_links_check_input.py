# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Complete typed input to the pure markdown validator."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

from .model_markdown_link_config import ModelMarkdownLinkConfig
from .model_markdown_link_inventory_entry import ModelMarkdownLinkInventoryEntry


class ModelMarkdownLinksCheckInput(BaseModel):
    """Documents, configuration and all filesystem facts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str
    files: tuple[ModelSourceFile, ...]
    config: ModelMarkdownLinkConfig = ModelMarkdownLinkConfig()
    inventory: tuple[ModelMarkdownLinkInventoryEntry, ...] = ()
    cross_repo_root: str | None = None
    external_results: dict[str, str | None] = {}
