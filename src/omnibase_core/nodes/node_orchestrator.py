"""
NodeOrchestrator - Workflow-driven orchestrator node for coordination.

Primary orchestrator implementation using workflow definitions for coordination.
Zero custom Python code required - all coordination logic defined declaratively.
"""

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.orchestrator import ModelOrchestratorOutput
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.workflow.execution.model_workflow_state_snapshot import (
    ModelWorkflowStateSnapshot,
)
from omnibase_core.utils.workflow_executor import WorkflowExecutionResult

# Error messages
_ERR_WORKFLOW_DEFINITION_NOT_LOADED = "Workflow definition not loaded"


class NodeOrchestrator(NodeCoreBase, MixinWorkflowExecution):
    """
        Workflow-driven orchestrator node for coordination.

        Enables creating orchestrator nodes entirely from YAML contracts without custom Python code.
        Workflow steps, dependencies, and execution modes are all defined in workflow definitions.

        Thread Safety:
            NodeOrchestrator instances are NOT thread-safe due to mutable workflow state:
            - Active workflow execution tracking
            - Step completion status
            - Workflow context accumulation

            Each thread should have its own NodeOrchestrator instance, or implement
            explicit synchronization. See docs/guides/THREADING.md for patterns.

        Pattern:
            class NodeMyOrchestrator(NodeOrchestrator):
                # No custom code needed - driven entirely by YAML contract
                pass

        Contract Injection:
            The node requires a workflow definition to be provided. Two approaches:

            1. **Manual Injection** (recommended for testing/simple usage):
                ```python
                node = NodeMyOrchestrator(container)
                node.workflow_definition = ModelWorkflowDefinition(...)
                ```

            2. **Automatic Loading** (for production with YAML contracts):
                - Use `MixinContractMetadata` to auto-load from YAML files
                - The mixin provides `self.contract` with workflow_coordination field
                - See `docs/guides/contracts/` for contract loading patterns

        Example YAML Contract:
            ```yaml
            workflow_coordination:
              workflow_definition:
                workflow_metadata:
                  workflow_name: data_processing_pipeline
                  workflow_version: {major: 1, minor: 0, patch: 0}
                  execution_mode: parallel
                  description: "Multi-stage data processing workflow"

                execution_graph:
                  nodes:
                    - node_id: "fetch_data"
                      node_type: effect
                      description: "Fetch data from sources"
                    - node_id: "validate_schema"
                      node_type: compute
                      description: "Validate data schema"
                    - node_id: "enrich_data"
                      node_type: compute
                      description: "Enrich with additional fields"
                    - node_id: "persist_results"
                      node_type: effect
                      description: "Save to database"

                coordination_rules:
                  parallel_execution_allowed: true
                  failure_recovery_strategy: retry
                  max_retries: 3
                  timeout_ms: 300000
            ```

        Usage:
            ```python
            import logging
            from uuid import uuid4
            from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
                ModelWorkflowDefinition,
            )
            from omnibase_core.models.orchestrator.model_orchestrator_input import (
        ModelOrchestratorInput,
    )
            from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode

            logger = logging.getLogger(__name__)

            # Create node from container
            node = NodeMyOrchestrator(container)

            # CRITICAL: Set workflow definition (required before processing)
            node.workflow_definition = ModelWorkflowDefinition(
                workflow_metadata=ModelWorkflowDefinitionMetadata(
                    workflow_name="data_processing",
                    workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                    execution_mode="parallel",
                ),
                execution_graph=ModelExecutionGraph(nodes=[...]),
                coordination_rules=ModelCoordinationRules(
                    parallel_execution_allowed=True,
                    failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                ),
            )

            # Define workflow steps as dicts (converted internally to ModelWorkflowStep)
            steps_config = [
                {
                    "step_id": uuid4(),
                    "step_name": "Fetch Data",
                    "step_type": "effect",
                    "timeout_ms": 10000,
                },
                {
                    "step_id": uuid4(),
                    "step_name": "Process Data",
                    "step_type": "compute",
                    "depends_on": [fetch_step_id],
                    "timeout_ms": 15000,
                },
            ]

            # Execute workflow via process method
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=steps_config,
                execution_mode=EnumExecutionMode.PARALLEL,
            )

            result = await node.process(input_data)
            logger.debug("Completed steps: %d", len(result.completed_steps))
            logger.debug("Actions emitted: %d", len(result.actions_emitted))
            ```

        Key Features:
            - Pure workflow pattern: (definition, steps) -> (result, actions[])
            - Actions emitted for deferred execution by target nodes
            - Complete Pydantic validation for contracts
            - Zero custom code - entirely YAML-driven
            - Sequential/parallel/batch execution modes
            - Dependency-aware execution with topological ordering
            - Cycle detection in workflow graphs
            - Disabled step handling
            - Action metadata tracking
    """

    # Type annotation for workflow_definition attribute
    # Set via object.__setattr__() in __init__ to bypass Pydantic validation
    workflow_definition: ModelWorkflowDefinition | None

    def __init__(self, container: ModelONEXContainer) -> None:
        """
        Initialize orchestrator node.

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Load workflow definition from node contract
        # This assumes the node contract has a workflow_coordination field
        # If not present, workflow capabilities are not active
        # Use object.__setattr__() to bypass Pydantic validation when mixins with
        # Pydantic BaseModel are in the MRO (e.g., MixinEventBus in ModelServiceOrchestrator)
        object.__setattr__(self, "workflow_definition", None)

        # Try to load workflow definition if available in node contract
        if hasattr(self, "contract") and hasattr(
            self.contract, "workflow_coordination"
        ):
            if hasattr(self.contract.workflow_coordination, "workflow_definition"):
                object.__setattr__(
                    self,
                    "workflow_definition",
                    self.contract.workflow_coordination.workflow_definition,
                )

    async def process(
        self,
        input_data: ModelOrchestratorInput,
    ) -> ModelOrchestratorOutput:
        """
        Process workflow using workflow-driven coordination.

        Pure workflow pattern: Executes steps, emits actions for deferred execution.

        Args:
            input_data: Orchestrator input with workflow steps and configuration

        Returns:
            Orchestrator output with execution results and emitted actions

        Raises:
            ModelOnexError: If workflow definition not loaded or execution fails

        Example:
            ```python
            import logging
            from uuid import uuid4

            logger = logging.getLogger(__name__)

            # Define workflow steps
            steps_config = [
                {
                    "step_name": "Fetch Data",
                    "step_type": "effect",
                    "timeout_ms": 10000
                },
                {
                    "step_name": "Process Data",
                    "step_type": "compute",
                    "depends_on": [fetch_step_id],
                    "timeout_ms": 15000
                },
            ]

            # Create workflow steps from config
            workflow_steps = node.create_workflow_steps_from_config(steps_config)

            # Execute workflow
            result = await node.execute_workflow_from_contract(
                node.workflow_definition,
                workflow_steps,
                workflow_id=uuid4()
            )

            logger.debug("Status: %s", result.execution_status)
            logger.debug("Actions: %d", len(result.actions_emitted))
            ```
        """
        if not self.workflow_definition:
            raise ModelOnexError(
                message=_ERR_WORKFLOW_DEFINITION_NOT_LOADED,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        # Convert dict steps to ModelWorkflowStep instances
        workflow_steps = self.create_workflow_steps_from_config(input_data.steps)  # type: ignore[arg-type]

        # Extract workflow ID
        workflow_id = input_data.workflow_id

        # Execute workflow from contract
        workflow_result = await self.execute_workflow_from_contract(
            self.workflow_definition,
            workflow_steps,
            workflow_id,
            execution_mode=input_data.execution_mode,
        )

        # Convert WorkflowExecutionResult to ModelOrchestratorOutput
        output = self._convert_workflow_result_to_output(workflow_result)

        return output

    async def validate_contract(self) -> list[str]:
        """
        Validate workflow contract for correctness.

        Returns:
            List of validation errors (empty if valid)

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            errors = await node.validate_contract()
            if errors:
                logger.warning("Contract validation failed: %s", errors)
            else:
                logger.info("Contract is valid!")
            ```
        """
        if not self.workflow_definition:
            return [_ERR_WORKFLOW_DEFINITION_NOT_LOADED]

        # For validation, we need some steps - use empty list for structural validation
        return await self.validate_workflow_contract(self.workflow_definition, [])

    async def validate_workflow_steps(
        self,
        steps: list[ModelWorkflowStep],
    ) -> list[str]:
        """
        Validate workflow steps against contract.

        Args:
            steps: Workflow steps to validate

        Returns:
            List of validation errors (empty if valid)

        Example:
            ```python
            steps = [ModelWorkflowStep(...), ModelWorkflowStep(...)]
            errors = await node.validate_workflow_steps(steps)
            if not errors:
                # Safe to execute workflow
                result = await node.execute_workflow_from_contract(...)
            ```
        """
        if not self.workflow_definition:
            return [_ERR_WORKFLOW_DEFINITION_NOT_LOADED]

        return await self.validate_workflow_contract(self.workflow_definition, steps)

    def get_execution_order_for_steps(
        self,
        steps: list[ModelWorkflowStep],
    ) -> list[UUID]:
        """
        Get topological execution order for workflow steps.

        Args:
            steps: Workflow steps to order

        Returns:
            List of step IDs in execution order

        Raises:
            ModelOnexError: If workflow contains cycles

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            steps = [ModelWorkflowStep(...), ModelWorkflowStep(...)]
            order = node.get_execution_order_for_steps(steps)
            logger.debug("Execution order: %s", order)
            ```
        """
        return self.get_workflow_execution_order(steps)

    def _convert_workflow_result_to_output(
        self,
        workflow_result: WorkflowExecutionResult,
    ) -> ModelOrchestratorOutput:
        """
        Convert WorkflowExecutionResult to ModelOrchestratorOutput.

        Args:
            workflow_result: Result from workflow execution

        Returns:
            ModelOrchestratorOutput with execution details

        Note:
            The start_time and end_time fields currently both contain the workflow
            completion timestamp (when the result was created), not an actual
            execution time range. For the actual execution duration, use
            execution_time_ms instead.

            This behavior is intentional to avoid breaking changes. Future versions
            may track actual start/end times separately.
        """
        # NOTE: Both start_time and end_time are set to the completion timestamp.
        # workflow_result.timestamp represents when the result was created (completion time),
        # not when execution started. For actual duration, use execution_time_ms.
        return ModelOrchestratorOutput(
            execution_status=workflow_result.execution_status.value,
            execution_time_ms=workflow_result.execution_time_ms,
            start_time=workflow_result.timestamp,  # Completion timestamp (not actual start)
            end_time=workflow_result.timestamp,  # Completion timestamp (same as start_time)
            completed_steps=workflow_result.completed_steps,
            failed_steps=workflow_result.failed_steps,
            final_result=None,  # No aggregate result for workflow-driven orchestration
            actions_emitted=workflow_result.actions_emitted,
            metrics={
                "actions_count": float(len(workflow_result.actions_emitted)),
                "completed_count": float(len(workflow_result.completed_steps)),
                "failed_count": float(len(workflow_result.failed_steps)),
            },
        )

    # =========================================================================
    # Workflow State Serialization Methods
    # =========================================================================

    def snapshot_workflow_state(self) -> ModelWorkflowStateSnapshot | None:
        """
        Return current workflow state snapshot.

        Returns the current workflow state as an immutable snapshot that can be
        serialized and restored later. This enables workflow replay and debugging.

        Returns:
            ModelWorkflowStateSnapshot if a workflow execution is in progress,
            None otherwise.

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            # Get current state during workflow execution
            snapshot = node.snapshot_workflow_state()
            if snapshot:
                logger.info("Workflow %s at step %d", snapshot.workflow_id, snapshot.current_step_index)
                logger.info("Completed: %d, Failed: %d",
                    len(snapshot.completed_step_ids),
                    len(snapshot.failed_step_ids))
            ```
        """
        return self._workflow_state

    def restore_workflow_state(self, snapshot: ModelWorkflowStateSnapshot) -> None:
        """
        Restore workflow state from snapshot.

        Restores the internal workflow state from a previously captured snapshot.
        This enables workflow replay and recovery from persisted state.

        Args:
            snapshot: The workflow state snapshot to restore.

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            # Save state before shutdown
            snapshot = node.snapshot_workflow_state()
            # ... persist snapshot to storage ...

            # Later, restore state
            node.restore_workflow_state(snapshot)
            logger.info("Restored workflow to step %d", snapshot.current_step_index)
            ```

        Note:
            The restored snapshot is stored as-is. Since ModelWorkflowStateSnapshot
            is immutable (frozen=True), subsequent workflow operations will create
            new snapshots rather than modifying the restored one.
        """
        self._workflow_state = snapshot

    def get_workflow_snapshot(self) -> dict[str, object]:
        """
        Return state as JSON-serializable dictionary.

        Convenience method that returns the workflow state as a dictionary
        suitable for JSON serialization. Uses Pydantic's model_dump() for
        proper serialization of complex types like UUIDs and datetimes.

        Returns:
            Dictionary representation of the current workflow state.
            Returns an empty dictionary if no workflow execution is in progress.

        Example:
            ```python
            import json
            import logging

            logger = logging.getLogger(__name__)

            # Get state as dictionary for JSON serialization
            state_dict = node.get_workflow_snapshot()
            json_str = json.dumps(state_dict, default=str)
            logger.debug("Workflow state JSON: %s", json_str)

            # Can be restored later via:
            # snapshot = ModelWorkflowStateSnapshot(**state_dict)
            # node.restore_workflow_state(snapshot)
            ```
        """
        if self._workflow_state is None:
            return {}
        return self._workflow_state.model_dump()
