# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Receipt files and required distributions for the runtime-identity gate."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelReceiptRuntimeIdentityCheckInput(BaseModel):
    """Receipt JSON files to scan; ``required_packages=None`` means the gate default."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipt_paths: tuple[str, ...] = ()
    required_packages: tuple[str, ...] | None = None
