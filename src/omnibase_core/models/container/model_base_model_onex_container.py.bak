from __future__ import annotations

from pydantic import BaseModel

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Base dependency injection container.
"""


from typing import Any

from dependency_injector import containers, providers

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

from .model_enhanced_logger import ModelEnhancedLogger
from .model_workflow_coordinator import ModelWorkflowCoordinator
from .model_workflow_factory import ModelWorkflowFactory


def _create_enhanced_logger(level: LogLevel) -> ModelEnhancedLogger:
    """Create enhanced logger with monadic patterns."""
    return ModelEnhancedLogger(level)


def _create_workflow_factory() -> ModelWorkflowFactory:
    """Create workflow factory for LlamaIndex integration."""
    return ModelWorkflowFactory()


def _create_workflow_coordinator(factory: Any) -> ModelWorkflowCoordinator:
    """Create workflow execution coordinator."""
    return ModelWorkflowCoordinator(factory)


class _BaseModelONEXContainer(containers.DeclarativeContainer):
    """Base dependency injection container."""

    # === CONFIGURATION ===
    config = providers.Configuration()

    # === ENHANCED CORE SERVICES ===

    # Enhanced logger with monadic patterns
    enhanced_logger = providers.Factory(
        lambda level: _create_enhanced_logger(level),
        level=LogLevel.INFO,
    )

    # === WORKFLOW ORCHESTRATION ===

    # LlamaIndex workflow factory
    workflow_factory = providers.Factory(lambda: _create_workflow_factory())

    # Workflow execution coordinator
    workflow_coordinator = providers.Singleton(
        lambda factory: _create_workflow_coordinator(factory),
        factory=workflow_factory,
    )


__all__ = ["_BaseModelONEXContainer"]
