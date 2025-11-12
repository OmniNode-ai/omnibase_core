"""
ONEX Service Wrappers - Pre-Composed Production-Ready Node Classes

This package provides standard service wrapper compositions that eliminate
boilerplate by pre-wiring commonly used mixins with ONEX node base classes.

Available Now:
    - ModelServiceEffect: Effect + HealthCheck + EventBus + Metrics
    - ModelServiceCompute: Compute + HealthCheck + Caching + Metrics

Available After Phase 3:
    - ModelServiceOrchestrator: Orchestrator + HealthCheck + EventBus + Metrics
    - ModelServiceReducer: Reducer + HealthCheck + Caching + Metrics

Usage:
    ```python
    from omnibase_core.models.nodes.node_services import ModelServiceEffect

    class MyDatabaseWriter(ModelServiceEffect):
        async def execute_effect(self, contract):
            # Just write your business logic!
            # Health checks, events, and metrics are automatic
            result = await self.database.write(contract.input_data)
            await self.publish_event("write_completed", {...})
            return result
    ```

When to Use Standard Services vs Custom Composition:

Use Standard Services When:
    - You need the standard set of capabilities (health, metrics, events/caching)
    - You're building a typical ONEX node (database adapters, API clients, etc.)
    - You want minimal boilerplate and fast development

Use Custom Composition When:
    - You need specialized mixin combinations (e.g., Retry + CircuitBreaker)
    - You're building a unique node with specific requirements
    - You need fine-grained control over mixin initialization order

Example Custom Composition:
    ```python
    from omnibase_core.nodes.node_effect import NodeEffect
    from omnibase_core.mixins.mixin_retry import MixinRetry
    from omnibase_core.mixins.mixin_circuit_breaker import MixinCircuitBreaker

    class ResilientApiClient(NodeEffect, MixinRetry, MixinCircuitBreaker):
        # Custom composition for fault-tolerant API client
        pass
    ```

Available Mixins for Custom Composition:
    - MixinRetry: Automatic retry with exponential backoff
    - MixinHealthCheck: Health monitoring and status reporting
    - MixinCaching: Multi-level caching with invalidation strategies
    - MixinEventBus: Event-driven communication
    - MixinCircuitBreaker: Circuit breaker fault tolerance
    - MixinLogging: Structured logging
    - MixinMetrics: Performance metrics collection
    - MixinSecurity: Security and redaction
    - MixinValidation: Input validation
    - MixinSerialization: YAML/JSON serialization

See: src/omnibase_core/data/config/mixin_metadata.yaml for detailed mixin capabilities
"""

from omnibase_core.models.nodes.node_services.model_service_compute import (
    ModelServiceCompute,
)
from omnibase_core.models.nodes.node_services.model_service_effect import (
    ModelServiceEffect,
)

# NOTE: Available after Phase 3 restoration:
# from omnibase_core.models.nodes.node_services.model_service_orchestrator import ModelServiceOrchestrator
# from omnibase_core.models.nodes.node_services.model_service_reducer import ModelServiceReducer

__all__ = [
    "ModelServiceEffect",
    "ModelServiceCompute",
]
