"""
ModelServiceCompute - Standard Production-Ready Compute Node

Pre-composed with essential mixins for production use:
- Compute semantics (pure transformations, deterministic outputs)
- Health monitoring (MixinHealthCheck)
- Result caching (MixinCaching)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for compute nodes that perform data transformations, calculations, or pure functions.

Usage Example:
    ```python
    from omnibase_core.models.nodes.services.model_service_compute import ModelServiceCompute
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

    class NodeDataTransformerCompute(ModelServiceCompute):
        '''Data transformer with automatic caching and metrics.'''

        async def execute_compute(self, contract: ModelContractCompute) -> dict:
            # Check cache first (automatic via MixinCaching)
            cache_key = self.generate_cache_key(contract.input_data)
            cached_result = await self.get_cached(cache_key)

            if cached_result:
                return cached_result

            # Perform computation
            result = await self._transform_data(contract.input_data)

            # Cache result automatically
            await self.set_cached(cache_key, result, ttl_seconds=600)

            return result
    ```

Included Capabilities:
    - Pure function semantics (no side effects)
    - Result caching with configurable TTL
    - Health check endpoints via MixinHealthCheck
    - Performance metrics collection via MixinMetrics
    - Automatic cache key generation
    - Cache hit/miss tracking

Node Type: Compute (Pure transformations, deterministic outputs)
"""

from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_compute import NodeCompute


class ModelServiceCompute(
    NodeCompute,
    MixinHealthCheck,
    MixinCaching,
    MixinMetrics,
):
    """
    Standard Compute Node Service.

    Combines NodeCompute base class with essential production mixins:
    - Compute semantics (pure transformations, idempotent operations)
    - Health monitoring (MixinHealthCheck)
    - Result caching (MixinCaching) - critical for expensive computations
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceCompute → NodeCompute → MixinHealthCheck → MixinCaching
        → MixinMetrics → NodeCoreBase → ABC

    This composition is optimized for:
    - Data transformation pipelines benefiting from caching
    - Expensive calculations with repeatable inputs
    - Pure functions requiring performance monitoring
    - Stateless processors with deterministic outputs

    Why MixinCaching is included:
        Compute nodes often perform expensive operations (ML inference,
        complex transformations, aggregations) that benefit significantly
        from result caching. The cache eliminates redundant computation
        for identical inputs.

    For custom mixin compositions, inherit directly from NodeCompute
    and add your desired mixins instead.
    """

    def __init__(self, container: ModelONEXContainer):
        """
        Initialize ModelServiceCompute with container dependency injection.

        All mixin initialization is handled automatically via Python's MRO.
        Each mixin's __init__ is called in sequence, setting up:
        - Health check framework
        - Cache service connection and configuration
        - Metrics collectors

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)
