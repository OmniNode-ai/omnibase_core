# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""What the install wrote and what it verified (OMN-18531; relocated from omnimarket by OMN-21093)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelBindingInstallResult"]


class ModelBindingInstallResult(BaseModel):
    """Hashes of the render and of the installed bytes, and the registrations in the settings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    module_path: str | None
    render_sha256: str | None
    installed_sha256: str | None
    installed_bindings: tuple[str, ...]
    skipped_bindings: tuple[str, ...]
    registered_commands: tuple[str, ...]
    removed_commands: tuple[str, ...]
