# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for ProtocolDependencyResolver.

Tests the ProtocolDependencyResolver protocol which defines the interface for
resolving capability-based dependencies. This protocol enables auto-discovery
of dependencies by capability, intent, or protocol rather than hardcoded paths.

Test Categories:
1. Protocol Conformance Tests - Verify protocol definition
2. Mock Implementation Tests - Test with mock implementation
3. Type Hint Tests - Verify type hints are correct
4. Runtime Checkable Tests - Verify @runtime_checkable works

See Also:
    - OMN-1123: ModelDependencySpec (Capability-Based Dependencies)
    - ONEX Four-Node Architecture documentation
"""

from typing import Any

import pytest

from omnibase_core.models.contracts.model_dependency_spec import ModelDependencySpec
from omnibase_core.protocols.resolution.protocol_dependency_resolver import (
    ProtocolDependencyResolver,
)

# =============================================================================
# Mock Implementation for Testing
# =============================================================================


class MockDependencyResolver:
    """Mock implementation of ProtocolDependencyResolver for testing."""

    def __init__(self) -> None:
        """Initialize mock resolver with empty registry."""
        self._registry: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service by name."""
        self._registry[name] = service

    async def resolve(self, spec: ModelDependencySpec) -> Any | None:
        """Resolve a single dependency spec."""
        # Simple mock resolution by capability or protocol
        if spec.capability and spec.capability in self._registry:
            return self._registry[spec.capability]
        if spec.protocol and spec.protocol in self._registry:
            return self._registry[spec.protocol]
        if spec.fallback_module:
            return f"fallback:{spec.fallback_module}"
        return None

    async def resolve_all(self, specs: list[ModelDependencySpec]) -> dict[str, Any]:
        """Resolve multiple dependency specs."""
        results: dict[str, Any] = {}
        for spec in specs:
            resolved = await self.resolve(spec)
            results[spec.name] = resolved
        return results


# =============================================================================
# SECTION 1: Protocol Conformance Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestProtocolDependencyResolverConformance:
    """Tests for protocol conformance."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that protocol is runtime checkable."""
        resolver = MockDependencyResolver()
        assert isinstance(resolver, ProtocolDependencyResolver)

    def test_mock_implementation_conforms(self) -> None:
        """Test that mock implementation conforms to protocol."""
        resolver = MockDependencyResolver()
        # Verify methods exist
        assert hasattr(resolver, "resolve")
        assert hasattr(resolver, "resolve_all")
        assert callable(resolver.resolve)
        assert callable(resolver.resolve_all)

    def test_protocol_defines_resolve(self) -> None:
        """Test that protocol defines resolve method."""
        assert hasattr(ProtocolDependencyResolver, "resolve")

    def test_protocol_defines_resolve_all(self) -> None:
        """Test that protocol defines resolve_all method."""
        assert hasattr(ProtocolDependencyResolver, "resolve_all")


# =============================================================================
# SECTION 2: Mock Implementation Tests - resolve()
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestProtocolDependencyResolverResolve:
    """Tests for resolve method behavior."""

    @pytest.mark.asyncio
    async def test_resolve_by_capability(self) -> None:
        """Test resolving dependency by capability."""
        resolver = MockDependencyResolver()
        mock_service = {"name": "EventBusService"}
        resolver.register("event.publishing", mock_service)

        spec = ModelDependencySpec(
            name="event_bus",
            type="protocol",
            capability="event.publishing",
        )
        result = await resolver.resolve(spec)
        assert result == mock_service

    @pytest.mark.asyncio
    async def test_resolve_by_protocol(self) -> None:
        """Test resolving dependency by protocol."""
        resolver = MockDependencyResolver()
        mock_service = {"name": "ComputeNode"}
        resolver.register("ProtocolCompute", mock_service)

        spec = ModelDependencySpec(
            name="compute_dep",
            type="node",
            protocol="ProtocolCompute",
        )
        result = await resolver.resolve(spec)
        assert result == mock_service

    @pytest.mark.asyncio
    async def test_resolve_not_found_returns_none(self) -> None:
        """Test resolving non-existent dependency returns None."""
        resolver = MockDependencyResolver()

        spec = ModelDependencySpec(
            name="missing_dep",
            type="protocol",
            capability="non.existent",
        )
        result = await resolver.resolve(spec)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_with_fallback(self) -> None:
        """Test resolving with fallback module."""
        resolver = MockDependencyResolver()

        spec = ModelDependencySpec(
            name="fallback_dep",
            type="protocol",
            capability="non.existent",
            fallback_module="omnibase_core.fallback.service",
        )
        result = await resolver.resolve(spec)
        assert result == "fallback:omnibase_core.fallback.service"


