# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed offline markdown link configuration."""

from pydantic import BaseModel, ConfigDict


class ModelMarkdownLinkConfig(BaseModel):
    """Core script configuration carried inline."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ignore_patterns: tuple[str, ...] = ()
    exclude_files: tuple[str, ...] = (
        ".pytest_cache/**",
        ".venv/**",
        "venv/**",
        "node_modules/**",
        "archived/**",
    )
    check_external: bool = False
    external_timeout: int = 5000
