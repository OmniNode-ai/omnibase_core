# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A file excluded from the source_file_gather EFFECT node's eligible set."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelSkippedSourceFile"]


class ModelSkippedSourceFile(BaseModel):
    """A file that was found by the include-pattern glob but excluded.

    ``reason`` mirrors the skip-reason vocabulary of the oracle
    ``DirectoryTraverser._find_files_with_config``
    (``omnibase_archived/src/omnibase/utils/directory_traverser.py:317-348``):
    "not a file", "not in directory (FLAT mode)", "not in immediate
    subdirectory (SHALLOW mode)", "ignored by pattern", "schema file",
    "exceeds max file size", "error checking file size: <exc>", or
    "read error: <exc>".
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: filesystem path to the skipped file, not a UUID
    path: str
    reason: str
