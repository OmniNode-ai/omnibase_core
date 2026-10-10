# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Handler: scenario generation for NodeBehaviorScenarioGeneratorCompute.

Pure async function — no I/O, no logging, no container access.
LLM calls are delegated to the injected llm_caller.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from omniintelligence.nodes.node_bloom_eval_orchestrator.models.model_behavior_spec import (
    ModelBehaviorSpec,
)
from omniintelligence.nodes.node_bloom_eval_orchestrator.models.model_eval_scenario import (
    ModelEvalScenario,
)


async def handle_scenario_generation(
    spec: ModelBehaviorSpec,
    n: int,
    *,
    llm_caller: Callable[[str, int], Awaitable[list[str]]],
) -> list[ModelEvalScenario]:
    """Generate exactly n ModelEvalScenario objects from a BehaviorSpec.

    Args:
        spec: The behavior specification defining failure mode and prompt template.
        n: Number of scenarios to generate.
        llm_caller: Async callable that accepts (prompt_template, n) and returns
            a list of exactly n raw scenario text strings.

    Returns:
        List of exactly n ModelEvalScenario objects with spec_id and failure_mode
        propagated from spec.
    """
    raw_texts: list[str] = await llm_caller(spec.scenario_prompt_template, n)
    return [
        ModelEvalScenario(
            spec_id=spec.spec_id,
            failure_mode=spec.failure_mode,
            input_text=text,
            context={},
        )
        for text in raw_texts
    ]


__all__ = ["handle_scenario_generation"]
