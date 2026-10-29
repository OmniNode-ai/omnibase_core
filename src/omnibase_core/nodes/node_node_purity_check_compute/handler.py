# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeNodePurityCheckCompute — node-purity validation COMPUTE handler.

Pure and deterministic: source text arrives on the request; the filesystem
walk and read happen in the runtime, never here. The checking logic lives in
``omnibase_core.validation.validator_node_purity``.

Ticket: OMN-21520.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.node_purity_check.model_node_purity_check_finding import (
    ModelNodePurityCheckFinding,
)
from omnibase_core.models.nodes.node_purity_check.model_node_purity_check_input import (
    ModelNodePurityCheckInput,
)
from omnibase_core.models.nodes.node_purity_check.model_node_purity_check_output import (
    ModelNodePurityCheckOutput,
)
from omnibase_core.validation.validator_node_purity import ValidatorNodePurity

__all__ = ["NodeNodePurityCheckCompute"]


class NodeNodePurityCheckCompute:
    """COMPUTE handler that checks (path, source) pairs for node-purity violations."""

    def handle(self, request: ModelNodePurityCheckInput) -> ModelNodePurityCheckOutput:
        """Return every node-purity violation in the supplied source files."""
        validator = ValidatorNodePurity()
        return ModelNodePurityCheckOutput(
            violations=tuple(
                ModelNodePurityCheckFinding(
                    file=str(violation.file),
                    line=violation.line,
                    column=violation.column,
                    rule=violation.rule.value,
                    message=violation.message,
                )
                for file in request.files
                for violation in validator.check_source(Path(file.path), file.source)
            )
        )
