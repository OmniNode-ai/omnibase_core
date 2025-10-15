"""
ONEX Service Wrappers - Pre-Composed Production-Ready Node Classes

This package provides standard service wrapper compositions that eliminate
boilerplate by pre-wiring commonly used mixins with ONEX node base classes.

Standard Service Wrappers:
    - NodeEffectService: Effect + HealthCheck + EventBus + Metrics
    - NodeComputeService: Compute + HealthCheck + Caching + Metrics
    - NodeOrchestratorService: Orchestrator + HealthCheck + EventBus + Metrics
    - NodeReducerService: Reducer + HealthCheck + Caching + Metrics

Usage:
    ```python
    from omnibase_core.nodes.services import NodeEffectService

    class MyDatabaseWriter(NodeEffectService):
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

See: src/omnibase_core/mixins/mixin_metadata.yaml for detailed mixin capabilities
"""

from omnibase_core.nodes.services.node_compute_service import NodeComputeService
from omnibase_core.nodes.services.node_effect_service import NodeEffectService
from omnibase_core.nodes.services.node_orchestrator_service import (
    NodeOrchestratorService,
)
from omnibase_core.nodes.services.node_reducer_service import NodeReducerService

__all__ = [
    "NodeEffectService",
    "NodeComputeService",
    "NodeOrchestratorService",
    "NodeReducerService",
]
