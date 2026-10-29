# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed demo-path topic coherence validation, delegating to the validation-layer checker."""

from __future__ import annotations

from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.nodes.demo_path_topic_coherence_check.model_demo_path_topic_coherence_check_input import (
    ModelDemoPathTopicCoherenceCheckInput,
)
from omnibase_core.validation.validator_demo_path_topic_coherence import (
    ValidatorDemoPathTopicCoherence,
)


class NodeDemoPathTopicCoherenceCheckCompute:
    """Run the demo-path topic coherence assertions over the supplied repo roots."""

    def handle(
        self, request: ModelDemoPathTopicCoherenceCheckInput
    ) -> ModelValidationResult[None]:
        """Return the aggregated coherence result."""
        return ValidatorDemoPathTopicCoherence(
            repo_roots=list(request.repo_roots)
        ).run()
