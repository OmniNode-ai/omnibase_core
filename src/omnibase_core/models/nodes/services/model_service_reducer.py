"""
ModelServiceReducer - Standard Production-Ready Reducer Node

Pre-composed with essential mixins for production use:
- Reducer semantics (aggregation, state management, persistence)
- Health monitoring (MixinHealthCheck)
- Result caching (MixinCaching)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for reducer nodes that aggregate data, manage state, or persist computed results.

Usage Example:
    ```python
    from omnibase_core.models.nodes.services.model_service_reducer import ModelServiceReducer
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer

    class NodeMetricsAggregatorReducer(ModelServiceReducer):
        '''Metrics aggregator with automatic caching and health checks.'''

        async def execute_reduction(self, contract: ModelContractReducer) -> dict:
            # Check cache for recent aggregation
            cache_key = self.generate_cache_key(contract.aggregation_window)
            cached_result = await self.get_cached(cache_key)

            if cached_result:
                return cached_result

            # Perform aggregation
            aggregated_data = await self._aggregate_metrics(contract.input_data)

            # Cache aggregated result
            await self.set_cached(cache_key, aggregated_data, ttl_seconds=300)

            return aggregated_data
    ```

Included Capabilities:
    - Aggregation and state management
    - Result caching with configurable TTL (critical for reducers)
    - Health check endpoints via MixinHealthCheck
    - Performance metrics collection via MixinMetrics
    - Automatic cache invalidation on state changes
    - State persistence health monitoring

Node Type: Reducer (Aggregation, state management, persistence)
"""

from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_reducer import NodeReducer


class ModelServiceReducer(
    NodeReducer,
    MixinHealthCheck,
    MixinCaching,
    MixinMetrics,
):
    """
    Standard Reducer Node Service following ONEX model naming conventions.

    Combines NodeReducer base class with essential production mixins:
    - Reducer semantics (aggregation, state management, persistence)
    - Health monitoring (MixinHealthCheck) - includes state persistence checks
    - Result caching (MixinCaching) - critical for expensive aggregations
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceReducer → NodeReducer → MixinHealthCheck → MixinCaching
        → MixinMetrics → NodeCoreBase → ABC

    This composition is optimized for:
    - Data aggregation pipelines benefiting from result caching
    - State management requiring persistence health checks
    - Metrics collectors aggregating large datasets
    - Stream processors reducing event streams to summaries

    Why MixinCaching is critical:
        Reducers often perform expensive aggregations over large datasets
        (sum, average, group-by operations). Caching aggregated results
        eliminates redundant computation for repeated queries over the
        same time window or dataset.

    Example use cases:
        - Metrics aggregator caching 5-minute rollups
        - Log analyzer caching daily summaries
        - Analytics reducer caching computed KPIs

    For custom mixin compositions, inherit directly from NodeReducer
    and add your desired mixins instead.
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize ModelServiceReducer with container dependency injection.

        All mixin initialization is handled automatically via Python's MRO.
        Each mixin's __init__ is called in sequence, setting up:
        - Health check framework (with state persistence monitoring)
        - Cache service connection and configuration
        - Metrics collectors for aggregation performance tracking

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)


ServiceReducerNode = ModelServiceReducer
