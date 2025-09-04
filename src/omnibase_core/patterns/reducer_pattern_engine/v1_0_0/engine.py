"""
ReducerPatternEngine - Core engine extending NodeReducer for multi-workflow execution.

Provides the main engine for the Reducer Pattern Engine Phase 1 implementation,
extending the existing NodeReducer architecture with workflow routing capabilities.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.core.node_reducer import NodeReducer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from ..models.state_transitions import WorkflowState, WorkflowStateModel
from .contracts import (
    BaseSubreducer,
    WorkflowMetrics,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowType,
)
from .metrics import ReducerMetricsCollector
from .registry import ReducerSubreducerRegistry
from .router import WorkflowRouter


class ReducerPatternEngine(NodeReducer):
    """
    Multi-workflow execution engine extending NodeReducer.

    Provides workflow routing, subreducer management, and instance isolation
    for processing multiple workflow types through the ONEX four-node architecture.

    Phase 2 Implementation:
    - Multi-workflow type support (document_regeneration, data_analysis, report_generation)
    - Enhanced hash-based routing with ReducerSubreducerRegistry
    - Instance isolation for concurrent workflow processing
    - Comprehensive metrics collection and performance monitoring
    - Pydantic state machine for workflow lifecycle management
    - Manual subreducer registration system

    Extends NodeReducer for:
    - ONEX four-node architecture compliance
    - Container-based dependency injection
    - Structured logging and error handling
    - Contract model validation
    """

    def __init__(
        self,
        container: ModelONEXContainer,
        max_workflow_states: int = 1000,
        state_retention_hours: int = 24,
    ) -> None:
        """
        Initialize ReducerPatternEngine with ModelONEXContainer.

        Args:
            container: ONEX container for dependency injection
            max_workflow_states: Maximum workflow states to keep in memory
            state_retention_hours: Hours to retain completed workflow states

        Raises:
            OnexError: If initialization fails
        """
        # Initialize parent NodeReducer
        super().__init__(container)

        # Initialize Phase 2 components
        self._router = WorkflowRouter()
        self._registry = ReducerSubreducerRegistry()
        self._metrics_collector = ReducerMetricsCollector()
        self._metrics = WorkflowMetrics()

        # State management with thread-safe access
        self._active_workflows: Dict[str, WorkflowRequest] = {}
        self._workflow_states: Dict[str, WorkflowStateModel] = {}
        self._state_lock = threading.RLock()  # Re-entrant lock for nested operations

        # Memory cleanup configuration (configurable parameters)
        self._max_workflow_states = max_workflow_states
        self._state_retention_hours = state_retention_hours
        self._last_cleanup_time = datetime.now()

        emit_log_event(
            level=LogLevel.INFO,
            event="reducer_pattern_engine_initialized",
            message="ReducerPatternEngine Phase 2 initialized successfully",
            context={
                "engine_type": self.__class__.__name__,
                "container_type": type(container).__name__,
                "phase": "2",
                "supported_workflow_types": [wt.value for wt in WorkflowType],
                "components": [
                    "router",
                    "registry",
                    "metrics_collector",
                    "state_machine",
                ],
            },
        )

    def register_subreducer(
        self, subreducer: BaseSubreducer, workflow_types: List[WorkflowType]
    ) -> None:
        """
        Register a subreducer for handling specific workflow types.

        Args:
            subreducer: The subreducer implementation
            workflow_types: List of workflow types this subreducer handles

        Raises:
            OnexError: If registration fails
        """
        try:
            # Register with both router (for routing) and registry (for management)
            for workflow_type in workflow_types:
                # Register subreducer class in registry for management
                self._registry.register_subreducer(
                    workflow_type=workflow_type,
                    subreducer_class=type(subreducer),
                    metadata={
                        "instance_name": subreducer.name,
                        "registered_at": time.time(),
                        "phase": "2",
                    },
                )

            # Register in router for routing functionality
            self._router.register_subreducer(subreducer, workflow_types)

            emit_log_event(
                level=LogLevel.INFO,
                event="subreducer_registered_in_engine",
                message=f"Subreducer {subreducer.name} registered in engine (Phase 2)",
                context={
                    "subreducer_name": subreducer.name,
                    "workflow_types": [wt.value for wt in workflow_types],
                    "registry_status": "registered",
                    "router_status": "registered",
                },
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                event="subreducer_registration_failed_in_engine",
                message=f"Failed to register subreducer in engine: {str(e)}",
                context={
                    "subreducer_name": getattr(subreducer, "name", "unknown"),
                    "error": str(e),
                },
            )
            raise

    async def process_workflow(self, request: WorkflowRequest) -> WorkflowResponse:
        """
        Process a workflow request through the Reducer Pattern Engine (Phase 2).

        Enhanced workflow processing that:
        1. Creates workflow state tracking
        2. Routes the workflow to appropriate subreducer
        3. Processes through subreducer with state management
        4. Collects comprehensive metrics
        5. Returns structured response with results

        Args:
            request: The workflow request to process

        Returns:
            WorkflowResponse: The processing result with enhanced metadata

        Raises:
            OnexError: If processing fails
        """
        start_time = time.perf_counter()

        try:
            # Step 1: Initialize workflow state
            workflow_state = WorkflowStateModel(
                workflow_id=request.workflow_id,
                workflow_type=request.workflow_type.value,
                instance_id=request.instance_id,
                correlation_id=request.correlation_id,
                metadata=request.metadata,
            )

            # Track active workflow and state (thread-safe)
            with self._state_lock:
                self._active_workflows[str(request.workflow_id)] = request
                self._workflow_states[str(request.workflow_id)] = workflow_state

            # Record workflow start in metrics collector
            self._metrics_collector.record_workflow_start(
                workflow_id=request.workflow_id,
                workflow_type=request.workflow_type.value,
            )

            emit_log_event(
                level=LogLevel.INFO,
                event="workflow_processing_started",
                message=f"Started processing workflow {request.workflow_id} (Phase 2)",
                context={
                    "workflow_id": str(request.workflow_id),
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "initial_state": workflow_state.current_state.value,
                },
            )

            # Step 2: Transition to PROCESSING state
            workflow_state.transition_to(
                WorkflowState.PROCESSING,
                reason="Starting workflow processing",
                metadata={"routing_phase": "started"},
            )

            # Step 3: Route the workflow
            routing_decision = await self._router.route(request)

            # Step 4: Get the selected subreducer from registry
            subreducer_instance = self._registry.get_subreducer_instance(
                request.workflow_type
            )
            if not subreducer_instance:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"No subreducer registered for workflow type: {request.workflow_type.value}",
                    context={
                        "workflow_type": request.workflow_type.value,
                        "workflow_id": str(request.workflow_id),
                        "available_types": self._registry.list_registered_workflows(),
                    },
                )

            # Step 5: Process through subreducer
            subreducer_result = await subreducer_instance.process(request)

            # Step 6: Calculate processing time
            end_time = time.perf_counter()
            processing_time_ms = (end_time - start_time) * 1000

            # Step 7: Update state and metrics based on results
            if subreducer_result.success:
                # Transition to completed state
                workflow_state.transition_to(
                    WorkflowState.COMPLETED,
                    reason="Workflow processing completed successfully",
                    metadata={
                        "processing_time_ms": processing_time_ms,
                        "subreducer_name": subreducer_result.subreducer_name,
                    },
                )

                # Record successful completion in metrics collector
                self._metrics_collector.record_workflow_completion(
                    workflow_id=request.workflow_id,
                    workflow_type=request.workflow_type.value,
                    success=True,
                    processing_time_ms=processing_time_ms,
                )

                # Create successful response
                response = WorkflowResponse(
                    workflow_id=request.workflow_id,
                    workflow_type=request.workflow_type,
                    instance_id=request.instance_id,
                    correlation_id=request.correlation_id,
                    status=WorkflowStatus.COMPLETED,
                    result=subreducer_result.result,
                    processing_time_ms=processing_time_ms,
                    subreducer_name=subreducer_result.subreducer_name,
                )

                # Update legacy metrics
                self._metrics.successful_workflows += 1

            else:
                # Set error and transition to failed state
                workflow_state.set_error(
                    error_message=subreducer_result.error_message
                    or "Processing failed",
                    error_details=subreducer_result.error_details or {},
                )

                # Record failed completion in metrics collector
                self._metrics_collector.record_workflow_completion(
                    workflow_id=request.workflow_id,
                    workflow_type=request.workflow_type.value,
                    success=False,
                    processing_time_ms=processing_time_ms,
                    error_type=subreducer_result.error_details.get(
                        "error_type", "unknown"
                    ),
                )

                # Create failed response
                response = WorkflowResponse(
                    workflow_id=request.workflow_id,
                    workflow_type=request.workflow_type,
                    instance_id=request.instance_id,
                    correlation_id=request.correlation_id,
                    status=WorkflowStatus.FAILED,
                    error_message=subreducer_result.error_message,
                    error_details=subreducer_result.error_details,
                    processing_time_ms=processing_time_ms,
                    subreducer_name=subreducer_result.subreducer_name,
                )

                self._metrics.failed_workflows += 1

            # Update overall metrics
            self._update_metrics(processing_time_ms)

            emit_log_event(
                level=LogLevel.INFO,
                event="workflow_processing_completed",
                message=f"Completed processing workflow {request.workflow_id}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "status": response.status.value,
                    "processing_time_ms": processing_time_ms,
                    "subreducer_name": subreducer_result.subreducer_name,
                    "success": subreducer_result.success,
                },
            )

            return response

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000

            # Update workflow state if it exists (thread-safe)
            with self._state_lock:
                workflow_state = self._workflow_states.get(str(request.workflow_id))
            if workflow_state:
                workflow_state.set_error(
                    error_message=str(e), error_details={"error_type": type(e).__name__}
                )

            # Record failure in metrics collector
            self._metrics_collector.record_workflow_completion(
                workflow_id=request.workflow_id,
                workflow_type=request.workflow_type.value,
                success=False,
                processing_time_ms=processing_time_ms,
                error_type=type(e).__name__,
            )

            # Update legacy metrics
            self._metrics.failed_workflows += 1
            self._update_metrics(processing_time_ms)

            error_response = WorkflowResponse(
                workflow_id=request.workflow_id,
                workflow_type=request.workflow_type,
                instance_id=request.instance_id,
                correlation_id=request.correlation_id,
                status=WorkflowStatus.FAILED,
                error_message=str(e),
                error_details={"error_type": type(e).__name__},
                processing_time_ms=processing_time_ms,
            )

            emit_log_event(
                level=LogLevel.ERROR,
                event="workflow_processing_failed",
                message=f"Failed to process workflow {request.workflow_id}: {str(e)}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time_ms": processing_time_ms,
                },
            )

            return error_response

        finally:
            # Clean up active workflow tracking (thread-safe)
            with self._state_lock:
                self._active_workflows.pop(str(request.workflow_id), None)

            # Periodic memory cleanup to prevent memory leaks
            self._cleanup_old_workflow_states()

    def _cleanup_old_workflow_states(self) -> None:
        """
        Clean up old workflow states to prevent memory leaks.

        Removes workflow states that are:
        1. Older than the retention period AND completed/failed
        2. Beyond the maximum count limit (keeps most recent)

        Runs periodically (every hour) to avoid performance impact.
        """
        now = datetime.now()

        # Only run cleanup once per hour to avoid performance impact
        if (now - self._last_cleanup_time).total_seconds() < 3600:
            return

        with self._state_lock:
            if not self._workflow_states:
                return

            states_to_remove = []
            retention_cutoff = now - timedelta(hours=self._state_retention_hours)

            # Find states to remove based on age and completion status
            for workflow_id, state in self._workflow_states.items():
                # Skip if workflow is still active
                if workflow_id in self._active_workflows:
                    continue

                # Remove if state is old and completed/failed
                completed_at = getattr(state, "completed_at", None)
                if (
                    completed_at
                    and completed_at < retention_cutoff
                    and state.current_state
                    in [WorkflowState.COMPLETED, WorkflowState.FAILED]
                ):
                    states_to_remove.append(workflow_id)

            # If still over limit, remove oldest completed states
            if (
                len(self._workflow_states) - len(states_to_remove)
                > self._max_workflow_states
            ):
                completed_states = [
                    (wf_id, state)
                    for wf_id, state in self._workflow_states.items()
                    if (
                        wf_id not in self._active_workflows
                        and wf_id not in states_to_remove
                        and state.current_state
                        in [WorkflowState.COMPLETED, WorkflowState.FAILED]
                    )
                ]

                # Sort by completion time and remove oldest
                completed_states.sort(key=lambda x: getattr(x[1], "completed_at", now))
                excess_count = (
                    len(self._workflow_states)
                    - len(states_to_remove)
                    - self._max_workflow_states
                )
                states_to_remove.extend(
                    [wf_id for wf_id, _ in completed_states[:excess_count]]
                )

            # Remove identified states
            if states_to_remove:
                for workflow_id in states_to_remove:
                    self._workflow_states.pop(workflow_id, None)

                emit_log_event(
                    level=LogLevel.INFO,
                    event="workflow_states_cleaned_up",
                    message=f"Cleaned up {len(states_to_remove)} old workflow states",
                    context={
                        "removed_count": len(states_to_remove),
                        "remaining_states": len(self._workflow_states),
                        "active_workflows": len(self._active_workflows),
                        "retention_hours": self._state_retention_hours,
                        "max_states": self._max_workflow_states,
                    },
                )

        self._last_cleanup_time = now

    def get_metrics(self) -> WorkflowMetrics:
        """
        Get current workflow processing metrics.

        Returns:
            WorkflowMetrics: Current performance and processing metrics
        """
        # Update active instances count (thread-safe)
        with self._state_lock:
            self._metrics.active_instances = len(self._active_workflows)

        # Include router metrics
        router_metrics = self._router.get_routing_metrics()
        self._metrics.subreducer_metrics["router"] = router_metrics

        return self._metrics

    def get_active_workflows(self) -> Dict[str, WorkflowRequest]:
        """
        Get currently active workflows.

        Returns:
            Dict[str, WorkflowRequest]: Active workflows by workflow ID
        """
        with self._state_lock:
            return self._active_workflows.copy()

    def _update_metrics(self, processing_time_ms: float) -> None:
        """
        Update processing metrics.

        Args:
            processing_time_ms: Time taken for this workflow processing
        """
        self._metrics.total_workflows_processed += 1

        # Calculate running average processing time
        total_processed = self._metrics.total_workflows_processed
        current_avg = self._metrics.average_processing_time_ms

        # Running average formula: new_avg = old_avg + (new_value - old_avg) / count
        self._metrics.average_processing_time_ms = (
            current_avg + (processing_time_ms - current_avg) / total_processed
        )

    # Phase 2 Enhanced Methods

    def get_registry_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive registry summary with health checks.

        Returns:
            Dict containing registry status and health information
        """
        return self._registry.get_registry_summary()

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics from all Phase 2 components.

        Returns:
            Dict containing metrics from all collectors and components
        """
        return {
            "legacy_metrics": self.get_metrics().__dict__,
            "enhanced_metrics": self._metrics_collector.get_metrics_summary(),
            "registry_status": self.get_registry_summary(),
            "active_workflows_count": self._get_active_workflows_count(),
            "workflow_states": self._get_workflow_states_summary(),
        }

    def _get_active_workflows_count(self) -> int:
        """Get count of active workflows (thread-safe)."""
        with self._state_lock:
            return len(self._active_workflows)

    def _get_workflow_states_summary(self) -> Dict[str, Dict]:
        """Get workflow states summary (thread-safe)."""
        with self._state_lock:
            return {
                wf_id: state.to_summary_dict()
                for wf_id, state in self._workflow_states.items()
            }

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowStateModel]:
        """
        Get the state model for a specific workflow.

        Args:
            workflow_id: The workflow ID to get state for

        Returns:
            WorkflowStateModel if found, None otherwise
        """
        with self._state_lock:
            return self._workflow_states.get(workflow_id)

    def list_supported_workflow_types(self) -> List[str]:
        """
        Get list of all supported workflow types from registry.

        Returns:
            List of registered workflow type strings
        """
        return self._registry.list_registered_workflows()

    def get_workflow_type_metrics(self, workflow_type: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific workflow type.

        Args:
            workflow_type: The workflow type to get metrics for

        Returns:
            Metrics dictionary for the workflow type, None if not found
        """
        return self._metrics_collector.get_workflow_type_metrics(workflow_type)

    def health_check_subreducers(self) -> Dict[str, bool]:
        """
        Perform health checks on all registered subreducers.

        Returns:
            Dictionary mapping workflow types to health status
        """
        return self._registry.health_check_subreducers()

    def register_multiple_subreducers(
        self, subreducer_configs: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Register multiple subreducers at once.

        Args:
            subreducer_configs: List of dicts with 'subreducer' and 'workflow_types' keys

        Returns:
            Dict mapping subreducer names to registration success status
        """
        results = {}

        for config in subreducer_configs:
            try:
                subreducer = config["subreducer"]
                workflow_types = config["workflow_types"]
                self.register_subreducer(subreducer, workflow_types)
                results[subreducer.name] = True
            except Exception as e:
                subreducer_name = getattr(config.get("subreducer"), "name", "unknown")
                results[subreducer_name] = False
                emit_log_event(
                    level=LogLevel.ERROR,
                    event="bulk_subreducer_registration_failed",
                    message=f"Failed to register subreducer {subreducer_name}: {str(e)}",
                )

        return results

    def reset_metrics(self) -> None:
        """Reset all metrics collectors. Used primarily for testing."""
        self._metrics_collector.reset_metrics()
        self._metrics = WorkflowMetrics()

        emit_log_event(
            level=LogLevel.INFO,
            event="metrics_reset",
            message="All metrics have been reset",
        )
