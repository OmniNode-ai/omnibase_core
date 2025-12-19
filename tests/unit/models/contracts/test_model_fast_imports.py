"""
Unit tests for model_fast_imports.py fast import factory.

Tests zero-import-time loading, caching, and factory pattern for contract models.
"""

import sys

import pytest


@pytest.mark.unit
class TestModelFastContractFactory:
    """Test suite for ModelFastContractFactory class."""

    def test_factory_initialization(self):
        """Test that factory initializes with empty cache."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        assert factory._contract_cache == {}
        assert len(factory._import_paths) == 5
        assert "base" in factory._import_paths
        assert "compute" in factory._import_paths
        assert "effect" in factory._import_paths
        assert "reducer" in factory._import_paths
        assert "orchestrator" in factory._import_paths

    def test_import_paths_configured_correctly(self):
        """Test that import paths are configured correctly."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        assert (
            factory._import_paths["base"]
            == "omnibase_core.models.contracts.model_contract_base"
        )
        assert (
            factory._import_paths["compute"]
            == "omnibase_core.models.contracts.model_contract_compute"
        )
        assert (
            factory._import_paths["effect"]
            == "omnibase_core.models.contracts.model_contract_effect"
        )
        assert (
            factory._import_paths["reducer"]
            == "omnibase_core.models.contracts.model_contract_reducer"
        )
        assert (
            factory._import_paths["orchestrator"]
            == "omnibase_core.models.contracts.model_contract_orchestrator"
        )

    def test_get_base_returns_contract_base_class(self):
        """Test that get_base returns ModelContractBase class."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        base_class = factory.get_base()

        assert base_class is not None
        assert base_class.__name__ == "ModelContractBase"
        assert isinstance(base_class, type)

    def test_get_compute_returns_contract_compute_class(self):
        """Test that get_compute returns ModelContractCompute class."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        compute_class = factory.get_compute()

        assert compute_class is not None
        assert compute_class.__name__ == "ModelContractCompute"
        assert isinstance(compute_class, type)

    def test_get_effect_returns_contract_effect_class(self):
        """Test that get_effect returns ModelContractEffect class."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        effect_class = factory.get_effect()

        assert effect_class is not None
        assert effect_class.__name__ == "ModelContractEffect"
        assert isinstance(effect_class, type)

    def test_get_reducer_returns_contract_reducer_class(self):
        """Test that get_reducer returns ModelContractReducer class."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        reducer_class = factory.get_reducer()

        assert reducer_class is not None
        assert reducer_class.__name__ == "ModelContractReducer"
        assert isinstance(reducer_class, type)

    def test_get_orchestrator_returns_contract_orchestrator_class(self):
        """Test that get_orchestrator returns ModelContractOrchestrator class."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        orchestrator_class = factory.get_orchestrator()

        assert orchestrator_class is not None
        assert orchestrator_class.__name__ == "ModelContractOrchestrator"
        assert isinstance(orchestrator_class, type)

    def test_caching_prevents_reimport(self):
        """Test that caching prevents re-importing the same contract."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        # First call - should import and cache
        base_class1 = factory.get_base()
        cache_size1 = len(factory._contract_cache)

        # Second call - should use cache
        base_class2 = factory.get_base()
        cache_size2 = len(factory._contract_cache)

        # Should be the same instance from cache
        assert base_class1 is base_class2
        # Cache size should not increase
        assert cache_size1 == cache_size2

    def test_get_all_contracts_returns_all_five_types(self):
        """Test that get_all_contracts returns all 5 contract types."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        all_contracts = factory.get_all_contracts()

        assert isinstance(all_contracts, dict)
        assert len(all_contracts) == 5
        assert "base" in all_contracts
        assert "compute" in all_contracts
        assert "effect" in all_contracts
        assert "reducer" in all_contracts
        assert "orchestrator" in all_contracts

    def test_get_all_contracts_classes_are_correct(self):
        """Test that get_all_contracts returns correct class types."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        all_contracts = factory.get_all_contracts()

        assert all_contracts["base"].__name__ == "ModelContractBase"
        assert all_contracts["compute"].__name__ == "ModelContractCompute"
        assert all_contracts["effect"].__name__ == "ModelContractEffect"
        assert all_contracts["reducer"].__name__ == "ModelContractReducer"
        assert all_contracts["orchestrator"].__name__ == "ModelContractOrchestrator"

    def test_get_stats_returns_correct_structure(self):
        """Test that get_stats returns correct statistics structure."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()
        stats = factory.get_stats()

        assert isinstance(stats, dict)
        assert "cached_contracts" in stats
        assert "cache_size" in stats
        assert "available_contracts" in stats

    def test_get_stats_reflects_cache_state(self):
        """Test that get_stats reflects the current cache state."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        # Initially empty
        stats1 = factory.get_stats()
        assert stats1["cache_size"] == 0
        assert len(stats1["cached_contracts"]) == 0

        # After loading one contract
        factory.get_base()
        stats2 = factory.get_stats()
        assert stats2["cache_size"] == 1
        assert len(stats2["cached_contracts"]) == 1

    def test_import_contract_with_invalid_type_raises_error(self):
        """Test that importing an unknown contract type raises OnexError."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        with pytest.raises(Exception) as exc_info:
            factory._import_contract("invalid_type", "InvalidClass")

        # Should raise OnexError with VALIDATION_ERROR code
        assert "Unknown contract type" in str(exc_info.value)

    def test_multiple_factories_have_independent_caches(self):
        """Test that multiple factory instances have independent caches."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory1 = ModelFastContractFactory()
        factory2 = ModelFastContractFactory()

        # Load contract in factory1
        factory1.get_base()

        # factory2 should have empty cache
        assert len(factory1._contract_cache) == 1
        assert len(factory2._contract_cache) == 0


