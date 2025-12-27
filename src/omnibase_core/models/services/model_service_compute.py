"""
ModelServiceCompute - Standard Production-Ready Compute Node

Pre-composed with essential mixins for production use:
- Persistent service mode (MixinNodeService) - long-lived MCP servers, tool invocation
- Compute semantics (pure transformations, deterministic outputs)
- Health monitoring (MixinHealthCheck)
- Result caching (MixinCaching)
- Performance metrics (MixinMetrics)

This service wrapper eliminates boilerplate by pre-wiring commonly used mixins
for compute nodes that perform data transformations, calculations, or pure functions.

Usage Example:
    ```python
    from omnibase_core.models.services.model_service_compute import ModelServiceCompute
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer
    from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute

    class NodeDataTransformerCompute(ModelServiceCompute):
        '''Data transformer with automatic caching and metrics.'''

        async def execute_compute(self, contract: ModelContractCompute) -> ModelComputeOutput:
            # Check cache first (automatic via MixinCaching)
            cache_key = self.generate_cache_key(contract.input_state)
            cached_result = await self.get_cached(cache_key)

            if cached_result:
                return cached_result

            # Perform computation
            result = await self._transform_data(contract.input_state)

            # Cache result automatically
            await self.set_cached(cache_key, result, ttl_seconds=600)

            return result
    ```

Included Capabilities:
    - Persistent service mode with TOOL_INVOCATION handling (MixinNodeService)
    - Service lifecycle management (start_service_mode, stop_service_mode)
    - Pure function semantics (no side effects)
    - Result caching with configurable TTL
    - Health check endpoints via MixinHealthCheck
    - Performance metrics collection via MixinMetrics
    - Automatic cache key generation
    - Cache hit/miss tracking

Node Type: Compute (Pure transformations, deterministic outputs)

Migration Notes:
    **v0.4.0**: Changed from PEP 695 type parameter syntax to traditional
    ``TypeVar`` syntax for mypy strict mode compatibility. This is a
    non-breaking change - the generic behavior is identical.

    Old syntax (PEP 695, not supported by mypy in CI):

    .. code-block:: python

        class ModelServiceCompute[T_Input, T_Output](
            MixinNodeService,
            NodeCompute[T_Input, T_Output],
            ...
        ):
            pass

    New syntax (traditional TypeVar, mypy-compatible):

    .. code-block:: python

        T_Input = TypeVar("T_Input")
        T_Output = TypeVar("T_Output")

        class ModelServiceCompute(
            MixinNodeService,
            NodeCompute[T_Input, T_Output],
            ...,
            Generic[T_Input, T_Output],
        ):
            pass

    Usage remains unchanged:

    .. code-block:: python

        class MyCompute(ModelServiceCompute[MyInput, MyOutput]):
            async def execute_compute(self, contract: ModelContractCompute) -> ModelComputeOutput[MyOutput]:
                ...
"""

from typing import Generic, TypeVar

from omnibase_core.mixins.mixin_caching import MixinCaching
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_compute import NodeCompute

# TypeVars for generic type parameters (using traditional syntax for mypy compatibility)
T_Input = TypeVar("T_Input")
T_Output = TypeVar("T_Output")


class ModelServiceCompute(
    MixinNodeService,
    NodeCompute[T_Input, T_Output],
    MixinHealthCheck,
    MixinCaching,
    MixinMetrics,
    Generic[T_Input, T_Output],
):
    """
    Standard Compute Node Service following ONEX model naming conventions.

    Generic type parameters:
        T_Input: Type of input data (flows from ModelComputeInput[T_Input])
        T_Output: Type of output result (flows to ModelComputeOutput[T_Output])

    Combines NodeCompute base class with essential production mixins:
    - Persistent service mode (MixinNodeService) - long-lived MCP servers, tool invocation
    - Compute semantics (pure transformations, idempotent operations)
    - Health monitoring (MixinHealthCheck)
    - Result caching (MixinCaching) - critical for expensive computations
    - Performance metrics (MixinMetrics)

    Method Resolution Order (MRO):
        ModelServiceCompute → MixinNodeService → NodeCompute → MixinHealthCheck
        → MixinCaching → MixinMetrics → NodeCoreBase → ABC

    This composition is optimized for:
    - Long-running compute services (MCP servers, tool providers)
    - Data transformation pipelines benefiting from caching
    - Expensive calculations with repeatable inputs
    - Pure functions requiring performance monitoring
    - Stateless processors with deterministic outputs

    Why MixinNodeService is first:
        Service mode must be initialized before other mixins to properly
        establish the persistent service lifecycle. This enables TOOL_INVOCATION
        handling, long-lived MCP server patterns, and proper service shutdown.

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
        - Service mode framework (MixinNodeService)
        - Health check framework (MixinHealthCheck)
        - Cache service connection and configuration (MixinCaching)
        - Metrics collectors (MixinMetrics)

        Args:
            container: ONEX container providing service dependencies
        """
        super().__init__(container)
