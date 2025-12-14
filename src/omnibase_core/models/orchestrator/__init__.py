"""
Orchestrator models for ONEX workflow coordination.

This module provides models for workflow-driven coordination in the ONEX
4-node architecture. Orchestrators manage multi-step workflows with parallel
execution, dependency resolution, and load balancing capabilities.

Key Components:
    ModelOrchestratorInput:
        Input model for workflow coordination with execution mode and
        branching configuration.

    ModelOrchestratorOutput:
        Output model with workflow results, step outcomes, and execution metrics.

    ModelOrchestratorStep:
        Individual step definition within a workflow, including dependencies
        and timeout configuration.

    ModelOrchestratorPlan:
        Execution plan for a workflow with step ordering and resource allocation.

    ModelOrchestratorGraph:
        Directed acyclic graph (DAG) representation for workflow visualization
        and dependency analysis.

    ModelOrchestratorResult:
        Complete result of workflow execution with timing and status information.

    ModelLoadBalancer:
        Load balancer for distributing workflow operations across available
        resources with concurrency control.

    ModelAction:
        Lease-based action model for single-writer semantics in distributed
        workflow coordination.

    ModelPlan:
        Generic plan model for workflow planning and scheduling.

    ModelGraph:
        Graph structure for representing workflow dependencies and relationships.

Thread Safety:
    Most models in this module are immutable after creation. ModelLoadBalancer
    uses asyncio.Semaphore for thread-safe concurrency control.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.orchestrator import (
    ...     ModelOrchestratorInput,
    ...     ModelOrchestratorStep,
    ... )
    >>> from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
    >>>
    >>> # Create workflow input
    >>> workflow_input = ModelOrchestratorInput(
    ...     workflow_id=uuid4(),
    ...     steps=[{"name": "step1", "action": "process"}],
    ...     execution_mode=EnumExecutionMode.PARALLEL,
    ...     max_parallel_steps=3,
    ... )

See Also:
    - omnibase_core.nodes.node_orchestrator: NodeOrchestrator implementation
    - docs/guides/node-building/06_ORCHESTRATOR_NODE_TUTORIAL.md: Tutorial
"""

from omnibase_core.models.graph import ModelGraph
from omnibase_core.models.infrastructure.model_protocol_action import ModelAction
from omnibase_core.models.services.model_plan import ModelPlan

# Re-export aggregator
from .model_load_balancer import ModelLoadBalancer
from .model_orchestrator import *
from .model_orchestrator_graph import ModelOrchestratorGraph
from .model_orchestrator_input import ModelOrchestratorInput
from .model_orchestrator_output import ModelOrchestratorOutput
from .model_orchestrator_plan import ModelOrchestratorPlan
from .model_orchestrator_result import ModelOrchestratorResult
from .model_orchestrator_step import ModelOrchestratorStep

__all__ = [
    "ModelAction",
    "ModelGraph",
    "ModelLoadBalancer",
    "ModelOrchestratorGraph",
    "ModelOrchestratorInput",
    "ModelOrchestratorOutput",
    "ModelOrchestratorPlan",
    "ModelOrchestratorResult",
    "ModelOrchestratorStep",
    "ModelPlan",
]
