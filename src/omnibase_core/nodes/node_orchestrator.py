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
from omnibase_core.models.workflow import ModelWorkflowStateSnapshot
from omnibase_core.utils.workflow_executor import WorkflowExecutionResult

# Error messages
_ERR_WORKFLOW_DEFINITION_NOT_LOADED = "Workflow definition not loaded"
_ERR_FUTURE_TIMESTAMP = (
    "Invalid workflow snapshot: timestamp {snapshot_time} is in the future "
    "(current: {current_time}, difference: {difference_seconds:.3f}s)"
)
_ERR_STEP_IDS_OVERLAP = "Step IDs cannot be both completed and failed"


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
        Return current workflow state as a strongly-typed snapshot model.

        Returns the current workflow state as an immutable ``ModelWorkflowStateSnapshot``
        that can be serialized and restored later. This enables workflow replay,
        debugging, and state persistence with full type safety.

        **Key Difference from get_workflow_snapshot()**:
            - ``snapshot_workflow_state()`` → ``ModelWorkflowStateSnapshot`` for internal use
              (type-safe access, Pydantic validation, direct restoration via
              ``restore_workflow_state()``)
            - ``get_workflow_snapshot()`` → ``dict[str, object]`` for external use
              (JSON APIs, storage, logging, cross-service communication)

        State Population:
            The ``_workflow_state`` attribute is populated in two ways:

            1. **Automatic** (recommended): After ``execute_workflow_from_contract()``
               or ``process()`` completes, the workflow state is automatically captured
               with execution results (completed/failed steps, execution metadata).

            2. **Manual**: Via ``update_workflow_state()`` for custom state tracking,
               or ``restore_workflow_state()`` to restore from a persisted snapshot.

        Returns:
            ModelWorkflowStateSnapshot if workflow state has been captured,
            None if no workflow execution has occurred or state was not set.
            The returned snapshot is the internal state reference - callers
            MUST NOT mutate the context dict contents (see Thread Safety).

        Thread Safety:
            The returned ``ModelWorkflowStateSnapshot`` is frozen (immutable fields)
            and safe to pass between threads for read access. However:

            - **Safe**: Passing snapshot to other threads for reading
            - **Safe**: Serializing snapshot via ``model_dump()``
            - **Safe**: Reading ``completed_step_ids`` and ``failed_step_ids`` (tuples)
            - **WARNING**: Do NOT mutate ``snapshot.context`` dict contents -
              this violates the immutability contract and affects the node state
            - **WARNING**: This method returns the internal state reference,
              not a deep copy. Mutating nested context structures affects the
              node's actual state and may cause race conditions.

            For isolation, create a deep copy::

                import copy
                isolated_snapshot = copy.deepcopy(node.snapshot_workflow_state())

        Context Considerations:
            The ``context`` field is a ``dict[str, Any]`` that may contain:

            - **PII Risk**: User data, session info, or other sensitive data
              may be stored in context by workflow implementations. Use
              ``ModelWorkflowStateSnapshot.sanitize_context_for_logging()``
              before logging or persisting to external systems.

            - **Size Limits**: No enforced size limits, but recommended:
              - Max keys: 100 (for serialization performance)
              - Max total serialized size: 1MB
              - Max nesting depth: 5 levels

            - **Deep Copy for Nested Structures**: If context contains nested
              mutable objects (lists, dicts), the caller should deep copy if
              isolation is required for concurrent access patterns.

        Example:
            ```python
            import logging

            logger = logging.getLogger(__name__)

            # After workflow execution, state is automatically available
            result = await node.process(input_data)
            snapshot = node.snapshot_workflow_state()
            if snapshot:
                # Type-safe access to snapshot fields
                logger.info("Workflow %s at step %d", snapshot.workflow_id, snapshot.current_step_index)
                logger.info("Completed: %d, Failed: %d",
                    len(snapshot.completed_step_ids),
                    len(snapshot.failed_step_ids))

                # Can be restored later for workflow replay
                node.restore_workflow_state(snapshot)
            ```

        See Also:
            get_workflow_snapshot: Returns dict[str, object] for JSON serialization
                and external use.
            restore_workflow_state: Restores state from a ModelWorkflowStateSnapshot.
            update_workflow_state: Manually updates workflow state.
        """
        return self._workflow_state

    def _validate_workflow_snapshot(
        self,
        snapshot: ModelWorkflowStateSnapshot,
    ) -> None:
        """
        Validate workflow snapshot for basic sanity.

        Ensures the restored snapshot represents a valid workflow state:
        - Timestamp sanity check (created_at not in the future)
        - Step IDs overlap check (a step cannot be both completed AND failed)

        Unlike NodeReducer which validates state names against FSM contract states,
        NodeOrchestrator's workflow definition doesn't have a fixed set of "valid
        step indices" - the step index can be any non-negative integer (already
        enforced by Field(ge=0) constraint in ModelWorkflowStateSnapshot).

        Args:
            snapshot: Workflow state snapshot to validate

        Raises:
            ModelOnexError: If snapshot fails validation (e.g., future timestamp,
                overlapping step IDs between completed and failed sets)

        Note:
            This validation prevents injection of invalid snapshots during
            restore operations, ensuring workflow consistency and integrity.
        """
        from datetime import UTC, datetime

        # Timestamp sanity check: created_at should not be in the future
        now = datetime.now(UTC)

        # Handle naive datetime (assume UTC)
        snapshot_time = snapshot.created_at
        if snapshot_time.tzinfo is None:
            snapshot_time = snapshot_time.replace(tzinfo=UTC)

        if snapshot_time > now:
            difference_seconds = (snapshot_time - now).total_seconds()
            raise ModelOnexError(
                message=_ERR_FUTURE_TIMESTAMP.format(
                    snapshot_time=snapshot_time.isoformat(),
                    current_time=now.isoformat(),
                    difference_seconds=difference_seconds,
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={
                    "snapshot_timestamp": snapshot_time.isoformat(),
                    "current_time": now.isoformat(),
                    "difference_seconds": difference_seconds,
                    "workflow_id": str(snapshot.workflow_id)
                    if snapshot.workflow_id
                    else None,
                },
            )

        # Check for step_ids overlap: a step cannot be both completed AND failed
        completed_set = set(snapshot.completed_step_ids)
        failed_set = set(snapshot.failed_step_ids)
        overlap = completed_set & failed_set

        if overlap:
            raise ModelOnexError(
                message=f"{_ERR_STEP_IDS_OVERLAP}: {overlap}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "overlapping_step_ids": [str(sid) for sid in overlap],
                    "workflow_id": str(snapshot.workflow_id)
                    if snapshot.workflow_id
                    else None,
                },
            )

    def restore_workflow_state(self, snapshot: ModelWorkflowStateSnapshot) -> None:
        """
        Restore workflow state from snapshot.

        Restores the internal workflow state from a previously captured snapshot.
        This enables workflow replay and recovery from persisted state.

        Validation performed:
            - Timestamp sanity check (created_at not in the future)
            - Step IDs overlap check (a step cannot be both completed AND failed)

        Args:
            snapshot: The workflow state snapshot to restore. The snapshot is
                stored as-is (not deep copied) - caller retains shared reference
                to any mutable nested context data.

        Raises:
            ModelOnexError: If snapshot fails validation. Error codes:
                - INVALID_STATE: Timestamp is in the future
                - VALIDATION_ERROR: Step IDs overlap (both completed and failed)

        Thread Safety:
            This method modifies the internal ``_workflow_state`` attribute, which
            is NOT thread-safe:

            - **NOT Safe**: Calling from multiple threads simultaneously
            - **NOT Safe**: Calling while another thread reads via ``snapshot_workflow_state()``
            - **Recommended**: Use external synchronization (lock) if concurrent
              access is required, or use separate NodeOrchestrator instances per thread

            The provided snapshot should not be mutated after calling this method,
            as the node stores a direct reference (not a deep copy).

        Context Considerations:
            The restored snapshot's ``context`` dict may contain sensitive data:

            - **PII Risk**: If restoring from external storage, validate that
              context does not contain unexpected PII before processing. Use
              ``ModelWorkflowStateSnapshot.sanitize_context_for_logging()`` if
              you need to log the restored state.

            - **Size Validation**: Large context dicts may impact performance;
              consider validating size before restore in production.

            - **No Deep Copy**: The snapshot is stored as-is. If caller needs
              to continue modifying the snapshot's context, create a copy first::

                  from copy import deepcopy
                  isolated = ModelWorkflowStateSnapshot(
                      workflow_id=snapshot.workflow_id,
                      current_step_index=snapshot.current_step_index,
                      completed_step_ids=snapshot.completed_step_ids,
                      failed_step_ids=snapshot.failed_step_ids,
                      context=deepcopy(snapshot.context),
                      created_at=snapshot.created_at,
                  )
                  node.restore_workflow_state(isolated)

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

        See Also:
            snapshot_workflow_state: Capture current state as ModelWorkflowStateSnapshot.
            _validate_workflow_snapshot: Internal validation logic details.
        """
        # Validate snapshot before restoring
        self._validate_workflow_snapshot(snapshot)

        self._workflow_state = snapshot

    def get_workflow_snapshot(self) -> dict[str, object] | None:
        """
        Return workflow state as a JSON-serializable dictionary.

        Converts the current workflow state snapshot to a plain dictionary
        suitable for JSON serialization, API responses, or external storage
        systems that require dict format. Uses ``mode="json"`` for proper
        JSON-native type conversion (e.g., UUIDs become strings, datetimes
        become ISO format strings).

        **Key Difference from snapshot_workflow_state()**:
            - ``get_workflow_snapshot()`` → ``dict[str, object]`` for external use
              (JSON APIs, storage, logging, cross-service communication)
            - ``snapshot_workflow_state()`` → ``ModelWorkflowStateSnapshot`` for internal use
              (type-safe access, Pydantic validation, direct restoration)

        Returns:
            dict[str, object] with workflow state data that can be directly
            serialized to JSON (all values are JSON-native types), or None
            if no workflow execution is in progress. The returned dict is
            a NEW dict created by Pydantic's ``model_dump()`` - modifications
            do not affect the internal node state.

        Thread Safety:
            This method is thread-safe for the dict creation itself (Pydantic
            model_dump creates a new dict). However, the underlying node state
            access is NOT synchronized:

            - **Safe**: The returned dict is independent of internal state
            - **Safe**: The dict can be modified without affecting node state
            - **Warning**: If another thread calls ``restore_workflow_state()``
              during this call, results may be inconsistent
            - **Recommended**: For concurrent scenarios, use external locking
              or separate NodeOrchestrator instances per thread

        Context Considerations:
            The returned dict contains a copy of the ``context`` field:

            - **PII Risk**: Before logging or sending to external systems,
              sanitize the context. Since this returns a dict, you must
              sanitize BEFORE calling this method using
              ``ModelWorkflowStateSnapshot.sanitize_context_for_logging()``
              on the model from ``snapshot_workflow_state()``.

            - **Safe for Persistence**: The returned dict is fully independent
              and can be safely stored, serialized, or transmitted without
              affecting node state.

            - **JSON-Native Types**: All values are already converted to
              JSON-native types (strings, numbers, lists, dicts). No custom
              serializers needed.

        Example:
            ```python
            import json
            import logging

            logger = logging.getLogger(__name__)

            snapshot_dict = node.get_workflow_snapshot()
            if snapshot_dict:
                # Direct JSON serialization - no default=str needed
                json_str = json.dumps(snapshot_dict)
                logger.debug("Workflow state JSON: %s", json_str)

                # Access fields as dict keys
                logger.info("Current step: %d", snapshot_dict["current_step_index"])
                logger.info("Completed: %d steps", len(snapshot_dict["completed_step_ids"]))

                # Send to external API
                response = await client.post("/workflow/state", json=snapshot_dict)

                # For restoration, use snapshot_workflow_state() to get the model
            ```

        See Also:
            snapshot_workflow_state: Returns strongly-typed ModelWorkflowStateSnapshot
                for internal use and restoration.
            restore_workflow_state: Restores state from a ModelWorkflowStateSnapshot.
        """
        if self._workflow_state is None:
            return None
        # Use mode="json" for proper JSON-native serialization:
        # - UUIDs become strings
        # - datetimes become ISO format strings
        # - All values are JSON-serializable without custom encoders
        return self._workflow_state.model_dump(mode="json")
