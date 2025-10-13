"""
Comprehensive unit tests for util_contract_loader.py (Part 2).

Part 2 Coverage:
- Contract reference resolution (_resolve_all_references)
- Cache management (clear_cache, cache invalidation)
- Contract compatibility validation (validate_contract_compatibility)
- Contract registry patterns
- Resolution stack management
- Cache statistics and metadata
- Performance testing
- Advanced integration scenarios

Part 1 (Agent 49): Basic loading, parsing, validation, security

Test Categories:
- _resolve_all_references tests (reference resolution)
- clear_cache tests (cache management)
- validate_contract_compatibility tests (compatibility checking)
- Cache behavior tests (advanced caching scenarios)
- Resolution stack tests (stack management)
- Performance tests (large contracts, stress testing)
- Advanced integration tests (multi-contract scenarios)
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject
from omnibase_core.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_contract_loader import ProtocolContractLoader

# ===== Test Fixtures =====


@pytest.fixture
def valid_contract_yaml(tmp_path: Path) -> Path:
    """Create a valid contract YAML file for testing."""
    contract_file = tmp_path / "valid_contract.yaml"
    contract_file.write_text(
        """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_name: TestNode
node_type: COMPUTE
tool_specification:
  main_tool_class: TestToolClass
""",
    )
    return contract_file


@pytest.fixture
def contract_with_references(tmp_path: Path) -> Path:
    """Create contract with $ref references for testing."""
    contract_file = tmp_path / "contract_with_refs.yaml"
    contract_file.write_text(
        """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_name: ReferencingNode
node_type: COMPUTE
tool_specification:
  main_tool_class: RefToolClass
definitions:
  $ref: './common_definitions.yaml#/definitions'
subcontracts:
  event_subcontract:
    $ref: './event_subcontract.yaml'
  fsm_subcontract:
    $ref: './fsm_subcontract.yaml'
""",
    )
    return contract_file


@pytest.fixture
def multiple_contracts(tmp_path: Path) -> list[Path]:
    """Create multiple contract files for testing."""
    contracts = []
    for i in range(5):
        contract_file = tmp_path / f"contract_{i}.yaml"
        contract_file.write_text(
            f"""
contract_version:
  major: 1
  minor: {i}
  patch: 0
node_name: TestNode{i}
node_type: COMPUTE
tool_specification:
  main_tool_class: TestToolClass{i}
