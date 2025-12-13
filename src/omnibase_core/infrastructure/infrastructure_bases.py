"""
Infrastructure Base Classes

Consolidated imports for all infrastructure node base classes and service wrappers.
Eliminates boilerplate initialization across the infrastructure tool group.

Service Wrappers (Standard Production-Ready Compositions):
    Service wrappers provide pre-configured mixin compositions for production use:
    - ModelServiceEffect: Effect + HealthCheck + EventBus + Metrics
    - ModelServiceCompute: Compute + HealthCheck + Caching + Metrics

Usage Examples:
    from omnibase_core.infrastructure.infrastructure_bases import (
        ModelServiceEffect,
        ModelServiceCompute,
    )

    class MyDatabaseWriter(ModelServiceEffect):
        async def execute_effect(self, contract):
            # Health checks, events, and metrics included automatically!
            result = await self.database.write(contract.input_data)
            await self.publish_event("write_completed", {...})
            return result

Note: ModelServiceOrchestrator and ModelServiceReducer will be available after
      NodeOrchestrator and NodeReducer are restored in Phase 3.
"""

# Standard service wrappers - production-ready mixin compositions
from omnibase_core.models.services.model_service_compute import ModelServiceCompute
from omnibase_core.models.services.model_service_effect import ModelServiceEffect

# NOTE: Available after Phase 3 restoration:
# from omnibase_core.models.services.model_service_orchestrator import ModelServiceOrchestrator
# from omnibase_core.models.services.model_service_reducer import ModelServiceReducer

__all__ = [
    "ModelServiceEffect",
    "ModelServiceCompute",
]
