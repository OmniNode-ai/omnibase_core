"""
Mixin for workflow execution from YAML contracts.

Enables orchestrator nodes to execute workflows declaratively from
ModelWorkflowDefinition.

Typing: Strongly typed with strategic Any usage for mixin kwargs and configuration dicts.
"""

from typing import Any
from uuid import UUID

from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.utils.workflow_executor import (
    WorkflowExecutionResult,
    execute_workflow,
    get_execution_order,
    validate_workflow_definition,
)


class MixinWorkflowExecution:
    """
    Mixin providing workflow execution capabilities from YAML contracts.

    Enables orchestrator nodes to execute workflows declaratively without
    custom code. Workflow coordination is driven entirely by contract.

    Usage:
        class NodeMyOrchestrator(NodeOrchestratorDeclarative, MixinWorkflowExecution):
            # No custom workflow code needed - driven by YAML contract
            pass

    Pattern:
        This mixin is stateless - delegates all execution to pure functions.
        Actions are emitted for orchestrated execution.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize workflow execution mixin.

        Args:
            **kwargs: Passed to super().__init__()
        """
        super().__init__(**kwargs)

    async def execute_workflow_from_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
        workflow_id: UUID,
        execution_mode: EnumExecutionMode | None = None,
    ) -> WorkflowExecutionResult:
        """
        Execute workflow from YAML contract.

        Pure function delegation: delegates to utils/workflow_executor.execute_workflow()
        which returns (result, actions) without side effects.

        Args:
            workflow_definition: Workflow definition from node contract
            workflow_steps: Workflow steps to execute
            workflow_id: Unique workflow execution ID
            execution_mode: Optional execution mode override

        Returns:
            WorkflowExecutionResult with emitted actions

        Example:
            result = await self.execute_workflow_from_contract(
                self.contract.workflow_coordination.workflow_definition,
                workflow_steps=[...],
                workflow_id=uuid4(),
            )

            # Check result
            if result.execution_status == EnumWorkflowState.COMPLETED:
                print(f"Workflow completed: {len(result.actions_emitted)} actions")
                # Process actions (emitted to target nodes)
                for action in result.actions_emitted:
                    print(f"Action: {action.action_type} -> {action.target_node_type}")
        """
        return await execute_workflow(
            workflow_definition,
            workflow_steps,
            workflow_id,
            execution_mode,
        )

    async def validate_workflow_contract(
        self,
        workflow_definition: ModelWorkflowDefinition,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[str]:
        """
        Validate workflow contract for correctness.

        Pure function delegation: delegates to utils/workflow_executor.validate_workflow_definition()

        Args:
            workflow_definition: Workflow definition to validate
            workflow_steps: Workflow steps to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            errors = await self.validate_workflow_contract(
                self.contract.workflow_coordination.workflow_definition,
                workflow_steps=[...]
            )

            if errors:
                print(f"Workflow validation failed: {errors}")
            else:
                print("Workflow contract is valid!")
        """
        return await validate_workflow_definition(workflow_definition, workflow_steps)

    def get_workflow_execution_order(
        self,
        workflow_steps: list[ModelWorkflowStep],
    ) -> list[UUID]:
        """
        Get topological execution order for workflow steps.

        Args:
            workflow_steps: Workflow steps to order

        Returns:
            List of step IDs in execution order

        Raises:
            ModelOnexError: If workflow contains cycles

        Example:
            steps = [...]
            order = self.get_workflow_execution_order(steps)
            print(f"Execution order: {order}")
        """
        return get_execution_order(workflow_steps)

    def create_workflow_steps_from_config(
        self,
        steps_config: list[dict[str, Any]],
    ) -> list[ModelWorkflowStep]:
        """
        Create ModelWorkflowStep instances from configuration dictionaries.

        Helper method for converting YAML/dict config to typed models.

        Args:
            steps_config: List of step configuration dictionaries

        Returns:
            List of ModelWorkflowStep instances

        Example:
            steps_config = [
                {
                    "step_name": "Fetch Data",
                    "step_type": "effect",
                    "timeout_ms": 10000,
                },
                {
                    "step_name": "Process Data",
                    "step_type": "compute",
                    "depends_on": [...],
                },
            ]
            steps = self.create_workflow_steps_from_config(steps_config)
        """
        workflow_steps: list[ModelWorkflowStep] = []

        for step_config in steps_config:
            step = ModelWorkflowStep(**step_config)
            workflow_steps.append(step)

        return workflow_steps
