# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One file contributing to a ticket's OCC contract (OMN-20068)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModelOccContractSource(BaseModel):
    """A legacy ``contracts/<TICKET>.yaml`` or a per-PR ``contracts/<TICKET>/<REPO>-<PR>.yaml``.

    ``sha256`` is ``sha256:<hex>`` of the file's raw bytes, the value a receipt's
    whole-file ``contract_sha256`` is compared with. ``data`` is the parsed YAML,
    the input to the per-entry hash.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path
    sha256: str
    data: object
    is_legacy: bool
