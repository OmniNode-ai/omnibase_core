# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure node-boundary check input."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_source_file import (
    ModelBoundaryImportSourceFile,
)


class ModelBoundaryImportCheckInput(BaseModel):
    """Explicit source, repository package inventory and shrink-only state.

    Directory and module inventories may be supplied by the EFFECT node to
    include packages whose contents are not eligible importers. Pure callers
    can omit them: directories and modules are then inferred from file paths.
    Runtime read and baseline errors travel as data and become ERROR findings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    files: tuple[ModelBoundaryImportSourceFile, ...] = ()
    repo_packages: tuple[str, ...] = ()
    node_packages: tuple[str, ...] = ()
    known_modules: tuple[str, ...] = ()
    baseline_path: str = ".onex_ratchets/node_boundary_import_baseline.yaml"
    baseline_edges: tuple[str, ...] = ()
    baseline_present: bool = False
    baseline_error: str | None = None
    read_errors: tuple[str, ...] = ()
