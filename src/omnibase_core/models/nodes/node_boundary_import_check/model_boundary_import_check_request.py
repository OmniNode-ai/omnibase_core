# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repository scan request for the paired EFFECT handler."""

from pydantic import BaseModel, ConfigDict


class ModelBoundaryImportCheckRequest(BaseModel):
    """Locate a repository and its baseline without widening either."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base: str = "HEAD"
    bootstrap: bool = False
    root: str = "."
    baseline_path: str = ".onex_ratchets/node_boundary_import_baseline.yaml"
