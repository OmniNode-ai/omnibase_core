"""
WorkflowRouter - Hash-based routing for Reducer Pattern Engine v1.0.0.

Provides consistent routing of workflow requests to appropriate subreducers
using hash-based distribution with correlation ID tracking and error handling.
"""

import hashlib
import time
from typing import Any, Dict, List, Optional

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .contracts import (
    BaseSubreducer,
    RoutingDecision,
    WorkflowRequest,
    WorkflowType,
)


class WorkflowRouter:
    """
    Hash-based workflow router for Reducer Pattern Engine.

    Routes workflows to appropriate subreducers using consistent hashing
    based on workflow type and instance ID. Provides observability through
    correlation ID tracking and structured logging.

    Phase 1 Implementation:
    - Single workflow type (document_regeneration) support
    - Hash-based routing for consistent distribution
    - Error handling and fallback mechanisms
    - Performance metrics collection
    """

    def __init__(self):
        """Initialize the WorkflowRouter."""
        self._subreducers: Dict[str, BaseSubreducer] = {}
        self._workflow_type_mappings: Dict[WorkflowType, str] = {}
        self._routing_metrics = {
            "total_routed": 0,
            "routing_errors": 0,
            "average_routing_time_ms": 0.0,
        }

    def register_subreducer(
        self, subreducer: BaseSubreducer, workflow_types: List[WorkflowType]
    ) -> None:
        """
        Register a subreducer for specific workflow types.

        Args:
            subreducer: The subreducer instance to register
            workflow_types: List of workflow types this subreducer handles

        Raises:
            OnexError: If registration fails or workflow type already registered
        """
        try:
            # Validate subreducer
            if not isinstance(subreducer, BaseSubreducer):
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message="Invalid subreducer type",
                    context={"subreducer_type": type(subreducer).__name__},
                )

            # Register subreducer
            self._subreducers[subreducer.name] = subreducer

            # Map workflow types to this subreducer
            for workflow_type in workflow_types:
                if workflow_type in self._workflow_type_mappings:
                    existing_subreducer = self._workflow_type_mappings[workflow_type]
                    raise OnexError(
                        error_code=CoreErrorCode.VALIDATION_ERROR,
                        message=f"Workflow type {workflow_type.value} already registered",
                        context={
                            "workflow_type": workflow_type.value,
                            "existing_subreducer": existing_subreducer,
                            "new_subreducer": subreducer.name,
                        },
                    )

                self._workflow_type_mappings[workflow_type] = subreducer.name

            emit_log_event(
                level=LogLevel.INFO,
                event="subreducer_registered",
                message=f"Registered subreducer {subreducer.name}",
                context={
                    "subreducer_name": subreducer.name,
                    "workflow_types": [wt.value for wt in workflow_types],
                    "total_subreducers": len(self._subreducers),
                },
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                event="subreducer_registration_failed",
                message=f"Failed to register subreducer: {str(e)}",
                context={
                    "subreducer_name": getattr(subreducer, "name", "unknown"),
                    "error": str(e),
                },
            )
            raise

    async def route(self, request: WorkflowRequest) -> RoutingDecision:
        """
        Route a workflow request to the appropriate subreducer.

        Uses hash-based routing for consistent distribution based on
        workflow type and instance ID combination.

        Args:
            request: The workflow request to route

        Returns:
            RoutingDecision: The routing decision with subreducer selection

        Raises:
            OnexError: If routing fails or no suitable subreducer found
        """
        start_time = time.perf_counter()

        try:
            # Validate workflow type is supported
            if request.workflow_type not in self._workflow_type_mappings:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Unsupported workflow type: {request.workflow_type.value}",
                    context={
                        "workflow_type": request.workflow_type.value,
                        "workflow_id": str(request.workflow_id),
                        "supported_types": list(self._workflow_type_mappings.keys()),
                    },
                )

            # Get subreducer name for this workflow type
            subreducer_name = self._workflow_type_mappings[request.workflow_type]

            # Generate routing hash for consistency and observability
            routing_hash = self._generate_routing_hash(
                request.workflow_type.value, request.instance_id
            )

            # Create routing decision
            decision = RoutingDecision(
                workflow_id=request.workflow_id,
                workflow_type=request.workflow_type,
                instance_id=request.instance_id,
                subreducer_name=subreducer_name,
                routing_hash=routing_hash,
                routing_metadata={
                    "correlation_id": str(request.correlation_id),
                    "routing_algorithm": "hash_based",
                    "total_subreducers": len(self._subreducers),
                },
            )

            # Update metrics
            routing_time_ms = (time.perf_counter() - start_time) * 1000
            self._update_routing_metrics(routing_time_ms)

            emit_log_event(
                level=LogLevel.INFO,
                event="workflow_routed",
                message=f"Routed workflow {request.workflow_id} to {subreducer_name}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "subreducer_name": subreducer_name,
                    "routing_hash": routing_hash,
                    "routing_time_ms": routing_time_ms,
                },
            )

            return decision

        except Exception as e:
            self._routing_metrics["routing_errors"] += 1

            emit_log_event(
                level=LogLevel.ERROR,
                event="routing_failed",
                message=f"Failed to route workflow: {str(e)}",
                context={
                    "workflow_id": str(request.workflow_id),
                    "workflow_type": request.workflow_type.value,
                    "instance_id": request.instance_id,
                    "correlation_id": str(request.correlation_id),
                    "error": str(e),
                },
            )
            raise

    def get_subreducer(self, name: str) -> Optional[BaseSubreducer]:
        """
        Get a registered subreducer by name.

        Args:
            name: The subreducer name

        Returns:
            Optional[BaseSubreducer]: The subreducer if found, None otherwise
        """
        return self._subreducers.get(name)

    def get_routing_metrics(self) -> Dict[str, Any]:
        """
        Get current routing performance metrics.

        Returns:
            Dict[str, Any]: Current routing metrics
        """
        return self._routing_metrics.copy()

    def _generate_routing_hash(self, workflow_type: str, instance_id: str) -> str:
        """
        Generate consistent hash for routing decisions.

        Uses SHA-256 for consistent routing based on workflow type
        and instance ID combination.

        Args:
            workflow_type: The workflow type string
            instance_id: The instance identifier

        Returns:
            str: Hex digest of routing hash
        """
        routing_key = f"{workflow_type}:{instance_id}"
        return hashlib.sha256(routing_key.encode()).hexdigest()[:16]

    def _update_routing_metrics(self, routing_time_ms: float) -> None:
        """
        Update routing performance metrics.

        Args:
            routing_time_ms: Time taken for this routing decision
        """
        self._routing_metrics["total_routed"] += 1

        # Calculate running average routing time
        total_routed = self._routing_metrics["total_routed"]
        current_avg = self._routing_metrics["average_routing_time_ms"]

        # Running average formula: new_avg = old_avg + (new_value - old_avg) / count
        self._routing_metrics["average_routing_time_ms"] = (
            current_avg + (routing_time_ms - current_avg) / total_routed
        )
