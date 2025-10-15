"""
ModelServiceEffect - Standard Production-Ready Effect Node

Pre-composed with essential mixins for production use:
- Effect semantics (transaction management, retry, circuit breaker)
- Health monitoring (MixinHealthCheck)
- Event publishing (MixinEventBus)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for effect nodes that perform I/O operations, external API calls, or database operations.

Usage Example:
    ```python
    from omnibase_core.nodes.node_services.model_service_effect import ModelServiceEffect
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

    class NodeDatabaseWriterEffect(ModelServiceEffect):
        '''Database writer with automatic health checks, events, and metrics.'''

        async def execute_effect(self, contract: ModelContractEffect) -> dict:
            # Just write your business logic!
            result = await self.database.write(contract.input_data)

            # Emit event automatically tracked with metrics
            await self.publish_event(
                event_type="write_completed",
                payload={"records_written": result["count"]},
                correlation_id=contract.correlation_id
            )

            return {"status": "success", "data": result}
    ```

Included Capabilities:
    - Transaction management with automatic rollback
    - Circuit breaker for fault tolerance
    - Automatic retry with configurable backoff
    - Health check endpoints via MixinHealthCheck
    - Event emission via MixinEventBus
    - Performance metrics collection via MixinMetrics
    - Structured logging with correlation tracking

Node Type: Effect (External I/O, side effects, state changes)
"""

from typing import Any

from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_effect import NodeEffect


class ModelServiceEffect(
    NodeEffect,
    MixinHealthCheck,
    MixinEventBus[Any, Any],
    MixinMetrics,
):
    """
    Standard Effect Node Service.

    Combines NodeEffect base class with essential production mixins:
    - Effect semantics (transaction mgmt, retry, circuit breaker)
    - Health monitoring (MixinHealthCheck)
    - Event publishing (MixinEventBus)
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceEffect → NodeEffect → MixinHealthCheck → MixinEventBus
        → MixinMetrics → NodeCoreBase → ABC

    This composition is optimized for:
    - Database operations requiring transactions
    - External API calls needing circuit breaker protection
    - File I/O operations with health monitoring
    - Message queue producers with event coordination

    For custom mixin compositions, inherit directly from NodeEffect
    and add your desired mixins instead.
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize ModelServiceEffect with container dependency injection.

        All mixin initialization is handled automatically via Python's MRO.
        Each mixin's __init__ is called in sequence, setting up:
        - Health check framework
        - Event bus connection
        - Metrics collectors

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)
