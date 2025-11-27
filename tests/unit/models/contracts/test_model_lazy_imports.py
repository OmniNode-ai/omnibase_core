"""
Unit tests for model_lazy_imports.py lazy import loader.

Tests lazy loading with caching, singleton pattern, and performance optimization.
"""

import sys


class TestModelLazyContractLoader:
    """Test suite for ModelLazyContractLoader class."""

    def test_loader_initialization(self):
        """Test that loader initializes with empty cache."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        assert loader._cache == {}
        assert loader._loading == {}

    def test_get_contract_base_returns_base_class(self):
        """Test that get_contract_base returns ModelContractBase class."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        base_class = loader.get_contract_base()

        assert base_class is not None
        assert base_class.__name__ == "ModelContractBase"
        assert isinstance(base_class, type)

    def test_get_contract_compute_returns_compute_class(self):
        """Test that get_contract_compute returns ModelContractCompute class."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        compute_class = loader.get_contract_compute()

        assert compute_class is not None
        assert compute_class.__name__ == "ModelContractCompute"
        assert isinstance(compute_class, type)

    def test_get_contract_effect_returns_effect_class(self):
        """Test that get_contract_effect returns ModelContractEffect class."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        effect_class = loader.get_contract_effect()

        assert effect_class is not None
        assert effect_class.__name__ == "ModelContractEffect"
        assert isinstance(effect_class, type)

    def test_get_contract_reducer_returns_reducer_class(self):
        """Test that get_contract_reducer returns ModelContractReducer class."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        reducer_class = loader.get_contract_reducer()

        assert reducer_class is not None
        assert reducer_class.__name__ == "ModelContractReducer"
        assert isinstance(reducer_class, type)

    def test_get_contract_orchestrator_returns_orchestrator_class(self):
        """Test that get_contract_orchestrator returns ModelContractOrchestrator class."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        orchestrator_class = loader.get_contract_orchestrator()

        assert orchestrator_class is not None
        assert orchestrator_class.__name__ == "ModelContractOrchestrator"
        assert isinstance(orchestrator_class, type)

    def test_caching_stores_classes_in_cache(self):
        """Test that caching stores loaded classes in the internal cache."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Initially empty
        assert len(loader._cache) == 0

        # Load base contract
        loader.get_contract_base()

        # Should be cached
        assert "ModelContractBase" in loader._cache

    def test_multiple_calls_return_same_instance(self):
        """Test that multiple calls return the same cached instance."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # First call
        base1 = loader.get_contract_base()

        # Second call - should return cached instance
        base2 = loader.get_contract_base()

        # Should be the same instance
        assert base1 is base2

    def test_functools_cache_decorator_applied(self):
        """Test that functools.cache decorator is applied to lazy loading methods."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Methods should have cache_info attribute from functools.cache
        assert hasattr(loader.get_contract_base, "cache_info")
        assert hasattr(loader.get_contract_compute, "cache_info")
        assert hasattr(loader.get_contract_effect, "cache_info")
        assert hasattr(loader.get_contract_reducer, "cache_info")
        assert hasattr(loader.get_contract_orchestrator, "cache_info")

    def test_preload_all_loads_all_contracts(self):
        """Test that preload_all loads all contract types."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Preload all contracts
        loader.preload_all()

        # All contracts should be cached
        assert "ModelContractBase" in loader._cache
        assert "ModelContractCompute" in loader._cache
        assert "ModelContractEffect" in loader._cache
        assert "ModelContractReducer" in loader._cache
        assert "ModelContractOrchestrator" in loader._cache

    def test_get_cache_stats_returns_correct_structure(self):
        """Test that get_cache_stats returns correct statistics structure."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        stats = loader.get_cache_stats()

        assert isinstance(stats, dict)
        assert "cached_models" in stats
        assert "cache_size" in stats
        assert "available_models" in stats

    def test_get_cache_stats_reflects_cache_state(self):
        """Test that get_cache_stats reflects the current cache state."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Initially empty
        stats1 = loader.get_cache_stats()
        assert stats1["cache_size"] == 0
        assert len(stats1["cached_models"]) == 0

        # After loading one contract
        loader.get_contract_base()
        stats2 = loader.get_cache_stats()
        assert stats2["cache_size"] == 1
        assert "ModelContractBase" in stats2["cached_models"]

    def test_get_cache_stats_available_models_list(self):
        """Test that get_cache_stats includes list of available models."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()
        stats = loader.get_cache_stats()

        assert "available_models" in stats
        assert len(stats["available_models"]) == 5
        assert "ModelContractBase" in stats["available_models"]
        assert "ModelContractCompute" in stats["available_models"]
        assert "ModelContractEffect" in stats["available_models"]
        assert "ModelContractReducer" in stats["available_models"]
        assert "ModelContractOrchestrator" in stats["available_models"]

    def test_multiple_loaders_have_independent_caches(self):
        """Test that multiple loader instances have independent caches."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader1 = ModelLazyContractLoader()
        loader2 = ModelLazyContractLoader()

        # Load contract in loader1
        loader1.get_contract_base()

        # loader2 should have empty cache (independent instances)
        assert len(loader1._cache) == 1
        assert len(loader2._cache) == 0


