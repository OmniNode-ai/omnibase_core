# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One observed symbol reference crossing a node or foreign private API boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelBoundaryImportEdge(BaseModel):
    """An edge identifies an importer, resolved target module and imported symbol."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    importer: str
    importer_path: str
    line: int = Field(ge=1)
    target: str
    kind: Literal[
        "outside->node", "node->node", "cross-repo->node", "cross-repo-private"
    ]
    seam: Literal["model", "protocol", "contract", "event", "private-api"]
    imported_name: str
    via: Literal["import", "yaml", "string"] = "import"

    @property
    def identity(self) -> str:
        """Stable baseline key, independent of line numbers and aliases."""
        return f"{self.importer} -> {self.target}:{self.imported_name}"
