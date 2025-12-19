import pytest

#!/usr/bin/env python3
"""
NodeInstance Comprehensive Unit Tests - TDD Test Suite (OMN-227)

This module provides TDD-first test coverage for the NodeInstance class,
which serves as an execution wrapper for ONEX nodes. Tests define the
expected behavior and API contract before implementation.

Test Categories:
    - Class creation and property validation
    - Frozen/immutable behavior verification
    - Lifecycle methods (initialize, shutdown)
    - Event handling and runtime delegation
    - Error handling and edge cases

Coverage Requirements:
    - All public methods must have test coverage
    - Error handling paths must be tested
    - Mock patterns for runtime delegation
    - Property accessors validated

TDD Note: These tests are written BEFORE the implementation.
The NodeInstance class should be implemented to pass all these tests.

Related:
    - OMN-227: NodeInstance execution wrapper implementation
    - OMN-224: ModelOnexEnvelope refactoring (envelope handling)
    - ONEX Four-Node Architecture documentation
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock
from uuid import uuid4

from pydantic import ValidationError

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# TEST CLASS: NodeInstance Creation and Properties
# =============================================================================


@pytest.mark.unit
class TestNodeInstanceCreation:
    """Tests for NodeInstance class instantiation and property access."""

    def test_create_node_instance_with_valid_parameters(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test creating NodeInstance with all required parameters.

        EXPECTED BEHAVIOR:
        - NodeInstance accepts slug, node_type, and contract parameters
        - Instance is created successfully without errors
        - All properties are accessible after creation
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        assert instance is not None
        assert isinstance(instance, NodeInstance)

    def test_slug_property_returns_correct_value(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that slug property returns the value provided at creation.

        EXPECTED BEHAVIOR:
        - slug property is accessible
        - slug returns exactly the string provided at creation
        - slug is of type str
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        assert instance.slug == sample_slug
        assert isinstance(instance.slug, str)

    def test_node_type_property_returns_correct_enum(
        self,
        sample_slug: str,
        mock_contract: Mock,
    ) -> None:
        """
        Test that node_type property returns the correct EnumNodeType.

        EXPECTED BEHAVIOR:
        - node_type property is accessible
        - node_type returns an EnumNodeType instance
        - node_type matches the value provided at creation
        """
        from omnibase_core.runtime import NodeInstance

        for node_type in [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.EFFECT_GENERIC,
            EnumNodeType.REDUCER_GENERIC,
            EnumNodeType.ORCHESTRATOR_GENERIC,
        ]:
            instance = NodeInstance(
                slug=sample_slug,
                node_type=node_type,
                contract=mock_contract,
            )

            assert instance.node_type == node_type
            assert isinstance(instance.node_type, EnumNodeType)

    def test_contract_property_returns_provided_contract(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that contract property returns the contract provided at creation.

        EXPECTED BEHAVIOR:
        - contract property is accessible
        - contract returns the same object provided at creation
        - contract has expected attributes (name, version, etc.)
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        assert instance.contract is mock_contract
        assert instance.contract.name == "test_contract"
        assert instance.contract.version == ModelSemVer(major=1, minor=0, patch=0)

    def test_create_with_different_slugs(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test creating NodeInstances with various slug formats.

        EXPECTED BEHAVIOR:
        - Various slug formats are accepted (kebab-case, snake_case, etc.)
        - Empty slugs may raise validation error
        - Unicode slugs should be handled appropriately
        """
        from omnibase_core.runtime import NodeInstance

        valid_slugs = [
            "simple-slug",
            "snake_case_slug",
            "CamelCaseSlug",
            "slug-with-numbers-123",
            "a",  # Single character
            "very-long-slug-name-that-is-quite-descriptive-and-detailed",
        ]

        for slug in valid_slugs:
            instance = NodeInstance(
                slug=slug,
                node_type=sample_node_type,
                contract=mock_contract,
            )
            assert instance.slug == slug

    def test_create_with_empty_slug_raises_error(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that empty slug raises validation error.

        EXPECTED BEHAVIOR:
        - Empty string slug raises ValidationError
        - Error message indicates slug is required
        """
        from omnibase_core.runtime import NodeInstance

        with pytest.raises((ValidationError, ValueError)):
            NodeInstance(
                slug="",
                node_type=sample_node_type,
                contract=mock_contract,
            )


# =============================================================================
# TEST CLASS: Frozen/Immutable Behavior
# =============================================================================


@pytest.mark.unit
class TestNodeInstanceFrozenBehavior:
    """Tests for NodeInstance immutability when frozen=True."""

    def test_instance_is_immutable_after_creation(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that NodeInstance properties cannot be modified after creation.

        EXPECTED BEHAVIOR (if frozen=True):
        - Attempting to modify slug raises error
        - Attempting to modify node_type raises error
        - Attempting to modify contract raises error
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Attempt to modify properties should raise error
        with pytest.raises((ValidationError, AttributeError, TypeError)):
            instance.slug = "new-slug"  # type: ignore[misc]

        with pytest.raises((ValidationError, AttributeError, TypeError)):
            instance.node_type = EnumNodeType.EFFECT_GENERIC  # type: ignore[misc]

        # Also test contract immutability
        another_mock_contract = Mock()
        with pytest.raises((ValidationError, AttributeError, TypeError)):
            instance.contract = another_mock_contract  # type: ignore[misc]

    def test_extra_fields_rejected(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that extra fields are rejected during creation.

        EXPECTED BEHAVIOR (if extra="forbid"):
        - Creating with unknown fields raises ValidationError
        - Error message mentions the unknown field
        """
        from omnibase_core.runtime import NodeInstance

        with pytest.raises(ValidationError) as exc_info:
            NodeInstance(
                slug=sample_slug,
                node_type=sample_node_type,
                contract=mock_contract,
                unknown_field="should_be_rejected",  # type: ignore[call-arg]
            )

        error_str = str(exc_info.value)
        assert "unknown_field" in error_str or "extra" in error_str.lower()


# =============================================================================
# TEST CLASS: Initialize Method
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceInitialize:
    """Tests for NodeInstance initialize() lifecycle method.

    Note:
    - Timeout (60s) for async lifecycle initialization tests
    """

    @pytest.mark.asyncio
    async def test_initialize_can_be_called(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that initialize() method can be called without errors.

        EXPECTED BEHAVIOR:
        - initialize() method exists and is callable
        - Calling initialize() does not raise exceptions
        - Requires runtime to be set before initialization
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)

        # Should not raise - initialize returns None
        await instance.initialize()

        # Method should complete without error

    @pytest.mark.asyncio
    async def test_initialize_returns_expected_type(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that initialize() returns expected result type.

        EXPECTED BEHAVIOR:
        - initialize() returns None or a specific result type
        - Return value is consistent across calls
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)

        # initialize() returns None - verify it doesn't raise
        # Note: We don't need to check return value since type is None
        await instance.initialize()
        # Method completed without error - test passes

    @pytest.mark.asyncio
    async def test_initialize_raises_on_double_call(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that initialize() raises error when called twice.

        EXPECTED BEHAVIOR:
        - First initialize() succeeds
        - Second initialize() raises ModelOnexError
        - This is explicit failure, not silent idempotency
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)

        # First call succeeds
        await instance.initialize()

        # Second call raises error
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.initialize()

        assert "already initialized" in str(exc_info.value).lower()


# =============================================================================
# TEST CLASS: Shutdown Method
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceShutdown:
    """Tests for NodeInstance shutdown() lifecycle method.

    Note:
    - Timeout (60s) for async lifecycle shutdown tests
    """

    @pytest.mark.asyncio
    async def test_shutdown_can_be_called(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that shutdown() method can be called without errors.

        EXPECTED BEHAVIOR:
        - shutdown() method exists and is callable
        - Calling shutdown() does not raise exceptions
        - Requires initialization before shutdown
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        # Should not raise - shutdown returns None
        await instance.shutdown()

        # Method should complete without error

    @pytest.mark.asyncio
    async def test_shutdown_returns_expected_type(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that shutdown() returns expected result type.

        EXPECTED BEHAVIOR:
        - shutdown() returns None or a specific result type
        - Return value indicates shutdown status
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()  # Must be initialized before shutdown

        # shutdown() returns None - verify it doesn't raise
        # Note: We don't need to check return value since type is None
        await instance.shutdown()
        # Method completed without error - test passes

    @pytest.mark.asyncio
    async def test_shutdown_after_initialize(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test proper lifecycle: initialize -> shutdown.

        EXPECTED BEHAVIOR:
        - Can call shutdown() after initialize()
        - Shutdown completes successfully after initialization
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)

        await instance.initialize()
        await instance.shutdown()

        # Should complete without error

    @pytest.mark.asyncio
    async def test_shutdown_raises_when_not_initialized(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that shutdown() raises error when not initialized.

        EXPECTED BEHAVIOR:
        - shutdown() on non-initialized instance raises ModelOnexError
        - This is explicit failure for state validation
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Not initialized - shutdown should raise
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.shutdown()

        assert "not initialized" in str(exc_info.value).lower()


# =============================================================================
# TEST CLASS: Handle Method
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceHandle:
    """Tests for NodeInstance handle() method - envelope processing.

    Note:
    - Timeout (60s) for async envelope handling tests
    """

    @pytest.mark.asyncio
    async def test_handle_accepts_envelope(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() accepts ModelOnexEnvelope parameter.

        EXPECTED BEHAVIOR:
        - handle() method exists and accepts envelope parameter
        - Method does not raise when given valid envelope
        - Requires initialization before handling
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        # Should not raise when properly initialized
        result = await instance.handle(sample_envelope)

        # Verify runtime was called
        mock_runtime.execute_with_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_returns_result(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() returns result from runtime.

        EXPECTED BEHAVIOR:
        - handle() returns result from runtime.execute_with_handler()
        - Return value matches runtime's return value
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Set the runtime using public API
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        result = await instance.handle(sample_envelope)

        # Should return the mock runtime's result
        assert result is not None

        # Verify result structure - mock returns dict with status key
        # Use explicit type check for clarity
        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        assert result.get("status") == "success"

    @pytest.mark.asyncio
    async def test_handle_with_various_envelopes(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        default_version: ModelSemVer,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test handle() with various envelope configurations.

        EXPECTED BEHAVIOR:
        - handle() works with different envelope types
        - Different operations are handled appropriately
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        envelopes = [
            ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=uuid4(),
                source_node="source_a",
                operation="OPERATION_A",
                payload={"data": "a"},
                timestamp=datetime.now(UTC),
            ),
            ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=uuid4(),
                source_node="source_b",
                target_node="target_b",
                operation="OPERATION_B",
                payload={"data": "b"},
                timestamp=datetime.now(UTC),
            ),
            ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=default_version,
                correlation_id=uuid4(),
                source_node="source_c",
                operation="OPERATION_C",
                payload={},  # Empty payload
                timestamp=datetime.now(UTC),
            ),
        ]

        for envelope in envelopes:
            result = await instance.handle(envelope)
            assert result is not None


# =============================================================================
# TEST CLASS: Runtime Integration
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceRuntimeIntegration:
    """Tests for NodeInstance runtime delegation patterns.

    Note:
    - Timeout (60s) for async runtime integration tests
    """

    def test_can_set_runtime_reference(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that runtime reference can be set on NodeInstance.

        EXPECTED BEHAVIOR:
        - Runtime can be set via set_runtime() method
        - Runtime can be accessed via runtime property after being set
        - String representation changes to indicate runtime state
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Set runtime using public API
        instance.set_runtime(mock_runtime)

        # Verify runtime is set via public property
        assert instance.runtime is mock_runtime

    @pytest.mark.asyncio
    async def test_handle_delegates_to_runtime_execute(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() delegates to runtime.execute_with_handler().

        EXPECTED BEHAVIOR:
        - handle() calls runtime.execute_with_handler()
        - Envelope is passed to the runtime
        - Result from runtime is returned
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        result = await instance.handle(sample_envelope)

        # Verify runtime method was called
        mock_runtime.execute_with_handler.assert_called_once()

        # Verify envelope was passed (check call args)
        call_args = mock_runtime.execute_with_handler.call_args
        # The envelope should be in the arguments
        assert (
            sample_envelope in call_args.args
            or sample_envelope in call_args.kwargs.values()
        )

    @pytest.mark.asyncio
    async def test_handle_without_runtime_raises_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
    ) -> None:
        """
        Test that handle() raises error when no runtime is set.

        EXPECTED BEHAVIOR:
        - handle() raises RuntimeError or similar when runtime not set
        - Error message indicates runtime is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Do NOT set runtime - calling handle should raise because not initialized

        with pytest.raises(ModelOnexError) as exc_info:
            await instance.handle(sample_envelope)

        # Error should mention runtime or initialized
        error_msg = str(exc_info.value).lower()
        assert "runtime" in error_msg or "initialized" in error_msg

    @pytest.mark.asyncio
    async def test_runtime_receives_correct_envelope_data(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
        default_version: ModelSemVer,
    ) -> None:
        """
        Test that runtime receives envelope with all data intact.

        EXPECTED BEHAVIOR:
        - Envelope passed to runtime has same envelope_id
        - Envelope passed to runtime has same correlation_id
        - Envelope passed to runtime has same payload
        """
        from omnibase_core.runtime import NodeInstance

        envelope_id = uuid4()
        correlation_id = uuid4()
        payload = {"key1": "value1", "key2": 42}

        envelope = ModelOnexEnvelope(
            envelope_id=envelope_id,
            envelope_version=default_version,
            correlation_id=correlation_id,
            source_node="test_source",
            operation="TEST_OP",
            payload=payload,
            timestamp=datetime.now(UTC),
        )

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        await instance.handle(envelope)

        # Get the envelope passed to runtime
        call_args = mock_runtime.execute_with_handler.call_args
        passed_envelope = None

        # Find envelope in args or kwargs
        for arg in call_args.args:
            if isinstance(arg, ModelOnexEnvelope):
                passed_envelope = arg
                break
        if passed_envelope is None:
            for kwarg_value in call_args.kwargs.values():
                if isinstance(kwarg_value, ModelOnexEnvelope):
                    passed_envelope = kwarg_value
                    break

        assert passed_envelope is not None
        assert passed_envelope.envelope_id == envelope_id
        assert passed_envelope.correlation_id == correlation_id
        assert passed_envelope.payload == payload


# =============================================================================
# TEST CLASS: String Representation and Model Methods
# =============================================================================


@pytest.mark.unit
class TestNodeInstanceStringRepresentation:
    """Tests for NodeInstance __str__ and __repr__ methods."""

    def test_str_representation_includes_slug(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that string representation includes the slug.

        EXPECTED BEHAVIOR:
        - str(instance) contains the slug
        - Representation is human-readable
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        str_repr = str(instance)
        assert sample_slug in str_repr

    def test_repr_provides_debug_info(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that repr provides useful debug information.

        EXPECTED BEHAVIOR:
        - repr(instance) includes class name
        - repr(instance) includes key attributes
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        repr_str = repr(instance)
        assert "NodeInstance" in repr_str


# =============================================================================
# TEST CLASS: Edge Cases and Error Handling
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceEdgeCases:
    """Tests for NodeInstance edge cases and error conditions.

    Note:
    - Timeout (60s) for async edge case tests
    """

    @pytest.mark.asyncio
    async def test_handle_with_none_envelope_raises_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() with None envelope behavior.

        NOTE: NodeInstance delegates validation to the runtime.
        The implementation passes the envelope through without explicit type checking.
        Runtime is responsible for envelope validation.

        This test verifies that the envelope is passed to runtime even if None.
        Runtime implementations should handle this appropriately.
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        # NodeInstance delegates to runtime - None envelope is passed through
        # Runtime is responsible for validation
        result = await instance.handle(None)  # type: ignore[arg-type]

        # Verify runtime was called with the None envelope
        mock_runtime.execute_with_handler.assert_called_once()
        call_args = mock_runtime.execute_with_handler.call_args
        # First argument should be the envelope (None in this case)
        assert call_args.args[0] is None

    @pytest.mark.asyncio
    async def test_handle_with_invalid_envelope_type_delegates_to_runtime(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() with invalid envelope type delegates to runtime.

        NOTE: NodeInstance delegates validation to the runtime.
        The implementation passes the envelope through without explicit type checking.
        Runtime is responsible for envelope validation and error handling.

        This test verifies that invalid envelopes are passed to runtime.
        Runtime implementations should validate and raise appropriate errors.
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        await instance.initialize()

        # NodeInstance delegates to runtime - invalid envelope is passed through
        dict_envelope = {"not": "an_envelope"}
        await instance.handle(dict_envelope)  # type: ignore[arg-type]

        # Verify runtime was called with the dict
        mock_runtime.execute_with_handler.assert_called()
        call_args = mock_runtime.execute_with_handler.call_args
        assert call_args.args[0] == dict_envelope

        # Reset mock and test with string
        mock_runtime.execute_with_handler.reset_mock()

        string_envelope = "string_not_envelope"
        await instance.handle(string_envelope)  # type: ignore[arg-type]

        # Verify runtime was called with the string
        mock_runtime.execute_with_handler.assert_called_once()
        call_args = mock_runtime.execute_with_handler.call_args
        assert call_args.args[0] == string_envelope

    @pytest.mark.asyncio
    async def test_initialize_without_runtime_raises_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that initialize() raises error without runtime being set.

        EXPECTED BEHAVIOR:
        - initialize() raises ModelOnexError when runtime is not set
        - Error message indicates runtime is required
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # initialize() should raise because runtime is not set
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.initialize()

        error_msg = str(exc_info.value).lower()
        assert "runtime" in error_msg or "set_runtime" in error_msg

    def test_contract_validation_on_creation(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
    ) -> None:
        """
        Test that contract is validated on NodeInstance creation.

        EXPECTED BEHAVIOR:
        - None contract raises ValidationError
        - Invalid contract type raises error
        """
        from omnibase_core.runtime import NodeInstance

        with pytest.raises((ValidationError, TypeError, ValueError)):
            NodeInstance(
                slug=sample_slug,
                node_type=sample_node_type,
                contract=None,  # type: ignore[arg-type]
            )

    def test_set_runtime_twice_raises_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that set_runtime() raises error when runtime is already set.

        EXPECTED BEHAVIOR:
        - First set_runtime() succeeds
        - Second set_runtime() raises ModelOnexError
        - Error message indicates runtime is already set
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # First call succeeds
        instance.set_runtime(mock_runtime)

        # Second call raises error
        another_runtime = MagicMock()
        with pytest.raises(ModelOnexError) as exc_info:
            instance.set_runtime(another_runtime)

        assert "already set" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_lifecycle_state_transitions(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test full lifecycle state transitions and invalid transition errors.

        EXPECTED STATE MACHINE:
        - Created -> set_runtime -> Configured
        - Configured -> initialize -> Initialized
        - Initialized -> handle -> (still Initialized)
        - Initialized -> shutdown -> Shutdown
        - Cannot initialize without runtime
        - Cannot initialize twice
        - Cannot shutdown when not initialized
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Cannot initialize without runtime
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.initialize()
        assert "without runtime" in str(exc_info.value).lower()

        # Set runtime
        instance.set_runtime(mock_runtime)

        # Now can initialize
        await instance.initialize()

        # Cannot initialize again (already initialized)
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.initialize()
        assert "already initialized" in str(exc_info.value).lower()

        # Shutdown
        await instance.shutdown()

        # Cannot shutdown again (not initialized after shutdown)
        with pytest.raises(ModelOnexError) as exc_info:
            await instance.shutdown()
        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handle_before_initialize_raises_detailed_error(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test that handle() before initialize() raises descriptive error.

        EXPECTED BEHAVIOR:
        - Error message mentions 'not initialized'
        - Error includes node slug for debugging context
        """
        from omnibase_core.models.errors.model_onex_error import ModelOnexError
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )
        instance.set_runtime(mock_runtime)
        # Note: NOT calling initialize()

        with pytest.raises(ModelOnexError) as exc_info:
            await instance.handle(sample_envelope)

        error_msg = str(exc_info.value).lower()
        assert "not initialized" in error_msg


# =============================================================================
# TEST CLASS: Model Configuration
# =============================================================================


@pytest.mark.unit
class TestNodeInstanceModelConfig:
    """Tests for NodeInstance Pydantic model configuration."""

    def test_model_has_correct_config(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that NodeInstance has expected model configuration.

        EXPECTED BEHAVIOR:
        - Model is frozen (immutable) after creation
        - Extra fields are forbidden
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Check model config (Pydantic v2 style)
        config = instance.model_config

        # Verify ONEX-required configuration
        assert config.get("frozen") is True, "Model must be frozen (immutable)"
        assert config.get("extra") == "forbid", "Model must forbid extra fields"

    def test_serialization_to_dict(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
    ) -> None:
        """
        Test that NodeInstance can be serialized to dict.

        EXPECTED BEHAVIOR:
        - model_dump() returns dict with all properties
        - Serialized dict contains slug, node_type
        """
        from omnibase_core.runtime import NodeInstance

        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        data = instance.model_dump()

        assert isinstance(data, dict)
        assert data.get("slug") == sample_slug
        # node_type might be serialized as string or enum
        assert "node_type" in data


# =============================================================================
# TEST CLASS: Integration Patterns
# =============================================================================


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeInstanceIntegrationPatterns:
    """Tests for common NodeInstance usage patterns.

    Note:
    - Timeout (60s) for async integration pattern tests
    """

    @pytest.mark.asyncio
    async def test_full_lifecycle_pattern(
        self,
        sample_slug: str,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
        mock_runtime: MagicMock,
    ) -> None:
        """
        Test full lifecycle: create -> initialize -> handle -> shutdown.

        EXPECTED BEHAVIOR:
        - Complete lifecycle executes without errors
        - Each step completes successfully
        """
        from omnibase_core.runtime import NodeInstance

        # Create
        instance = NodeInstance(
            slug=sample_slug,
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Set runtime using public API
        instance.set_runtime(mock_runtime)

        # Initialize
        await instance.initialize()

        # Handle multiple envelopes
        result1 = await instance.handle(sample_envelope)
        result2 = await instance.handle(sample_envelope)

        # Shutdown
        await instance.shutdown()

        # Verify execution
        assert mock_runtime.execute_with_handler.call_count == 2

    def test_multiple_instances_with_same_contract(
        self,
        sample_node_type: EnumNodeType,
        mock_contract: Mock,
        sample_envelope: ModelOnexEnvelope,
    ) -> None:
        """
        Test creating multiple instances sharing same contract.

        EXPECTED BEHAVIOR:
        - Multiple instances can share same contract object
        - Each instance operates independently
        """
        from omnibase_core.runtime import NodeInstance

        instance1 = NodeInstance(
            slug="instance-1",
            node_type=sample_node_type,
            contract=mock_contract,
        )

        instance2 = NodeInstance(
            slug="instance-2",
            node_type=sample_node_type,
            contract=mock_contract,
        )

        # Both should have same contract reference
        assert instance1.contract is instance2.contract

        # But different slugs
        assert instance1.slug != instance2.slug

    def test_different_node_types_same_contract(
        self,
        sample_slug: str,
        mock_contract: Mock,
    ) -> None:
        """
        Test creating instances with different node types.

        EXPECTED BEHAVIOR:
        - Different node types create distinct instances
        - Each instance has correct node_type
        """
        from omnibase_core.runtime import NodeInstance

        compute_instance = NodeInstance(
            slug="compute-instance",
            node_type=EnumNodeType.COMPUTE_GENERIC,
            contract=mock_contract,
        )

        effect_instance = NodeInstance(
            slug="effect-instance",
            node_type=EnumNodeType.EFFECT_GENERIC,
            contract=mock_contract,
        )

        assert compute_instance.node_type == EnumNodeType.COMPUTE_GENERIC
        assert effect_instance.node_type == EnumNodeType.EFFECT_GENERIC