class TestModuleLevelFunctions:
    """Test suite for module-level convenience functions."""

    def test_get_contract_base_function_returns_base_class(self):
        """Test that get_contract_base() returns ModelContractBase."""
        from omnibase_core.models.contracts.model_lazy_imports import get_contract_base

        base_class = get_contract_base()

        assert base_class is not None
        assert base_class.__name__ == "ModelContractBase"

    def test_get_contract_compute_function_returns_compute_class(self):
        """Test that get_contract_compute() returns ModelContractCompute."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_compute,
        )

        compute_class = get_contract_compute()

        assert compute_class is not None
        assert compute_class.__name__ == "ModelContractCompute"

    def test_get_contract_effect_function_returns_effect_class(self):
        """Test that get_contract_effect() returns ModelContractEffect."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_effect,
        )

        effect_class = get_contract_effect()

        assert effect_class is not None
        assert effect_class.__name__ == "ModelContractEffect"

    def test_get_contract_reducer_function_returns_reducer_class(self):
        """Test that get_contract_reducer() returns ModelContractReducer."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_reducer,
        )

        reducer_class = get_contract_reducer()

        assert reducer_class is not None
        assert reducer_class.__name__ == "ModelContractReducer"

    def test_get_contract_orchestrator_function_returns_orchestrator_class(self):
        """Test that get_contract_orchestrator() returns ModelContractOrchestrator."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_orchestrator,
        )

        orchestrator_class = get_contract_orchestrator()

        assert orchestrator_class is not None
        assert orchestrator_class.__name__ == "ModelContractOrchestrator"

    def test_preload_all_contracts_function(self):
        """Test that preload_all_contracts() preloads all contracts."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_loader_stats,
            preload_all_contracts,
        )

        # Preload all contracts
        preload_all_contracts()

        # Check stats - all contracts should be cached
        stats = get_loader_stats()
        assert stats["cache_size"] == 5

    def test_get_loader_stats_function_returns_statistics(self):
        """Test that get_loader_stats() returns loader statistics."""
        from omnibase_core.models.contracts.model_lazy_imports import get_loader_stats

        stats = get_loader_stats()

        assert isinstance(stats, dict)
        assert "cached_models" in stats
        assert "cache_size" in stats
        assert "available_models" in stats

    def test_module_functions_use_singleton_loader(self):
        """Test that module-level functions use the singleton _lazy_loader instance."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_base,
            get_contract_compute,
        )

        # Load contracts using module functions
        base1 = get_contract_base()
        compute1 = get_contract_compute()

        # Load again - should use singleton cache
        base2 = get_contract_base()
        compute2 = get_contract_compute()

        # Should be the same instances from singleton
        assert base1 is base2
        assert compute1 is compute2


class TestSingletonBehavior:
    """Test suite for singleton pattern behavior."""

    def test_singleton_loader_instance_exists(self):
        """Test that _lazy_loader singleton instance exists."""
        from omnibase_core.models.contracts import model_lazy_imports

        assert hasattr(model_lazy_imports, "_lazy_loader")
        assert model_lazy_imports._lazy_loader is not None

    def test_singleton_loader_is_model_lazy_contract_loader(self):
        """Test that singleton is instance of ModelLazyContractLoader."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
            _lazy_loader,
        )

        assert isinstance(_lazy_loader, ModelLazyContractLoader)

    def test_module_functions_access_same_singleton(self):
        """Test that all module functions access the same singleton instance."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_base,
            get_loader_stats,
        )

        # Load a contract
        get_contract_base()

        # Stats should reflect the singleton's state
        stats = get_loader_stats()
        assert "ModelContractBase" in stats["cached_models"]


