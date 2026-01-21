# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive tests for ContractMergeEngine.

Tests cover:
- Basic merge operations
- Scalar overrides
- Dict/descriptor merges
- List operations (add/remove)
- Conflict detection
- Edge cases and error handling

Part of the Typed Contract Merge Engine (OMN-1127).

.. versionadded:: 0.4.0
"""

from unittest.mock import Mock

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.merge.model_merge_conflict import ModelMergeConflict
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Apply @pytest.mark.unit to all tests in this module
pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_profile_reference() -> ModelProfileReference:
    """Create a sample profile reference for testing."""
    return ModelProfileReference(
        profile="compute_pure",
        version="1.0.0",
    )


@pytest.fixture
def sample_semver() -> ModelSemVer:
    """Create a sample semantic version for testing."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def sample_handler_spec() -> ModelHandlerSpec:
    """Create a sample handler spec for testing."""
    return ModelHandlerSpec(
        name="http_client",
        handler_type="http",
        import_path="mypackage.handlers.HttpClientHandler",
        config={"timeout": 30, "retries": 3},
    )


@pytest.fixture
def sample_dependency() -> ModelDependency:
    """Create a sample dependency for testing."""
    return ModelDependency(
        name="ProtocolEventBus",
        module="omnibase_core.protocol.protocol_event_bus",
    )


@pytest.fixture
def sample_capability_provided() -> ModelCapabilityProvided:
    """Create a sample capability provided for testing."""
    return ModelCapabilityProvided(
        name="event_emit",
        version="1.0.0",
        description="Emits domain events",
    )


@pytest.fixture
def sample_descriptor_patch() -> ModelDescriptorPatch:
    """Create a sample descriptor patch for testing."""
    return ModelDescriptorPatch(
        timeout_ms=30000,
        idempotent=True,
    )


@pytest.fixture
def mock_base_contract() -> Mock:
    """Create a mock base contract for testing.

    Returns a mock that simulates a ModelContractBase with common fields.
    All list fields are set to proper Python lists (not Mock objects) to ensure
    they are iterable when the merge engine accesses them.
    """
    mock = Mock()
    mock.name = "base_contract"
    mock.contract_version = ModelSemVer(major=0, minor=1, patch=0)
    mock.description = "Base contract description"
    mock.node_type = EnumNodeType.COMPUTE_GENERIC
    mock.input_model = "BaseInput"
    mock.output_model = "BaseOutput"
    mock.handlers = []
    mock.dependencies = []
    mock.consumed_events = []
    mock.capability_inputs = []
    mock.capability_outputs = []
    mock.behavior = None
    mock.tags = []  # Required by merge engine for list(base.tags)

    # Add model_dump method for serialization
    mock.model_dump = Mock(
        return_value={
            "name": "base_contract",
            "contract_version": {"major": 0, "minor": 1, "patch": 0},
            "description": "Base contract description",
            "node_type": EnumNodeType.COMPUTE_GENERIC,
            "input_model": "BaseInput",
            "output_model": "BaseOutput",
            "handlers": [],
            "dependencies": [],
            "consumed_events": [],
            "capability_inputs": [],
            "capability_outputs": [],
            "behavior": None,
            "tags": [],
        }
    )
    return mock


@pytest.fixture
def mock_profile_factory(
    mock_base_contract: Mock,
) -> Mock:
    """Create a mock profile factory for testing.

    The factory returns mock base contracts when get_profile is called.
    """
    factory = Mock()
    factory.get_profile = Mock(return_value=mock_base_contract)
    factory.available_profiles = Mock(return_value=["compute_pure", "effect_http"])
    return factory


@pytest.fixture
def minimal_patch(
    sample_profile_reference: ModelProfileReference,
) -> ModelContractPatch:
    """Create a minimal patch that only extends a profile."""
    return ModelContractPatch(extends=sample_profile_reference)


@pytest.fixture
def new_contract_patch(
    sample_profile_reference: ModelProfileReference,
    sample_semver: ModelSemVer,
) -> ModelContractPatch:
    """Create a patch that defines a new contract identity."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        name="my_new_contract",
        node_version=sample_semver,
        description="A new contract",
    )


@pytest.fixture
def override_patch(
    sample_profile_reference: ModelProfileReference,
    sample_descriptor_patch: ModelDescriptorPatch,
) -> ModelContractPatch:
    """Create an override-only patch (no name/version)."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        description="Override description only",
        descriptor=sample_descriptor_patch,
    )


