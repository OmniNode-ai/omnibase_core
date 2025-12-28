"""
ModelServiceEffect - Standard Production-Ready Effect Node

Pre-composed with essential mixins for production use:
- Persistent service mode (MixinNodeService) - long-lived MCP servers, tool invocation
- Effect semantics (transaction management, retry, circuit breaker)
- Health monitoring (MixinHealthCheck)
- Event publishing (MixinEventBus)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for effect nodes that perform I/O operations, external API calls, or database operations.

Usage Example:
    ```python
    from omnibase_core.models.services.model_service_effect import ModelServiceEffect
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

    class NodeDatabaseWriterEffect(ModelServiceEffect):
        '''Database writer with automatic health checks, events, and metrics.'''

        async def execute_effect(self, input_data: ModelEffectInput) -> ModelEffectOutput:
            # Just write your business logic!
            result = await self.database.write(input_data.operation_data)

            # Emit event automatically tracked with metrics
            await self.publish_event(
                event_type="write_completed",
                payload={"records_written": result["count"]},
                correlation_id=input_data.correlation_id
            )

            return ModelEffectOutput(...)
    ```

Included Capabilities:
    - Persistent service mode with TOOL_INVOCATION handling (MixinNodeService)
    - Service lifecycle management (start_service_mode, stop_service_mode)
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
from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_effect import NodeEffect


class ModelServiceEffect(  # type: ignore[misc]  # MRO method signature conflicts between mixins
    MixinNodeService,
    NodeEffect,
    MixinHealthCheck,
    MixinEventBus[Any, Any],
    MixinMetrics,
):
    """
    Standard Effect Node Service.

    Combines NodeEffect base class with essential production mixins:
    - Persistent service mode (MixinNodeService) - run as long-lived tool service
    - Effect semantics (transaction mgmt, retry, circuit breaker)
    - Health monitoring (MixinHealthCheck)
    - Event publishing (MixinEventBus)
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceEffect → MixinNodeService → NodeEffect → MixinHealthCheck
        → MixinEventBus → MixinMetrics → NodeCoreBase → ABC

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

    def cleanup_event_handlers(self) -> None:
        """
        Clean up event handlers during service shutdown.

        This method is called by MixinNodeService during stop_service_mode()
        to allow cleanup of any event subscriptions or handlers. Override this
        method in subclasses to add custom cleanup logic.

        Calls dispose_event_bus_resources() to clean up MixinEventBus state
        if available, otherwise falls back to stop_event_listener().
        """
        # Dispose event bus resources (threads, subscriptions, etc.)
        # Use new dispose method if available (refactored MixinEventBus),
        # otherwise fall back to legacy stop_event_listener
        if hasattr(self, "dispose_event_bus_resources"):
            self.dispose_event_bus_resources()
        elif hasattr(self, "stop_event_listener"):
            self.stop_event_listener()
        # Subclasses can override this to add custom event handler cleanup
