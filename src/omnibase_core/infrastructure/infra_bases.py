"""
Infrastructure Base Classes

Consolidated imports for all infrastructure node base classes and service wrappers.
Eliminates boilerplate initialization across the infrastructure tool group.

Service Wrappers (Standard Production-Ready Compositions):
    Service wrappers provide pre-configured mixin compositions for production use:
    - ModelServiceEffect: Effect + HealthCheck + EventBus + Metrics
    - ModelServiceCompute: Compute + HealthCheck + Caching + Metrics
    - ModelServiceOrchestrator: Orchestrator + HealthCheck + EventBus + Metrics
    - ModelServiceReducer: Reducer + HealthCheck + Caching + Metrics

Usage Examples:
    from omnibase_core.infrastructure.infra_bases import (
        ModelServiceEffect,
        ModelServiceCompute,
        ModelServiceOrchestrator,
        ModelServiceReducer,
    )

    class MyDatabaseWriter(ModelServiceEffect):
        async def execute_effect(self, contract):
            # Health checks, events, and metrics included automatically!
            result = await self.database.write(contract.input_data)
            await self.publish_event("write_completed", {...})
            return result
"""

# Standard service wrappers - production-ready mixin compositions
from omnibase_core.models.services.model_service_compute import ModelServiceCompute
from omnibase_core.models.services.model_service_effect import ModelServiceEffect
from omnibase_core.models.services.model_service_orchestrator import (
    ModelServiceOrchestrator,
)
from omnibase_core.models.services.model_service_reducer import ModelServiceReducer

__all__ = [
    "ModelServiceCompute",
    "ModelServiceEffect",
    "ModelServiceOrchestrator",
    "ModelServiceReducer",
]
