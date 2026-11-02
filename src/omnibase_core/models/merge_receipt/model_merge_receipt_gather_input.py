# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Where the merge-side receipt fact gathering reads from (OMN-21926)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelMergeReceiptGatherInput(BaseModel):
    """Paths to the watcher state, the canonical clones and the ledger files."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    state_path: Path = Field(description="PR watcher state JSON")
    clone_root: Path = Field(
        description="Directory holding one canonical clone per repository"
    )
    ledger_paths: tuple[Path, ...] = Field(
        description="Rolling ledger files, live and archived"
    )
    repos: tuple[str, ...] = Field(
        description="Repositories whose open pull requests are examined"
    )
    check_names: tuple[str, ...] = Field(
        description="Check-run names read from the watcher state as receipts (a contract value)"
    )
    surface_pattern: str = Field(
        description="Ledger surface that marks a pre-PR slot HOLD or RELEASE (a contract value)"
    )