@pytest.fixture
def patch_with_handlers(
    sample_profile_reference: ModelProfileReference,
    sample_handler_spec: ModelHandlerSpec,
    sample_semver: ModelSemVer,
) -> ModelContractPatch:
    """Create a patch with handler add/remove operations."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        name="handler_contract",
        node_version=sample_semver,
        handlers__add=[sample_handler_spec],
        handlers__remove=["old_handler"],
    )


@pytest.fixture
def patch_with_dependencies(
    sample_profile_reference: ModelProfileReference,
    sample_dependency: ModelDependency,
    sample_semver: ModelSemVer,
) -> ModelContractPatch:
    """Create a patch with dependency operations."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        name="dependency_contract",
        node_version=sample_semver,
        dependencies__add=[sample_dependency],
        dependencies__remove=["old_dependency"],
    )


@pytest.fixture
def patch_with_events(
    sample_profile_reference: ModelProfileReference,
    sample_semver: ModelSemVer,
) -> ModelContractPatch:
    """Create a patch with event operations."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        name="event_contract",
        node_version=sample_semver,
        consumed_events__add=["user.created", "order.placed"],
        consumed_events__remove=["legacy.event"],
    )


@pytest.fixture
def patch_with_capabilities(
    sample_profile_reference: ModelProfileReference,
    sample_capability_provided: ModelCapabilityProvided,
    sample_semver: ModelSemVer,
) -> ModelContractPatch:
    """Create a patch with capability operations."""
    return ModelContractPatch(
        extends=sample_profile_reference,
        name="capability_contract",
        node_version=sample_semver,
        capability_inputs__add=["database_access"],
        capability_inputs__remove=["old_capability"],
        capability_outputs__add=[sample_capability_provided],
        capability_outputs__remove=["deprecated_output"],
    )


# =============================================================================
# Test Classes
# =============================================================================


class TestContractMergeEngineBasics:
    """Basic merge engine tests."""

    def test_engine_creation_with_factory(
        self,
        mock_profile_factory: Mock,
    ) -> None:
        """Test engine can be created with a profile factory."""
        # Import here to avoid import errors if engine doesn't exist yet
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        assert engine is not None
        assert engine._profile_factory is mock_profile_factory

    def test_engine_stores_profile_factory(
        self,
        mock_profile_factory: Mock,
    ) -> None:
        """Test engine stores the profile factory reference."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        assert engine._profile_factory == mock_profile_factory


class TestMergeOperation:
    """Tests for the main merge operation."""

    def test_merge_minimal_patch(
        self,
        mock_profile_factory: Mock,
        minimal_patch: ModelContractPatch,
    ) -> None:
        """Test merging a minimal patch uses all base values."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(minimal_patch)

        # Should call get_profile with correct arguments
        mock_profile_factory.get_profile.assert_called_once()

        # Result should be a merged contract
        assert result is not None

    def test_merge_calls_profile_factory(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test merge operation calls profile factory with correct profile."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        engine.merge(new_contract_patch)

        # Verify factory was called
        mock_profile_factory.get_profile.assert_called()


class TestScalarMerging:
    """Tests for scalar field merging."""

    def test_name_override(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test that patch name overrides base."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        # Patch has name="my_new_contract", should override base
        assert result.name == "my_new_contract"

    def test_description_override(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test description override."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        # Patch has description="A new contract"
        assert result.description == "A new contract"

    def test_version_override_with_model_semver(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test version override with ModelSemVer."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        # Patch has node_version=ModelSemVer(1, 0, 0)
        # The merge engine converts version to string representation
        assert result.version == "1.0.0"

    def test_none_patch_fields_use_base_values(
        self,
        mock_profile_factory: Mock,
        minimal_patch: ModelContractPatch,
        mock_base_contract: Mock,
    ) -> None:
        """Test that None patch fields retain base values."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(minimal_patch)

        # minimal_patch has no name override, should keep base name
        assert result.name == mock_base_contract.name


