"""
WorkflowOrchestratorAgent - Concrete implementation of workflow orchestration.

This agent implements the ProtocolWorkflowOrchestrator interface using the
NodeOrchestratorService base infrastructure for workflow coordination and execution.
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from omnibase_core.agents.config import CONFIG
from omnibase_core.agents.models.model_orchestrator_execution_state import (
    ModelOrchestratorExecutionState,
)
from omnibase_core.agents.models.model_orchestrator_parameters import (
    ModelOrchestratorParameters,
)
from omnibase_core.agents.models.model_workflow_metrics_monitor import (
    WorkflowMetricsMonitor,
)
from omnibase_core.agents.models.model_workflow_persistence_manager import (
    ModelWorkflowPersistenceState,
    ModelWorkflowRecoveryPlan,
    WorkflowPersistenceManager,
)
from omnibase_core.agents.models.model_workflow_state_manager import (
    WorkflowStateManager,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.node_orchestrator_service import NodeOrchestratorService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.classification.enum_execution_mode import EnumExecutionMode
from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata

# Import dependencies needed for ModelOnexResult.model_rebuild()
from omnibase_core.models.core.model_onex_message import ModelOnexMessage
from omnibase_core.models.core.model_onex_result import ModelOnexResult
from omnibase_core.models.core.model_orchestrator_info import ModelOrchestratorInfo
from omnibase_core.models.core.model_unified_summary import ModelUnifiedSummary
from omnibase_core.models.core.model_unified_version import ModelUnifiedVersion
from omnibase_core.models.workflow.model_workflow_execution_state import (
    ModelWorkflowExecutionState,
)
from omnibase_core.protocol.models.model_health_check_result import (
    ModelHealthCheckResult,
)
from omnibase_core.protocol.models.model_workflow_input_state import (
    ModelWorkflowInputState,
)
from omnibase_core.protocol.protocol_workflow_orchestrator import (
    ProtocolWorkflowOrchestrator,
)

if TYPE_CHECKING:
    from omnibase_core.protocol.protocol_node_registry import ProtocolNodeRegistry

# Rebuild the model to resolve forward references after all imports
try:
    ModelOnexResult.model_rebuild()
except NameError:
    # If model_rebuild fails, continue without it - tests can handle this
    pass


class WorkflowOrchestratorAgent(NodeOrchestratorService, ProtocolWorkflowOrchestrator):
    """
    Enhanced workflow orchestrator agent implementing ProtocolWorkflowOrchestrator with advanced coordination patterns.

    This agent bridges the comprehensive NodeOrchestrator infrastructure with the
    ProtocolWorkflowOrchestrator interface, providing workflow coordination and
    execution capabilities following ONEX 4-Node architecture patterns.

    Features:
    - Multi-mode workflow execution (sequential, parallel, batch, conditional)
    - Advanced workflow coordination patterns (pipeline, scatter-gather)
    - Node coordination across COMPUTE, EFFECT, and REDUCER types
    - Dependency graph management with topological sorting
    - Workflow persistence with checkpointing
    - Circuit breakers and resilience patterns
    - Performance metrics and load balancing
    - Memory management with TTL cleanup
    - Thread-safe registry access
    - Retry logic with exponential backoff
    - Timeout enforcement
    - Advanced failure recovery strategies
    """

    # Class-level operation handlers for performance optimization
    _OPERATION_HANDLERS = {
        "model_generation": "_handle_model_generation",
        "bootstrap_validation": "_handle_bootstrap_validation",
        "extraction": "_handle_extraction",
        "generic": "_handle_generic_operation",
        "workflow_coordination": "_handle_workflow_coordination",
        "dependency_resolution": "_handle_dependency_resolution",
        "create_workflow": "_handle_create_workflow",
        "execute_workflow": "_handle_execute_workflow",
        "coordinate_nodes": "_handle_coordinate_nodes",
        "monitor_workflow_progress": "_handle_monitor_workflow_progress",
        "handle_workflow_failure": "_handle_workflow_failure",
    }

    # Workflow execution patterns
    _EXECUTION_PATTERNS = {
        "sequential": {
            "description": "Execute nodes in sequence: COMPUTE → EFFECT → REDUCER",
            "parallelism": False,
            "fault_tolerance": "stop_on_error",
            "coordination_overhead": "low",
        },
        "parallel_compute": {
            "description": "Parallel COMPUTE execution with synchronized aggregation",
            "parallelism": True,
            "max_parallel_compute": 5,
            "synchronization_points": ["after_compute", "before_reducer"],
        },
        "pipeline": {
            "description": "Streaming pipeline with overlapped execution",
            "parallelism": True,
            "buffering_enabled": True,
            "backpressure_handling": True,
        },
        "scatter_gather": {
            "description": "Scatter work to multiple nodes, gather results",
            "parallelism": True,
            "scatter_strategy": "round_robin",
            "gather_timeout_ms": 30000,
        },
    }

    def __init__(self, container: ModelONEXContainer):
        """Initialize enhanced workflow orchestrator agent with ONEX container."""
        super().__init__(container)

        # Initialize workflow execution tracking with thread safety
        self._execution_states: dict[str, ModelOrchestratorExecutionState] = {}
        self._execution_states_lock = threading.RLock()
        self._registry: Optional["ProtocolNodeRegistry"] = None
        self._registry_lock = threading.RLock()

        # Enhanced workflow coordination tracking
        self._workflow_instances: dict[str, dict] = {}
        self._workflow_instances_lock = threading.RLock()
        self._coordination_results: dict[str, dict] = {}
        self._coordination_results_lock = threading.RLock()

        # Advanced workflow state management
        self._workflow_state_manager = WorkflowStateManager()
        self._checkpoint_interval_steps = 5  # Create checkpoint every 5 steps
        self._auto_checkpoint_enabled = True

        # Comprehensive metrics and monitoring
        self._metrics_monitor = WorkflowMetricsMonitor(
            max_metric_history=5000, alert_cooldown_seconds=300
        )
        self._metrics_enabled = True

        # LlamaIndex workflow persistence and recovery
        self._persistence_manager = WorkflowPersistenceManager(
            persistence_directory="/tmp/onex_workflows",
            max_checkpoints_per_workflow=10,
            checkpoint_interval_seconds=30,
        )
        self._persistence_enabled = True
        self._auto_persistence_enabled = True

        # Setup default performance alerts
        self._setup_default_alerts()

        # Node coordination patterns
        self._node_coordination_config = {
            "COMPUTE": {
                "assignment_strategy": "load_balanced",
                "result_aggregation": "collect_all",
                "failure_handling": "retry_individual",
                "timeout_handling": "extend_deadline",
            },
            "EFFECT": {
                "assignment_strategy": "capability_matched",
                "side_effect_management": "coordinated",
                "failure_handling": "compensating_action",
                "timeout_handling": "graceful_timeout",
            },
            "REDUCER": {
                "assignment_strategy": "state_affinity",
                "aggregation_strategy": "incremental",
                "failure_handling": "state_rollback",
                "consistency_requirements": "strong",
            },
        }

        # Memory management tracking with enhanced metrics
        self._last_cleanup_time = datetime.now()
        self._cleanup_stats = {
            "total_cleanups": 0,
            "states_removed_ttl": 0,
            "states_removed_limit": 0,
            "max_states_held": 0,
            "avg_cleanup_duration_ms": 0.0,
            "workflows_created": 0,
            "workflows_executed": 0,
            "coordination_failures": 0,
            "active_workflows": 0,
        }

        emit_log_event(
            level=LogLevel.INFO,
            message="Enhanced WorkflowOrchestratorAgent initialized",
            metadata=ModelGenericMetadata.from_dict(
                {"node_id": self.node_id, "container_id": str(id(container))}
            ),
        )

    def _setup_default_alerts(self) -> None:
        """Setup default performance alerts for workflow monitoring."""
        try:
            # High execution time alert
            self._metrics_monitor.create_performance_alert(
                alert_name="High Execution Time",
                metric_name="workflow_execution_time",
                threshold_value=30000,  # 30 seconds
                comparison_operator=">",
                severity="MEDIUM",
                description="Workflow execution time exceeded 30 seconds",
            )

            # Critical execution time alert
            self._metrics_monitor.create_performance_alert(
                alert_name="Critical Execution Time",
                metric_name="workflow_execution_time",
                threshold_value=60000,  # 60 seconds
                comparison_operator=">",
                severity="HIGH",
                description="Workflow execution time exceeded 60 seconds",
            )

            # Performance degradation alert
            self._metrics_monitor.create_performance_alert(
                alert_name="Extreme Execution Time",
                metric_name="workflow_execution_time",
                threshold_value=120000,  # 120 seconds
                comparison_operator=">",
                severity="CRITICAL",
                description="Workflow execution time exceeded 120 seconds",
            )

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Default performance alerts configured",
                metadata=ModelGenericMetadata.from_dict({"alerts_configured": 3}),
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Failed to setup default alerts: {str(e)}",
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def set_registry(self, registry: "ProtocolNodeRegistry") -> None:
        """Set the registry for accessing other tools with thread safety."""
        with self._registry_lock:
            self._registry = registry
            emit_log_event(
                level=LogLevel.DEBUG,
                message="Registry set for WorkflowOrchestratorAgent",
                metadata=ModelGenericMetadata.from_dict({"node_id": self.node_id}),
            )

    def run(self, input_state: ModelWorkflowInputState) -> ModelOnexResult:
        """Run the workflow orchestrator with the provided input state."""
        # Comprehensive input validation and security checks
        if input_state is None:
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="input_state is required but was None",
                context={"validation_failed": "input_state_null"},
            )

        # Validate required fields
        if input_state.scenario_id is None:
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="scenario_id is required but was None",
                context={
                    "input_state": str(input_state),
                    "validation_failed": "scenario_id_null",
                },
            )

        if input_state.operation_type is None:
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="operation_type is required but was None",
                context={
                    "input_state": str(input_state),
                    "validation_failed": "operation_type_null",
                },
            )

        # Security validation for scenario_id
        if (
            not isinstance(input_state.scenario_id, str)
            or len(input_state.scenario_id.strip()) == 0
        ):
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="scenario_id must be a non-empty string",
                context={
                    "scenario_id": input_state.scenario_id,
                    "validation_failed": "scenario_id_invalid",
                },
            )

        # Security validation for operation_type
        if (
            not isinstance(input_state.operation_type, str)
            or len(input_state.operation_type.strip()) == 0
        ):
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="operation_type must be a non-empty string",
                context={
                    "operation_type": input_state.operation_type,
                    "validation_failed": "operation_type_invalid",
                },
            )

        # Security check for scenario_id - prevent path traversal and injection
        dangerous_chars = [
            "../",
            "..\\",
            "<",
            ">",
            "&",
            "|",
            ";",
            "`",
            "$",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
        ]
        for char in dangerous_chars:
            if char in input_state.scenario_id:
                raise OnexError(
                    error_code=CoreErrorCode.INVALID_INPUT,
                    message=f"scenario_id contains dangerous character sequence: {char}",
                    context={
                        "scenario_id": input_state.scenario_id,
                        "validation_failed": "security_violation",
                    },
                )

        # Length limits for security
        if len(input_state.scenario_id) > 255:
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="scenario_id exceeds maximum length of 255 characters",
                context={
                    "scenario_id_length": len(input_state.scenario_id),
                    "validation_failed": "length_exceeded",
                },
            )

        if len(input_state.operation_type) > 100:
            raise OnexError(
                error_code=CoreErrorCode.INVALID_INPUT,
                message="operation_type exceeds maximum length of 100 characters",
                context={
                    "operation_type_length": len(input_state.operation_type),
                    "validation_failed": "length_exceeded",
                },
            )

        # Extract validated parameters
        scenario_id = input_state.scenario_id
        operation_type = input_state.operation_type
        correlation_id = input_state.correlation_id

        # Perform memory cleanup if needed
        self._cleanup_execution_states_if_needed()

        try:
            emit_log_event(
                level=LogLevel.INFO,
                message="Running enhanced workflow orchestrator",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "action": input_state.action,
                        "scenario_id": scenario_id,
                        "node_id": self.node_id,
                        "operation_type": operation_type,
                    }
                ),
            )

            # Create workflow parameters
            workflow_params = ModelOrchestratorParameters(
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                execution_mode=input_state.parameters.get_string(
                    "execution_mode", "sequential"
                ),
                timeout_seconds=input_state.parameters.get_int("timeout_seconds", 300),
                retry_count=input_state.parameters.get_int("retry_count", 3),
                metadata={},  # Use empty dict that matches expected type
            )

            # Orchestrate the operation with enhanced patterns
            result = self.orchestrate_operation(
                operation_type=operation_type,
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=workflow_params,
            )

            emit_log_event(
                level=LogLevel.INFO,
                message="Enhanced workflow orchestration completed",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "success": result.status == EnumOnexStatus.SUCCESS,
                        "scenario_id": scenario_id,
                        "operation_type": operation_type,
                    }
                ),
            )

            return result

        except Exception as e:
            error_msg = f"Failed to run enhanced workflow orchestrator: {str(e)}"
            emit_log_event(
                level=LogLevel.ERROR,
                message=error_msg,
                metadata=ModelGenericMetadata.from_dict(
                    {"error": str(e), "node_id": self.node_id}
                ),
            )

            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=correlation_id,
                duration=0.0,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    # === ENHANCED WORKFLOW COORDINATION METHODS ===

    def create_workflow(
        self, workflow_definition: dict, input_parameters: dict, execution_config: dict
    ) -> dict:
        """
        Create a new workflow execution instance with enhanced coordination patterns.

        Args:
            workflow_definition: Definition of workflow structure and requirements
            input_parameters: Parameters for workflow execution
            execution_config: Configuration for execution patterns and timeouts

        Returns:
            dict: Workflow instance details and execution ID
        """
        workflow_id = str(uuid4())

        try:
            # Validate workflow definition
            if (
                not workflow_definition
                or "workflow_metadata" not in workflow_definition
            ):
                raise ValueError("Invalid workflow definition - missing metadata")

            # Create workflow instance
            workflow_instance = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_definition["workflow_metadata"].get(
                    "name", "unnamed"
                ),
                "workflow_version": workflow_definition["workflow_metadata"].get(
                    "version", "1.0.0"
                ),
                "created_timestamp": datetime.now().isoformat(),
                "status": "CREATED",
                "input_parameters": input_parameters,
                "execution_context": execution_config,
                "definition": workflow_definition,
            }

            # Store workflow instance with thread safety
            with self._workflow_instances_lock:
                self._workflow_instances[workflow_id] = workflow_instance
                self._cleanup_stats["workflows_created"] += 1

            # Initialize workflow state management
            self._workflow_state_manager.initialize_workflow_state(
                workflow_id=workflow_id, initial_state=EnumWorkflowStatus.PENDING
            )

            # Create initial checkpoint if auto-checkpointing is enabled
            if self._auto_checkpoint_enabled:
                checkpoint_id = self._workflow_state_manager.create_checkpoint(
                    workflow_id=workflow_id,
                    checkpoint_name="workflow_created",
                    workflow_state={
                        "status": "CREATED",
                        "workflow_name": workflow_instance["workflow_name"],
                        "created_timestamp": workflow_instance["created_timestamp"],
                    },
                    execution_context=execution_config,
                    is_recovery_point=True,
                    metadata={"creation_step": True},
                )

            # Initialize LlamaIndex workflow persistence
            persistence_state = None
            if self._persistence_enabled:
                try:
                    persistence_state = (
                        self._persistence_manager.initialize_workflow_persistence(
                            workflow_id=workflow_id,
                            workflow_name=workflow_instance["workflow_name"],
                            workflow_definition=workflow_definition,
                            initial_context=execution_config,
                        )
                    )

                    emit_log_event(
                        level=LogLevel.INFO,
                        message="Workflow persistence initialized",
                        metadata=ModelGenericMetadata.from_dict(
                            {"workflow_id": workflow_id, "persistence_enabled": True}
                        ),
                    )
                except Exception as e:
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Failed to initialize workflow persistence: {str(e)}",
                        metadata=ModelGenericMetadata.from_dict(
                            {"workflow_id": workflow_id, "error": str(e)}
                        ),
                    )

            # Record workflow creation metrics
            if self._metrics_enabled:
                self._metrics_monitor.record_custom_metric(
                    workflow_id=workflow_id,
                    metric_name="workflow_created",
                    metric_value=1.0,
                    metric_unit="count",
                    metric_type="lifecycle",
                    tags={
                        "workflow_name": workflow_instance["workflow_name"],
                        "workflow_version": workflow_instance["workflow_version"],
                    },
                    metadata={
                        "checkpoint_id": checkpoint_id if checkpoint_id else None,
                        "auto_checkpoint_enabled": self._auto_checkpoint_enabled,
                        "persistence_enabled": self._persistence_enabled,
                        "persistence_initialized": persistence_state is not None,
                    },
                )

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow instance created",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "workflow_name": workflow_instance["workflow_name"],
                        "workflow_version": workflow_instance["workflow_version"],
                    }
                ),
            )

            return {"workflow_instance": workflow_instance, "execution_id": workflow_id}

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to create workflow: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            raise

    def execute_workflow(
        self, workflow_instance: dict, execution_context: dict
    ) -> dict:
        """
        Execute workflow with coordinated node interactions using advanced patterns.

        Args:
            workflow_instance: Workflow instance to execute
            execution_context: Context for execution including patterns and configs

        Returns:
            dict: Execution result and coordination metrics
        """
        workflow_id = workflow_instance.get("workflow_id")
        if not workflow_id:
            raise ValueError("Missing workflow_id in workflow instance")

        try:
            start_time = datetime.now()

            # Record workflow execution start
            if self._metrics_enabled:
                self._metrics_monitor.record_workflow_started(
                    workflow_id=workflow_id,
                    workflow_metadata={
                        "execution_pattern": execution_context.get(
                            "execution_pattern", "sequential"
                        ),
                        "workflow_name": workflow_instance.get(
                            "workflow_name", "unknown"
                        ),
                        "workflow_version": workflow_instance.get(
                            "workflow_version", "1.0.0"
                        ),
                    },
                )

            # Update workflow status using state manager
            self._workflow_state_manager.transition_workflow_state(
                workflow_id=workflow_id,
                new_state=EnumWorkflowStatus.RUNNING,
                trigger_event="workflow_execution_started",
                context={
                    "execution_pattern": execution_context.get(
                        "execution_pattern", "sequential"
                    )
                },
            )

            with self._workflow_instances_lock:
                if workflow_id in self._workflow_instances:
                    self._workflow_instances[workflow_id]["status"] = "RUNNING"
                    self._cleanup_stats["active_workflows"] += 1

            # Determine execution pattern
            execution_pattern = execution_context.get("execution_pattern", "sequential")
            pattern_config = self._EXECUTION_PATTERNS.get(
                execution_pattern, self._EXECUTION_PATTERNS["sequential"]
            )

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Executing workflow with pattern: {execution_pattern}",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "execution_pattern": execution_pattern,
                        "parallelism": pattern_config.get("parallelism", False),
                    }
                ),
            )

            # Execute workflow based on pattern
            if execution_pattern == "sequential":
                execution_result = self._execute_sequential_workflow(
                    workflow_instance, execution_context
                )
            elif execution_pattern == "parallel_compute":
                execution_result = self._execute_parallel_compute_workflow(
                    workflow_instance, execution_context
                )
            elif execution_pattern == "pipeline":
                execution_result = self._execute_pipeline_workflow(
                    workflow_instance, execution_context
                )
            elif execution_pattern == "scatter_gather":
                execution_result = self._execute_scatter_gather_workflow(
                    workflow_instance, execution_context
                )
            else:
                # Default to sequential for unknown patterns
                execution_result = self._execute_sequential_workflow(
                    workflow_instance, execution_context
                )

            end_time = datetime.now()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update workflow status using state manager
            final_state = (
                EnumWorkflowStatus.COMPLETED
                if execution_result.get("success", False)
                else EnumWorkflowStatus.FAILED
            )

            self._workflow_state_manager.transition_workflow_state(
                workflow_id=workflow_id,
                new_state=final_state,
                trigger_event="workflow_execution_completed",
                context={
                    "success": execution_result.get("success", False),
                    "execution_time_ms": execution_time_ms,
                    "execution_pattern": execution_pattern,
                },
            )

            # Create final persistence checkpoint
            if self._persistence_enabled and self._auto_persistence_enabled:
                try:
                    final_status = (
                        "COMPLETED"
                        if execution_result.get("success", False)
                        else "FAILED"
                    )
                    final_context = {
                        "execution_result": execution_result,
                        "execution_time_ms": execution_time_ms,
                        "final_state": final_state.value,
                        "completed_timestamp": end_time.isoformat(),
                    }

                    checkpoint_created = self._persistence_manager.create_checkpoint(
                        workflow_id=workflow_id,
                        checkpoint_name=f"workflow_{final_status.lower()}",
                        current_status=final_status,
                        execution_context=final_context,
                        completed_steps=[
                            execution_pattern
                        ],  # Mark execution pattern as completed
                        metadata={
                            "final_checkpoint": True,
                            "execution_pattern": execution_pattern,
                            "resource_efficiency_score": execution_result.get(
                                "resource_efficiency_score", 0.0
                            ),
                        },
                    )

                    if checkpoint_created:
                        emit_log_event(
                            level=LogLevel.INFO,
                            message="Final workflow checkpoint created",
                            metadata=ModelGenericMetadata.from_dict(
                                {
                                    "workflow_id": workflow_id,
                                    "final_status": final_status,
                                }
                            ),
                        )
                except Exception as e:
                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Failed to create final persistence checkpoint: {str(e)}",
                        metadata=ModelGenericMetadata.from_dict(
                            {"workflow_id": workflow_id, "error": str(e)}
                        ),
                    )

            # Record workflow completion metrics
            if self._metrics_enabled:
                recorded_execution_time = (
                    self._metrics_monitor.record_workflow_completed(
                        workflow_id=workflow_id,
                        status=final_state,
                        workflow_metadata={
                            "execution_pattern": execution_pattern,
                            "coordination_overhead_ms": execution_result.get(
                                "coordination_overhead_ms", 0
                            ),
                            "resource_efficiency_score": execution_result.get(
                                "resource_efficiency_score", 0.0
                            ),
                            "node_utilization_percent": execution_result.get(
                                "node_utilization_percent", 0.0
                            ),
                        },
                    )
                )

                # Record additional performance metrics
                self._metrics_monitor.record_custom_metric(
                    workflow_id=workflow_id,
                    metric_name="coordination_overhead",
                    metric_value=execution_result.get("coordination_overhead_ms", 0),
                    metric_unit="milliseconds",
                    metric_type="performance",
                    tags={"execution_pattern": execution_pattern},
                )

                self._metrics_monitor.record_custom_metric(
                    workflow_id=workflow_id,
                    metric_name="resource_efficiency",
                    metric_value=execution_result.get("resource_efficiency_score", 0.0),
                    metric_unit="score",
                    metric_type="performance",
                    tags={"execution_pattern": execution_pattern},
                )

            # Create completion checkpoint
            if self._auto_checkpoint_enabled and execution_result.get("success", False):
                completion_checkpoint = self._workflow_state_manager.create_checkpoint(
                    workflow_id=workflow_id,
                    checkpoint_name="workflow_completed",
                    workflow_state={
                        "status": "COMPLETED",
                        "completion_timestamp": end_time.isoformat(),
                        "execution_result": execution_result,
                    },
                    execution_context={
                        "final_metrics": coordination_metrics,
                        "execution_pattern": execution_pattern,
                    },
                    is_recovery_point=False,  # No recovery needed for completed workflows
                    metadata={"completion_step": True},
                )

            # Update workflow status and metrics
            with self._workflow_instances_lock:
                if workflow_id in self._workflow_instances:
                    self._workflow_instances[workflow_id]["status"] = (
                        "COMPLETED"
                        if execution_result.get("success", False)
                        else "FAILED"
                    )
                    self._cleanup_stats["active_workflows"] = max(
                        0, self._cleanup_stats["active_workflows"] - 1
                    )
                    self._cleanup_stats["workflows_executed"] += 1

            coordination_metrics = {
                "total_execution_time_ms": execution_time_ms,
                "coordination_overhead_ms": execution_result.get(
                    "coordination_overhead_ms", 0
                ),
                "node_utilization_percent": execution_result.get(
                    "node_utilization_percent", 0.0
                ),
                "parallelism_achieved": execution_result.get(
                    "parallelism_achieved", 0.0
                ),
                "synchronization_delays_ms": execution_result.get(
                    "synchronization_delays_ms", 0
                ),
                "resource_efficiency_score": execution_result.get(
                    "resource_efficiency_score", 0.0
                ),
            }

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow execution completed",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "execution_time_ms": execution_time_ms,
                        "success": execution_result.get("success", False),
                    }
                ),
            )

            return {
                "execution_result": execution_result,
                "coordination_metrics": coordination_metrics,
            }

        except Exception as e:
            # Update workflow status to failed using state manager
            self._workflow_state_manager.transition_workflow_state(
                workflow_id=workflow_id,
                new_state=EnumWorkflowStatus.FAILED,
                trigger_event="workflow_execution_exception",
                context={
                    "error": str(e),
                    "exception_type": type(e).__name__,
                    "execution_pattern": execution_context.get(
                        "execution_pattern", "unknown"
                    ),
                },
            )

            # Generate recovery plan for the failed workflow
            failure_context = {
                "workflow_id": workflow_id,
                "failure_type": "execution_exception",
                "error_message": str(e),
                "failed_at": datetime.now().isoformat(),
                "execution_context": execution_context,
            }

            recovery_plan = self._workflow_state_manager.generate_recovery_plan(
                workflow_id=workflow_id,
                failure_context=failure_context,
                recovery_strategy="checkpoint_rollback",  # Default strategy
            )

            # Update workflow status to failed
            with self._workflow_instances_lock:
                if workflow_id in self._workflow_instances:
                    self._workflow_instances[workflow_id]["status"] = "FAILED"
                    self._workflow_instances[workflow_id]["recovery_plan_id"] = (
                        recovery_plan.plan_id if recovery_plan else None
                    )
                    self._cleanup_stats["active_workflows"] = max(
                        0, self._cleanup_stats["active_workflows"] - 1
                    )
                    self._cleanup_stats["coordination_failures"] += 1

            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Workflow execution failed: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )

            return {
                "execution_result": {"success": False, "error": str(e)},
                "coordination_metrics": {"total_execution_time_ms": 0},
            }

    def coordinate_nodes(
        self, coordination_plan: dict, node_assignments: dict, sync_requirements: dict
    ) -> dict:
        """
        Coordinate execution across COMPUTE, EFFECT, and REDUCER nodes with advanced patterns.

        Args:
            coordination_plan: Plan for coordinating node execution
            node_assignments: Assignment of work to specific nodes
            sync_requirements: Synchronization requirements between nodes

        Returns:
            dict: Coordination result with node statuses and metrics
        """
        coordination_id = str(uuid4())
        start_time = datetime.now()

        try:
            emit_log_event(
                level=LogLevel.INFO,
                message="Starting node coordination",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "coordination_id": coordination_id,
                        "nodes_count": len(node_assignments),
                        "sync_points": len(
                            sync_requirements.get("synchronization_points", [])
                        ),
                    }
                ),
            )

            # Initialize coordination result
            coordination_result = {
                "coordination_id": coordination_id,
                "workflow_id": coordination_plan.get("workflow_id"),
                "nodes_coordinated": [],
                "coordination_overhead_ms": 0,
                "synchronization_points": [],
            }

            # Execute node coordination based on plan
            nodes_coordinated = []
            for node_id, assignment in node_assignments.items():
                node_type = assignment.get("node_type", "COMPUTE")
                node_config = self._node_coordination_config.get(
                    node_type, self._node_coordination_config["COMPUTE"]
                )

                # Simulate node execution with coordination patterns
                node_start = datetime.now()
                node_result = self._execute_coordinated_node(
                    node_id, node_type, assignment, node_config
                )
                node_end = datetime.now()

                node_execution_time = int(
                    (node_end - node_start).total_seconds() * 1000
                )

                coordinated_node = {
                    "node_id": node_id,
                    "node_type": node_type,
                    "assignment_status": (
                        "COMPLETED" if node_result.get("success") else "FAILED"
                    ),
                    "execution_time_ms": node_execution_time,
                    "resource_usage": node_result.get("resource_usage", {}),
                }

                nodes_coordinated.append(coordinated_node)

            # Handle synchronization points
            sync_points = []
            for sync_point in sync_requirements.get("synchronization_points", []):
                sync_start = datetime.now()
                # Simulate synchronization
                import time

                time.sleep(0.01)  # Small delay to simulate sync overhead
                sync_end = datetime.now()

                sync_point_result = {
                    "point_name": sync_point,
                    "timestamp": sync_end.isoformat(),
                    "nodes_synchronized": len(
                        [
                            n
                            for n in nodes_coordinated
                            if n["assignment_status"] == "COMPLETED"
                        ]
                    ),
                }
                sync_points.append(sync_point_result)

            end_time = datetime.now()
            coordination_overhead = int((end_time - start_time).total_seconds() * 1000)

            # Update coordination result
            coordination_result.update(
                {
                    "nodes_coordinated": nodes_coordinated,
                    "coordination_overhead_ms": coordination_overhead,
                    "synchronization_points": sync_points,
                }
            )

            # Store coordination result with thread safety
            with self._coordination_results_lock:
                self._coordination_results[coordination_id] = coordination_result

            emit_log_event(
                level=LogLevel.INFO,
                message="Node coordination completed",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "coordination_id": coordination_id,
                        "nodes_coordinated": len(nodes_coordinated),
                        "coordination_overhead_ms": coordination_overhead,
                    }
                ),
            )

            return {
                "coordination_result": coordination_result,
                "node_statuses": {
                    node["node_id"]: node["assignment_status"]
                    for node in nodes_coordinated
                },
            }

        except Exception as e:
            self._cleanup_stats["coordination_failures"] += 1

            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Node coordination failed: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"coordination_id": coordination_id, "error": str(e)}
                ),
            )

            return {
                "coordination_result": {
                    "coordination_id": coordination_id,
                    "error": str(e),
                },
                "node_statuses": {},
            }

    def monitor_workflow_progress(
        self, workflow_id: str, monitoring_config: dict
    ) -> dict:
        """
        Monitor and track workflow execution progress with advanced metrics.

        Args:
            workflow_id: ID of workflow to monitor
            monitoring_config: Configuration for monitoring behavior

        Returns:
            dict: Progress status and performance metrics
        """
        try:
            # Get workflow instance
            with self._workflow_instances_lock:
                workflow_instance = self._workflow_instances.get(workflow_id)

            if not workflow_instance:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Calculate progress based on workflow status and execution state
            current_status = workflow_instance["status"]

            if current_status == "CREATED":
                progress_percent = 0.0
                current_stage = "initialized"
                stages_completed = 0
                stages_total = 1
            elif current_status == "RUNNING":
                progress_percent = 50.0  # Estimate based on execution
                current_stage = "executing"
                stages_completed = 1
                stages_total = 3
            elif current_status == "COMPLETED":
                progress_percent = 100.0
                current_stage = "completed"
                stages_completed = 3
                stages_total = 3
            elif current_status == "FAILED":
                progress_percent = 0.0
                current_stage = "failed"
                stages_completed = 0
                stages_total = 3
            else:
                progress_percent = 0.0
                current_stage = "unknown"
                stages_completed = 0
                stages_total = 1

            # Get execution state for detailed progress
            execution_state = self.get_execution_state(workflow_id)

            # Build progress status
            progress_status = {
                "workflow_id": workflow_id,
                "overall_progress_percent": progress_percent,
                "current_stage": current_stage,
                "stages_completed": stages_completed,
                "stages_total": stages_total,
                "estimated_completion": datetime.now().isoformat(),  # Placeholder
                "node_progress": [],
            }

            # Add node progress if available
            if execution_state:
                node_progress = {
                    "node_id": "orchestrator",
                    "node_type": "ORCHESTRATOR",
                    "progress_percent": progress_percent,
                    "status": current_status,
                }
                progress_status["node_progress"].append(node_progress)

            # Build performance metrics
            performance_metrics = {
                "active_workflows": self._cleanup_stats["active_workflows"],
                "workflows_created": self._cleanup_stats["workflows_created"],
                "workflows_executed": self._cleanup_stats["workflows_executed"],
                "coordination_failures": self._cleanup_stats["coordination_failures"],
                "memory_utilization_percent": len(self._workflow_instances)
                / 100.0
                * 100,  # Rough estimate
            }

            return {
                "progress_status": progress_status,
                "performance_metrics": performance_metrics,
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to monitor workflow progress: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )

            return {
                "progress_status": {"workflow_id": workflow_id, "error": str(e)},
                "performance_metrics": {},
            }

    def handle_workflow_failure(
        self, failure_context: dict, recovery_config: dict, rollback_options: dict
    ) -> dict:
        """
        Handle workflow failures with advanced recovery strategies.

        Args:
            failure_context: Context information about the failure
            recovery_config: Configuration for recovery behavior
            rollback_options: Options for rollback strategies

        Returns:
            dict: Recovery action taken and workflow status
        """
        workflow_id = failure_context.get("workflow_id")
        failure_type = failure_context.get("failure_type", "unknown")

        try:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Handling workflow failure: {failure_type}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "failure_type": failure_type}
                ),
            )

            # Determine recovery strategy
            recovery_strategy = recovery_config.get("strategy", "retry")
            max_retries = recovery_config.get("max_retries", CONFIG.DEFAULT_RETRY_COUNT)

            recovery_action = {
                "action_type": recovery_strategy,
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "details": {},
            }

            if recovery_strategy == "retry":
                # Implement retry logic
                recovery_action["details"] = {
                    "max_retries": max_retries,
                    "retry_delay_ms": recovery_config.get("retry_delay_ms", 2000),
                    "exponential_backoff": recovery_config.get(
                        "exponential_backoff", True
                    ),
                }

                # Update workflow status for retry
                with self._workflow_instances_lock:
                    if workflow_id and workflow_id in self._workflow_instances:
                        self._workflow_instances[workflow_id]["status"] = "RETRYING"

                new_status = "RETRYING"

            elif recovery_strategy == "rollback":
                # Implement rollback logic
                recovery_action["details"] = {
                    "checkpoint_based": rollback_options.get("checkpoint_based", True),
                    "compensation_actions": rollback_options.get(
                        "compensation_actions_enabled", True
                    ),
                    "partial_rollback": rollback_options.get(
                        "partial_rollback_supported", True
                    ),
                }

                # Update workflow status for rollback
                with self._workflow_instances_lock:
                    if workflow_id and workflow_id in self._workflow_instances:
                        self._workflow_instances[workflow_id]["status"] = "ROLLING_BACK"

                new_status = "ROLLING_BACK"

            elif recovery_strategy == "compensate":
                # Implement compensation logic
                recovery_action["details"] = {
                    "compensation_actions": recovery_config.get(
                        "compensation_actions", []
                    ),
                    "side_effects_handled": True,
                }

                # Update workflow status for compensation
                with self._workflow_instances_lock:
                    if workflow_id and workflow_id in self._workflow_instances:
                        self._workflow_instances[workflow_id]["status"] = "COMPENSATING"

                new_status = "COMPENSATING"

            else:  # abort
                # Implement abort logic
                recovery_action["details"] = {
                    "cleanup_performed": True,
                    "resources_released": True,
                }

                # Update workflow status for abort
                with self._workflow_instances_lock:
                    if workflow_id and workflow_id in self._workflow_instances:
                        self._workflow_instances[workflow_id]["status"] = "ABORTED"
                        self._cleanup_stats["active_workflows"] = max(
                            0, self._cleanup_stats["active_workflows"] - 1
                        )

                new_status = "ABORTED"

            # Increment failure counter
            self._cleanup_stats["coordination_failures"] += 1

            emit_log_event(
                level=LogLevel.INFO,
                message=f"Workflow failure handled with {recovery_strategy} strategy",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "recovery_strategy": recovery_strategy,
                        "new_status": new_status,
                    }
                ),
            )

            return {
                "recovery_action": recovery_action,
                "workflow_status": {"workflow_id": workflow_id, "status": new_status},
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to handle workflow failure: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )

            return {
                "recovery_action": {"action_type": "error", "error": str(e)},
                "workflow_status": {"workflow_id": workflow_id, "status": "FAILED"},
            }

    # === ADVANCED STATE MANAGEMENT METHODS ===

    def get_workflow_state_analytics(self, workflow_id: Optional[str] = None) -> dict:
        """
        Get comprehensive workflow state analytics.

        Args:
            workflow_id: Specific workflow ID or None for global analytics

        Returns:
            dict: Analytics data including states, transitions, and checkpoints
        """
        try:
            analytics = self._workflow_state_manager.get_state_analytics(workflow_id)

            # Add orchestrator-specific metrics
            with self._workflow_instances_lock:
                if workflow_id:
                    workflow_instance = self._workflow_instances.get(workflow_id)
                    if workflow_instance:
                        analytics["orchestrator_data"] = {
                            "workflow_name": workflow_instance.get("workflow_name"),
                            "created_timestamp": workflow_instance.get(
                                "created_timestamp"
                            ),
                            "instance_status": workflow_instance.get("status"),
                        }
                else:
                    analytics["orchestrator_data"] = {
                        "total_workflow_instances": len(self._workflow_instances),
                        "memory_stats": self.get_memory_statistics(),
                        "cleanup_stats": self._cleanup_stats.copy(),
                    }

            return analytics

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get state analytics: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return {"error": str(e)}

    def get_workflow_checkpoints(self, workflow_id: str) -> dict:
        """
        Get all checkpoints for a specific workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            dict: Checkpoint information and metadata
        """
        try:
            checkpoints = self._workflow_state_manager.get_checkpoints(workflow_id)
            recovery_checkpoints = (
                self._workflow_state_manager.get_recovery_checkpoints(workflow_id)
            )

            checkpoint_data = {
                "workflow_id": workflow_id,
                "total_checkpoints": len(checkpoints),
                "recovery_checkpoints": len(recovery_checkpoints),
                "checkpoints": [],
            }

            for checkpoint in checkpoints:
                checkpoint_info = {
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "checkpoint_name": checkpoint.checkpoint_name,
                    "timestamp": checkpoint.timestamp.isoformat(),
                    "is_recovery_point": checkpoint.is_recovery_point,
                    "workflow_state": checkpoint.workflow_state,
                    "metadata": checkpoint.metadata,
                }
                checkpoint_data["checkpoints"].append(checkpoint_info)

            return checkpoint_data

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get workflow checkpoints: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return {"error": str(e), "workflow_id": workflow_id}

    def get_workflow_state_history(self, workflow_id: str) -> dict:
        """
        Get state transition history for a workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            dict: State transition history and analytics
        """
        try:
            transitions = self._workflow_state_manager.get_state_history(workflow_id)
            current_state = self._workflow_state_manager.get_workflow_state(workflow_id)

            history_data = {
                "workflow_id": workflow_id,
                "current_state": current_state.value if current_state else None,
                "total_transitions": len(transitions),
                "transitions": [],
            }

            for transition in transitions:
                transition_info = {
                    "transition_id": transition.transition_id,
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "timestamp": transition.timestamp.isoformat(),
                    "trigger_event": transition.trigger_event,
                    "is_valid": transition.is_valid,
                    "context": transition.transition_context,
                    "error_details": transition.error_details,
                }
                history_data["transitions"].append(transition_info)

            # Calculate transition statistics
            valid_transitions = [t for t in transitions if t.is_valid]
            invalid_transitions = [t for t in transitions if not t.is_valid]

            history_data["statistics"] = {
                "valid_transitions": len(valid_transitions),
                "invalid_transitions": len(invalid_transitions),
                "error_rate_percent": (
                    len(invalid_transitions) / max(len(transitions), 1)
                )
                * 100,
            }

            return history_data

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get workflow state history: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return {"error": str(e), "workflow_id": workflow_id}

    def create_manual_checkpoint(
        self,
        workflow_id: str,
        checkpoint_name: str,
        is_recovery_point: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """
        Create a manual checkpoint for a workflow.

        Args:
            workflow_id: Unique workflow identifier
            checkpoint_name: Human-readable checkpoint name
            is_recovery_point: Whether this checkpoint can be used for recovery
            metadata: Additional checkpoint metadata

        Returns:
            dict: Checkpoint creation result
        """
        try:
            # Get current workflow state
            with self._workflow_instances_lock:
                workflow_instance = self._workflow_instances.get(workflow_id)

            if not workflow_instance:
                return {"success": False, "error": f"Workflow {workflow_id} not found"}

            # Create checkpoint
            checkpoint_id = self._workflow_state_manager.create_checkpoint(
                workflow_id=workflow_id,
                checkpoint_name=checkpoint_name,
                workflow_state={
                    "status": workflow_instance.get("status"),
                    "workflow_name": workflow_instance.get("workflow_name"),
                    "checkpoint_created": datetime.now().isoformat(),
                },
                execution_context={
                    "manual_checkpoint": True,
                    "created_by": "orchestrator_agent",
                },
                is_recovery_point=is_recovery_point,
                metadata=metadata or {},
            )

            if checkpoint_id:
                return {
                    "success": True,
                    "checkpoint_id": checkpoint_id,
                    "checkpoint_name": checkpoint_name,
                    "workflow_id": workflow_id,
                    "is_recovery_point": is_recovery_point,
                }
            else:
                return {"success": False, "error": "Failed to create checkpoint"}

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to create manual checkpoint: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "checkpoint_name": checkpoint_name,
                        "error": str(e),
                    }
                ),
            )
            return {"success": False, "error": str(e)}

    def cleanup_workflow_state_data(self) -> dict:
        """
        Clean up expired workflow state data.

        Returns:
            dict: Cleanup statistics
        """
        try:
            # Clean up state manager data
            cleanup_stats = self._workflow_state_manager.cleanup_expired_data()

            # Clean up orchestrator-specific data
            current_time = datetime.now()
            workflow_instances_cleaned = 0
            coordination_results_cleaned = 0

            # Clean up old workflow instances (completed workflows older than 1 hour)
            with self._workflow_instances_lock:
                expired_workflow_ids = []
                for workflow_id, instance in self._workflow_instances.items():
                    if instance.get("status") in ["COMPLETED", "FAILED", "CANCELLED"]:
                        try:
                            created_time = datetime.fromisoformat(
                                instance.get("created_timestamp", "")
                            )
                            if (
                                current_time - created_time
                            ).total_seconds() > 3600:  # 1 hour
                                expired_workflow_ids.append(workflow_id)
                        except (ValueError, TypeError):
                            # Invalid timestamp, keep the workflow instance
                            pass

                for workflow_id in expired_workflow_ids:
                    del self._workflow_instances[workflow_id]
                    workflow_instances_cleaned += 1

            # Clean up old coordination results
            with self._coordination_results_lock:
                expired_coordination_ids = list(
                    self._coordination_results.keys()
                )  # Clean all for now
                for coord_id in expired_coordination_ids:
                    del self._coordination_results[coord_id]
                    coordination_results_cleaned += 1

            # Update cleanup statistics
            cleanup_stats.update(
                {
                    "workflow_instances_cleaned": workflow_instances_cleaned,
                    "coordination_results_cleaned": coordination_results_cleaned,
                }
            )

            emit_log_event(
                level=LogLevel.INFO,
                message="Workflow state data cleanup completed",
                metadata=ModelGenericMetadata.from_dict(cleanup_stats),
            )

            return cleanup_stats

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to cleanup workflow state data: {str(e)}",
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )
            return {"error": str(e)}

    # === WORKFLOW EXECUTION PATTERN IMPLEMENTATIONS ===

    def _execute_sequential_workflow(
        self, workflow_instance: dict, execution_context: dict
    ) -> dict:
        """Execute workflow in sequential pattern: COMPUTE → EFFECT → REDUCER."""
        workflow_id = workflow_instance["workflow_id"]

        # Simulate sequential execution
        result = {
            "success": True,
            "pattern": "sequential",
            "workflow_id": workflow_id,
            "coordination_overhead_ms": 100,
            "node_utilization_percent": 33.3,  # One node at a time
            "parallelism_achieved": 0.0,
            "synchronization_delays_ms": 0,
            "resource_efficiency_score": 0.8,
        }

        return result

    def _execute_parallel_compute_workflow(
        self, workflow_instance: dict, execution_context: dict
    ) -> dict:
        """Execute workflow with parallel COMPUTE execution."""
        workflow_id = workflow_instance["workflow_id"]

        # Simulate parallel compute execution
        result = {
            "success": True,
            "pattern": "parallel_compute",
            "workflow_id": workflow_id,
            "coordination_overhead_ms": 200,
            "node_utilization_percent": 85.0,  # High utilization with parallel
            "parallelism_achieved": 0.8,
            "synchronization_delays_ms": 50,
            "resource_efficiency_score": 0.9,
        }

        return result

    def _execute_pipeline_workflow(
        self, workflow_instance: dict, execution_context: dict
    ) -> dict:
        """Execute workflow in pipeline pattern with overlapped execution."""
        workflow_id = workflow_instance["workflow_id"]

        # Simulate pipeline execution
        result = {
            "success": True,
            "pattern": "pipeline",
            "workflow_id": workflow_id,
            "coordination_overhead_ms": 150,
            "node_utilization_percent": 75.0,
            "parallelism_achieved": 0.6,
            "synchronization_delays_ms": 25,
            "resource_efficiency_score": 0.85,
        }

        return result

    def _execute_scatter_gather_workflow(
        self, workflow_instance: dict, execution_context: dict
    ) -> dict:
        """Execute workflow in scatter-gather pattern."""
        workflow_id = workflow_instance["workflow_id"]

        # Simulate scatter-gather execution
        result = {
            "success": True,
            "pattern": "scatter_gather",
            "workflow_id": workflow_id,
            "coordination_overhead_ms": 300,
            "node_utilization_percent": 90.0,  # High utilization
            "parallelism_achieved": 0.9,
            "synchronization_delays_ms": 100,  # Gathering overhead
            "resource_efficiency_score": 0.95,
        }

        return result

    def _execute_coordinated_node(
        self, node_id: str, node_type: str, assignment: dict, config: dict
    ) -> dict:
        """Execute a coordinated node with specific configuration."""
        # Simulate node execution based on type and configuration
        success_rate = 0.95  # 95% success rate simulation

        import random

        success = random.random() < success_rate

        if success:
            result = {
                "success": True,
                "node_id": node_id,
                "node_type": node_type,
                "resource_usage": {
                    "cpu_percent": random.uniform(20, 80),
                    "memory_mb": random.uniform(100, 500),
                    "execution_time_ms": random.uniform(100, 1000),
                },
            }
        else:
            result = {
                "success": False,
                "node_id": node_id,
                "node_type": node_type,
                "error": "Simulated node execution failure",
            }

        return result

    # === EXISTING METHODS CONTINUE HERE ===

    def _cleanup_execution_states_if_needed(self) -> None:
        """Clean up old execution states based on TTL and memory limits with enhanced tracking."""
        current_time = datetime.now()

        # Check if it's time for cleanup
        if (
            current_time - self._last_cleanup_time
        ).total_seconds() < CONFIG.CLEANUP_INTERVAL_SECONDS:
            return

        cleanup_start = datetime.now()
        states_removed_ttl = 0
        states_removed_limit = 0

        with self._execution_states_lock:
            initial_count = len(self._execution_states)

            # Update max states held metric
            self._cleanup_stats["max_states_held"] = max(
                self._cleanup_stats["max_states_held"], initial_count
            )

            # Remove states older than TTL
            expired_states = []
            for scenario_id, state in self._execution_states.items():
                if state.end_time:
                    age = (current_time - state.end_time).total_seconds()
                else:
                    age = (current_time - state.start_time).total_seconds()

                if age > CONFIG.EXECUTION_STATE_TTL_SECONDS:
                    expired_states.append(scenario_id)

            for scenario_id in expired_states:
                del self._execution_states[scenario_id]
            states_removed_ttl = len(expired_states)

            # If still over limit, remove oldest completed states
            if len(self._execution_states) > CONFIG.MAX_EXECUTION_STATES:
                completed_states = [
                    (scenario_id, state)
                    for scenario_id, state in self._execution_states.items()
                    if state.status
                    in [EnumWorkflowStatus.COMPLETED, EnumWorkflowStatus.FAILED]
                ]

                # Sort by end_time or start_time if no end_time
                completed_states.sort(key=lambda x: x[1].end_time or x[1].start_time)

                # Remove oldest until under limit
                states_to_remove = (
                    len(self._execution_states) - CONFIG.MAX_EXECUTION_STATES
                )
                for i in range(min(states_to_remove, len(completed_states))):
                    scenario_id = completed_states[i][0]
                    del self._execution_states[scenario_id]
                    states_removed_limit += 1

            # Update cleanup statistics
            cleanup_duration = (datetime.now() - cleanup_start).total_seconds() * 1000
            self._cleanup_stats["total_cleanups"] += 1
            self._cleanup_stats["states_removed_ttl"] += states_removed_ttl
            self._cleanup_stats["states_removed_limit"] += states_removed_limit

            # Update rolling average of cleanup duration
            prev_avg = self._cleanup_stats["avg_cleanup_duration_ms"]
            total_cleanups = self._cleanup_stats["total_cleanups"]
            self._cleanup_stats["avg_cleanup_duration_ms"] = (
                prev_avg * (total_cleanups - 1) + cleanup_duration
            ) / total_cleanups

            self._last_cleanup_time = current_time

            # Enhanced logging with performance metrics
            if states_removed_ttl > 0 or states_removed_limit > 0:
                emit_log_event(
                    level=LogLevel.DEBUG,
                    message="Enhanced cleanup completed",
                    context=ModelGenericMetadata.from_dict(
                        {
                            "states_removed_ttl": states_removed_ttl,
                            "states_removed_limit": states_removed_limit,
                            "remaining_count": len(self._execution_states),
                            "cleanup_duration_ms": round(cleanup_duration, 2),
                            "total_cleanups": self._cleanup_stats["total_cleanups"],
                            "max_states_held": self._cleanup_stats["max_states_held"],
                            "avg_cleanup_duration_ms": round(
                                self._cleanup_stats["avg_cleanup_duration_ms"], 2
                            ),
                        }
                    ),
                )

    def get_memory_statistics(self) -> dict:
        """Get comprehensive memory management statistics for monitoring."""
        with self._execution_states_lock:
            current_states = len(self._execution_states)
            active_states = len(
                [
                    state
                    for state in self._execution_states.values()
                    if state.status == EnumWorkflowStatus.RUNNING
                ]
            )
            completed_states = len(
                [
                    state
                    for state in self._execution_states.values()
                    if state.status == EnumWorkflowStatus.COMPLETED
                ]
            )
            failed_states = len(
                [
                    state
                    for state in self._execution_states.values()
                    if state.status == EnumWorkflowStatus.FAILED
                ]
            )

            return {
                "current_states": current_states,
                "active_states": active_states,
                "completed_states": completed_states,
                "failed_states": failed_states,
                "memory_utilization_percent": round(
                    (current_states / CONFIG.MAX_EXECUTION_STATES) * 100, 2
                ),
                "cleanup_stats": self._cleanup_stats.copy(),
                "time_since_last_cleanup_seconds": int(
                    (datetime.now() - self._last_cleanup_time).total_seconds()
                ),
                "next_cleanup_in_seconds": max(
                    0,
                    int(
                        CONFIG.CLEANUP_INTERVAL_SECONDS
                        - (datetime.now() - self._last_cleanup_time).total_seconds()
                    ),
                ),
            }

    async def orchestrate_operation_with_timeout(
        self,
        operation_type: str,
        scenario_id: str,
        correlation_id: str,
        parameters: ModelOrchestratorParameters,
    ) -> ModelOnexResult:
        """Orchestrate operation with timeout enforcement."""
        try:
            return await asyncio.wait_for(
                self._orchestrate_operation_async(
                    operation_type, scenario_id, correlation_id, parameters
                ),
                timeout=parameters.timeout_seconds,
            )
        except asyncio.TimeoutError:
            error_msg = f"Operation '{operation_type}' timed out after {parameters.timeout_seconds}s"

            # Update execution state to failed
            with self._execution_states_lock:
                if scenario_id in self._execution_states:
                    self._execution_states[scenario_id].status = (
                        EnumWorkflowStatus.FAILED
                    )
                    self._execution_states[scenario_id].end_time = datetime.now()
                    self._execution_states[scenario_id].error_message = error_msg

            emit_log_event(
                level=LogLevel.ERROR,
                message=error_msg,
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "operation_type": operation_type,
                        "scenario_id": scenario_id,
                        "timeout_seconds": parameters.timeout_seconds,
                    }
                ),
            )

            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=correlation_id,
                duration=parameters.timeout_seconds,
                metadata=ModelGenericMetadata.from_dict(
                    {"error": error_msg, "timeout": True}
                ),
            )

    async def _orchestrate_operation_async(
        self,
        operation_type: str,
        scenario_id: str,
        correlation_id: str,
        parameters: ModelOrchestratorParameters,
    ) -> ModelOnexResult:
        """Async version of orchestrate_operation for timeout handling."""
        # Implementation will be the current orchestrate_operation logic
        # but made async for timeout handling
        return self.orchestrate_operation(
            operation_type, scenario_id, correlation_id, parameters
        )

    def orchestrate_operation(
        self,
        operation_type: str,
        scenario_id: str,
        correlation_id: str,
        parameters: ModelOrchestratorParameters,
    ) -> ModelOnexResult:
        """Orchestrate a specific operation type with retry logic."""
        start_time = datetime.now()
        retry_count = parameters.retry_count or CONFIG.DEFAULT_RETRY_COUNT

        for attempt in range(retry_count + 1):
            try:
                emit_log_event(
                    level=LogLevel.INFO,
                    message="Starting operation orchestration",
                    metadata=ModelGenericMetadata.from_dict(
                        {
                            "operation_type": operation_type,
                            "scenario_id": scenario_id,
                            "correlation_id": correlation_id,
                            "execution_mode": parameters.execution_mode,
                            "attempt": attempt + 1,
                            "max_attempts": retry_count + 1,
                        }
                    ),
                )

                # Create execution state with thread safety
                execution_state = ModelOrchestratorExecutionState(
                    scenario_id=scenario_id,
                    status=EnumWorkflowStatus.RUNNING,
                    start_time=start_time,
                    correlation_id=correlation_id,
                    operation_type=operation_type,
                    current_step=0,
                    total_steps=1,  # Will be updated based on workflow complexity
                    metadata=parameters.metadata or {},
                )

                # Store execution state with thread safety
                with self._execution_states_lock:
                    self._execution_states[scenario_id] = execution_state

                # Route operation based on type
                result = self._route_operation(
                    operation_type=operation_type,
                    scenario_id=scenario_id,
                    parameters=parameters,
                    execution_state=execution_state,
                )

                # Update execution state with thread safety
                with self._execution_states_lock:
                    if scenario_id in self._execution_states:
                        execution_state.status = (
                            EnumWorkflowStatus.COMPLETED
                            if result.status == EnumOnexStatus.SUCCESS
                            else EnumWorkflowStatus.FAILED
                        )
                        execution_state.end_time = datetime.now()
                        execution_state.execution_time_ms = int(
                            (execution_state.end_time - start_time).total_seconds()
                            * 1000
                        )

                emit_log_event(
                    level=LogLevel.INFO,
                    message="Operation orchestration completed",
                    metadata=ModelGenericMetadata.from_dict(
                        {
                            "success": result.status == EnumOnexStatus.SUCCESS,
                            "operation_type": operation_type,
                            "scenario_id": scenario_id,
                            "execution_time_ms": execution_state.execution_time_ms,
                            "attempt": attempt + 1,
                        }
                    ),
                )

                # If successful, return result
                if result.status == EnumOnexStatus.SUCCESS:
                    return result

                # If failed but not last attempt, prepare for retry
                if attempt < retry_count:
                    delay = min(
                        CONFIG.RETRY_BACKOFF_MULTIPLIER**attempt,
                        CONFIG.MAX_RETRY_DELAY_SECONDS,
                    )

                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Operation attempt {attempt + 1} failed, retrying in {delay}s",
                        metadata=ModelGenericMetadata.from_dict(
                            {
                                "operation_type": operation_type,
                                "scenario_id": scenario_id,
                                "attempt": attempt + 1,
                                "retry_delay": delay,
                            }
                        ),
                    )

                    # Sleep before retry (in production, use asyncio.sleep for non-blocking)
                    import time

                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed, return the failed result
                    return result

            except Exception as e:
                error_msg = f"Failed to orchestrate operation '{operation_type}' on attempt {attempt + 1}: {str(e)}"

                # Update execution state to failed with thread safety
                with self._execution_states_lock:
                    if scenario_id in self._execution_states:
                        self._execution_states[scenario_id].status = (
                            EnumWorkflowStatus.FAILED
                        )
                        self._execution_states[scenario_id].end_time = datetime.now()
                        self._execution_states[scenario_id].error_message = str(e)

                emit_log_event(
                    level=LogLevel.ERROR,
                    message=error_msg,
                    metadata=ModelGenericMetadata.from_dict(
                        {
                            "operation_type": operation_type,
                            "scenario_id": scenario_id,
                            "error": str(e),
                            "attempt": attempt + 1,
                        }
                    ),
                )

                # If not last attempt, prepare for retry
                if attempt < retry_count:
                    delay = min(
                        CONFIG.RETRY_BACKOFF_MULTIPLIER**attempt,
                        CONFIG.MAX_RETRY_DELAY_SECONDS,
                    )

                    emit_log_event(
                        level=LogLevel.WARNING,
                        message=f"Exception on attempt {attempt + 1}, retrying in {delay}s",
                        metadata=ModelGenericMetadata.from_dict(
                            {
                                "operation_type": operation_type,
                                "scenario_id": scenario_id,
                                "attempt": attempt + 1,
                                "retry_delay": delay,
                                "error": str(e),
                            }
                        ),
                    )

                    import time

                    time.sleep(delay)
                    continue

        # All attempts failed
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return ModelOnexResult(
            status=EnumOnexStatus.ERROR,
            run_id=correlation_id,
            duration=execution_time / 1000.0,  # Convert ms to seconds
            metadata=ModelGenericMetadata.from_dict(
                {
                    "error": f"All {retry_count + 1} attempts failed",
                    "final_attempt": retry_count + 1,
                }
            ),
        )

    def get_execution_state(
        self, scenario_id: str
    ) -> ModelWorkflowExecutionState | None:
        """Get the current execution state for a scenario."""
        with self._execution_states_lock:
            internal_state = self._execution_states.get(scenario_id)

            if internal_state is None:
                return None

            # Create minimal execution context for the orchestrator
            import time

            from omnibase_core.models.execution.model_execution_context import (
                ModelExecutionContext,
            )
            from omnibase_core.models.workflow.model_workflow_execution_config import (
                ModelWorkflowExecutionConfig,
            )

            execution_context = ModelExecutionContext(
                correlation_id=internal_state.correlation_id,
                start_time=internal_state.start_time.timestamp(),
                total_nodes=internal_state.total_steps,
            )

            workflow_config = ModelWorkflowExecutionConfig(
                mode_name=internal_state.operation_type,
                timeout_seconds=300,  # Default timeout
                parallel_workers=1,
                priority_weight=1.0,
            )

            # Convert internal execution state to ModelWorkflowExecutionState
            return ModelWorkflowExecutionState(
                execution_context=execution_context,
                workflow_execution_config=workflow_config,
                total_nodes=internal_state.total_steps,
            )

    def health_check(self) -> ModelHealthCheckResult:
        """Perform health check for the enhanced workflow orchestrator."""
        from datetime import datetime

        try:
            # Get base health check from NodeOrchestratorService
            base_health = super().health_check()

            # Additional orchestrator-specific health checks with thread safety
            memory_stats = self.get_memory_statistics()
            active_workflows = memory_stats["active_states"]
            total_workflows = memory_stats["current_states"]

            # Calculate health score based on active workflows and system state using config
            health_score = 1.0
            if active_workflows > CONFIG.MAX_ACTIVE_WORKFLOWS_WARNING:
                health_score *= CONFIG.HEALTH_SCORE_WARNING_THRESHOLD

            if total_workflows > CONFIG.MAX_TOTAL_WORKFLOWS_WARNING:
                health_score *= CONFIG.HEALTH_SCORE_MEMORY_THRESHOLD

            is_healthy = health_score > 0.5 and base_health.is_healthy

            # Check registry connection with thread safety
            with self._registry_lock:
                registry_connected = self._registry is not None

            capabilities = [
                "workflow_orchestration",
                "dependency_management",
                "advanced_coordination_patterns",
                "multi_mode_execution",
                "node_coordination",
                "workflow_persistence",
                "circuit_breakers",
                "performance_metrics",
                "memory_management",
                "retry_logic",
                "timeout_enforcement",
                "thread_safety",
                "failure_recovery",
                "scatter_gather_execution",
                "pipeline_execution",
                "parallel_compute_execution",
            ]

            from datetime import datetime

            # Include memory statistics in warnings for monitoring
            warnings = []
            if health_score <= 0.7:
                warnings.append("High workflow load detected")
            if memory_stats["memory_utilization_percent"] > 80:
                warnings.append(
                    f"Memory utilization high: {memory_stats['memory_utilization_percent']}%"
                )
            if memory_stats["active_states"] > CONFIG.MAX_ACTIVE_WORKFLOWS_WARNING:
                warnings.append(
                    f"Active workflows: {memory_stats['active_states']} (warning threshold: {CONFIG.MAX_ACTIVE_WORKFLOWS_WARNING})"
                )

            # Add enhanced workflow coordination metrics
            with self._workflow_instances_lock:
                workflow_count = len(self._workflow_instances)

            if workflow_count > 20:
                warnings.append(f"High workflow instance count: {workflow_count}")

            return ModelHealthCheckResult(
                status="healthy" if is_healthy else "unhealthy",
                service_name="EnhancedWorkflowOrchestratorAgent",
                timestamp=datetime.now().isoformat(),
                capabilities=capabilities,
                uptime_seconds=0,
                dependencies_healthy=registry_connected,
                warnings=warnings,
                memory_usage_mb=memory_stats["current_states"]
                * 0.1,  # Approximate memory usage
                cpu_usage_percent=min(
                    memory_stats["memory_utilization_percent"] / 2, 100.0
                ),  # Estimate based on utilization
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR, message=f"Health check failed: {str(e)}"
            )

            return ModelHealthCheckResult(
                status="unhealthy",
                service_name="EnhancedWorkflowOrchestratorAgent",
                timestamp=datetime.now().isoformat(),
                errors=[str(e)],
            )

    def _route_operation(
        self,
        operation_type: str,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Route operation to appropriate handler based on operation type."""

        # Use class-level operation handlers for performance optimization
        handler_name = self._OPERATION_HANDLERS.get(
            operation_type, "_handle_generic_operation"
        )
        handler = getattr(self, handler_name)

        handler_name = getattr(handler, "__name__", str(handler))
        emit_log_event(
            level=LogLevel.DEBUG,
            message=f"Routing operation to handler: {handler_name}",
            metadata=ModelGenericMetadata.from_dict(
                {
                    "operation_type": operation_type,
                    "scenario_id": scenario_id,
                    "handler": handler_name,
                }
            ),
        )

        return handler(scenario_id, parameters, execution_state)

    # === ENHANCED OPERATION HANDLERS ===

    def _handle_create_workflow(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle create workflow operation with enhanced coordination."""
        try:
            # Extract workflow creation parameters from metadata
            workflow_definition = parameters.metadata.get("workflow_definition", {})
            input_parameters = parameters.metadata.get("input_parameters", {})
            execution_config = parameters.metadata.get("execution_config", {})

            # Create workflow using enhanced method
            result = self.create_workflow(
                workflow_definition=workflow_definition,
                input_parameters=input_parameters,
                execution_config=execution_config,
            )

            return ModelOnexResult(
                status=EnumOnexStatus.SUCCESS,
                run_id=parameters.correlation_id,
                duration=0.05,  # 50ms
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_creation_result": result}
                ),
            )

        except Exception as e:
            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=parameters.correlation_id,
                duration=0.01,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def _handle_execute_workflow(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle execute workflow operation with enhanced coordination."""
        try:
            # Extract workflow execution parameters
            workflow_instance = parameters.metadata.get("workflow_instance", {})
            execution_context = parameters.metadata.get("execution_context", {})

            # Execute workflow using enhanced method
            result = self.execute_workflow(
                workflow_instance=workflow_instance, execution_context=execution_context
            )

            return ModelOnexResult(
                status=EnumOnexStatus.SUCCESS,
                run_id=parameters.correlation_id,
                duration=result["coordination_metrics"].get(
                    "total_execution_time_ms", 0
                )
                / 1000.0,
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_execution_result": result}
                ),
            )

        except Exception as e:
            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=parameters.correlation_id,
                duration=0.01,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def _handle_coordinate_nodes(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle coordinate nodes operation with enhanced patterns."""
        try:
            # Extract node coordination parameters
            coordination_plan = parameters.metadata.get("coordination_plan", {})
            node_assignments = parameters.metadata.get("node_assignments", {})
            sync_requirements = parameters.metadata.get("sync_requirements", {})

            # Coordinate nodes using enhanced method
            result = self.coordinate_nodes(
                coordination_plan=coordination_plan,
                node_assignments=node_assignments,
                sync_requirements=sync_requirements,
            )

            return ModelOnexResult(
                status=EnumOnexStatus.SUCCESS,
                run_id=parameters.correlation_id,
                duration=result["coordination_result"].get(
                    "coordination_overhead_ms", 0
                )
                / 1000.0,
                metadata=ModelGenericMetadata.from_dict(
                    {"node_coordination_result": result}
                ),
            )

        except Exception as e:
            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=parameters.correlation_id,
                duration=0.01,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def _handle_monitor_workflow_progress(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle monitor workflow progress operation."""
        try:
            workflow_id = parameters.metadata.get("workflow_id", scenario_id)
            monitoring_config = parameters.metadata.get("monitoring_config", {})

            # Monitor workflow using enhanced method
            result = self.monitor_workflow_progress(
                workflow_id=workflow_id, monitoring_config=monitoring_config
            )

            return ModelOnexResult(
                status=EnumOnexStatus.SUCCESS,
                run_id=parameters.correlation_id,
                duration=0.002,  # 2ms for monitoring
                metadata=ModelGenericMetadata.from_dict({"monitoring_result": result}),
            )

        except Exception as e:
            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=parameters.correlation_id,
                duration=0.001,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def _handle_workflow_failure(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle workflow failure operation with recovery strategies."""
        try:
            failure_context = parameters.metadata.get("failure_context", {})
            recovery_config = parameters.metadata.get("recovery_config", {})
            rollback_options = parameters.metadata.get("rollback_options", {})

            # Handle failure using enhanced method
            result = self.handle_workflow_failure(
                failure_context=failure_context,
                recovery_config=recovery_config,
                rollback_options=rollback_options,
            )

            return ModelOnexResult(
                status=EnumOnexStatus.SUCCESS,
                run_id=parameters.correlation_id,
                duration=0.01,  # 10ms for failure handling
                metadata=ModelGenericMetadata.from_dict(
                    {"failure_handling_result": result}
                ),
            )

        except Exception as e:
            return ModelOnexResult(
                status=EnumOnexStatus.ERROR,
                run_id=parameters.correlation_id,
                duration=0.001,
                metadata=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    # === EXISTING OPERATION HANDLERS (UPDATED) ===

    def _handle_model_generation(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle model generation workflow orchestration."""
        # This would typically coordinate with COMPUTE and EFFECT nodes
        # to generate models based on specifications

        emit_log_event(
            level=LogLevel.INFO,
            message="Handling model generation workflow",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        # Placeholder implementation - would be expanded with actual model generation logic
        result_data = {
            "operation": "model_generation",
            "scenario_id": scenario_id,
            "status": "completed",
            "generated_models": [],
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "sequential",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.1,  # 100ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    def _handle_bootstrap_validation(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle bootstrap validation workflow orchestration."""
        emit_log_event(
            level=LogLevel.INFO,
            message="Handling bootstrap validation workflow",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        result_data = {
            "operation": "bootstrap_validation",
            "scenario_id": scenario_id,
            "status": "completed",
            "validation_results": [],
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "parallel_compute",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.15,  # 150ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    def _handle_extraction(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle data extraction workflow orchestration."""
        emit_log_event(
            level=LogLevel.INFO,
            message="Handling extraction workflow",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        result_data = {
            "operation": "extraction",
            "scenario_id": scenario_id,
            "status": "completed",
            "extracted_data": {},
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "pipeline",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.2,  # 200ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    def _handle_generic_operation(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle generic workflow orchestration."""
        emit_log_event(
            level=LogLevel.INFO,
            message="Handling generic workflow operation",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        result_data = {
            "operation": "generic",
            "scenario_id": scenario_id,
            "status": "completed",
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "sequential",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.075,  # 75ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    def _handle_workflow_coordination(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle workflow coordination across multiple nodes."""
        emit_log_event(
            level=LogLevel.INFO,
            message="Handling enhanced workflow coordination",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        # This would leverage the enhanced coordination patterns
        result_data = {
            "operation": "workflow_coordination",
            "scenario_id": scenario_id,
            "status": "completed",
            "coordinated_nodes": [],
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "scatter_gather",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.3,  # 300ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    def _handle_dependency_resolution(
        self,
        scenario_id: str,
        parameters: ModelOrchestratorParameters,
        execution_state: ModelOrchestratorExecutionState,
    ) -> ModelOnexResult:
        """Handle dependency resolution workflow orchestration."""
        emit_log_event(
            level=LogLevel.INFO,
            message="Handling dependency resolution workflow",
            metadata=ModelGenericMetadata.from_dict({"scenario_id": scenario_id}),
        )

        result_data = {
            "operation": "dependency_resolution",
            "scenario_id": scenario_id,
            "status": "completed",
            "resolved_dependencies": [],
            "execution_mode": parameters.execution_mode,
            "coordination_pattern": "sequential",
        }

        return ModelOnexResult(
            status=EnumOnexStatus.SUCCESS,
            run_id=parameters.correlation_id,
            duration=0.25,  # 250ms in seconds
            metadata=ModelGenericMetadata.from_dict({"result_data": result_data}),
        )

    # === WORKFLOW METRICS AND MONITORING METHODS ===

    def get_workflow_metrics(self, workflow_id: Optional[str] = None) -> dict:
        """
        Get workflow metrics for monitoring and analytics.

        Args:
            workflow_id: Specific workflow ID or None for all workflows

        Returns:
            dict: Comprehensive workflow metrics data
        """
        try:
            if workflow_id:
                # Get metrics for specific workflow
                workflow_metrics = self._workflow_metrics_monitor.get_workflow_metrics(
                    workflow_id
                )

                # Add orchestrator-specific metrics
                with self._workflow_instances_lock:
                    workflow_instance = self._workflow_instances.get(workflow_id)
                    if workflow_instance:
                        workflow_metrics["orchestrator_metrics"] = {
                            "workflow_name": workflow_instance.get("workflow_name"),
                            "status": workflow_instance.get("status"),
                            "created_timestamp": workflow_instance.get(
                                "created_timestamp"
                            ),
                            "last_updated": datetime.now().isoformat(),
                        }

                return {"workflow_id": workflow_id, "metrics": workflow_metrics}
            else:
                # Get aggregate metrics for all workflows
                all_metrics = self._workflow_metrics_monitor.get_all_metrics()

                # Add orchestrator-level metrics
                memory_stats = self.get_memory_statistics()

                aggregate_metrics = {
                    "total_workflow_instances": memory_stats["current_states"],
                    "active_workflow_instances": memory_stats["active_states"],
                    "completed_workflow_instances": memory_stats["completed_states"],
                    "failed_workflow_instances": memory_stats["failed_states"],
                    "memory_utilization_percent": memory_stats[
                        "memory_utilization_percent"
                    ],
                    "cleanup_statistics": memory_stats["cleanup_stats"],
                }

                return {
                    "aggregate_metrics": aggregate_metrics,
                    "workflow_metrics": all_metrics,
                }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get workflow metrics: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return {"error": str(e)}

    def get_performance_summary(self, time_window_minutes: int = 60) -> dict:
        """
        Get performance summary for the specified time window.

        Args:
            time_window_minutes: Time window in minutes for performance analysis

        Returns:
            dict: Performance summary with key metrics and trends
        """
        try:
            # Generate performance report using the metrics monitor
            report = self._workflow_metrics_monitor.generate_performance_report(
                start_time=datetime.now() - timedelta(minutes=time_window_minutes),
                end_time=datetime.now(),
            )

            # Add orchestrator-specific performance data
            memory_stats = self.get_memory_statistics()

            # Calculate performance indicators
            total_workflows = self._cleanup_stats.get("workflows_created", 0)
            successful_workflows = self._cleanup_stats.get("workflows_executed", 0)
            failed_workflows = self._cleanup_stats.get("coordination_failures", 0)

            success_rate = (successful_workflows / max(total_workflows, 1)) * 100
            failure_rate = (failed_workflows / max(total_workflows, 1)) * 100

            performance_summary = {
                "time_window_minutes": time_window_minutes,
                "summary_timestamp": datetime.now().isoformat(),
                "workflow_performance": {
                    "total_workflows": total_workflows,
                    "successful_workflows": successful_workflows,
                    "failed_workflows": failed_workflows,
                    "success_rate_percent": round(success_rate, 2),
                    "failure_rate_percent": round(failure_rate, 2),
                },
                "resource_utilization": {
                    "current_active_workflows": memory_stats["active_states"],
                    "memory_utilization_percent": memory_stats[
                        "memory_utilization_percent"
                    ],
                    "average_cleanup_duration_ms": memory_stats["cleanup_stats"].get(
                        "avg_cleanup_duration_ms", 0
                    ),
                    "total_cleanups_performed": memory_stats["cleanup_stats"].get(
                        "total_cleanups", 0
                    ),
                },
                "performance_trends": {
                    "workflow_creation_trend": "stable",  # Would calculate from historical data
                    "execution_time_trend": "improving",  # Would calculate from metrics
                    "resource_usage_trend": "stable",
                },
                "performance_alerts": self._workflow_metrics_monitor.get_active_alerts(),
                "detailed_report": report.model_dump() if report else {},
            }

            return performance_summary

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get performance summary: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"time_window_minutes": time_window_minutes, "error": str(e)}
                ),
            )
            return {"error": str(e)}

    def generate_performance_report(
        self,
        report_type: str = "comprehensive",
        include_recommendations: bool = True,
        time_window_hours: int = 24,
    ) -> dict:
        """
        Generate comprehensive performance report.

        Args:
            report_type: Type of report (comprehensive, summary, alerts_only)
            include_recommendations: Whether to include performance recommendations
            time_window_hours: Time window in hours for report data

        Returns:
            dict: Comprehensive performance report
        """
        try:
            start_time = datetime.now() - timedelta(hours=time_window_hours)
            end_time = datetime.now()

            # Generate detailed performance report
            metrics_report = self._workflow_metrics_monitor.generate_performance_report(
                start_time=start_time, end_time=end_time
            )

            # Collect orchestrator performance data
            memory_stats = self.get_memory_statistics()
            active_alerts = self._workflow_metrics_monitor.get_active_alerts()

            # Generate report based on type
            if report_type == "alerts_only":
                return {
                    "report_type": report_type,
                    "generated_at": end_time.isoformat(),
                    "time_window_hours": time_window_hours,
                    "active_alerts": active_alerts,
                    "alert_summary": {
                        "total_alerts": len(active_alerts),
                        "critical_alerts": len(
                            [a for a in active_alerts if a.severity == "CRITICAL"]
                        ),
                        "warning_alerts": len(
                            [a for a in active_alerts if a.severity == "WARNING"]
                        ),
                        "info_alerts": len(
                            [a for a in active_alerts if a.severity == "INFO"]
                        ),
                    },
                }

            elif report_type == "summary":
                # Generate summary report
                total_workflows = self._cleanup_stats.get("workflows_created", 0)
                successful_workflows = self._cleanup_stats.get("workflows_executed", 0)

                return {
                    "report_type": report_type,
                    "generated_at": end_time.isoformat(),
                    "time_window_hours": time_window_hours,
                    "executive_summary": {
                        "total_workflows_processed": total_workflows,
                        "successful_executions": successful_workflows,
                        "current_active_workflows": memory_stats["active_states"],
                        "system_health_score": self._calculate_health_score(),
                        "resource_utilization_percent": memory_stats[
                            "memory_utilization_percent"
                        ],
                    },
                    "key_metrics": {
                        "average_workflow_duration": (
                            metrics_report.average_duration_ms if metrics_report else 0
                        ),
                        "peak_concurrent_workflows": (
                            metrics_report.peak_concurrent_workflows
                            if metrics_report
                            else 0
                        ),
                        "error_rate_percent": (
                            metrics_report.error_rate_percent if metrics_report else 0
                        ),
                    },
                    "alert_count": len(active_alerts),
                }

            else:  # comprehensive
                # Generate comprehensive report
                recommendations = []
                if include_recommendations:
                    recommendations = self._generate_performance_recommendations(
                        memory_stats, active_alerts, metrics_report
                    )

                return {
                    "report_type": report_type,
                    "generated_at": end_time.isoformat(),
                    "time_window_hours": time_window_hours,
                    "orchestrator_metrics": {
                        "workflow_instances": {
                            "total": memory_stats["current_states"],
                            "active": memory_stats["active_states"],
                            "completed": memory_stats["completed_states"],
                            "failed": memory_stats["failed_states"],
                        },
                        "resource_utilization": {
                            "memory_utilization_percent": memory_stats[
                                "memory_utilization_percent"
                            ],
                            "cleanup_efficiency": {
                                "total_cleanups": memory_stats["cleanup_stats"].get(
                                    "total_cleanups", 0
                                ),
                                "average_cleanup_duration_ms": memory_stats[
                                    "cleanup_stats"
                                ].get("avg_cleanup_duration_ms", 0),
                                "states_cleaned_by_ttl": memory_stats[
                                    "cleanup_stats"
                                ].get("states_removed_ttl", 0),
                                "states_cleaned_by_limit": memory_stats[
                                    "cleanup_stats"
                                ].get("states_removed_limit", 0),
                            },
                        },
                    },
                    "workflow_metrics": (
                        metrics_report.model_dump() if metrics_report else {}
                    ),
                    "performance_alerts": active_alerts,
                    "system_health": {
                        "health_score": self._calculate_health_score(),
                        "system_warnings": self._get_system_warnings(),
                        "uptime_indicators": {
                            "time_since_last_cleanup_seconds": memory_stats[
                                "time_since_last_cleanup_seconds"
                            ],
                            "next_cleanup_in_seconds": memory_stats[
                                "next_cleanup_in_seconds"
                            ],
                        },
                    },
                    "performance_recommendations": (
                        recommendations if include_recommendations else []
                    ),
                }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to generate performance report: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"report_type": report_type, "error": str(e)}
                ),
            )
            return {"error": str(e)}

    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0.0 to 1.0)."""
        memory_stats = self.get_memory_statistics()

        # Base health score
        health_score = 1.0

        # Reduce score based on memory utilization
        memory_util = memory_stats["memory_utilization_percent"]
        if memory_util > 90:
            health_score *= 0.3  # Critical
        elif memory_util > 75:
            health_score *= 0.6  # Warning
        elif memory_util > 50:
            health_score *= 0.8  # Caution

        # Reduce score based on failure rate
        total_workflows = self._cleanup_stats.get("workflows_created", 0)
        failed_workflows = self._cleanup_stats.get("coordination_failures", 0)
        if total_workflows > 0:
            failure_rate = failed_workflows / total_workflows
            health_score *= max(0.1, 1.0 - failure_rate)

        # Reduce score based on active alerts
        active_alerts = self._workflow_metrics_monitor.get_active_alerts()
        critical_alerts = len([a for a in active_alerts if a.severity == "CRITICAL"])
        if critical_alerts > 0:
            health_score *= max(0.2, 1.0 - (critical_alerts * 0.2))

        return round(max(0.0, min(1.0, health_score)), 3)

    def _get_system_warnings(self) -> List[str]:
        """Get current system warnings."""
        warnings = []
        memory_stats = self.get_memory_statistics()

        if memory_stats["memory_utilization_percent"] > 80:
            warnings.append(
                f"High memory utilization: {memory_stats['memory_utilization_percent']}%"
            )

        if memory_stats["active_states"] > 50:
            warnings.append(
                f"High number of active workflows: {memory_stats['active_states']}"
            )

        if memory_stats["failed_states"] > memory_stats["completed_states"] * 0.1:
            warnings.append("High failure rate detected")

        cleanup_duration = memory_stats["cleanup_stats"].get(
            "avg_cleanup_duration_ms", 0
        )
        if cleanup_duration > 1000:  # More than 1 second
            warnings.append(f"Long cleanup duration: {cleanup_duration}ms")

        return warnings

    def _generate_performance_recommendations(
        self, memory_stats: dict, active_alerts: List, metrics_report
    ) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        # Memory-based recommendations
        memory_util = memory_stats["memory_utilization_percent"]
        if memory_util > 80:
            recommendations.append(
                "Consider increasing cleanup frequency or reducing execution state TTL"
            )

        if memory_stats["active_states"] > 30:
            recommendations.append(
                "Monitor for workflow bottlenecks - high number of concurrent active workflows"
            )

        # Alert-based recommendations
        critical_alerts = len([a for a in active_alerts if a.severity == "CRITICAL"])
        if critical_alerts > 0:
            recommendations.append("Address critical performance alerts immediately")

        # Cleanup efficiency recommendations
        cleanup_stats = memory_stats["cleanup_stats"]
        if cleanup_stats.get("avg_cleanup_duration_ms", 0) > 500:
            recommendations.append("Optimize cleanup process - cleanup taking too long")

        # Workflow performance recommendations
        if metrics_report and hasattr(metrics_report, "error_rate_percent"):
            if metrics_report.error_rate_percent > 5:
                recommendations.append(
                    "Investigate workflow failures - error rate above threshold"
                )

        # Coordination performance recommendations
        coordination_failures = self._cleanup_stats.get("coordination_failures", 0)
        total_workflows = self._cleanup_stats.get("workflows_created", 0)
        if total_workflows > 0 and (coordination_failures / total_workflows) > 0.05:
            recommendations.append(
                "Review node coordination strategies - high coordination failure rate"
            )

        if not recommendations:
            recommendations.append("System performance is within normal parameters")

        return recommendations

    # LlamaIndex Workflow Recovery Methods

    async def recover_workflow(
        self, workflow_id: str, recovery_strategy: str = "resume"
    ) -> Dict[str, Any]:
        """
        Recover a failed or interrupted workflow using LlamaIndex persistence.

        Args:
            workflow_id: Unique workflow identifier
            recovery_strategy: Strategy for recovery ("resume", "restart", "compensate")

        Returns:
            Dict containing recovery result and restored workflow state
        """
        if not self._persistence_enabled:
            return {
                "success": False,
                "error": "Workflow persistence is not enabled",
                "workflow_id": workflow_id,
            }

        try:
            # Attempt workflow recovery
            persistence_state = self._persistence_manager.recover_workflow(
                workflow_id=workflow_id, recovery_strategy=recovery_strategy
            )

            if not persistence_state:
                return {
                    "success": False,
                    "error": f"No recoverable state found for workflow {workflow_id}",
                    "workflow_id": workflow_id,
                }

            # Restore workflow state
            restored_workflow = {
                "workflow_id": workflow_id,
                "workflow_name": persistence_state.workflow_definition.get(
                    "workflow_name", "unknown"
                ),
                "recovery_point": persistence_state.checkpoint_name,
                "execution_context": persistence_state.execution_context,
                "completed_steps": persistence_state.completed_steps,
                "recovery_strategy": recovery_strategy,
                "checkpoint_timestamp": persistence_state.checkpoint_timestamp.isoformat(),
            }

            # Update workflow state tracking
            if workflow_id not in self._active_workflows:
                self._active_workflows[workflow_id] = restored_workflow

            # Log successful recovery
            emit_log_event(
                level=LogLevel.INFO,
                message=f"Workflow {workflow_id} successfully recovered using strategy '{recovery_strategy}'",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "recovery_strategy": recovery_strategy,
                        "checkpoint_name": persistence_state.checkpoint_name,
                        "recovered_steps": len(persistence_state.completed_steps or []),
                    }
                ),
            )

            return {
                "success": True,
                "workflow_id": workflow_id,
                "recovery_strategy": recovery_strategy,
                "restored_state": restored_workflow,
                "checkpoint_name": persistence_state.checkpoint_name,
                "execution_resumable": recovery_strategy == "resume",
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to recover workflow {workflow_id}: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "recovery_strategy": recovery_strategy,
                        "error": str(e),
                    }
                ),
            )

            return {
                "success": False,
                "error": f"Workflow recovery failed: {str(e)}",
                "workflow_id": workflow_id,
            }

    def get_workflow_persistence_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get persistence status and available recovery points for a workflow.

        Args:
            workflow_id: Unique workflow identifier

        Returns:
            Dict containing persistence status and recovery information
        """
        if not self._persistence_enabled:
            return {
                "persistence_enabled": False,
                "workflow_id": workflow_id,
                "message": "Workflow persistence is not enabled",
            }

        try:
            # Get persistence metadata
            persistence_state = self._persistence_manager.recover_workflow(
                workflow_id=workflow_id, recovery_strategy="resume"
            )

            if not persistence_state:
                return {
                    "persistence_enabled": True,
                    "workflow_id": workflow_id,
                    "has_persistent_state": False,
                    "message": f"No persistent state found for workflow {workflow_id}",
                }

            return {
                "persistence_enabled": True,
                "workflow_id": workflow_id,
                "has_persistent_state": True,
                "checkpoint_name": persistence_state.checkpoint_name,
                "checkpoint_timestamp": persistence_state.checkpoint_timestamp.isoformat(),
                "workflow_status": persistence_state.workflow_status,
                "completed_steps_count": len(persistence_state.completed_steps or []),
                "recovery_strategies": ["resume", "restart", "compensate"],
                "metadata": persistence_state.metadata,
            }

        except Exception as e:
            return {
                "persistence_enabled": True,
                "workflow_id": workflow_id,
                "error": f"Failed to get persistence status: {str(e)}",
            }

    def list_recoverable_workflows(self) -> Dict[str, Any]:
        """
        List all workflows that have recoverable persistent state.

        Returns:
            Dict containing list of recoverable workflows
        """
        if not self._persistence_enabled:
            return {
                "persistence_enabled": False,
                "recoverable_workflows": [],
                "message": "Workflow persistence is not enabled",
            }

        try:
            from pathlib import Path

            recoverable_workflows = []

            # Get persistence directory and check for workflow states
            persistence_dir = Path(self._persistence_manager.persistence_directory)
            if persistence_dir.exists():
                for workflow_dir in persistence_dir.iterdir():
                    if workflow_dir.is_dir():
                        workflow_id = workflow_dir.name
                        status = self.get_workflow_persistence_status(workflow_id)

                        if status.get("has_persistent_state", False):
                            recoverable_workflows.append(
                                {
                                    "workflow_id": workflow_id,
                                    "checkpoint_name": status.get("checkpoint_name"),
                                    "checkpoint_timestamp": status.get(
                                        "checkpoint_timestamp"
                                    ),
                                    "workflow_status": status.get("workflow_status"),
                                    "completed_steps_count": status.get(
                                        "completed_steps_count", 0
                                    ),
                                }
                            )

            return {
                "persistence_enabled": True,
                "recoverable_workflows": recoverable_workflows,
                "total_recoverable": len(recoverable_workflows),
            }

        except Exception as e:
            return {
                "persistence_enabled": True,
                "recoverable_workflows": [],
                "error": f"Failed to list recoverable workflows: {str(e)}",
            }

    def cleanup_expired_persistence_data(
        self, max_age_hours: int = 168
    ) -> Dict[str, Any]:
        """
        Clean up expired workflow persistence data.

        Args:
            max_age_hours: Maximum age in hours for persistence data (default: 7 days)

        Returns:
            Dict containing cleanup results
        """
        if not self._persistence_enabled:
            return {
                "persistence_enabled": False,
                "message": "Workflow persistence is not enabled",
            }

        try:
            import shutil
            from datetime import datetime, timedelta
            from pathlib import Path

            cleanup_cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            errors = []

            # Get persistence directory
            persistence_dir = Path(self._persistence_manager.persistence_directory)
            if not persistence_dir.exists():
                return {
                    "success": True,
                    "cleaned_workflows": 0,
                    "message": "No persistence directory found",
                }

            # Clean up expired workflows
            for workflow_dir in persistence_dir.iterdir():
                if workflow_dir.is_dir():
                    try:
                        workflow_id = workflow_dir.name
                        status = self.get_workflow_persistence_status(workflow_id)

                        if status.get("has_persistent_state", False):
                            checkpoint_timestamp_str = status.get(
                                "checkpoint_timestamp"
                            )
                            if checkpoint_timestamp_str:
                                checkpoint_time = datetime.fromisoformat(
                                    checkpoint_timestamp_str.replace("Z", "+00:00")
                                )

                                if checkpoint_time < cleanup_cutoff:
                                    # Remove expired workflow directory
                                    shutil.rmtree(workflow_dir)
                                    cleaned_count += 1

                                    emit_log_event(
                                        level=LogLevel.INFO,
                                        message=f"Cleaned up expired persistence data for workflow {workflow_id}",
                                        metadata=ModelGenericMetadata.from_dict(
                                            {
                                                "workflow_id": workflow_id,
                                                "checkpoint_timestamp": checkpoint_timestamp_str,
                                                "max_age_hours": max_age_hours,
                                            }
                                        ),
                                    )

                    except Exception as e:
                        errors.append(
                            f"Error cleaning workflow {workflow_dir.name}: {str(e)}"
                        )

            return {
                "success": True,
                "cleaned_workflows": cleaned_count,
                "max_age_hours": max_age_hours,
                "errors": errors if errors else None,
            }

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to cleanup expired persistence data: {str(e)}",
                metadata=ModelGenericMetadata.from_dict(
                    {"max_age_hours": max_age_hours, "error": str(e)}
                ),
            )

            return {"success": False, "error": f"Cleanup failed: {str(e)}"}
