# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Node NodeBehaviorScenarioGeneratorCompute — adversarial scenario generation.

Bloom eval compute node. Receives a ModelBehaviorSpec and an injected llm_caller,
delegates to handler_scenario_generation, and returns exactly n ModelEvalScenario objects.

This node follows the ONEX declarative pattern:
    - DECLARATIVE compute driven by contract.yaml
    - Zero I/O — pure function, no side effects
    - Lightweight shell that delegates to handler_scenario_generator

Responsibilities:
    - Generate n adversarial evaluation scenarios from a BehaviorSpec
    - Propagate spec_id and failure_mode to all returned scenarios

Does NOT:
    - Perform any I/O
    - Make HTTP calls directly
    - Use logging
    - Access container

Related:
    - OMN-4022: This node implementation
    - OMN-4016: Bloom eval parent epic
"""

from __future__ import annotations

from omnibase_core.nodes.node_compute import NodeCompute

from omniintelligence.nodes.node_bloom_eval_orchestrator.models.model_behavior_spec import (
    ModelBehaviorSpec,
)
from omniintelligence.nodes.node_bloom_eval_orchestrator.models.model_eval_scenario import (
    ModelEvalScenario,
)


class NodeBehaviorScenarioGeneratorCompute(
    NodeCompute[ModelBehaviorSpec, list[ModelEvalScenario]]
):
    """Declarative compute node for adversarial scenario generation.

    Pure declarative shell. All handler dispatch is defined in contract.yaml
    via handler_routing. The node itself contains NO custom routing code.

    Supported Operations (defined in contract.yaml handler_routing):
        - generate_scenarios: Generate n ModelEvalScenario objects from a BehaviorSpec

    Example:
        ```python
        from omniintelligence.nodes.node_behavior_scenario_generator_compute.handlers import (
            handle_scenario_generation,
        )

        scenarios = await handle_scenario_generation(
            spec=some_spec,
            n=3,
            llm_caller=async_llm_fn,
        )
        ```
    """

    # Pure declarative shell — all behavior defined in contract.yaml


__all__ = ["NodeBehaviorScenarioGeneratorCompute"]