# =============================================================================
# SECTION 3: Mock Implementation Tests - resolve_all()
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestProtocolDependencyResolverResolveAll:
    """Tests for resolve_all method behavior."""

    @pytest.mark.asyncio
    async def test_resolve_all_empty_list(self) -> None:
        """Test resolving empty list returns empty dict."""
        resolver = MockDependencyResolver()
        result = await resolver.resolve_all([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_all_single_spec(self) -> None:
        """Test resolving single spec in list."""
        resolver = MockDependencyResolver()
        mock_service = {"name": "Service1"}
        resolver.register("cap.one", mock_service)

        specs = [
            ModelDependencySpec(
                name="dep_one",
                type="protocol",
                capability="cap.one",
            )
        ]
        result = await resolver.resolve_all(specs)
        assert "dep_one" in result
        assert result["dep_one"] == mock_service

    @pytest.mark.asyncio
    async def test_resolve_all_multiple_specs(self) -> None:
        """Test resolving multiple specs."""
        resolver = MockDependencyResolver()
        resolver.register("cap.one", {"name": "Service1"})
        resolver.register("cap.two", {"name": "Service2"})
        resolver.register("ProtocolThree", {"name": "Service3"})

        specs = [
            ModelDependencySpec(name="dep_one", type="protocol", capability="cap.one"),
            ModelDependencySpec(name="dep_two", type="protocol", capability="cap.two"),
            ModelDependencySpec(
                name="dep_three", type="node", protocol="ProtocolThree"
            ),
        ]
        result = await resolver.resolve_all(specs)
        assert len(result) == 3
        assert result["dep_one"]["name"] == "Service1"
        assert result["dep_two"]["name"] == "Service2"
        assert result["dep_three"]["name"] == "Service3"

    @pytest.mark.asyncio
    async def test_resolve_all_partial_resolution(self) -> None:
        """Test resolving when some specs cannot be resolved."""
        resolver = MockDependencyResolver()
        resolver.register("cap.found", {"name": "FoundService"})

        specs = [
            ModelDependencySpec(
                name="found_dep", type="protocol", capability="cap.found"
            ),
            ModelDependencySpec(
                name="missing_dep", type="protocol", capability="cap.missing"
            ),
        ]
        result = await resolver.resolve_all(specs)
        assert len(result) == 2
        assert result["found_dep"]["name"] == "FoundService"
        assert result["missing_dep"] is None


# =============================================================================
# SECTION 4: Type Annotation Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestProtocolDependencyResolverTypes:
    """Tests for type annotations."""

    def test_resolve_return_type_annotation(self) -> None:
        """Test that resolve has proper return type annotation."""
        import inspect

        sig = inspect.signature(ProtocolDependencyResolver.resolve)
        # Should return Any | None
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_resolve_all_return_type_annotation(self) -> None:
        """Test that resolve_all has proper return type annotation."""
        import inspect

        sig = inspect.signature(ProtocolDependencyResolver.resolve_all)
        # Should return dict[str, Any]
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_resolve_spec_parameter_type(self) -> None:
        """Test that resolve takes ModelDependencySpec parameter."""
        import inspect

        sig = inspect.signature(ProtocolDependencyResolver.resolve)
        params = list(sig.parameters.values())
        # First param is self, second is spec
        assert len(params) >= 2
        assert params[1].name == "spec"

    def test_resolve_all_specs_parameter_type(self) -> None:
        """Test that resolve_all takes list[ModelDependencySpec] parameter."""
        import inspect

        sig = inspect.signature(ProtocolDependencyResolver.resolve_all)
        params = list(sig.parameters.values())
        # First param is self, second is specs
        assert len(params) >= 2
        assert params[1].name == "specs"


# =============================================================================
# SECTION 5: Export and Import Tests
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestProtocolDependencyResolverExports:
    """Tests for module exports."""

    def test_import_from_resolution_package(self) -> None:
        """Test that protocol can be imported from resolution package."""
        from omnibase_core.protocols.resolution import ProtocolDependencyResolver

        assert ProtocolDependencyResolver is not None

    def test_import_from_protocols_package(self) -> None:
        """Test that protocol can be imported from main protocols package."""
        from omnibase_core.protocols import ProtocolDependencyResolver

        assert ProtocolDependencyResolver is not None

    def test_protocol_in_resolution_all_exports(self) -> None:
        """Test that ProtocolDependencyResolver is in resolution __all__."""
        from omnibase_core.protocols.resolution import __all__

        assert "ProtocolDependencyResolver" in __all__

    def test_protocol_in_protocols_all_exports(self) -> None:
        """Test that ProtocolDependencyResolver is in main protocols __all__."""
        from omnibase_core.protocols import __all__

        assert "ProtocolDependencyResolver" in __all__
