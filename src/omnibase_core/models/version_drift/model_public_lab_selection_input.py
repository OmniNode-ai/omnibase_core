# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the public-repository lab selection check (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.version_drift.model_public_lab_node_routes import (
    ModelPublicLabNodeRoutes,
)

__all__ = ["ModelPublicLabSelectionInput"]


class ModelPublicLabSelectionInput(BaseModel):
    """A repository's workflows, its visibility, the routes and its live variables.

    Attributes:
        repository: The repository name the findings name.
        public: False means a private repository, where the check passes.
        files: Repository-relative (path, source) pairs of the workflows.
        routes: The typed routes read from the pinned omnibase_core, never from the caller.
        variables: Live Actions variable values (name to value) when the caller
            passes them; a hosted seam variable that holds a lab label is refused.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(min_length=1)
    public: bool = True
    files: tuple[ModelSourceFile, ...] = Field(default=())
    routes: ModelPublicLabNodeRoutes = Field(default_factory=ModelPublicLabNodeRoutes)
    variables: dict[str, str] = Field(default_factory=dict)
