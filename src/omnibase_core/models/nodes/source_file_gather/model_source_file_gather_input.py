# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the source_file_gather EFFECT node.

Field shape mirrors ``DirectoryTraverser.find_files``
(``omnibase_archived/src/omnibase/utils/directory_traverser.py:129-167``),
plus a ``source_only`` extension ported from
``node_compliance_scan_compute`` (``handler.py:57-58,97-105``, OMN-9537).

Ticket: OMN-14656 (RSD canary).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_ignore_pattern_source import EnumTraversalMode

__all__ = ["ModelSourceFileGatherInput"]


class ModelSourceFileGatherInput(BaseModel):
    """Request to gather eligible source files under a directory.

    Attributes:
        root: Directory to scan.
        include_patterns: Glob patterns (relative to ``root``) of files to
            include. Defaults to ``["**/*.py"]`` (the oracle's own default
            is YAML/YML/JSON; gather/ignore/schema-exclusion semantics are
            pattern-agnostic).
        exclude_patterns: Additional ignore patterns, merged with
            ``.onexignore`` patterns and the default ignore directories.
        traversal_mode: FLAT, SHALLOW, or RECURSIVE eligibility scoping.
        ignore_file: Path to a file or directory to start the
            ``.onexignore`` parent-walk from. ``None`` starts from the
            current working directory (matches oracle behavior).
        max_file_size: Files larger than this many bytes are skipped.
        source_only: When True, additionally prune ``env``/``.env``
            directories (``.venv``/``venv`` are already pruned
            unconditionally via the default ignore directories).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-path-ok: directory to scan, not a UUID
    root: str
    include_patterns: list[str] = Field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: list[str] = Field(default_factory=list)
    traversal_mode: EnumTraversalMode = Field(default=EnumTraversalMode.RECURSIVE)
    # string-path-ok: optional path to a .onexignore file/directory
    ignore_file: str | None = Field(default=None)
    max_file_size: int = Field(default=5 * 1024 * 1024, ge=0)
    source_only: bool = Field(default=False)