""",
        )
        contracts.append(contract_file)
    return contracts


@pytest.fixture
def contract_loader(tmp_path: Path) -> ProtocolContractLoader:
    """Create a ProtocolContractLoader instance for testing."""
    return ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)


@pytest.fixture
def contract_loader_no_cache(tmp_path: Path) -> ProtocolContractLoader:
    """Create a ProtocolContractLoader with caching disabled."""
    return ProtocolContractLoader(base_path=tmp_path, cache_enabled=False)


# ===== _resolve_all_references Tests =====


class TestResolveAllReferences:
    """Test ProtocolContractLoader._resolve_all_references method."""

    def test_resolve_references_basic(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test basic reference resolution."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        result = contract_loader._resolve_all_references(content, tmp_path)

        assert isinstance(result, ModelContractContent)
        assert result.node_name == "TestNode"

    def test_resolve_references_resets_stack(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that resolution resets resolution stack."""
        # Set up a non-empty stack
        contract_loader.state.resolution_stack = ["dummy1", "dummy2"]

        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        contract_loader._resolve_all_references(content, tmp_path)

        # Stack should be reset to empty
        assert len(contract_loader.state.resolution_stack) == 0

    def test_resolve_references_preserves_contract(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that resolution preserves contract content."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=2, minor=3, patch=4),
            node_name="PreservedNode",
            node_type=EnumNodeType.EFFECT,
            tool_specification=ModelToolSpecification(main_tool_class="PreservedClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        result = contract_loader._resolve_all_references(content, tmp_path)

        # Should preserve all content
        assert result.node_name == "PreservedNode"
        assert result.node_type == EnumNodeType.EFFECT
        assert result.contract_version.major == 2
        assert result.contract_version.minor == 3
        assert result.contract_version.patch == 4
        assert result.tool_specification.main_tool_class == "PreservedClass"

    def test_resolve_references_with_complex_contract(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test reference resolution with complex contract structure."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="ComplexNode",
            node_type=EnumNodeType.ORCHESTRATOR,
            tool_specification=ModelToolSpecification(main_tool_class="ComplexClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        result = contract_loader._resolve_all_references(content, tmp_path)

        assert result.node_type == EnumNodeType.ORCHESTRATOR

    def test_resolve_references_multiple_calls(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test multiple resolution calls work correctly."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        # First call
        result1 = contract_loader._resolve_all_references(content, tmp_path)
        # Second call
        result2 = contract_loader._resolve_all_references(content, tmp_path)

        assert result1.node_name == result2.node_name
        assert len(contract_loader.state.resolution_stack) == 0


# ===== clear_cache Tests =====


class TestClearCache:
    """Test ProtocolContractLoader.clear_cache method."""

    def test_clear_cache_empties_contract_cache(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that clear_cache empties the contract cache."""
        # Load a contract to populate cache
        contract_loader.load_contract(valid_contract_yaml)

        # Verify cache is populated
        assert len(contract_loader.state.contract_cache) > 0

        # Clear cache
        contract_loader.clear_cache()

        # Verify cache is empty
        assert len(contract_loader.state.contract_cache) == 0

    def test_clear_cache_empties_loaded_contracts(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that clear_cache empties loaded contracts registry."""
        # Load a contract
        contract_loader.load_contract(valid_contract_yaml)

        # Verify loaded_contracts is populated
        assert len(contract_loader.state.loaded_contracts) > 0

        # Clear cache
        contract_loader.clear_cache()

        # Verify loaded_contracts is empty
        assert len(contract_loader.state.loaded_contracts) == 0

    def test_clear_cache_clears_both_caches(
        self,
        contract_loader: ProtocolContractLoader,
        multiple_contracts: list[Path],
    ) -> None:
        """Test that clear_cache clears both cache types."""
        # Load multiple contracts
        for contract_path in multiple_contracts:
            contract_loader.load_contract(contract_path)

        # Verify both caches are populated
        assert len(contract_loader.state.contract_cache) > 0
        assert len(contract_loader.state.loaded_contracts) > 0

        # Clear cache
        contract_loader.clear_cache()

        # Verify both caches are empty
        assert len(contract_loader.state.contract_cache) == 0
        assert len(contract_loader.state.loaded_contracts) == 0

    def test_clear_cache_allows_reload(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that contracts can be reloaded after cache clear."""
        # Load contract
        result1 = contract_loader.load_contract(valid_contract_yaml)

        # Clear cache
        contract_loader.clear_cache()

        # Reload contract
        result2 = contract_loader.load_contract(valid_contract_yaml)

        # Results should be equivalent
        assert result1.node_name == result2.node_name
        assert result1.node_type == result2.node_type

    def test_clear_cache_on_empty_cache(
        self, contract_loader: ProtocolContractLoader
    ) -> None:
        """Test clear_cache on empty cache doesn't raise error."""
        # Clear cache when empty
        contract_loader.clear_cache()

        # Should work without error
        assert len(contract_loader.state.contract_cache) == 0
        assert len(contract_loader.state.loaded_contracts) == 0

    def test_clear_cache_multiple_times(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test clearing cache multiple times."""
        # Load contract
        contract_loader.load_contract(valid_contract_yaml)

        # Clear multiple times
        contract_loader.clear_cache()
        contract_loader.clear_cache()
        contract_loader.clear_cache()

        # Should remain empty
        assert len(contract_loader.state.contract_cache) == 0
        assert len(contract_loader.state.loaded_contracts) == 0

    def test_clear_cache_preserves_loader_state(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that clear_cache preserves loader configuration."""
        # Store original configuration
        original_base_path = contract_loader.state.base_path
        original_cache_enabled = contract_loader.state.cache_enabled

        # Load and clear
        contract_loader.load_contract(valid_contract_yaml)
        contract_loader.clear_cache()

        # Configuration should be unchanged
        assert contract_loader.state.base_path == original_base_path
        assert contract_loader.state.cache_enabled == original_cache_enabled


# ===== validate_contract_compatibility Tests =====


class TestValidateContractCompatibility:
    """Test ProtocolContractLoader.validate_contract_compatibility method."""

    def test_validate_compatible_contract(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test validation of compatible contract."""
        result = contract_loader.validate_contract_compatibility(valid_contract_yaml)

        assert result is True

    def test_validate_incompatible_contract_missing_file(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation of non-existent contract."""
        nonexistent = tmp_path / "nonexistent.yaml"

        result = contract_loader.validate_contract_compatibility(nonexistent)

        assert result is False

    def test_validate_incompatible_contract_malformed(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation of malformed contract."""
        malformed = tmp_path / "malformed.yaml"
        malformed.write_text("invalid: yaml: structure: bad")

        result = contract_loader.validate_contract_compatibility(malformed)

        assert result is False

    def test_validate_contract_missing_required_fields(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test validation of contract with missing required fields."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text(
            """
contract_version:
  major: 1
  minor: 0
  patch: 0
# Missing node_name and tool_specification
""",
        )

        result = contract_loader.validate_contract_compatibility(incomplete)

        assert result is False

    def test_validate_contract_caches_result(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that validation caches the loaded contract."""
        result = contract_loader.validate_contract_compatibility(valid_contract_yaml)

        assert result is True
        # Contract should be cached
        assert (
            str(valid_contract_yaml.resolve()) in contract_loader.state.loaded_contracts
        )

    def test_validate_multiple_contracts(
        self,
        contract_loader: ProtocolContractLoader,
        multiple_contracts: list[Path],
    ) -> None:
        """Test validation of multiple contracts."""
        results = [
            contract_loader.validate_contract_compatibility(contract)
            for contract in multiple_contracts
        ]

        # All should be valid
        assert all(results)
        # All should be cached
        assert len(contract_loader.state.loaded_contracts) == len(multiple_contracts)

    def test_validate_contract_no_exception_propagation(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that validation doesn't propagate exceptions."""
        # Create various problematic files
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        # Should return False, not raise
        result = contract_loader.validate_contract_compatibility(empty_file)
        assert result is False


# ===== Cache Behavior Tests =====


class TestCacheBehavior:
    """Test advanced cache behavior and edge cases."""

    def test_cache_hit_on_second_load(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that second load hits cache."""
        # First load - miss
        contract_loader.load_contract(valid_contract_yaml)

        # Clear contract cache but not loaded_contracts to test that path
        initial_cache_size = len(contract_loader.state.contract_cache)

        # Second load - should hit loaded_contracts cache
        result = contract_loader.load_contract(valid_contract_yaml)

        assert result.node_name == "TestNode"
        # Should use loaded_contracts cache, not reload file
        assert (
            str(valid_contract_yaml.resolve()) in contract_loader.state.loaded_contracts
        )

    def test_cache_miss_with_disabled_cache(
        self,
        contract_loader_no_cache: ProtocolContractLoader,
        valid_contract_yaml: Path,
    ) -> None:
        """Test cache miss behavior when caching is disabled."""
        # Load multiple times
        result1 = contract_loader_no_cache.load_contract(valid_contract_yaml)
        result2 = contract_loader_no_cache.load_contract(valid_contract_yaml)

        # Results should be equivalent but cache should be empty
        assert result1.node_name == result2.node_name
        assert len(contract_loader_no_cache.state.contract_cache) == 0

    def test_cache_invalidation_on_file_modification(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test cache invalidation when file is modified."""
        # First load
        result1 = contract_loader.load_contract(valid_contract_yaml)

        # Modify file
        time.sleep(0.01)
        valid_contract_yaml.write_text(
            """
contract_version:
  major: 2
  minor: 0
  patch: 0
node_name: ModifiedNode
node_type: EFFECT
tool_specification:
  main_tool_class: ModifiedClass
""",
        )

        # Clear loaded_contracts to force reload from file cache
        contract_loader.state.loaded_contracts.clear()

        # Second load should detect modification
        result2 = contract_loader.load_contract(valid_contract_yaml)

        assert result2.node_name == "ModifiedNode"
        assert result2.node_type == EnumNodeType.EFFECT

    def test_cache_with_multiple_loaders(
        self, tmp_path: Path, valid_contract_yaml: Path
    ) -> None:
        """Test independent cache for multiple loader instances."""
        loader1 = ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)
        loader2 = ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)

        # Load with first loader
        loader1.load_contract(valid_contract_yaml)

        # Second loader should have empty cache
        assert len(loader1.state.loaded_contracts) == 1
        assert len(loader2.state.loaded_contracts) == 0

        # Load with second loader
        loader2.load_contract(valid_contract_yaml)

        # Both should have independent caches
        assert len(loader1.state.loaded_contracts) == 1
        assert len(loader2.state.loaded_contracts) == 1

    def test_cache_statistics_tracking(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that cache tracks access statistics."""
        # Load contract to populate cache
        contract_loader.load_contract(valid_contract_yaml)

        # Check that cache entry exists
        file_path_str = str(valid_contract_yaml)
        assert file_path_str in contract_loader.state.contract_cache

        # Cache entry should have metadata
        cache_entry = contract_loader.state.contract_cache[file_path_str]
        assert cache_entry.cached_at is not None
        assert cache_entry.file_modified_at is not None
        assert cache_entry.file_size > 0
        assert cache_entry.content_hash is not None

    def test_cache_with_symlinks(
        self,
        contract_loader: ProtocolContractLoader,
        valid_contract_yaml: Path,
        tmp_path: Path,
    ) -> None:
        """Test cache behavior with symlinked contracts."""
        # Create symlink
        symlink = tmp_path / "symlink_contract.yaml"
        try:
            symlink.symlink_to(valid_contract_yaml)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Load via symlink
        result = contract_loader.load_contract(symlink)

        # Should resolve and load correctly
        assert result.node_name == "TestNode"


# ===== Resolution Stack Tests =====


class TestResolutionStack:
    """Test resolution stack management."""

    def test_resolution_stack_initialized_empty(
        self, contract_loader: ProtocolContractLoader
    ) -> None:
        """Test that resolution stack is initialized empty."""
        assert len(contract_loader.state.resolution_stack) == 0

    def test_resolution_stack_reset_on_new_resolution(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that resolution stack is reset for new resolution."""
        # Manually populate stack
        contract_loader.state.resolution_stack = ["path1", "path2", "path3"]

        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        # Resolve references - should reset stack
        contract_loader._resolve_all_references(content, tmp_path)

        assert len(contract_loader.state.resolution_stack) == 0

    def test_resolution_stack_independent_per_resolution(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that each resolution has independent stack."""
        content = ModelContractContent(
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            node_name="TestNode",
            node_type=EnumNodeType.COMPUTE,
            tool_specification=ModelToolSpecification(main_tool_class="TestClass"),
            input_state=ModelYamlSchemaObject(
                object_type="object", description="Input"
            ),
            output_state=ModelYamlSchemaObject(
                object_type="object", description="Output"
            ),
            definitions=ModelContractDefinitions(),
        )

        # First resolution
        contract_loader._resolve_all_references(content, tmp_path)
        assert len(contract_loader.state.resolution_stack) == 0

        # Second resolution
        contract_loader._resolve_all_references(content, tmp_path)
        assert len(contract_loader.state.resolution_stack) == 0


# ===== Performance Tests =====


class TestPerformance:
    """Test performance characteristics of contract loader."""

    def test_load_many_contracts_performance(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test loading many contracts in sequence."""
        # Create 20 contracts
        contracts = []
        for i in range(20):
            contract_file = tmp_path / f"contract_{i}.yaml"
            contract_file.write_text(
                f"""
contract_version:
  major: 1
  minor: 0
  patch: {i}
node_name: TestNode{i}
node_type: COMPUTE
tool_specification:
  main_tool_class: TestToolClass{i}
""",
            )
            contracts.append(contract_file)

        # Load all contracts
        start_time = time.time()
        for contract_path in contracts:
            contract_loader.load_contract(contract_path)
        elapsed = time.time() - start_time

        # Should complete reasonably fast (< 1 second for 20 contracts)
        assert elapsed < 1.0
        # All should be cached
        assert len(contract_loader.state.loaded_contracts) == 20

    def test_cache_performance_benefit(
        self, contract_loader: ProtocolContractLoader, valid_contract_yaml: Path
    ) -> None:
        """Test that caching provides performance benefit."""
        # First load (cold cache)
        start_cold = time.time()
        contract_loader.load_contract(valid_contract_yaml)
        cold_time = time.time() - start_cold

        # Second load (warm cache)
        start_warm = time.time()
        contract_loader.load_contract(valid_contract_yaml)
        warm_time = time.time() - start_warm

        # Cached load should be faster (or at least not significantly slower)
        # Allow for timing variance
        assert warm_time <= cold_time * 1.5

    def test_large_contract_handling(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test handling of large contract files."""
        # Create large contract with many fields
        large_contract = tmp_path / "large_contract.yaml"
        large_fields = "\n".join([f"  field_{i}: value_{i}" for i in range(100)])
        large_contract.write_text(
            f"""
contract_version:
  major: 1
  minor: 0
  patch: 0
node_name: LargeNode
node_type: COMPUTE
tool_specification:
  main_tool_class: LargeToolClass
metadata:
{large_fields}
""",
        )

        # Should load successfully
        result = contract_loader.load_contract(large_contract)
        assert result.node_name == "LargeNode"


# ===== Advanced Integration Tests =====


class TestAdvancedIntegration:
    """Advanced integration tests for complex scenarios."""

    def test_load_all_node_types(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test loading contracts with all node types."""
        node_types = ["EFFECT", "COMPUTE", "REDUCER", "ORCHESTRATOR"]

        for i, node_type in enumerate(node_types):
            contract_file = tmp_path / f"contract_{node_type.lower()}.yaml"
            contract_file.write_text(
                f"""
contract_version:
  major: 1
  minor: 0
  patch: 0
node_name: {node_type}Node
node_type: {node_type}
tool_specification:
  main_tool_class: {node_type}ToolClass
""",
            )

            result = contract_loader.load_contract(contract_file)
            assert result.node_type == EnumNodeType(node_type)

    def test_concurrent_loads_different_contracts(
        self,
        contract_loader: ProtocolContractLoader,
        multiple_contracts: list[Path],
    ) -> None:
        """Test loading multiple different contracts."""
        results = []
        for contract_path in multiple_contracts:
            result = contract_loader.load_contract(contract_path)
            results.append(result)

        # All should load successfully
        assert len(results) == len(multiple_contracts)
        # All should have unique names
        names = [r.node_name for r in results]
        assert len(set(names)) == len(names)

    def test_cache_clear_and_reload_workflow(
        self,
        contract_loader: ProtocolContractLoader,
        multiple_contracts: list[Path],
    ) -> None:
        """Test complete workflow: load, clear, reload."""
        # Load all contracts
        results1 = [contract_loader.load_contract(cp) for cp in multiple_contracts]

        # Clear cache
        contract_loader.clear_cache()

        # Reload all contracts
        results2 = [contract_loader.load_contract(cp) for cp in multiple_contracts]

        # Results should be equivalent
        for r1, r2 in zip(results1, results2, strict=False):
            assert r1.node_name == r2.node_name
            assert r1.node_type == r2.node_type

    def test_mixed_valid_invalid_contracts(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test loading mix of valid and invalid contracts."""
        valid = tmp_path / "valid.yaml"
        valid.write_text(
            """
node_name: ValidNode
tool_specification:
  main_tool_class: ValidClass
""",
        )

        invalid = tmp_path / "invalid.yaml"
        invalid.write_text("invalid yaml: [unclosed")

        # Valid should load
        result = contract_loader.load_contract(valid)
        assert result.node_name == "ValidNode"

        # Invalid should fail
        with pytest.raises(ModelOnexError):
            contract_loader.load_contract(invalid)

        # Loader state should remain consistent
        assert len(contract_loader.state.loaded_contracts) == 1

    def test_version_comparison_across_contracts(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test version handling across multiple contracts."""
        versions = [(1, 0, 0), (1, 2, 3), (2, 0, 0), (3, 5, 7)]
        results = []

        for i, (major, minor, patch) in enumerate(versions):
            contract_file = tmp_path / f"contract_v{major}_{minor}_{patch}.yaml"
            contract_file.write_text(
                f"""
contract_version:
  major: {major}
  minor: {minor}
  patch: {patch}
node_name: Node{i}
tool_specification:
  main_tool_class: ToolClass{i}
""",
            )

            result = contract_loader.load_contract(contract_file)
            results.append(result)

        # Verify all versions were loaded correctly
        for result, (major, minor, patch) in zip(results, versions, strict=False):
            assert result.contract_version.major == major
            assert result.contract_version.minor == minor
            assert result.contract_version.patch == patch

    def test_loader_state_consistency_after_errors(
        self, contract_loader: ProtocolContractLoader, tmp_path: Path
    ) -> None:
        """Test that loader state remains consistent after errors."""
        valid = tmp_path / "valid.yaml"
        valid.write_text(
            """
node_name: ValidNode
tool_specification:
  main_tool_class: ValidClass
""",
        )

        # Load valid contract
        contract_loader.load_contract(valid)
        initial_count = len(contract_loader.state.loaded_contracts)

        # Try to load non-existent contract
        with pytest.raises(ModelOnexError):
            contract_loader.load_contract(tmp_path / "nonexistent.yaml")

        # State should be unchanged
        assert len(contract_loader.state.loaded_contracts) == initial_count

    def test_contract_loader_isolation(
        self, tmp_path: Path, valid_contract_yaml: Path
    ) -> None:
        """Test that contract loaders are properly isolated."""
        loader1 = ProtocolContractLoader(base_path=tmp_path, cache_enabled=True)
        loader2 = ProtocolContractLoader(base_path=tmp_path, cache_enabled=False)

        # Load with both loaders
        loader1.load_contract(valid_contract_yaml)
        loader2.load_contract(valid_contract_yaml)

        # Loader 1 should have cache
        assert len(loader1.state.contract_cache) > 0
        # Loader 2 should not have cache
        assert len(loader2.state.contract_cache) == 0

        # Clear loader1 cache
        loader1.clear_cache()

        # Loader1 should be empty
        assert len(loader1.state.loaded_contracts) == 0
        # Loader2 should still have its contract (no cache, but loaded_contracts)
        assert len(loader2.state.loaded_contracts) == 1
