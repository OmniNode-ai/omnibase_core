# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One frozen, provenance-validated suite baseline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelSkipCountBaselineEntry(BaseModel):
    """Baseline values supplied by the runtime after validating provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    key: str
    repo: str
    job: str
    mode: Literal["count", "nodeids"]
    max_skips: int
    baseline_collected: int
    node_ids: frozenset[str]
    path: str
