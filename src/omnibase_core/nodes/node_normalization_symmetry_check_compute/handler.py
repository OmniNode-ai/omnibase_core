# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Normalization-symmetry check COMPUTE handler over the pure validation-layer checker."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.normalization_symmetry_check.model_normalization_symmetry_check_input import (
    ModelNormalizationSymmetryCheckInput,
)
from omnibase_core.models.nodes.normalization_symmetry_check.model_normalization_symmetry_check_output import (
    ModelNormalizationSymmetryCheckOutput,
)
from omnibase_core.validation.checker_normalization_symmetry import (
    SourceModule,
    parse_source_module,
    scan_source_modules,
)


class NodeNormalizationSymmetryCheckCompute:
    """Normalization-symmetry check COMPUTE handler over the pure validation-layer checker.

    Pure and deterministic: all input arrives through the typed request, so the
    handler performs no filesystem access.
    """

    def handle(
        self, request: ModelNormalizationSymmetryCheckInput
    ) -> ModelNormalizationSymmetryCheckOutput:
        """Run the check over the supplied request and return the result."""
        root = Path(request.root)
        modules: list[SourceModule] = []
        for source_file in request.files:
            module = parse_source_module(
                root, Path(source_file.path), source_file.source
            )
            if module is not None:
                modules.append(module)
        findings = scan_source_modules(modules)
        return ModelNormalizationSymmetryCheckOutput(
            messages=tuple(finding.message for finding in findings)
        )
