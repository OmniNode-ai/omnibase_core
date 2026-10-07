# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Paired EFFECT boundary: tracked inventory, source reads and artifact writes.

Git listing, content reads and report persistence reuse the existing canonical
effects. No existing write effect accepts arbitrary baseline YAML or edge JSON;
``write_artifact`` owns those writes here, outside the pure COMPUTE package.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.git_file_listing.model_git_file_listing_input import (
    ModelGitFileListingInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_artifact_write_input import (
    ModelBoundaryImportArtifactWriteInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_input import (
    ModelBoundaryImportCheckInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_request import (
    ModelBoundaryImportCheckRequest,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_source_file import (
    ModelBoundaryImportSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
    eligible_importer,
    module_name,
    node_directories,
    parse_baseline,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


class NodeBoundaryImportCheckEffect:
    """Gather a repo into the typed COMPUTE request and persist CLI artifacts."""

    def handle(
        self, request: ModelBoundaryImportCheckRequest
    ) -> ModelBoundaryImportCheckInput:
        """Read only tracked eligible importers; inspect local package directories."""
        root = Path(request.root).resolve()
        paths = (
            NodeGitFileListingEffect()
            .handle(ModelGitFileListingInput(root=root, scope="tracked"))
            .paths
        )
        source_root = root / "src"
        packages = (
            tuple(
                sorted(
                    child.name
                    for child in source_root.iterdir()
                    if child.is_dir() and (child / "__init__.py").is_file()
                )
            )
            if source_root.is_dir()
            else ()
        )
        known_modules: set[str] = set()
        nodes: set[str] = set()
        for package in packages:
            package_root = source_root / package
            for path in package_root.rglob("*"):
                relative = path.relative_to(root).as_posix()
                if path.is_file() and path.suffix == ".py":
                    known_modules.add(module_name(relative, packages))
                elif (
                    path.is_dir()
                    and path.name.startswith("node_")
                    and path.parent.name == "nodes"
                ):
                    nodes.update(node_directories(f"{relative}/__init__.py", packages))
        selected = sorted({path for path in paths if eligible_importer(path)})
        files: tuple[ModelBoundaryImportSourceFile, ...] = ()
        read_errors: tuple[str, ...] = ()
        if selected:
            gathered = NodeSourceFileGatherEffect().handle(
                ModelSourceFileGatherInput(
                    root=str(root),
                    explicit_paths=[str(root / path) for path in selected],
                    include_patterns=["*.py"],
                )
            )
            files = tuple(
                ModelBoundaryImportSourceFile(
                    path=Path(file.path).relative_to(root).as_posix(),
                    source=file.source,
                )
                for file in gathered.files
            )
            read_errors = tuple(
                f"{file.path}: {file.reason}" for file in gathered.skipped
            )
        baseline_path = root / request.baseline_path
        present = baseline_path.exists()
        baseline: tuple[str, ...] = ()
        baseline_error: str | None = None
        if present:
            gathered_baseline = NodeSourceFileGatherEffect().handle(
                ModelSourceFileGatherInput(
                    root=str(root),
                    explicit_paths=[str(baseline_path)],
                    include_patterns=["*"],
                )
            )
            if gathered_baseline.skipped:
                baseline_error = "; ".join(
                    file.reason for file in gathered_baseline.skipped
                )
            else:
                try:
                    baseline = parse_baseline(
                        gathered_baseline.files[0].source, request.baseline_path
                    )
                except (ValueError, yaml.YAMLError, ModelOnexError) as exc:
                    baseline_error = str(exc)
        return ModelBoundaryImportCheckInput(
            files=files,
            repo_packages=packages,
            node_packages=tuple(sorted(nodes)),
            known_modules=tuple(sorted(known_modules)),
            baseline_path=request.baseline_path,
            baseline_edges=baseline,
            baseline_present=present,
            baseline_error=baseline_error,
            read_errors=read_errors,
        )

    def write_artifact(self, request: ModelBoundaryImportArtifactWriteInput) -> None:
        """Persist rendered baseline or edge JSON at the EFFECT boundary."""
        target = Path(request.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(request.content, encoding="utf-8")

    def write_report(self, path: str, report: ModelValidationReport) -> None:
        """Delegate canonical report persistence to its existing EFFECT node."""
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )
