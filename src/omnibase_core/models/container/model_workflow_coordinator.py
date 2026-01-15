"""
ModelWorkflowCoordinator

Workflow execution coordinator for dependency injection container.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

if TYPE_CHECKING:
    from .model_workflow_factory import ModelWorkflowFactory


class ModelWorkflowCoordinator:
    """Workflow execution coordinator."""

    def __init__(self, factory: ModelWorkflowFactory) -> None:
        self.factory = factory
        self.active_workflows: SerializedDict = {}

    async def execute_workflow(
        self,
        workflow_id: str,  # string-id-ok: external workflow identifier from caller
        workflow_type: str,
        input_data: object,
        config: SerializedDict | None = None,
    ) -> object:
        """Execute workflow with logging and error handling."""
        # Import at function level to avoid circular imports and eliminate duplication
        from omnibase_core.logging.logging_structured import (
            emit_log_event_sync as emit_log_event,
        )

        try:
            self.factory.create_workflow(workflow_type, config)

            # Log workflow start
            emit_log_event(
                LogLevel.INFO,
                f"Workflow execution started: {workflow_type}",
                {
                    "workflow_id": str(workflow_id),
                    "workflow_type": workflow_type,
                },
            )

            # Execute workflow using the configured type and input data
            workflow_result = await self._execute_workflow_type(
                workflow_type,
                input_data,
                config,
            )

            # Log workflow success
            emit_log_event(
                LogLevel.INFO,
                f"Workflow execution completed: {workflow_type}",
                {
                    "workflow_id": str(workflow_id),
                    "workflow_type": workflow_type,
                },
            )

            return workflow_result

        except PYDANTIC_MODEL_ERRORS as e:  # boundary-ok: normalize model/validation failures into ModelOnexError at workflow boundary
            # Log workflow failure
            emit_log_event(
                LogLevel.ERROR,
                f"Workflow execution failed: {workflow_type}",
                {
                    "workflow_id": str(workflow_id),
                    "workflow_type": workflow_type,
                    "error": str(e),
                },
            )
            raise ModelOnexError(
                message=f"Workflow execution failed: {e!s}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={
                    "workflow_id": str(workflow_id),
                    "workflow_type": workflow_type,
                },
            ) from e

    async def _execute_workflow_type(
        self,
        workflow_type: str,
        input_data: object,
        config: SerializedDict | None,
    ) -> object:
        """Execute a specific workflow type with input data."""
        # Import at function level to avoid circular imports
        from omnibase_core.logging.logging_structured import (
            emit_log_event_sync as emit_log_event,
        )

        try:
            # Create and run workflow based on type
            workflow = self.factory.create_workflow(workflow_type, config)

            # Execute workflow with input data
            if hasattr(workflow, "run"):
                result = await workflow.run(input_data)
            elif callable(workflow):
                result = await workflow(input_data)
            else:
                # Fallback: return input data as placeholder
                result = input_data

            return result

        except PYDANTIC_MODEL_ERRORS as e:  # boundary-ok: log and propagate model/validation failures at workflow execution boundary
            emit_log_event(
                LogLevel.ERROR,
                f"Workflow execution failed for type {workflow_type}: {e}",
                {
                    "workflow_type": workflow_type,
                    "error": str(e),
                },
            )
            raise

    def get_active_workflows(self) -> list[str]:
        """Get list of active workflow IDs."""
        return list(self.active_workflows.keys())
