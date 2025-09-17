#!/usr/bin/env python3
"""
WorkflowRouter - Phase 1 Implementation.

ONEX-compliant workflow router with LlamaIndex integration and
hash-based routing for consistent workflow distribution.

Key Features:
- Hash-based routing mechanism for deterministic workflow distribution
- Integration with WorkflowCoordinationSubcontract
- Support for LlamaIndex workflow patterns (StartEvent, StopEvent, step decorators)
- Correlation ID tracking for comprehensive observability
- Error handling and fallback patterns
"""

import hashlib
from typing import Any, Dict
from uuid import uuid4

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel


class WorkflowRouter:
    """
    Phase 1 workflow router with LlamaIndex integration.

    Routes workflows to appropriate subreducers with coordination support
    and deterministic hash-based routing for consistent distribution.

    Phase 1 Scope:
    - Single workflow type support (document_regeneration)
    - Hash-based routing for consistency
    - Foundation for LlamaIndex workflow patterns
    - Comprehensive error handling and observability
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize workflow router with ONEX container integration.

        Args:
            container: ONEX container for dependency injection

        Raises:
            OnexError: If initialization fails
        """
        self.container = container
        self.correlation_id = str(uuid4())

        # Subreducer registry for Phase 1
        self._subreducer_registry: Dict[str, Any] = {}

        # Routing metrics
        self._routing_metrics: Dict[str, Dict[str, float]] = {}

        # WorkflowCoordination subcontract integration
        # Phase 1: Placeholder for future LlamaIndex integration
        self._workflow_coordination = self._initialize_workflow_coordination()

        emit_log_event(
            LogLevel.INFO,
            "WorkflowRouter initialized",
            {
                "correlation_id": self.correlation_id,
                "workflow_coordination_ready": self._workflow_coordination is not None,
                "phase": "Phase 1 - Core Implementation",
            },
        )

    def route_workflow(
        self, workflow_type: str, instance_id: str, workflow_data: Dict[str, Any]
    ) -> "ReducerDocumentRegenerationSubreducer":
        """
        Route workflow to appropriate subreducer with coordination.

        Uses hash-based routing for deterministic distribution and supports
        WorkflowCoordinationSubcontract patterns for LlamaIndex integration.

        Args:
            workflow_type: Type of workflow to route
            instance_id: Unique workflow instance identifier
            workflow_data: Workflow payload data

        Returns:
            ReducerDocumentRegenerationSubreducer: Appropriate subreducer for processing

        Raises:
            OnexError: If routing fails or workflow type unsupported
        """
        route_correlation_id = str(uuid4())

        try:
            emit_log_event(
                LogLevel.DEBUG,
                "Starting workflow routing",
                {
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "route_correlation_id": route_correlation_id,
                    "router_correlation_id": self.correlation_id,
                },
            )

            # Validate inputs
            self._validate_routing_inputs(workflow_type, instance_id, workflow_data)

            # Calculate routing key for deterministic distribution
            route_key = self._calculate_route_key(workflow_type, instance_id)

            emit_log_event(
                LogLevel.DEBUG,
                "Calculated routing key",
                {
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "route_key": route_key,
                    "route_correlation_id": route_correlation_id,
                },
            )

            # Phase 1: Simple routing to document regeneration subreducer only
            if workflow_type != "document_regeneration":
                raise OnexError(
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    message=f"Phase 1 only supports 'document_regeneration' workflow type, got '{workflow_type}'",
                    context={
                        "workflow_type": workflow_type,
                        "supported_types": ["document_regeneration"],
                        "phase": "Phase 1 - Core Implementation",
                        "route_correlation_id": route_correlation_id,
                    },
                )

            # Get or create subreducer for document regeneration
            subreducer = self._get_document_regeneration_subreducer()

            # Update routing metrics
            self._update_routing_metrics(workflow_type, route_key, success=True)

            emit_log_event(
                LogLevel.INFO,
                "Workflow routed successfully",
                {
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "route_key": route_key,
                    "subreducer_type": "ReducerDocumentRegenerationSubreducer",
                    "route_correlation_id": route_correlation_id,
                },
            )

            return subreducer

        except OnexError:
            # Re-raise ONEX errors as-is
            self._update_routing_metrics(workflow_type, "error", success=False)
            raise
        except Exception as e:
            # Wrap other exceptions
            self._update_routing_metrics(workflow_type, "error", success=False)

            emit_log_event(
                LogLevel.ERROR,
                "Workflow routing failed",
                {
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "route_correlation_id": route_correlation_id,
                },
            )

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Workflow routing failed: {str(e)}",
                context={
                    "workflow_type": workflow_type,
                    "instance_id": instance_id,
                    "route_correlation_id": route_correlation_id,
                    "original_error": str(e),
                },
            ) from e

    def _calculate_route_key(self, workflow_type: str, instance_id: str) -> str:
        """
        Calculate consistent routing key for workflow instance.

        Uses SHA-256 hash for deterministic routing that remains consistent
        across router restarts and scaling.

        Args:
            workflow_type: Type of workflow
            instance_id: Workflow instance identifier

        Returns:
            str: 16-character routing key for consistent distribution
        """
        combined_key = f"{workflow_type}:{instance_id}"
        hash_object = hashlib.sha256(combined_key.encode())
        return hash_object.hexdigest()[:16]

    def _get_document_regeneration_subreducer(
        self,
    ) -> "ReducerDocumentRegenerationSubreducer":
        """
        Get or create document regeneration subreducer.

        Phase 1 implementation creates a single subreducer instance.
        Future phases will support multiple subreducers and load balancing.

        Returns:
            ReducerDocumentRegenerationSubreducer: Subreducer for document workflows

        Raises:
            OnexError: If subreducer creation fails
        """
        registry_key = "document_regeneration"

        if registry_key not in self._subreducer_registry:
            try:
                # Import locally to avoid circular imports
                from ..subreducers.reducer_document_regeneration import (
                    ReducerDocumentRegenerationSubreducer,
                )

                self._subreducer_registry[registry_key] = (
                    ReducerDocumentRegenerationSubreducer(self.container)
                )

                emit_log_event(
                    LogLevel.INFO,
                    "Document regeneration subreducer created",
                    {
                        "registry_key": registry_key,
                        "subreducer_type": "ReducerDocumentRegenerationSubreducer",
                        "router_correlation_id": self.correlation_id,
                    },
                )

            except Exception as e:
                raise OnexError(
                    error_code=CoreErrorCode.INITIALIZATION_ERROR,
                    message=f"Failed to create document regeneration subreducer: {str(e)}",
                    context={
                        "registry_key": registry_key,
                        "router_correlation_id": self.correlation_id,
                        "error": str(e),
                    },
                ) from e

        return self._subreducer_registry[registry_key]

    def _validate_routing_inputs(
        self, workflow_type: str, instance_id: str, workflow_data: Dict[str, Any]
    ) -> None:
        """
        Validate workflow routing inputs.

        Args:
            workflow_type: Type of workflow to validate
            instance_id: Instance ID to validate
            workflow_data: Workflow data to validate

        Raises:
            OnexError: If validation fails
        """
        if not isinstance(workflow_type, str) or not workflow_type.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="workflow_type must be non-empty string",
                context={
                    "workflow_type": workflow_type,
                    "workflow_type_type": type(workflow_type).__name__,
                    "router_correlation_id": self.correlation_id,
                },
            )

        if not isinstance(instance_id, str) or not instance_id.strip():
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="instance_id must be non-empty string",
                context={
                    "instance_id": instance_id,
                    "instance_id_type": type(instance_id).__name__,
                    "router_correlation_id": self.correlation_id,
                },
            )

        if not isinstance(workflow_data, dict):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="workflow_data must be dictionary",
                context={
                    "workflow_data_type": type(workflow_data).__name__,
                    "router_correlation_id": self.correlation_id,
                },
            )

    def _initialize_workflow_coordination(self) -> Dict[str, Any] | None:
        """
        Initialize WorkflowCoordination subcontract integration.

        Phase 1: Placeholder for future LlamaIndex workflow integration.
        Sets up foundation for workflow coordination patterns.

        Returns:
            Dict[str, Any] | None: Workflow coordination configuration or None if unavailable
        """
        try:
            # Phase 1: Basic configuration placeholder
            # Future phases will integrate with WorkflowCoordinationSubcontract
            coordination_config = {
                "enabled": True,
                "coordination_type": "basic",
                "supports_llamaindex": False,  # Phase 1 limitation
                "max_concurrent_workflows": 10,
                "workflow_timeout_ms": 600000,
                "phase": "Phase 1 - Foundation Only",
            }

            emit_log_event(
                LogLevel.DEBUG,
                "Workflow coordination initialized",
                {
                    "coordination_type": coordination_config["coordination_type"],
                    "supports_llamaindex": coordination_config["supports_llamaindex"],
                    "router_correlation_id": self.correlation_id,
                },
            )

            return coordination_config

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                "Workflow coordination initialization failed, proceeding without",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "router_correlation_id": self.correlation_id,
                },
            )
            return None

    def _update_routing_metrics(
        self, workflow_type: str, route_key: str, success: bool
    ) -> None:
        """
        Update routing metrics for monitoring and optimization.

        Args:
            workflow_type: Type of workflow routed
            route_key: Calculated route key
            success: Whether routing succeeded
        """
        metric_key = f"{workflow_type}_routing"

        if metric_key not in self._routing_metrics:
            self._routing_metrics[metric_key] = {
                "total_count": 0.0,
                "success_count": 0.0,
                "error_count": 0.0,
                "route_distribution": {},
            }

        metrics = self._routing_metrics[metric_key]
        metrics["total_count"] += 1

        if success:
            metrics["success_count"] += 1
            # Track route distribution for load balancing insights
            if route_key not in metrics["route_distribution"]:
                metrics["route_distribution"][route_key] = 0
            metrics["route_distribution"][route_key] += 1
        else:
            metrics["error_count"] += 1

    def get_routing_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive routing metrics.

        Returns:
            Dict[str, Dict[str, Any]]: Routing metrics and statistics
        """
        return {
            "routing_metrics": dict(self._routing_metrics),
            "subreducers_registered": len(self._subreducer_registry),
            "workflow_coordination_enabled": self._workflow_coordination is not None,
            "router_info": {
                "correlation_id": self.correlation_id,
                "phase": "Phase 1 - Core Implementation",
                "supported_workflow_types": ["document_regeneration"],
            },
        }
