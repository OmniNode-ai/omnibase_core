# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One repository source file supplied to the imperative contract guard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGuardModuleSource"]


class ModelGuardModuleSource(BaseModel):
    """A ``src/**/*.py`` module, read by the caller.

    ``path`` is relative to the repository root and POSIX-separated
    (``src/<package>/<module>.py``), so the handler judges the same segments whatever
    directory the repository is checked out under.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repository-relative POSIX path of the module.")
    source: str = Field(description="Full text of the module.")