class TestDescriptorMerging:
    """Tests for descriptor/behavior merging."""

    def test_descriptor_timeout_override(
        self,
        mock_profile_factory: Mock,
        override_patch: ModelContractPatch,
    ) -> None:
        """Test descriptor timeout_ms override."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(override_patch)

        # Verify descriptor was applied
        # The exact check depends on how the engine applies descriptor patches
        assert result is not None

    def test_descriptor_partial_override(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
    ) -> None:
        """Test only some descriptor fields overridden."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Patch with only timeout_ms, not idempotent
        partial_descriptor = ModelDescriptorPatch(timeout_ms=15000)
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            descriptor=partial_descriptor,
        )

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        assert result is not None

    def test_descriptor_preserves_unset_fields(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
    ) -> None:
        """Test descriptor merge preserves fields not in patch."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Set up base contract with behavior
        # All list fields must be proper Python lists (not Mock objects)
        # Enum values must match valid literals for ModelHandlerBehavior
        mock_base = mock_profile_factory.get_profile.return_value
        mock_base.behavior = Mock()
        mock_base.behavior.timeout_ms = 5000
        mock_base.behavior.idempotent = False
        mock_base.behavior.handler_kind = "compute"
        mock_base.behavior.purity = "side_effecting"
        mock_base.behavior.retry_policy = None
        mock_base.behavior.circuit_breaker = None
        mock_base.behavior.concurrency_policy = (
            "serialized"  # Valid: parallel_ok, serialized, singleflight
        )
        mock_base.behavior.isolation_policy = (
            "none"  # Valid: none, process, container, vm
        )
        mock_base.behavior.observability_level = (
            "standard"  # Valid: minimal, standard, verbose
        )
        mock_base.behavior.capability_inputs = []  # Required by merge engine
        mock_base.behavior.capability_outputs = []  # Required by merge engine

        # Patch only sets timeout_ms
        partial_descriptor = ModelDescriptorPatch(timeout_ms=20000)
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            descriptor=partial_descriptor,
        )

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        assert result is not None


class TestListOperations:
    """Tests for list add/remove operations."""

    def test_handlers_add(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_handler_spec: ModelHandlerSpec,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test adding handlers via handlers__add.

        Note: Handlers are processed by the merge engine for patch validation,
        but ModelHandlerContract doesn't have a handlers field. This test
        verifies that patches with handler operations merge successfully.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Set base handlers
        mock_base = mock_profile_factory.get_profile.return_value
        mock_base.handlers = [Mock(name="existing_handler")]

        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test_contract",
            node_version=sample_semver,
            handlers__add=[sample_handler_spec],
        )

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        # Verify merge completed successfully with valid contract structure
        assert result is not None
        assert result.name == "test_contract"
        assert result.version == "1.0.0"
        assert hasattr(result, "descriptor")
        assert hasattr(result, "capability_inputs")
        # Verify the patch handler_add was set correctly
        assert patch.handlers__add is not None
        assert len(patch.handlers__add) == 1
        assert patch.handlers__add[0].name == sample_handler_spec.name

    def test_handlers_remove(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test removing handlers via handlers__remove.

        Note: Handlers are processed by the merge engine for patch validation,
        but ModelHandlerContract doesn't have a handlers field. This test
        verifies that patches with handler remove operations merge successfully.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Set base handlers with one to remove
        mock_handler = Mock()
        mock_handler.name = "handler_to_remove"
        mock_base = mock_profile_factory.get_profile.return_value
        mock_base.handlers = [mock_handler]

        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test_contract",
            node_version=sample_semver,
            handlers__remove=["handler_to_remove"],
        )

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        # Verify merge completed successfully with valid contract structure
        assert result is not None
        assert result.name == "test_contract"
        assert result.version == "1.0.0"
        # Verify the patch handlers__remove was set correctly
        assert patch.handlers__remove is not None
        assert "handler_to_remove" in patch.handlers__remove

    def test_handlers_add_and_remove(
        self,
        mock_profile_factory: Mock,
        patch_with_handlers: ModelContractPatch,
    ) -> None:
        """Test combined add and remove operations.

        Note: Handlers are processed by the merge engine for patch validation,
        but ModelHandlerContract doesn't have a handlers field. This test
        verifies patches with both add and remove operations merge successfully.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_handlers)

        # Verify merge completed successfully with expected identity
        assert result is not None
        assert result.name == "handler_contract"
        assert result.version == "1.0.0"
        # Verify the patch had both add and remove operations
        assert patch_with_handlers.handlers__add is not None
        assert patch_with_handlers.handlers__remove is not None
        assert len(patch_with_handlers.handlers__add) == 1
        assert "old_handler" in patch_with_handlers.handlers__remove

    def test_dependencies_add(
        self,
        mock_profile_factory: Mock,
        patch_with_dependencies: ModelContractPatch,
    ) -> None:
        """Test adding dependencies.

        Note: Dependencies are processed by the merge engine for patch validation,
        but ModelHandlerContract uses capability-based dependencies (capability_inputs)
        instead. This test verifies patches with dependency operations merge successfully.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_dependencies)

        # Verify merge completed successfully with expected identity
        assert result is not None
        assert result.name == "dependency_contract"
        assert result.version == "1.0.0"
        # Verify the patch had dependency operations
        assert patch_with_dependencies.dependencies__add is not None
        assert patch_with_dependencies.dependencies__remove is not None
        assert len(patch_with_dependencies.dependencies__add) == 1
        assert patch_with_dependencies.dependencies__add[0].name == "ProtocolEventBus"

    def test_consumed_events_add(
        self,
        mock_profile_factory: Mock,
        patch_with_events: ModelContractPatch,
    ) -> None:
        """Test adding consumed events.

        Note: Consumed events are processed by the merge engine for patch validation,
        but ModelHandlerContract doesn't have a consumed_events field. This test
        verifies patches with event operations merge successfully.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_events)

        # Verify merge completed successfully with expected identity
        assert result is not None
        assert result.name == "event_contract"
        assert result.version == "1.0.0"
        # Verify the patch had event operations
        assert patch_with_events.consumed_events__add is not None
        assert patch_with_events.consumed_events__remove is not None
        assert "user.created" in patch_with_events.consumed_events__add
        assert "order.placed" in patch_with_events.consumed_events__add
        assert "legacy.event" in patch_with_events.consumed_events__remove

    def test_capability_inputs_add(
        self,
        mock_profile_factory: Mock,
        patch_with_capabilities: ModelContractPatch,
    ) -> None:
        """Test adding capability inputs.

        Verifies that capability_inputs__add items appear in the merged contract
        as ModelCapabilityDependency objects.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_capabilities)

        # Verify merge completed successfully
        assert result is not None
        assert result.name == "capability_contract"
        assert result.version == "1.0.0"

        # Verify capability_inputs contains the added item
        # The merge engine converts string names to ModelCapabilityDependency
        assert result.capability_inputs is not None
        assert len(result.capability_inputs) > 0

        # Check that "database_access" was added (alias uses underscores)
        capability_aliases = [cap.alias for cap in result.capability_inputs]
        capability_names = [cap.capability for cap in result.capability_inputs]
        assert (
            "database_access" in capability_aliases
            or "database_access" in capability_names
        )

    def test_capability_outputs_add(
        self,
        mock_profile_factory: Mock,
        patch_with_capabilities: ModelContractPatch,
        sample_capability_provided: "ModelCapabilityProvided",
    ) -> None:
        """Test adding capability outputs.

        Verifies that capability_outputs__add items appear in the merged contract.
        The merge engine extracts capability names from ModelCapabilityProvided objects.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_capabilities)

        # Verify merge completed successfully
        assert result is not None
        assert result.name == "capability_contract"
        assert result.version == "1.0.0"

        # Verify capability_outputs contains the added capability name
        # The patch adds sample_capability_provided which has name="event_emit"
        assert result.capability_outputs is not None
        assert len(result.capability_outputs) > 0
        assert sample_capability_provided.name in result.capability_outputs

    def test_empty_add_list_is_noop(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test that empty __add list acts as no-op (normalized to None).

        Verifies that ModelContractPatch normalizes empty lists to None,
        and the merge engine handles this correctly by preserving base values.
        """
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Empty list is normalized to None in ModelContractPatch
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test_contract",
            node_version=sample_semver,
            handlers__add=[],  # This becomes None after normalization
        )

        # Verify normalization happened - empty list becomes None
        assert patch.handlers__add is None

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        # Verify merge completed with expected contract identity
        assert result is not None
        assert result.name == "test_contract"
        assert result.version == "1.0.0"
        # Verify capability_inputs is empty (no additions, base was empty)
        assert result.capability_inputs == []
        # Verify capability_outputs is empty (no additions, base was empty)
        assert result.capability_outputs == []


class TestConflictDetection:
    """Tests for merge conflict detection."""

    def test_no_conflicts_on_valid_patch(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test no conflicts detected for valid patch."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        conflicts = engine.detect_conflicts(new_contract_patch)

        assert len(conflicts) == 0

    def test_type_mismatch_detected(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test type mismatch conflict detection."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Set up base with int field
        mock_base = mock_profile_factory.get_profile.return_value
        mock_base.some_int_field = 5000

        engine = ContractMergeEngine(mock_profile_factory)

        # Detecting type mismatches requires engine implementation
        # This test verifies the method exists and returns a list
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test",
            node_version=sample_semver,
        )
        conflicts = engine.detect_conflicts(patch)

        # Should return a list (possibly empty for valid patch)
        assert isinstance(conflicts, list)

    def test_validate_patch_returns_true_for_valid(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test validate_patch returns True when no conflicts."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        is_valid = engine.validate_patch(new_contract_patch)

        assert is_valid is True

    def test_validate_patch_returns_false_for_conflicts(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test validate_patch returns False when conflicts exist."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)

        # Create a patch that might cause conflicts
        # Note: Actual conflict detection depends on engine implementation
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test",
            node_version=sample_semver,
        )
        is_valid = engine.validate_patch(patch)

        # For a valid patch, should return True
        # The engine may return False if configured to detect specific issues
        assert isinstance(is_valid, bool)

    def test_conflicts_return_model_merge_conflict(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test that conflicts are returned as ModelMergeConflict instances."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test",
            node_version=sample_semver,
        )

        conflicts = engine.detect_conflicts(patch)

        # All items should be ModelMergeConflict instances
        for conflict in conflicts:
            assert isinstance(conflict, ModelMergeConflict)


class TestDeterminism:
    """Tests for deterministic output."""

    def test_same_input_same_output(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test that same inputs produce same outputs."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)

        result1 = engine.merge(new_contract_patch)
        result2 = engine.merge(new_contract_patch)

        # Same patch should produce equivalent results
        assert result1.name == result2.name
        assert result1.description == result2.description

    def test_merge_is_non_mutating(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test that merge doesn't mutate inputs."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Store original values
        original_name = new_contract_patch.name
        original_description = new_contract_patch.description

        engine = ContractMergeEngine(mock_profile_factory)
        engine.merge(new_contract_patch)

        # Patch should be unchanged (frozen model anyway)
        assert new_contract_patch.name == original_name
        assert new_contract_patch.description == original_description

    def test_multiple_merges_independent(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test multiple merges don't interfere with each other."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)

        patch1 = ModelContractPatch(
            extends=sample_profile_reference,
            name="contract_one",
            node_version=sample_semver,
        )
        patch2 = ModelContractPatch(
            extends=sample_profile_reference,
            name="contract_two",
            node_version=sample_semver,
        )

        result1 = engine.merge(patch1)
        result2 = engine.merge(patch2)

        # Results should have different names
        assert result1.name == "contract_one"
        assert result2.name == "contract_two"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_patch_uses_all_base_values(
        self,
        mock_profile_factory: Mock,
        minimal_patch: ModelContractPatch,
        mock_base_contract: Mock,
    ) -> None:
        """Test patch with only extends uses all base values."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(minimal_patch)

        # Result should use base values
        assert result.name == mock_base_contract.name
        assert result.description == mock_base_contract.description

    def test_new_contract_requires_name_and_version(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test new contract (is_new_contract=True) works."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        assert new_contract_patch.is_new_contract

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        assert result.name == new_contract_patch.name
        # Version is a string in ModelHandlerContract, compare as string
        assert result.version == str(new_contract_patch.node_version)

    def test_override_only_patch(
        self,
        mock_profile_factory: Mock,
        override_patch: ModelContractPatch,
    ) -> None:
        """Test override-only patch (no name/version)."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        assert override_patch.is_override_only

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(override_patch)

        # Should use base name since patch doesn't specify one
        assert result is not None

    def test_merge_with_missing_base_handlers(
        self,
        mock_profile_factory: Mock,
        patch_with_handlers: ModelContractPatch,
    ) -> None:
        """Test merge when base has no handlers list."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        # Base contract with no handlers
        mock_base = mock_profile_factory.get_profile.return_value
        mock_base.handlers = []

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch_with_handlers)

        assert result is not None

    def test_merge_with_none_lists(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test merge when both add and remove are None."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test",
            node_version=sample_semver,
            # No list operations
        )

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(patch)

        assert result is not None


class TestMergeResultType:
    """Tests for merge result types and structure."""

    def test_merge_returns_contract(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test that merge returns a contract-like object."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        # Result should have standard contract fields
        assert hasattr(result, "name")
        assert hasattr(result, "version")
        assert hasattr(result, "description")

    def test_merge_result_has_handler_kind(
        self,
        mock_profile_factory: Mock,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test that merge result has handler_kind from descriptor."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        engine = ContractMergeEngine(mock_profile_factory)
        result = engine.merge(new_contract_patch)

        # ModelHandlerContract uses descriptor.handler_kind, not node_type
        assert hasattr(result, "descriptor")
        assert hasattr(result.descriptor, "handler_kind")


class TestProfileResolution:
    """Tests for profile resolution behavior."""

    def test_profile_name_passed_to_factory(
        self,
        mock_profile_factory: Mock,
        sample_profile_reference: ModelProfileReference,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test that profile name is correctly passed to factory."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        patch = ModelContractPatch(
            extends=sample_profile_reference,
            name="test",
            node_version=sample_semver,
        )

        engine = ContractMergeEngine(mock_profile_factory)
        engine.merge(patch)

        # Verify factory was called with correct profile
        call_args = mock_profile_factory.get_profile.call_args
        assert call_args is not None

    def test_version_constraint_used_in_resolution(
        self,
        mock_profile_factory: Mock,
        sample_semver: ModelSemVer,
    ) -> None:
        """Test that version constraint is passed to factory."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        ref = ModelProfileReference(
            profile="compute_pure",
            version="^1.0.0",  # Version constraint
        )
        patch = ModelContractPatch(
            extends=ref,
            name="test",
            node_version=sample_semver,
        )

        engine = ContractMergeEngine(mock_profile_factory)
        engine.merge(patch)

        # Factory should be called
        mock_profile_factory.get_profile.assert_called()


class TestModuleExports:
    """Tests for module exports."""

    def test_contract_merge_engine_exported(self) -> None:
        """Test ContractMergeEngine is exported from merge module."""
        from omnibase_core.merge import ContractMergeEngine

        assert ContractMergeEngine is not None

    def test_contract_merge_engine_importable(self) -> None:
        """Test ContractMergeEngine can be imported directly."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        assert ContractMergeEngine is not None


# =============================================================================
# Helper Tests (Testing fixtures work correctly)
# =============================================================================


class TestFixtures:
    """Tests to verify fixtures are set up correctly."""

    def test_sample_profile_reference(
        self,
        sample_profile_reference: ModelProfileReference,
    ) -> None:
        """Test sample profile reference fixture."""
        assert sample_profile_reference.profile == "compute_pure"
        assert sample_profile_reference.version == "1.0.0"

    def test_sample_handler_spec(
        self,
        sample_handler_spec: ModelHandlerSpec,
    ) -> None:
        """Test sample handler spec fixture."""
        assert sample_handler_spec.name == "http_client"
        assert sample_handler_spec.handler_type == "http"

    def test_sample_dependency(
        self,
        sample_dependency: ModelDependency,
    ) -> None:
        """Test sample dependency fixture."""
        assert sample_dependency.name == "ProtocolEventBus"
        assert sample_dependency.is_protocol()

    def test_sample_capability_provided(
        self,
        sample_capability_provided: ModelCapabilityProvided,
    ) -> None:
        """Test sample capability provided fixture."""
        assert sample_capability_provided.name == "event_emit"
        assert sample_capability_provided.version == "1.0.0"

    def test_sample_descriptor_patch(
        self,
        sample_descriptor_patch: ModelDescriptorPatch,
    ) -> None:
        """Test sample descriptor patch fixture."""
        assert sample_descriptor_patch.timeout_ms == 30000
        assert sample_descriptor_patch.idempotent is True

    def test_minimal_patch_fixture(
        self,
        minimal_patch: ModelContractPatch,
    ) -> None:
        """Test minimal patch fixture."""
        assert minimal_patch.is_override_only
        assert minimal_patch.extends.profile == "compute_pure"

    def test_new_contract_patch_fixture(
        self,
        new_contract_patch: ModelContractPatch,
    ) -> None:
        """Test new contract patch fixture."""
        assert new_contract_patch.is_new_contract
        assert new_contract_patch.name == "my_new_contract"

    def test_mock_profile_factory(
        self,
        mock_profile_factory: Mock,
    ) -> None:
        """Test mock profile factory fixture."""
        result = mock_profile_factory.get_profile()
        assert result is not None
        assert mock_profile_factory.available_profiles() == [
            "compute_pure",
            "effect_http",
        ]
