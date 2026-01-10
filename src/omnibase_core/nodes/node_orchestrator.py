"""
NodeOrchestrator - Workflow-driven orchestrator node for coordination.

Primary orchestrator implementation using workflow definitions for coordination.
Zero custom Python code required - all coordination logic defined declaratively.

Key Capabilities:
- Workflow-driven coordination via declarative YAML contracts
- Event-driven message handling with ModelIntent/ModelAction patterns
- Workflow state snapshot and restore capabilities
- Contract-driven handler routing via MixinHandlerRouting (OMN-1293)
"""

import copy
from datetime import timedelta
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.infrastructure.node_core_base import NodeCoreBase
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.mixins.mixin_handler_routing import MixinHandlerRouting
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
from omnibase_core.models.workflow import (
    WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
    ModelWorkflowStateSnapshot,
)
from omnibase_core.utils.util_workflow_executor import WorkflowExecutionResult

# Clock skew tolerance for snapshot timestamp validation
SNAPSHOT_FUTURE_TOLERANCE_SECONDS: int = 60
"""Maximum allowed future timestamp tolerance in seconds.

Allows for minor clock skew between distributed systems when validating
snapshot timestamps. Snapshots with created_at up to this many seconds
in the future are accepted to prevent false rejections due to clock drift.

This tolerance is applied in ``_validate_workflow_snapshot()`` when
checking the ``created_at`` timestamp of ``ModelWorkflowStateSnapshot``.
"""

# Error messages
_ERR_WORKFLOW_DEFINITION_NOT_LOADED = "Workflow definition not loaded"
_ERR_FUTURE_TIMESTAMP = (
    "Invalid workflow snapshot: timestamp {snapshot_time} is in the future "
    "(current: {current_time}, difference: {difference_seconds:.3f}s, "
    "tolerance: {tolerance_seconds}s)"
)
_ERR_STEP_IDS_OVERLAP = "Step IDs cannot be both completed and failed"
_ERR_SCHEMA_VERSION_MISMATCH = (
    "Invalid workflow snapshot: schema_version {snapshot_version} does not match "
    "current schema version {current_version}"
)

# Warning messages for terminal/problematic workflow states
_WARN_WORKFLOW_APPEARS_COMPLETE = (
    "Restoring workflow snapshot to potentially terminal state: "
    "all tracked steps are either completed or failed"
)
_WARN_WORKFLOW_ALL_STEPS_FAILED = (
    "Restoring workflow snapshot where all tracked steps have failed"
)


