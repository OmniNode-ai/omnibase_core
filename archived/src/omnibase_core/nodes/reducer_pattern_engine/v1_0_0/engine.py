#!/usr/bin/env python3
"""
ReducerPatternEngine - Phase 1 Implementation.

ONEX-compliant reducer pattern engine extending NodeReducer architecture
with comprehensive subcontract integration and LlamaIndex workflow support.

Key Features:
- Extends NodeReducerService for full ONEX compliance
- ModelContractReducer contract validation
- Comprehensive subcontract composition
- LlamaIndex workflow integration via WorkflowCoordinationSubcontract
- Pass-through integration with existing infrastructure
"""

import time
from typing import Any, Dict
from uuid import uuid4

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.node_reducer_service import NodeReducerService
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event

from .router import WorkflowRouter


class ReducerPatternEngine(NodeReducerService):
    """
    Phase 1 Reducer Pattern Engine - ONEX compliant with LlamaIndex support.

    Provides workflow routing and processing with contract compliance,
    extending the established NodeReducer architecture patterns.

    Architecture Compliance:
    - Extends NodeReducerService (includes NodeReducer, MixinNodeService, etc.)
    - Uses ModelContractReducer contract validation
    - Integrates with ModelONEXContainer dependency injection
    - Supports WorkflowCoordinationSubcontract for LlamaIndex workflows

    Phase 1 Scope:
    - Single workflow type support (document_regeneration)
    - Basic routing through WorkflowRouter
    - Foundation for future expansion
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize reducer pattern engine with ONEX compliance.

        Args:
            container: ONEX container for dependency injection

        Raises:
            OnexError: If initialization fails
        """
        # Initialize NodeReducerService (handles all ONEX boilerplate)
        super().__init__(container)

        # Initialize Phase 1 components
        self.workflow_router = WorkflowRouter(container)

        # Engine-specific state
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.processing_metrics: Dict[str, float] = {}

        # Load Phase 1 configuration
        self._load_phase1_config()

        emit_log_event(
            LogLevel.INFO,
            "ReducerPatternEngine initialized successfully",
            {
                "node_id": self.node_id,
                "version": "1.0.0",
                "phase": "Phase 1 - Core Implementation",
                "workflow_router_ready": True,
            },
        )

    async def reduce(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main reduction entry point for workflow processing.

        Follows NodeReducer.reduce signature while adding workflow coordination.

        Args:
            input_data: Workflow input data containing:
                - workflow_type: Type of workflow to process
                - instance_id: Unique workflow instance identifier
                - data: Workflow payload data

        Returns:
            Dict[str, Any]: Processed workflow results containing:
                - success: Whether processing succeeded
                - result_data: Workflow results
                - workflow_type: Processed workflow type
                - instance_id: Workflow instance ID
                - execution_time_ms: Processing time
                - correlation_id: Tracking correlation ID

        Raises:
            OnexError: If workflow processing fails
        """
        start_time = time.time()
        correlation_id = str(uuid4())

        # Extract workflow parameters
        workflow_type = input_data.get("workflow_type")
        instance_id = input_data.get("instance_id")
        workflow_data = input_data.get("data", {})

        try:
            # Validate input
            self._validate_workflow_input(input_data)

            emit_log_event(
                LogLevel.INFO,
                "Starting workflow processing",
                {
                    "node_id": self.node_id,
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "correlation_id": correlation_id,
                },
            )

            # Track active workflow
            self.active_workflows[instance_id] = {
                "workflow_type": workflow_type,
                "start_time": start_time,
                "correlation_id": correlation_id,
                "status": "processing",
            }

            # Route workflow to appropriate subreducer
            subreducer = self.workflow_router.route_workflow(
                workflow_type, instance_id, workflow_data
            )

            # Process workflow through subreducer
            workflow_context = {
                "workflow_type": workflow_type,
                "instance_id": instance_id,
                "data": workflow_data,
                "correlation_id": correlation_id,
                "start_time": start_time,
            }

            result = await subreducer.process_workflow(workflow_context)

            execution_time = (time.time() - start_time) * 1000

            # Update metrics
            await self._update_processing_metrics(
                workflow_type, execution_time, success=result.get("success", True)
            )

            # Clean up active workflow tracking
            if instance_id in self.active_workflows:
                self.active_workflows[instance_id]["status"] = "completed"
                del self.active_workflows[instance_id]

            # Prepare output
            output = {
                "success": result.get("success", True),
                "result_data": result.get("result_data", {}),
                "workflow_type": workflow_type,
                "instance_id": instance_id,
                "execution_time_ms": int(execution_time),
                "correlation_id": correlation_id,
                "processing_timestamp": time.time(),
            }

            if not result.get("success", True):
                output["error_message"] = result.get("error_message", "Unknown error")

            emit_log_event(
                LogLevel.INFO,
                "Workflow processing completed",
                {
                    "node_id": self.node_id,
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "correlation_id": correlation_id,
                    "execution_time_ms": int(execution_time),
                    "success": result.get("success", True),
                },
            )

            return output

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # Update error metrics
            await self._update_processing_metrics(
                workflow_type or "unknown", execution_time, success=False
            )

            # Clean up active workflow tracking
            if instance_id and instance_id in self.active_workflows:
                self.active_workflows[instance_id]["status"] = "failed"
                del self.active_workflows[instance_id]

            emit_log_event(
                LogLevel.ERROR,
                "Workflow processing failed",
                {
                    "node_id": self.node_id,
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "correlation_id": correlation_id,
                    "execution_time_ms": int(execution_time),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            return {
                "success": False,
                "error_message": str(e),
                "workflow_type": workflow_type,
                "instance_id": instance_id,
                "execution_time_ms": int(execution_time),
                "correlation_id": correlation_id,
                "processing_timestamp": time.time(),
            }

    def _validate_workflow_input(self, input_data: Dict[str, Any]) -> None:
        """
        Validate workflow input data.

        Args:
            input_data: Input data to validate

        Raises:
            OnexError: If validation fails
        """
        required_fields = ["workflow_type", "instance_id"]

        for field in required_fields:
            if field not in input_data:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Required field '{field}' missing from input",
                    context={
                        "node_id": self.node_id,
                        "missing_field": field,
                        "provided_fields": list(input_data.keys()),
                    },
                )

        # Validate workflow_type
        workflow_type = input_data["workflow_type"]
        if not isinstance(workflow_type, str) or not workflow_type.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="workflow_type must be non-empty string",
                context={
                    "node_id": self.node_id,
                    "workflow_type": workflow_type,
                    "workflow_type_type": type(workflow_type).__name__,
                },
            )

        # Validate instance_id
        instance_id = input_data["instance_id"]
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="instance_id must be non-empty string",
                context={
                    "node_id": self.node_id,
                    "instance_id": instance_id,
                    "instance_id_type": type(instance_id).__name__,
                },
            )

    async def _update_processing_metrics(
        self, workflow_type: str, execution_time_ms: float, success: bool
    ) -> None:
        """
        Update processing metrics for workflow types.

        Args:
            workflow_type: Type of workflow processed
            execution_time_ms: Processing time in milliseconds
            success: Whether processing succeeded
        """
        metric_key = f"{workflow_type}_processing"

        if metric_key not in self.processing_metrics:
            self.processing_metrics[metric_key] = {
                "total_count": 0,
                "success_count": 0,
                "error_count": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "min_time_ms": float("inf"),
                "max_time_ms": 0.0,
            }

        metrics = self.processing_metrics[metric_key]
        metrics["total_count"] += 1
        metrics["total_time_ms"] += execution_time_ms

        if success:
            metrics["success_count"] += 1
        else:
            metrics["error_count"] += 1

        # Update timing metrics
        metrics["avg_time_ms"] = metrics["total_time_ms"] / metrics["total_count"]
        metrics["min_time_ms"] = min(metrics["min_time_ms"], execution_time_ms)
        metrics["max_time_ms"] = max(metrics["max_time_ms"], execution_time_ms)

    def _load_phase1_config(self) -> None:
        """
        Load Phase 1 minimal configuration.

        Phase 1 uses minimal configuration. Later phases will add
        comprehensive configuration loading and validation.
        """
        emit_log_event(
            LogLevel.DEBUG,
            "Phase 1 configuration loaded",
            {
                "node_id": self.node_id,
                "config_level": "minimal",
                "supported_workflows": ["document_regeneration"],
            },
        )

    async def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """
        Get currently active workflows.

        Returns:
            Dict[str, Dict[str, Any]]: Active workflow instances
        """
        return dict(self.active_workflows)

    async def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing metrics.

        Returns:
            Dict[str, Any]: Processing metrics and statistics
        """
        return {
            "workflow_metrics": dict(self.processing_metrics),
            "active_workflows_count": len(self.active_workflows),
            "node_info": {
                "node_id": self.node_id,
                "node_type": "REDUCER",
                "engine_version": "1.0.0",
                "phase": "Phase 1 - Core Implementation",
            },
        }
