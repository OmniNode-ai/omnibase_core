# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the validator-requirements consumer (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.requirements_consumer_check.model_requirements_consumer_check_input import (
    ModelRequirementsConsumerCheckInput,
)
from omnibase_core.models.nodes.requirements_consumer_check.model_requirements_consumer_check_output import (
    ModelRequirementsConsumerCheckOutput,
)
from omnibase_core.validation.validator_requirements_consumer import (
    ValidatorRequirementsConsumer,
)


class NodeRequirementsConsumerCheckCompute:
    """Scan one repo against the validator-requirements spec and return its gaps."""

    def handle(
        self, request: ModelRequirementsConsumerCheckInput
    ) -> ModelRequirementsConsumerCheckOutput:
        """Delegate to the validation-layer consumer; the canonical spec is the default."""
        consumer = (
            ValidatorRequirementsConsumer.from_spec_path(Path(request.spec_path))
            if request.spec_path is not None
            else ValidatorRequirementsConsumer.from_canonical()
        )
        gaps = consumer.scan_repo(
            repo_name=request.repo, repo_root=Path(request.repo_root)
        )
        return ModelRequirementsConsumerCheckOutput(gaps=tuple(gaps))
