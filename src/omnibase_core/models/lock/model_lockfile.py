# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Lockfile model — the ``omn.lock`` file schema.

The lockfile pins the exact contract fingerprints, CLI version, and schema
versions used at a point in time.  It is analogous to ``poetry.lock`` or
``package-lock.json`` for CLI contracts.

Lockfile format: YAML (serialized via this model), human-readable, suitable
for git diff review.

Design constraints:
- Lockfile is deterministic: same catalog state → identical lockfile bytes.
- Partial lockfiles (subset of commands) are rejected — all-or-nothing.
- The ``lock_version`` field is versioned for forward compatibility.

.. versionadded:: 0.20.0  (OMN-2570)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.lock.model_lock_entry import ModelLockEntry

__all__ = ["ModelLockfile"]

# Current lock format version.
LOCK_FORMAT_VERSION: str = "1"


class ModelLockfile(BaseModel):
    """The ``omn.lock`` lockfile document.

    Represents the full lockfile pinning all CLI commands in the catalog
    at the time ``omn lock`` was executed.

    Attributes:
        lock_version: Lockfile format version.  Incremented on breaking
            changes to the schema.  Current: ``"1"``.
        generated_at: ISO 8601 UTC timestamp of when the lockfile was
            generated.
        cli_version: The CLI version string that generated this lockfile.
            Empty string when CLI version was not provided.
        commands: Sorted list of per-command lock entries.  Sorted by
            ``command_id`` for deterministic output.
    """

    # string-version-ok: lockfile format version as opaque integer string ("1"), not a SemVer
    lock_version: str = Field(
        default=LOCK_FORMAT_VERSION,
        description="Lockfile format version (incremented on breaking schema changes).",
    )
    generated_at: Annotated[datetime, Field(description="UTC timestamp of generation.")]
    # string-version-ok: CLI binary version stored for informational purposes only, not a ModelSemVer constraint
    cli_version: str = Field(
        default="",
        description="CLI version string that generated this lockfile.",
    )
    commands: list[ModelLockEntry] = Field(
        default_factory=list,
        description="Per-command lock entries, sorted by command_id.",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
