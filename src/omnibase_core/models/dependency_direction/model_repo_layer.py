# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One repository's declared layer and the names it is referenced by (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelRepoLayer"]


class ModelRepoLayer(BaseModel):
    """A repository, its layer number and the names other repositories use for it.

    Attributes:
        repo: The GitHub repository name (``omnibase_infra``).
        layer: Its position in the dependency order. A repository may depend
            only on repositories at a strictly lower layer.
        python_modules: Top-level import names its distribution provides.
        distributions: Distribution names it publishes (``omninode-memory``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(min_length=1)
    layer: int = Field(ge=0)
    python_modules: tuple[str, ...] = Field(default=())
    distributions: tuple[str, ...] = Field(default=())