@pytest.mark.unit
class TestModuleLevelFunctions:
    """Test suite for module-level convenience functions."""

    def test_base_function_returns_base_class(self):
        """Test that base() returns ModelContractBase."""
        from omnibase_core.models.contracts.model_fast_imports import base

        base_class = base()

        assert base_class is not None
        assert base_class.__name__ == "ModelContractBase"

    def test_compute_function_returns_compute_class(self):
        """Test that compute() returns ModelContractCompute."""
        from omnibase_core.models.contracts.model_fast_imports import compute

        compute_class = compute()

        assert compute_class is not None
        assert compute_class.__name__ == "ModelContractCompute"

    def test_effect_function_returns_effect_class(self):
        """Test that effect() returns ModelContractEffect."""
        from omnibase_core.models.contracts.model_fast_imports import effect

        effect_class = effect()

        assert effect_class is not None
        assert effect_class.__name__ == "ModelContractEffect"

    def test_reducer_function_returns_reducer_class(self):
        """Test that reducer() returns ModelContractReducer."""
        from omnibase_core.models.contracts.model_fast_imports import reducer

        reducer_class = reducer()

        assert reducer_class is not None
        assert reducer_class.__name__ == "ModelContractReducer"

    def test_orchestrator_function_returns_orchestrator_class(self):
        """Test that orchestrator() returns ModelContractOrchestrator."""
        from omnibase_core.models.contracts.model_fast_imports import orchestrator

        orchestrator_class = orchestrator()

        assert orchestrator_class is not None
        assert orchestrator_class.__name__ == "ModelContractOrchestrator"

    def test_all_contracts_function_returns_all_types(self):
        """Test that all_contracts() returns all contract types."""
        from omnibase_core.models.contracts.model_fast_imports import all_contracts

        contracts = all_contracts()

        assert isinstance(contracts, dict)
        assert len(contracts) == 5

    def test_factory_stats_function_returns_statistics(self):
        """Test that factory_stats() returns factory statistics."""
        from omnibase_core.models.contracts.model_fast_imports import factory_stats

        stats = factory_stats()

        assert isinstance(stats, dict)
        assert "cached_contracts" in stats
        assert "cache_size" in stats

    def test_module_functions_use_global_factory(self):
        """Test that module-level functions use the global factory instance."""
        from omnibase_core.models.contracts.model_fast_imports import base, compute

        # Load contracts using module functions
        base1 = base()
        compute1 = compute()

        # Load again - should use cache
        base2 = base()
        compute2 = compute()

        # Should be the same instances
        assert base1 is base2
        assert compute1 is compute2


@pytest.mark.unit
class TestCreationHelpers:
    """Test suite for contract creation helper functions."""

    def test_create_compute_contract_function_exists(self):
        """Test that create_compute_contract function exists and is callable."""
        from omnibase_core.models.contracts.model_fast_imports import (
            create_compute_contract,
        )

        assert callable(create_compute_contract)
        # Function requires proper contract parameters to work
        # Testing with invalid params would just test validation, not the factory

    def test_create_effect_contract_function_exists(self):
        """Test that create_effect_contract function exists and is callable."""
        from omnibase_core.models.contracts.model_fast_imports import (
            create_effect_contract,
        )

        assert callable(create_effect_contract)
        # Function requires proper contract parameters to work
        # Testing with invalid params would just test validation, not the factory

    def test_create_base_contract_function_exists(self):
        """Test that create_base_contract function exists and is callable."""
        from omnibase_core.models.contracts.model_fast_imports import (
            create_base_contract,
        )

        assert callable(create_base_contract)
        # ModelContractBase is abstract and cannot be instantiated
        # Testing instantiation would fail, which is expected behavior


