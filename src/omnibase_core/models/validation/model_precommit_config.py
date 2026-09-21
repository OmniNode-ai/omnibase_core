# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed projection of pre-commit configuration consumed by Core validators."""

from pydantic import BaseModel, ConfigDict, Field


class ModelPrecommitConfig(BaseModel):
    """Validated hook rows and install stages used by repository meta-checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repos: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    default_install_hook_types: tuple[str, ...] = Field(default_factory=tuple)
    default_stages: tuple[str, ...] = Field(default_factory=tuple)
    fail_fast: bool | None = None
    ci: dict[str, object] | None = None


__all__ = ["ModelPrecommitConfig"]
