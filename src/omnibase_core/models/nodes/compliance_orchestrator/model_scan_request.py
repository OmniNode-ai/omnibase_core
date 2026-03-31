# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input payload for a compliance scan request."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelScanRequest"]


class ModelScanRequest(BaseModel):
    """Input payload for a compliance scan request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_dir: str
    run_id: str = ""
