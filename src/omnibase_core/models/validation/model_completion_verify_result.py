# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-receipt deterministic completion check result model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCompletionVerifyResult(BaseModel):
    """Result of a pre-receipt identifier-vs-file completion check.

    Captures which identifiers were searched, where each was found,
    what is missing, and skip reasons. Operates before a worker claims done.
    """

    model_config = ConfigDict(frozen=True)

    task_id: str  # string-id-ok: external Linear ticket identifier (e.g. "OMN-1234")
    checked_identifiers: list[str]
    found: dict[str, str]
    missing: list[str]
    skipped: bool
    skipped_reason: str | None
