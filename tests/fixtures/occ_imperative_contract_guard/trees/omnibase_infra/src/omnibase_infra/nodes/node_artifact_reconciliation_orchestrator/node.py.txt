# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2026 OmniNode Team
"""NodeArtifactReconciliationOrchestrator — declarative ORCHESTRATOR.

Coordinates the artifact reconciliation pipeline: receives update plans,
posts PR comments, and emits YAML plan events.

All behavior is defined in contract.yaml — no custom logic here.

This orchestrator follows the ONEX declarative pattern:
    - DECLARATIVE orchestrator driven by contract.yaml
    - Zero custom routing logic — all behavior from workflow_definition
    - Used for ONEX-compliant runtime execution via RuntimeHostProcess
    - Pattern: "Contract-driven, handlers wired by registry"

Workflow Pattern:
    1. Receive ModelUpdatePlan (from update-plan-created event)
    2. Post PR comment via HandlerPlanToPRComment (for PR triggers only)
    3. Emit YAML plan via HandlerPlanToYaml

Handler Routing:
    Handler routing is defined declaratively in contract.yaml under
    handler_routing section. The orchestrator does NOT contain custom
    dispatch logic — the base class routes events based on:
    - routing_strategy: "payload_type_match"
    - handlers: mapping of event_model to handler_class

Design Decisions:
    - 100% Contract-Driven: All workflow logic in YAML, not Python
    - Zero Custom Methods: Base class handles everything
    - Declarative Execution: Workflow steps defined in execution_graph
    - No Filesystem Writes: HandlerPlanToYaml emits events, not files

Tracking:
    - OMN-3944: Task 7 — Reconciliation ORCHESTRATOR Node
    - OMN-3925: Artifact Reconciliation + Update Planning MVP
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.nodes.node_orchestrator import NodeOrchestrator

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


class NodeArtifactReconciliationOrchestrator(NodeOrchestrator):
    """Declarative orchestrator for the artifact reconciliation pipeline.

    All behavior is defined in contract.yaml and delegated to handlers.
    No custom logic.

    Coordinates the reconciliation workflow: receives update plans from the
    REDUCER node, posts PR comments via HandlerPlanToPRComment, and emits
    YAML plan events via HandlerPlanToYaml.

    Handler Routing:
        Handler routing is initialized by the runtime, not by this class.
        The runtime uses RegistryInfraArtifactReconciliationOrchestrator
        to create instances with properly configured dependencies.

    Usage:
        >>> from omnibase_core.models.container import ModelONEXContainer
        >>> container = ModelONEXContainer()
        >>> orchestrator = NodeArtifactReconciliationOrchestrator(container)
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize with container dependency injection.

        Args:
            container: ONEX dependency injection container.
        """
        super().__init__(container)


__all__: list[str] = ["NodeArtifactReconciliationOrchestrator"]
