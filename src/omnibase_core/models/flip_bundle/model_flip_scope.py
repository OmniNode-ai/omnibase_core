# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Mutable, explicitly shared scope of one flip-bundle verification."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelFlipScope(BaseModel):
    """Paths and refs shared by binding and receipt verification."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    package: str
    repo_root: Path
    src_root: Path
    nodes_glob: str
    baseline_path: Path
    receipts_dir: Path
    base_ref: str