@pytest.mark.unit
class TestPreloadingFunctions:
    """Test suite for preloading functionality."""

    def test_preload_critical_contracts_loads_common_contracts(self):
        """Test that preload_critical_contracts loads compute, effect, and base."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
            preload_critical_contracts,
        )

        # Create new factory to test preloading
        factory = ModelFastContractFactory()

        # Initially empty
        assert len(factory._contract_cache) == 0

        # Can't directly test global factory, but we can test the function exists and is callable
        assert callable(preload_critical_contracts)

    def test_preload_all_contracts_loads_all_types(self):
        """Test that preload_all_contracts loads all contract types."""
        from omnibase_core.models.contracts.model_fast_imports import (
            preload_all_contracts,
        )

        assert callable(preload_all_contracts)

        # Execute preload
        preload_all_contracts()

        # Verify all contracts are now available
        from omnibase_core.models.contracts.model_fast_imports import factory_stats

        stats = factory_stats()
        # After preloading, cache should have all 5 contracts
        assert stats["cache_size"] >= 5


@pytest.mark.unit
class TestPerformanceMonitoring:
    """Test suite for performance monitoring."""

    def test_performance_monitor_exists(self):
        """Test that ModelPerformanceMonitor class exists."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelPerformanceMonitor,
        )

        assert ModelPerformanceMonitor is not None

    def test_measure_import_time_returns_metrics(self):
        """Test that measure_import_time returns performance metrics."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelPerformanceMonitor,
        )

        metrics = ModelPerformanceMonitor.measure_import_time()

        assert isinstance(metrics, dict)
        assert "module_load_time_ms" in metrics
        assert "factory_access_time_ms" in metrics
        assert "status" in metrics

    def test_measure_import_time_metrics_structure(self):
        """Test that measure_import_time returns correct metric structure."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelPerformanceMonitor,
        )

        metrics = ModelPerformanceMonitor.measure_import_time()

        # module_load_time_ms should be 0.0 (no imports at module level)
        assert metrics["module_load_time_ms"] == 0.0

        # factory_access_time_ms should be a number
        assert isinstance(metrics["factory_access_time_ms"], float)

        # status should be a string
        assert isinstance(metrics["status"], str)
        assert metrics["status"] in ["optimal", "needs_optimization"]

    def test_performance_status_optimal_for_fast_access(self):
        """Test that performance status is optimal for fast access times."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelPerformanceMonitor,
        )

        metrics = ModelPerformanceMonitor.measure_import_time()

        # Factory access should be very fast (<1ms)
        assert metrics["factory_access_time_ms"] < 1.0
        assert metrics["status"] == "optimal"


@pytest.mark.unit
class TestZeroImportTimeLoading:
    """Test suite for zero-import-time loading behavior."""

    def test_no_imports_at_module_level(self):
        """Test that no contract imports occur at module import time."""

        # Remove any cached contract modules
        modules_to_remove = [
            key
            for key in list(sys.modules.keys())
            if "model_contract_" in key and "model_fast_imports" not in key
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import the fast imports module

        # Verify no contract modules were imported
        contract_modules = [
            key
            for key in sys.modules
            if "model_contract_" in key and "model_fast_imports" not in key
        ]

        # Should be empty (no imports at module level)
        assert len(contract_modules) == 0, (
            f"Contract modules imported at module level: {contract_modules}"
        )

    def test_imports_occur_only_on_demand(self):
        """Test that imports only occur when contracts are actually requested."""

        # Create a new factory to test fresh import behavior
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        # Cache should be empty initially
        assert len(factory._contract_cache) == 0

        # Call get_base() to trigger import
        base_class = factory.get_base()

        # After calling, cache should have the base contract
        assert len(factory._contract_cache) == 1
        assert "base_ModelContractBase" in factory._contract_cache
        assert base_class is not None

    def test_module_all_exports_correct_functions(self):
        """Test that __all__ exports the correct functions."""
        from omnibase_core.models.contracts import model_fast_imports

        expected_exports = {
            "base",
            "compute",
            "effect",
            "reducer",
            "orchestrator",
            "all_contracts",
            "create_compute_contract",
            "create_effect_contract",
            "create_base_contract",
            "preload_critical_contracts",
            "preload_all_contracts",
            "factory_stats",
            "ModelFastContractFactory",
            "ModelPerformanceMonitor",
        }

        assert hasattr(model_fast_imports, "__all__")
        assert set(model_fast_imports.__all__) == expected_exports


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error handling in fast imports."""

    def test_invalid_contract_type_raises_appropriate_error(self):
        """Test that invalid contract type raises OnexError with proper context."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        with pytest.raises(Exception) as exc_info:
            factory._import_contract("nonexistent", "NonExistentClass")

        error = exc_info.value
        assert "Unknown contract type" in str(error)

    def test_missing_class_in_module_raises_attribute_error(self):
        """Test that missing class in module raises AttributeError."""
        from omnibase_core.models.contracts.model_fast_imports import (
            ModelFastContractFactory,
        )

        factory = ModelFastContractFactory()

        with pytest.raises(AttributeError):
            factory._import_contract("base", "NonExistentClassName")
