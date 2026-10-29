# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the transport-import validator (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.transport_import_check.model_transport_import_check_input import (
    ModelTransportImportCheckInput,
)
from omnibase_core.models.nodes.transport_import_check.model_transport_import_check_output import (
    ModelTransportImportCheckOutput,
)
from omnibase_core.models.nodes.transport_import_check.model_transport_import_finding import (
    ModelTransportImportFinding,
)
from omnibase_core.validation.validator_transport_import import (
    ValidatorTransportImport,
)


class NodeTransportImportCheckCompute:
    """Check the named paths for banned transport imports and return the findings."""

    def handle(
        self, request: ModelTransportImportCheckInput
    ) -> ModelTransportImportCheckOutput:
        """Delegate to the validation-layer checker; render each violation once."""
        violations = ValidatorTransportImport().check_paths(
            [Path(p) for p in request.paths]
        )
        return ModelTransportImportCheckOutput(
            findings=tuple(
                ModelTransportImportFinding(
                    file=str(v.file),
                    line=v.line,
                    module_name=v.module_name,
                    context=v.context,
                    message=str(v),
                )
                for v in violations
            )
        )