class TestLazyLoadingBehavior:
    """Test suite for lazy loading behavior."""

    def test_no_imports_at_module_level(self):
        """Test that no contract imports occur at module import time."""

        # Remove any cached contract modules
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if "model_contract_" in key and "model_lazy_imports" not in key
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import the lazy imports module

        # Verify no contract modules were imported
        contract_modules = [
            key
            for key in sys.modules
            if "model_contract_" in key and "model_lazy_imports" not in key
        ]

        # Should be empty (no imports at module level)
        assert (
            len(contract_modules) == 0
        ), f"Contract modules imported at module level: {contract_modules}"

    def test_imports_occur_only_on_demand(self):
        """Test that imports only occur when contracts are actually requested."""

        # Create a new loader to test fresh import behavior
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Cache should be empty initially
        assert len(loader._cache) == 0

        # Call get_contract_base() to trigger import
        base_class = loader.get_contract_base()

        # After calling, cache should have the base contract
        assert len(loader._cache) == 1
        assert "ModelContractBase" in loader._cache
        assert base_class is not None

    def test_type_checking_imports_dont_affect_runtime(self):
        """Test that TYPE_CHECKING imports don't affect runtime behavior."""
        from omnibase_core.models.contracts.model_lazy_imports import get_contract_base

        # Should work at runtime despite TYPE_CHECKING imports
        base_class = get_contract_base()
        assert base_class is not None

    def test_module_all_exports_correct_functions(self):
        """Test that __all__ exports the correct functions."""
        from omnibase_core.models.contracts import model_lazy_imports

        expected_exports = {
            "get_contract_base",
            "get_contract_compute",
            "get_contract_effect",
            "get_contract_reducer",
            "get_contract_orchestrator",
            "preload_all_contracts",
            "get_loader_stats",
            "ModelLazyContractLoader",
        }

        assert hasattr(model_lazy_imports, "__all__")
        assert set(model_lazy_imports.__all__) == expected_exports


class TestPerformanceOptimization:
    """Test suite for performance optimization features."""

    def test_lazy_loading_defers_import_penalty(self):
        """Test that lazy loading defers import penalty until first access."""
        import time

        # Clear cached modules
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if "model_contract_" in key and "model_lazy_imports" not in key
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import lazy imports module - should be fast
        start = time.perf_counter()

        import_time = (time.perf_counter() - start) * 1000

        # Verify no contract modules loaded yet
        contract_modules = [
            key
            for key in sys.modules
            if "model_contract_" in key and "model_lazy_imports" not in key
        ]

        assert (
            len(contract_modules) == 0
        ), f"Import cascade detected: {contract_modules}"

    def test_functools_cache_reduces_repeated_loading(self):
        """Test that functools.cache reduces repeated loading overhead."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # First call - triggers import
        base1 = loader.get_contract_base()

        # Check cache info - should have 1 hit after second call
        base2 = loader.get_contract_base()
        cache_info = loader.get_contract_base.cache_info()

        # Cache should have been hit
        assert cache_info.hits > 0

    def test_preload_all_for_performance_critical_scenarios(self):
        """Test preload_all for performance-critical scenarios."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            ModelLazyContractLoader,
        )

        loader = ModelLazyContractLoader()

        # Preload all contracts
        loader.preload_all()

        # All contracts should be immediately available from cache
        stats = loader.get_cache_stats()
        assert stats["cache_size"] == 5

        # Subsequent access should be very fast (from cache)
        base_class = loader.get_contract_base()
        assert base_class is not None


class TestIntegrationWithContracts:
    """Integration tests with actual contract classes."""

    def test_loaded_base_contract_is_class(self):
        """Test that loaded ModelContractBase is a valid class type."""
        from omnibase_core.models.contracts.model_lazy_imports import get_contract_base

        BaseContract = get_contract_base()

        # Should be a class type
        assert isinstance(BaseContract, type)
        assert BaseContract.__name__ == "ModelContractBase"
        # ModelContractBase is abstract and cannot be instantiated directly

    def test_loaded_compute_contract_is_class(self):
        """Test that loaded ModelContractCompute is a valid class type."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_compute,
        )

        ComputeContract = get_contract_compute()

        # Should be a class type
        assert isinstance(ComputeContract, type)
        assert ComputeContract.__name__ == "ModelContractCompute"
        # Contract requires proper parameters for instantiation

    def test_all_contract_types_can_be_loaded_and_used(self):
        """Test that all contract types can be loaded and used."""
        from omnibase_core.models.contracts.model_lazy_imports import (
            get_contract_base,
            get_contract_compute,
            get_contract_effect,
            get_contract_orchestrator,
            get_contract_reducer,
        )

        # Load all contract types
        contracts = {
            "base": get_contract_base(),
            "compute": get_contract_compute(),
            "effect": get_contract_effect(),
            "reducer": get_contract_reducer(),
            "orchestrator": get_contract_orchestrator(),
        }

        # All should be loaded successfully
        assert all(contract is not None for contract in contracts.values())
        assert all(isinstance(contract, type) for contract in contracts.values())
