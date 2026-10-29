# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Which baseline entries a run is allowed to judge stale."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelFindingBaselineScope"]


class ModelFindingBaselineScope(BaseModel):
    """The files and directories a run covered.

    File mode (pre-commit passes staged filenames) covers only those files;
    directory mode covers everything under the scanned directories. An empty
    directory string is the repository root.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: tuple[str, ...] = Field(default=())
    dirs: tuple[str, ...] = Field(default=())

    def contains(self, path: str) -> bool:
        """True when a baseline entry for ``path`` is this run's to judge."""
        if path in self.files:
            return True
        return any(not d or path.startswith(d.rstrip("/") + "/") for d in self.dirs)
