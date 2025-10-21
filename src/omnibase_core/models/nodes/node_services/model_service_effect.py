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
    from omnibase_core.models.nodes.node_services.model_service_effect import ModelServiceEffect
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

# Type aliases for MixinEventBus generic parameters
# These use Any for flexibility in the base ModelServiceEffect class.
# Concrete implementations SHOULD override with specific state types for type safety.
#
# Example override in subclass:
#   from omnibase_core.models.state.model_database_state import ModelDatabaseState
#   ServiceInputState = ModelDatabaseState
#   ServiceOutputState = ModelDatabaseState
#
# This provides type checking for event payloads while keeping the base class flexible.
ServiceInputState = Any
ServiceOutputState = Any


class ModelServiceEffect(  # type: ignore[misc]
    MixinNodeService,
    NodeEffect,
    MixinHealthCheck,
    MixinEventBus[ServiceInputState, ServiceOutputState],
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

        Default implementation does nothing as MixinEventBus manages its own
        event subscriptions internally.
        """
        # Default implementation - no cleanup needed as MixinEventBus manages itself
        # Subclasses can override this to add custom event handler cleanup
        return
