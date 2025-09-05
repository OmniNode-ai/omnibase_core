"""
ReducerSubreducerRegistry - Manual subreducer registration and management.

Provides centralized registration system for subreducers with validation,
health checks, and runtime lookup capabilities.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Type
from uuid import UUID

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    BaseSubreducer,
    WorkflowType,
)


class RegistryError(OnexError):
    """Registry-specific errors."""

    pass


class DefaultSubreducer(BaseSubreducer):
    """Default fallback subreducer for unregistered workflow types."""

    def __init__(self, name: str = "default_subreducer"):
        super().__init__(name)

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """Default subreducer supports all workflow types as fallback."""
        return True

    async def process(self, request):
        """Default processing that returns empty success result."""
        from ..models import ModelSubreducerResult as SubreducerResult

        return SubreducerResult(
            workflow_id=getattr(request, "workflow_id", "unknown"),
            subreducer_name=self.name,
            success=True,
            result={
                "message": "Default processing completed",
                "workflow_type": (
                    str(request.workflow_type)
                    if hasattr(request, "workflow_type")
                    else "unknown"
                ),
            },
            processing_time_ms=0.0,
        )


class ReducerSubreducerRegistry:
    """Manual subreducer registration and management system."""

    def __init__(self):
        """Initialize empty registry."""
        self._subreducers: Dict[str, Type[BaseSubreducer]] = {}
        self._subreducer_instances: Dict[str, BaseSubreducer] = {}
        self._registration_metadata: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)
        self._lock = threading.RLock()  # Thread-safe registry operations

    def register_subreducer(
        self,
        workflow_type: WorkflowType,
        subreducer_class: Type[BaseSubreducer],
        metadata: Dict[str, Any] = None,
    ) -> None:
        """
        Register a subreducer for a specific workflow type.

        Args:
            workflow_type: The workflow type this subreducer handles
            subreducer_class: The subreducer class to register
            metadata: Optional metadata about the subreducer

        Raises:
            RegistryError: If registration fails or subreducer is invalid
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )

        # Thread-safe registration with validation
        with self._lock:
            # Validate subreducer class
            if not issubclass(subreducer_class, BaseSubreducer):
                raise RegistryError(
                    f"Subreducer class must inherit from BaseSubreducer",
                    CoreErrorCode.VALIDATION_FAILED,
                )

            # Check for existing registration
            if workflow_type_str in self._subreducers:
                emit_log_event(
                    logger=self._logger,
                    level="WARNING",
                    message=f"Overwriting existing subreducer registration for {workflow_type_str}",
                )

            # Test instantiation
            try:
                test_instance = subreducer_class(f"test_{workflow_type_str}_subreducer")
                if not test_instance.supports_workflow_type(workflow_type):
                    raise RegistryError(
                        f"Subreducer {subreducer_class.__name__} does not support workflow type {workflow_type_str}",
                        CoreErrorCode.VALIDATION_FAILED,
                    )
            except (TypeError, ValueError, AttributeError, NotImplementedError) as e:
                raise RegistryError(
                    f"Failed to instantiate subreducer {subreducer_class.__name__}: {str(e)}",
                    CoreErrorCode.VALIDATION_FAILED,
                ) from e

            # Register the subreducer
            self._subreducers[workflow_type_str] = subreducer_class
            self._registration_metadata[workflow_type_str] = {
                "class_name": subreducer_class.__name__,
                "registered_at": time.time(),
                "metadata": metadata or {},
            }

            # Clear any existing instance to force recreation with new class
            if workflow_type_str in self._subreducer_instances:
                del self._subreducer_instances[workflow_type_str]

        emit_log_event(
            logger=self._logger,
            level="INFO",
            message=f"Registered subreducer {subreducer_class.__name__} for workflow type {workflow_type_str}",
        )

    def get_subreducer(self, workflow_type: WorkflowType) -> Type[BaseSubreducer]:
        """
        Get the registered subreducer class for a workflow type.

        Args:
            workflow_type: The workflow type to look up

        Returns:
            The subreducer class if registered, DefaultSubreducer otherwise
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )
        return self._subreducers.get(workflow_type_str, DefaultSubreducer)

    def get_subreducer_instance(self, workflow_type: WorkflowType) -> BaseSubreducer:
        """
        Get or create a subreducer instance for a workflow type.

        Args:
            workflow_type: The workflow type to get instance for

        Returns:
            Subreducer instance (registered or default fallback)
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )

        # Thread-safe instance creation with double-checked locking
        with self._lock:
            # Double-check if instance was created by another thread
            if workflow_type_str in self._subreducer_instances:
                return self._subreducer_instances[workflow_type_str]

            # Get subreducer class and create instance
            subreducer_class = self.get_subreducer(workflow_type)

            try:
                instance = subreducer_class(f"{workflow_type_str}_subreducer")
                self._subreducer_instances[workflow_type_str] = instance
                return instance
            except (TypeError, ValueError, AttributeError, NotImplementedError) as e:
                emit_log_event(
                    logger=self._logger,
                    level="ERROR",
                    message=f"Failed to create subreducer instance for {workflow_type_str}: {str(e)}",
                )
                # Return default fallback instance
                default_instance = DefaultSubreducer(
                    f"default_{workflow_type_str}_subreducer"
                )
                self._subreducer_instances[workflow_type_str] = default_instance
                return default_instance

    def unregister_subreducer(self, workflow_type: WorkflowType) -> bool:
        """
        Unregister a subreducer for a workflow type.

        Args:
            workflow_type: The workflow type to unregister

        Returns:
            True if unregistered, False if not found
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )

        removed = False
        if workflow_type_str in self._subreducers:
            del self._subreducers[workflow_type_str]
            removed = True

        if workflow_type_str in self._subreducer_instances:
            del self._subreducer_instances[workflow_type_str]

        if workflow_type_str in self._registration_metadata:
            del self._registration_metadata[workflow_type_str]

        if removed:
            emit_log_event(
                logger=self._logger,
                level="INFO",
                message=f"Unregistered subreducer for workflow type {workflow_type_str}",
            )

        return removed

    def validate_registration(self, workflow_type: WorkflowType) -> bool:
        """
        Validate that a subreducer registration is valid.

        Args:
            workflow_type: The workflow type to validate

        Returns:
            True if registration is valid, False otherwise
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )

        subreducer_class = self.get_subreducer(workflow_type)
        if subreducer_class is None:
            return False

        # Try to create instance and verify it supports the workflow type
        try:
            instance = subreducer_class(f"validation_{workflow_type_str}_subreducer")
            return instance.supports_workflow_type(workflow_type)
        except (TypeError, ValueError, AttributeError, NotImplementedError) as e:
            emit_log_event(
                logger=self._logger,
                level="WARNING",
                message=f"Validation failed for subreducer {subreducer_class.__name__}: {str(e)}",
            )
            return False

    def list_registered_workflows(self) -> List[str]:
        """
        Get a list of all registered workflow types.

        Returns:
            List of registered workflow type strings
        """
        return list(self._subreducers.keys())

    def health_check_subreducers(self) -> Dict[str, bool]:
        """
        Perform health checks on all registered subreducers.

        Returns:
            Dictionary mapping workflow types to health status
        """
        health_status = {}

        for workflow_type_str in self._subreducers:
            try:
                # Try to get/create instance
                workflow_type = WorkflowType(workflow_type_str)
                instance = self.get_subreducer_instance(workflow_type)

                if instance is None:
                    health_status[workflow_type_str] = False
                else:
                    # Check if instance supports its workflow type
                    health_status[workflow_type_str] = instance.supports_workflow_type(
                        workflow_type
                    )
            except (AttributeError, TypeError, NotImplementedError) as e:
                emit_log_event(
                    logger=self._logger,
                    level="WARNING",
                    message=f"Health check failed for {workflow_type_str}: {str(e)}",
                )
                health_status[workflow_type_str] = False

        return health_status

    def get_registration_metadata(self, workflow_type: WorkflowType) -> Dict[str, Any]:
        """
        Get registration metadata for a workflow type.

        Args:
            workflow_type: The workflow type to get metadata for

        Returns:
            Registration metadata (empty dict if not found)
        """
        workflow_type_str = (
            workflow_type.value
            if isinstance(workflow_type, WorkflowType)
            else str(workflow_type)
        )
        return self._registration_metadata.get(
            workflow_type_str,
            {
                "class_name": "DefaultSubreducer",
                "registered_at": 0.0,
                "metadata": {},
                "is_default": True,
            },
        )

    def get_registry_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current registry state.

        Returns:
            Dictionary with registry statistics and information
        """
        return {
            "total_registered": len(self._subreducers),
            "workflow_types": list(self._subreducers.keys()),
            "active_instances": len(self._subreducer_instances),
            "health_status": self.health_check_subreducers(),
            "registration_metadata": self._registration_metadata.copy(),
        }

    def clear_registry(self) -> None:
        """Clear all registrations. Used primarily for testing."""
        self._subreducers.clear()
        self._subreducer_instances.clear()
        self._registration_metadata.clear()

        emit_log_event(logger=self._logger, level="INFO", message="Registry cleared")