class NodeOrchestrator(NodeCoreBase, MixinWorkflowExecution, MixinHandlerRouting):
    """
    Workflow-driven orchestrator node for coordination.

    Enables creating orchestrator nodes entirely from YAML contracts without custom Python code.
    Workflow steps, dependencies, and execution modes are all defined in workflow definitions.

    Key Features:
        - Workflow-driven coordination with step dependencies
        - ModelAction emission for deferred execution
        - Workflow state snapshot and restore
        - Contract-driven handler routing via MixinHandlerRouting

    Handler Routing (via MixinHandlerRouting):
        Enables routing events to handlers based on YAML contract configuration.
        Use ``payload_type_match`` routing strategy for orchestrator nodes to route
        by event model class name (e.g., "UserCreatedEvent", "OrderCompletedEvent").

        Example handler_routing contract section::

            handler_routing:
              version: { major: 1, minor: 0, patch: 0 }
              routing_strategy: payload_type_match
              handlers:
                - routing_key: UserCreatedEvent
                  handler_key: handle_user_created
                  message_category: event
                  priority: 0
                - routing_key: OrderCompletedEvent
                  handler_key: handle_order_completed
                  message_category: event
                  priority: 10
              default_handler: handle_unknown_event

    Thread Safety:
            **MVP Design Decision**: NodeOrchestrator uses mutable workflow state intentionally
            for the MVP phase to enable workflow coordination with minimal complexity.
            This is a documented trade-off.

            **Mutable State Components**:
            - `workflow_definition`: Loaded workflow definition reference
            - Workflow execution state (via MixinWorkflowExecution):
              - Active workflow execution tracking
              - Step completion status
              - Workflow context accumulation

            **Current Limitations**:
            NodeOrchestrator instances are NOT thread-safe. Concurrent access will corrupt
            workflow execution state.

            **Mitigation**: Each thread should have its own NodeOrchestrator instance,
            or implement explicit synchronization. See docs/guides/THREADING.md for
            thread-local instance patterns.

            Unsafe Pattern (DO NOT DO THIS)::

                # WRONG - shared mutable state causes race conditions
                shared_node = NodeOrchestrator(container)
                def worker():
                    result = asyncio.run(shared_node.process(input_data))  # Race!
                threads = [Thread(target=worker) for _ in range(4)]
                for t in threads: t.start()

            Safe Pattern 1 - Separate Instances::

                # CORRECT - each thread has its own instance
                def worker():
                    node = NodeOrchestrator(container)  # Per-thread instance
                    result = asyncio.run(node.process(input_data))
                threads = [Thread(target=worker) for _ in range(4)]
                for t in threads: t.start()

            Safe Pattern 2 - External Synchronization::

                # CORRECT - external lock for shared instance
                node = NodeOrchestrator(container)
                lock = threading.Lock()
                def worker():
                    with lock:
                        result = asyncio.run(node.process(input_data))

            Safe Pattern 3 - Immutable Snapshots::

                # CORRECT - snapshots are immutable and safe to share
                snapshot = node.snapshot_workflow_state(deep_copy=True)
                # snapshot can be safely passed to any thread for reading

            **Production Path**: Future versions will support stateless workflow execution
            with external state stores and lease-based coordination. See
            docs/architecture/MUTABLE_STATE_STRATEGY.md for the production improvement roadmap.

        Side Effect Prohibition (v1.0.1 Fix 15 Normative):
            **CRITICAL**: NodeOrchestrator MUST NOT write to external systems directly.

            The orchestrator is a pure coordination layer that:
            - Emits ModelAction objects for deferred execution by target nodes
            - Tracks workflow step completion status
            - Maintains internal execution state

            **Forbidden Operations** (MUST NOT occur during process()):
            - Direct database writes
            - HTTP/gRPC calls to external services
            - File system writes to external paths
            - Message queue publishing (direct)
            - Cache writes to external stores

            **Allowed Operations**:
            - Emitting ModelAction objects via actions_emitted list
            - Internal state management (workflow tracking)
            - Logging (informational only, not business data persistence)

            This separation ensures:
            - Orchestrator execution is deterministic and replayable
            - Side effects are explicit via action emission
            - Target nodes (EFFECT nodes) handle actual external I/O
            - Workflow coordination remains pure and testable

            Subclasses that violate this rule will produce non-deterministic
            behavior and break workflow replay capabilities.

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
                  # Use TIMEOUT_LONG_MS (300000) for long-running workflows
                  timeout_ms: 300000  # See omnibase_core.constants.TIMEOUT_LONG_MS
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

            # Define typed workflow steps (v1.0.2: steps MUST be ModelWorkflowStep)
            from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

            fetch_step_id = uuid4()
            process_step_id = uuid4()

            workflow_steps = [
                ModelWorkflowStep(
                    step_id=fetch_step_id,
                    step_name="Fetch Data",
                    step_type="effect",
                    timeout_ms=10000,
                ),
                ModelWorkflowStep(
                    step_id=process_step_id,
                    step_name="Process Data",
                    step_type="compute",
                    depends_on=[fetch_step_id],
                    timeout_ms=15000,
                ),
            ]

            # Execute workflow via process method (v1.0.2: no dict coercion)
            input_data = ModelOrchestratorInput(
                workflow_id=uuid4(),
                steps=workflow_steps,
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

        v1.0.2 Normative (Contract Loading Responsibility):
            NodeOrchestrator MUST NOT load workflow_definition from self.contract.
            Contract resolution occurs at container build time, not inside orchestrator.
            workflow_definition MUST be injected by container or dispatcher layer
            prior to calling process(). NodeOrchestrator receives fully-resolved
            typed models, not raw contracts.

            Rationale: Separation of concerns - contract loading is infrastructure
            (SPI/Infra), execution is core logic (Core).

        Args:
            container: ONEX container for dependency injection

        Raises:
            ModelOnexError: If container is invalid or initialization fails
        """
        super().__init__(container)

        # Initialize workflow_definition to None - MUST be injected externally
        # v1.0.2: NodeOrchestrator does NOT load from self.contract
        # v1.0.2: workflow_definition MUST be treated as immutable once injected
        # Use object.__setattr__() to bypass Pydantic validation when mixins with
        # Pydantic BaseModel are in the MRO (e.g., MixinEventBus in ModelServiceOrchestrator)
        object.__setattr__(self, "workflow_definition", None)

        # Initialize handler routing from contract (optional - not all orchestrators have it)
        # The handler_routing subcontract enables contract-driven message routing.
        # If the node's contract has handler_routing defined, initialize the routing table.
        handler_routing = None
        if hasattr(self, "contract") and self.contract is not None:
            handler_routing = getattr(self.contract, "handler_routing", None)

        if handler_routing is not None:
            handler_registry: object = container.get_service("ProtocolHandlerRegistry")  # type: ignore[arg-type]  # Protocol-based DI lookup per ONEX conventions
            self._init_handler_routing(handler_routing, handler_registry)  # type: ignore[arg-type]  # Registry retrieved via DI

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
            from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep

            logger = logging.getLogger(__name__)

            # Define step IDs for dependency tracking
            fetch_step_id = uuid4()
            process_step_id = uuid4()

            # Define typed workflow steps (v1.0.2 compliant - no dict coercion)
            workflow_steps = [
                ModelWorkflowStep(
                    step_id=fetch_step_id,
                    step_name="Fetch Data",
                    step_type="effect",
                    timeout_ms=10000,
                ),
                ModelWorkflowStep(
                    step_id=process_step_id,
                    step_name="Process Data",
                    step_type="compute",
                    depends_on=[fetch_step_id],
                    timeout_ms=15000,
                ),
            ]

            # Create action for each step via orchestrator
            result = await node.execute_workflow_from_contract(
                node.workflow_definition,
                workflow_steps,
                workflow_id=uuid4()
            )

            logger.debug("Status: %s", result.execution_status)
            logger.debug("Actions created: %d", len(result.actions_emitted))
            ```
        """
        if not self.workflow_definition:
            raise ModelOnexError(
                message=_ERR_WORKFLOW_DEFINITION_NOT_LOADED,
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_WORKFLOW_NOT_LOADED,
            )

        # v1.0.2: Steps are already typed ModelWorkflowStep instances - no coercion needed
        # Steps MUST arrive as typed instances. Orchestrator does NOT coerce dicts.
        # Core does NOT parse YAML. Core does NOT coerce dicts into models.
        workflow_steps = input_data.steps

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

        This transformation follows the v1.0.1 Fix 14 normative rule:
        **OrchestratorOutput MUST contain only data derivable from the pure result.**

        The mapping is deterministic and one-to-one:

        +----------------------------+----------------------------------+
        | WorkflowExecutionResult    | ModelOrchestratorOutput          |
        +============================+==================================+
        | execution_status.value     | execution_status                 |
        | execution_time_ms          | execution_time_ms                |
        | timestamp                  | start_time, end_time             |
        | completed_steps            | completed_steps                  |
        | failed_steps               | failed_steps                     |
        | skipped_steps              | skipped_steps                    |
        | actions_emitted            | actions_emitted                  |
        | (derived)                  | metrics (computed counts)        |
        | (not set)                  | final_result = None              |
        +----------------------------+----------------------------------+

        Args:
            workflow_result: Result from workflow execution (pure data structure)

        Returns:
            ModelOrchestratorOutput with execution details derived only from
            the workflow result - no external state or side effects consulted.

        Note:
            The start_time and end_time fields currently both contain the workflow
            completion timestamp (when the result was created), not an actual
            execution time range. For the actual execution duration, use
            execution_time_ms instead.

            This behavior is intentional to avoid breaking changes. Future versions
            may track actual start/end times separately.

        Transformation Guarantees (v1.0.1 Normative):
            - Output contains ONLY data derivable from workflow_result
            - No container services consulted during transformation
            - No external I/O performed during transformation
            - Transformation is deterministic (same input -> same output)
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
            skipped_steps=workflow_result.skipped_steps,  # v1.0.1 Fix 17
            final_result=None,  # No aggregate result for workflow-driven orchestration
            actions_emitted=workflow_result.actions_emitted,
            metrics={
                "actions_count": float(len(workflow_result.actions_emitted)),
                "completed_count": float(len(workflow_result.completed_steps)),
                "failed_count": float(len(workflow_result.failed_steps)),
                "skipped_count": float(
                    len(workflow_result.skipped_steps)
                ),  # v1.0.1 Fix 17
            },
        )

    # =========================================================================
    # Workflow State Serialization Methods
    # =========================================================================

    def snapshot_workflow_state(
        self, *, deep_copy: bool = False
    ) -> ModelWorkflowStateSnapshot | None:
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

        Args:
            deep_copy: If ``True``, returns a deep copy of the snapshot to prevent
                any mutation of internal state. Defaults to ``False`` for performance.
                When ``True``, uses ``copy.deepcopy()`` to create fully independent
                nested structures.

        Returns:
            ``ModelWorkflowStateSnapshot | None`` - The frozen, strongly-typed
            workflow state snapshot if workflow state has been captured, ``None``
            if no workflow execution has occurred or state was not set.

            When ``deep_copy=False`` (default):
            - Returns internal state reference (O(1) operation)
            - Callers MUST NOT mutate ``snapshot.context`` dict contents
            - Suitable for read-only access in single-threaded contexts

            When ``deep_copy=True``:
            - Returns fully independent copy (O(n) operation)
            - Safe for concurrent access and modification
            - Recommended when isolation is required

        Thread Safety:
            The returned ``ModelWorkflowStateSnapshot`` is frozen (immutable fields)
            and safe to pass between threads for read access. However:

            - **Safe**: Passing snapshot to other threads for reading
            - **Safe**: Serializing snapshot via ``model_dump()``
            - **Safe**: Reading ``completed_step_ids`` and ``failed_step_ids`` (tuples)
            - **WARNING**: Do NOT mutate ``snapshot.context`` dict contents -
              this violates the immutability contract and affects the node state
            - **WARNING**: When deep_copy=False, this method returns the internal
              state reference, not a deep copy. Mutating nested context structures
              affects the node's actual state and may cause race conditions.

            For isolation, use deep_copy=True or create a deep copy manually::

                # Option 1: Use deep_copy parameter (recommended)
                isolated_snapshot = node.snapshot_workflow_state(deep_copy=True)

                # Option 2: Manual deep copy
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
              mutable objects (lists, dicts), use deep_copy=True if isolation
              is required for concurrent access patterns.

        Performance Considerations:
            - **Default (deep_copy=False)**: O(1) operation, returns internal reference.
              Suitable for read-only access in single-threaded contexts.
            - **With deep_copy=True**: O(n) where n is the serialized context size.
              Creates a complete independent copy of all nested structures.

            Approximate overhead for deep_copy=True:

            - Context < 1KB: < 0.1ms (negligible)
            - Context 1-10KB: 0.1-1ms
            - Context 10-100KB: 1-10ms
            - Context > 100KB: Consider restructuring to avoid large contexts

            Recommendations:

            - Use ``deep_copy=False`` (default) for hot paths and read-only access
            - Use ``deep_copy=True`` when:

              - Passing snapshots to untrusted code
              - Concurrent access patterns require isolation
              - Modifying context copy without affecting node state

            Warning:
                Large context dicts (>100KB) with ``deep_copy=True`` can impact
                performance. Consider using ``validate_context_size()`` to enforce
                size limits in production.

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

            # For isolation (e.g., concurrent access), use deep_copy=True
            safe_snapshot = node.snapshot_workflow_state(deep_copy=True)
            ```

        See Also:
            get_workflow_snapshot: Returns dict[str, object] for JSON serialization
                and external use.
            restore_workflow_state: Restores state from a ModelWorkflowStateSnapshot.
            update_workflow_state: Manually updates workflow state.
        """
        if self._workflow_state is None:
            return None
        if deep_copy:
            return copy.deepcopy(self._workflow_state)
        return self._workflow_state

    def _validate_workflow_snapshot(
        self,
        snapshot: ModelWorkflowStateSnapshot,
    ) -> None:
        """
        Validate workflow snapshot for basic sanity.

        Ensures the restored snapshot represents a valid workflow state:
        - Timestamp sanity check (created_at not too far in the future)
        - Step IDs overlap check (a step cannot be both completed AND failed)

        Additionally, emits warnings (but does not block restore) for potentially
        terminal workflow states:
        - All tracked steps failed (workflow completely failed)
        - Workflow appears complete (all steps either completed or failed)

        Unlike NodeReducer which validates state names against FSM contract states,
        NodeOrchestrator's workflow definition doesn't have a fixed set of "valid
        step indices" - the step index can be any non-negative integer (already
        enforced by Field(ge=0) constraint in ModelWorkflowStateSnapshot).

        Clock Skew Tolerance:
            A tolerance of ``SNAPSHOT_FUTURE_TOLERANCE_SECONDS`` (default: 60s)
            is applied to future timestamp validation to account for minor clock
            drift between distributed systems. Snapshots with timestamps up to
            this tolerance in the future are accepted.

        Args:
            snapshot: Workflow state snapshot to validate

        Raises:
            ModelOnexError: If snapshot fails validation (e.g., future timestamp
                beyond tolerance, overlapping step IDs between completed and failed sets)

        Note:
            This validation prevents injection of invalid snapshots during
            restore operations, ensuring workflow consistency and integrity.
            Warnings for terminal states are logged but do not block the restore,
            as there are legitimate use cases (e.g., replay, analysis, debugging).
        """
        from datetime import UTC, datetime

        # Schema version check: snapshot must be compatible with current version
        if snapshot.schema_version != WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION:
            raise ModelOnexError(
                message=_ERR_SCHEMA_VERSION_MISMATCH.format(
                    snapshot_version=snapshot.schema_version,
                    current_version=WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "snapshot_schema_version": snapshot.schema_version,
                    "current_schema_version": WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
                    "workflow_id": str(snapshot.workflow_id)
                    if snapshot.workflow_id
                    else None,
                },
            )

        # Timestamp sanity check: created_at should not be too far in the future
        # Allow tolerance for clock skew between distributed systems
        now = datetime.now(UTC)
        tolerance = timedelta(seconds=SNAPSHOT_FUTURE_TOLERANCE_SECONDS)

        # Handle naive datetime (assume UTC)
        snapshot_time = snapshot.created_at
        if snapshot_time.tzinfo is None:
            snapshot_time = snapshot_time.replace(tzinfo=UTC)

        if snapshot_time > (now + tolerance):
            difference_seconds = (snapshot_time - now).total_seconds()
            raise ModelOnexError(
                message=_ERR_FUTURE_TIMESTAMP.format(
                    snapshot_time=snapshot_time.isoformat(),
                    current_time=now.isoformat(),
                    difference_seconds=difference_seconds,
                    tolerance_seconds=SNAPSHOT_FUTURE_TOLERANCE_SECONDS,
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={
                    "snapshot_timestamp": snapshot_time.isoformat(),
                    "current_time": now.isoformat(),
                    "difference_seconds": difference_seconds,
                    "tolerance_seconds": SNAPSHOT_FUTURE_TOLERANCE_SECONDS,
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

        # Warn about potentially terminal workflow states (but don't block restore)
        # These warnings help identify restoration to states that may not progress further
        completed_count = len(completed_set)
        failed_count = len(failed_set)
        total_tracked = completed_count + failed_count

        # Build context for warnings
        warning_context: dict[str, object] = {
            "workflow_id": str(snapshot.workflow_id) if snapshot.workflow_id else None,
            "current_step_index": snapshot.current_step_index,
            "completed_count": completed_count,
            "failed_count": failed_count,
        }

        # Check if all tracked steps failed (workflow completely failed)
        if failed_count > 0 and completed_count == 0:
            emit_log_event_sync(
                level=EnumLogLevel.WARNING,
                message=_WARN_WORKFLOW_ALL_STEPS_FAILED,
                context=warning_context,
            )
        # Check if workflow appears complete (all steps either completed or failed)
        # This heuristic: step_index >= total_tracked AND we have some tracked steps
        elif total_tracked > 0 and snapshot.current_step_index >= total_tracked:
            emit_log_event_sync(
                level=EnumLogLevel.WARNING,
                message=_WARN_WORKFLOW_APPEARS_COMPLETE,
                context=warning_context,
            )

    def restore_workflow_state(self, snapshot: ModelWorkflowStateSnapshot) -> None:
        """
        Restore workflow state from snapshot.

        Restores the internal workflow state from a previously captured snapshot.
        This enables workflow replay and recovery from persisted state.

        Validation performed:
            - Schema version compatibility check
            - Timestamp sanity check (``created_at`` not too far in the future,
              with 60s clock skew tolerance)
            - Step IDs overlap check (a step cannot be both completed AND failed)
            - Warnings for potentially terminal workflow states (all steps
              completed/failed)

        Args:
            snapshot: ``ModelWorkflowStateSnapshot`` - The workflow state snapshot
                to restore. The snapshot is stored as-is (not deep copied) -
                caller retains shared reference to any mutable nested context data.

        Raises:
            ModelOnexError: If snapshot fails validation.

            Error codes:
                - ``VALIDATION_ERROR``: Schema version mismatch or step IDs overlap
                  (a step cannot be both completed AND failed)
                - ``INVALID_STATE``: Timestamp is in the future (beyond 60s
                  clock skew tolerance)

        Thread Safety:
            **WARNING: This method is NOT thread-safe.**

            Modifies internal ``_workflow_state`` attribute with NO synchronization:

            - **NOT Safe**: Calling from multiple threads simultaneously
            - **NOT Safe**: Calling while another thread reads via ``snapshot_workflow_state()``
            - **NOT Safe**: Calling while another thread executes ``process()``

            **Recommended Patterns**:

            1. **Separate Instances** (preferred)::

                # Each thread gets its own NodeOrchestrator instance
                def worker():
                    node = NodeOrchestrator(container)
                    node.restore_workflow_state(snapshot)
                    asyncio.run(node.process(input_data))

            2. **External Synchronization**::

                # Use lock for shared instance
                node = NodeOrchestrator(container)
                lock = threading.Lock()
                def worker():
                    with lock:
                        node.restore_workflow_state(snapshot)
                        asyncio.run(node.process(input_data))

            The provided snapshot should not be mutated after calling this method,
            as the node stores a direct reference (not a deep copy). For complete
            isolation, create a deep copy before passing::

                from copy import deepcopy
                isolated = deepcopy(snapshot)
                node.restore_workflow_state(isolated)

            See ``docs/guides/THREADING.md`` for comprehensive thread safety patterns.

        Context Considerations:
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

    def get_workflow_snapshot(
        self, *, deep_copy: bool = False
    ) -> dict[str, object] | None:
        """
        Return workflow state as a JSON-serializable dictionary.

        Converts the current workflow state snapshot to a plain dictionary
        suitable for JSON serialization, API responses, or external storage
        systems that require dict format. Uses Pydantic's ``mode="json"``
        for proper JSON-native type conversion.

        **Key Difference from snapshot_workflow_state()**:
            - ``get_workflow_snapshot()`` → ``dict[str, object]`` for external use
              (JSON APIs, storage, logging, cross-service communication)
            - ``snapshot_workflow_state()`` → ``ModelWorkflowStateSnapshot`` for internal use
              (type-safe access, Pydantic validation, direct restoration via
              ``restore_workflow_state()``)

        For strongly-typed access to workflow state with validation and direct
        restoration, use ``snapshot_workflow_state()`` instead.

        Args:
            deep_copy: If ``True``, returns a deep copy of the snapshot dictionary
                to prevent any mutation of nested structures. Defaults to ``False``
                for performance. When ``True``, uses ``copy.deepcopy()`` to create
                fully independent nested structures.

                Note: Pydantic's ``model_dump()`` creates a new dict, but nested
                mutable objects (lists, dicts in context) may share references
                with internal state when ``deep_copy=False``.

        Returns:
            ``dict[str, object] | None`` - Dictionary with JSON-serializable
            workflow state data, or ``None`` if no workflow execution is in progress.

            Dictionary structure (when workflow state exists):
                - ``workflow_id``: str | None - Workflow ID (UUID as string)
                - ``current_step_index``: int - Current step index (0-based)
                - ``completed_step_ids``: list[str] - Completed step IDs (UUIDs as strings)
                - ``failed_step_ids``: list[str] - Failed step IDs (UUIDs as strings)
                - ``context``: dict - Workflow context data (arbitrary JSON values)
                - ``created_at``: str - Snapshot creation timestamp (ISO format)
                - ``schema_version``: int - Snapshot schema version number

            When ``deep_copy=False`` (default):
            - Returns new dict from Pydantic ``model_dump(mode="json")``
            - Nested mutable objects may share references with internal state
            - Suitable for immediate JSON serialization
            - O(n) operation for model_dump

            When ``deep_copy=True``:
            - Returns fully independent dict with deep-copied nested structures
            - Safe for storing and modifying later
            - O(n + m) operation (model_dump + deepcopy)

            JSON-native type conversions applied (``mode="json"``):
            - UUIDs → strings
            - datetimes → ISO format strings
            - tuples → lists
            - All values are JSON-serializable without custom encoders

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

        Performance Considerations:
            - **Default (deep_copy=False)**: O(n) operation for ``model_dump()``,
              but nested mutable objects may share references with internal state.
              Suitable for immediate serialization or single-threaded access.
            - **With deep_copy=True**: O(n) + O(m) where n is model_dump cost and
              m is deepcopy cost. Creates fully independent nested structures.

            Approximate overhead for deep_copy=True (additional to model_dump):

            - Context < 1KB: < 0.1ms (negligible)
            - Context 1-10KB: 0.1-1ms
            - Context 10-100KB: 1-10ms
            - Context > 100KB: Consider restructuring to avoid large contexts

            Recommendations:

            - Use ``deep_copy=False`` (default) for immediate JSON serialization
            - Use ``deep_copy=True`` when:

              - Storing the dict for later modification
              - Passing to code that may mutate nested structures
              - Concurrent access patterns require isolation

            Warning:
                Large context dicts (>100KB) with ``deep_copy=True`` can impact
                performance. Consider using ``validate_context_size()`` to enforce
                size limits in production.

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

            # For full isolation of nested structures, use deep_copy=True
            safe_dict = node.get_workflow_snapshot(deep_copy=True)
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
        result = self._workflow_state.model_dump(mode="json")
        if deep_copy:
            return copy.deepcopy(result)
        return result
