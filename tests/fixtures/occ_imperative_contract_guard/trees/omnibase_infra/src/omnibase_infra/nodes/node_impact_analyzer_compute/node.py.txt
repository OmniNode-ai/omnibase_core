# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2026 OmniNode Team
"""Node Impact Analyzer Compute -- artifact impact scoring.

Pure COMPUTE node: deterministic, no external I/O.
Matches change triggers against the artifact registry to produce
impact analysis results with per-artifact scores and merge policy.

Handlers:
    - HandlerImpactAnalysis: Scoring logic per OMN-3925 table

Related:
    - contract.yaml: Capability definitions and routing
    - handlers/handler_impact_analysis.py: Core scoring handler
    - handlers/constants.py: Thresholds and reason codes

Tracking:
    - OMN-3935: Task 3 - Impact Analyzer COMPUTE Node
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes.node_compute import NodeCompute

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

from omnibase_infra.nodes.node_artifact_change_detector_effect.models.model_update_trigger import (
    ModelUpdateTrigger,
)
from omnibase_infra.nodes.node_impact_analyzer_compute.models.model_impact_analysis_result import (
    ModelImpactAnalysisResult,
)


class NodeImpactAnalyzerCompute(
    NodeCompute[ModelUpdateTrigger, ModelImpactAnalysisResult]
):
    """Declarative compute node for artifact impact analysis.

    Capability: artifact.analyze_impact

    Matches a ModelUpdateTrigger against the artifact registry using
    fnmatch file patterns, applies the OMN-3925 scoring table, and
    returns a ModelImpactAnalysisResult. All behavior is defined in
    contract.yaml and implemented in handlers.

    Attributes:
        container: ONEX dependency injection container.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize the impact analyzer compute node.

        Args:
            container: ONEX dependency injection container.
        """
        super().__init__(container)


__all__: list[str] = ["NodeImpactAnalyzerCompute"]
