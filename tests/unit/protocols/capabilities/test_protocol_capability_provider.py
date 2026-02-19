# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""
Unit tests for ProtocolCapabilityProvider.

Tests all aspects of the capability provider protocol including:
- Protocol defines correct method signatures
- Protocol is runtime_checkable for isinstance checks
- Protocol methods have correct return types
- Duck typing allows implementation without inheritance
"""

from __future__ import annotations

from typing import Any

import pytest

from omnibase_core.protocols.capabilities.protocol_capability_provider import (
    ProtocolCapabilityProvider,
)

# =============================================================================
# Protocol Structure Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolCapabilityProviderStructure:
    """Tests for protocol structure and method definitions."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that ProtocolCapabilityProvider is @runtime_checkable.

        The @runtime_checkable decorator enables isinstance checks for
        protocol compliance, essential for duck typing verification.
        """

        class MockProvider:
            def get_capabilities(self) -> dict[str, Any]:
                return {}

            def get_contract_capabilities(self) -> None:
                return None

        mock = MockProvider()

        # Runtime checkable protocols support isinstance without TypeError
        result = isinstance(mock, ProtocolCapabilityProvider)
        assert result is True, "MockProvider should satisfy the protocol"

    def test_protocol_has_get_capabilities_method(self) -> None:
        """Test that protocol defines get_capabilities method."""
        assert hasattr(ProtocolCapabilityProvider, "get_capabilities"), (
            "Protocol must define get_capabilities method"
        )

    def test_protocol_has_get_contract_capabilities_method(self) -> None:
        """Test that protocol defines get_contract_capabilities method."""
        assert hasattr(ProtocolCapabilityProvider, "get_contract_capabilities"), (
            "Protocol must define get_contract_capabilities method"
        )


# =============================================================================
# Duck Typing Compliance Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolCapabilityProviderDuckTyping:
    """Tests for duck typing compliance with the protocol."""

    def test_class_with_matching_methods_satisfies_protocol(self) -> None:
        """Test that a class with matching methods satisfies the protocol.

        Duck typing should allow any class with the correct method signatures
        to be treated as implementing the protocol.
        """

        class MockCapabilityProvider:
            """Mock implementation with matching method signatures."""

            def get_capabilities(self) -> dict[str, Any]:
                """Return node capabilities."""
                return {"capability_1": True, "capability_2": False}

            def get_contract_capabilities(self) -> dict[str, Any] | None:
                """Return contract capabilities or None."""
                return {"contract_type": "compute", "contract_version": "1.0.0"}

        mock = MockCapabilityProvider()

        # Should satisfy the protocol via isinstance check
        assert isinstance(mock, ProtocolCapabilityProvider), (
            "Class with matching methods should satisfy ProtocolCapabilityProvider"
        )

    def test_class_returning_none_for_contract_capabilities_satisfies_protocol(
        self,
    ) -> None:
        """Test that returning None for contract capabilities is valid."""

        class MockProviderWithNone:
            """Mock implementation that returns None for contract capabilities."""

            def get_capabilities(self) -> dict[str, Any]:
                return {"basic_capability": True}

            def get_contract_capabilities(self) -> None:
                return None

        mock = MockProviderWithNone()

        assert isinstance(mock, ProtocolCapabilityProvider), (
            "Class returning None for contract capabilities should satisfy protocol"
        )

    def test_class_missing_get_capabilities_does_not_satisfy_protocol(self) -> None:
        """Test that missing get_capabilities method fails protocol check."""

        class IncompleteProvider:
            """Mock missing get_capabilities method."""

            def get_contract_capabilities(self) -> None:
                return None

        mock = IncompleteProvider()

        # Should NOT satisfy the protocol
        assert not isinstance(mock, ProtocolCapabilityProvider), (
            "Class missing get_capabilities should not satisfy protocol"
        )

    def test_class_missing_get_contract_capabilities_does_not_satisfy_protocol(
        self,
    ) -> None:
        """Test that missing get_contract_capabilities method fails protocol check."""

        class IncompleteProvider:
            """Mock missing get_contract_capabilities method."""

            def get_capabilities(self) -> dict[str, Any]:
                return {}

        mock = IncompleteProvider()

        # Should NOT satisfy the protocol
        assert not isinstance(mock, ProtocolCapabilityProvider), (
            "Class missing get_contract_capabilities should not satisfy protocol"
        )

    def test_class_missing_both_methods_does_not_satisfy_protocol(self) -> None:
        """Test that missing both methods fails protocol check."""

        class EmptyProvider:
            """Mock with no protocol methods."""

        mock = EmptyProvider()

        # Should NOT satisfy the protocol
        assert not isinstance(mock, ProtocolCapabilityProvider), (
            "Empty class should not satisfy protocol"
        )


# =============================================================================
# Method Behavior Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolCapabilityProviderMethodBehavior:
    """Tests for expected method behavior when protocol is implemented."""

    def test_get_capabilities_returns_dict(self) -> None:
        """Test that get_capabilities returns a dictionary."""

        class Provider:
            def get_capabilities(self) -> dict[str, Any]:
                return {
                    "node_type": "COMPUTE_GENERIC",
                    "supports_caching": True,
                    "max_retries": 3,
                }

            def get_contract_capabilities(self) -> None:
                return None

        provider = Provider()
        capabilities = provider.get_capabilities()

        assert isinstance(capabilities, dict)
        assert capabilities["node_type"] == "COMPUTE_GENERIC"
        assert capabilities["supports_caching"] is True
        assert capabilities["max_retries"] == 3

    def test_get_contract_capabilities_returns_model_or_none(self) -> None:
        """Test that get_contract_capabilities returns model or None."""

        class Provider:
            def __init__(self, has_contract: bool = True) -> None:
                self._has_contract = has_contract

            def get_capabilities(self) -> dict[str, Any]:
                return {}

            def get_contract_capabilities(self) -> dict[str, Any] | None:
                if self._has_contract:
                    return {
                        "contract_type": "effect",
                        "contract_version": "2.0.0",
                        "intent_types": ["IntentA"],
                    }
                return None

        provider_with_contract = Provider(has_contract=True)
        provider_without_contract = Provider(has_contract=False)

        result_with = provider_with_contract.get_contract_capabilities()
        result_without = provider_without_contract.get_contract_capabilities()

        assert result_with is not None
        assert result_with["contract_type"] == "effect"

        assert result_without is None


# =============================================================================
# Protocol Integration Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolCapabilityProviderIntegration:
    """Tests for protocol integration scenarios."""

    def test_protocol_can_be_used_as_type_hint(self) -> None:
        """Test that the protocol can be used as a type hint parameter."""

        def process_provider(provider: ProtocolCapabilityProvider) -> dict[str, Any]:
            """Function that accepts any ProtocolCapabilityProvider."""
            return provider.get_capabilities()

        class MockProvider:
            def get_capabilities(self) -> dict[str, Any]:
                return {"test": True}

            def get_contract_capabilities(self) -> None:
                return None

        provider = MockProvider()
        result = process_provider(provider)

        assert result == {"test": True}

    def test_multiple_implementations_satisfy_protocol(self) -> None:
        """Test that different implementations all satisfy the protocol."""

        class EffectProvider:
            def get_capabilities(self) -> dict[str, Any]:
                return {"type": "effect", "io_bound": True}

            def get_contract_capabilities(self) -> dict[str, Any]:
                return {"contract_type": "effect", "contract_version": "1.0.0"}

        class ComputeProvider:
            def get_capabilities(self) -> dict[str, Any]:
                return {"type": "compute", "pure": True}

            def get_contract_capabilities(self) -> dict[str, Any]:
                return {"contract_type": "compute", "contract_version": "1.0.0"}

        class OrchestratorProvider:
            def get_capabilities(self) -> dict[str, Any]:
                return {"type": "orchestrator", "coordinates": True}

            def get_contract_capabilities(self) -> None:
                return None

        effect = EffectProvider()
        compute = ComputeProvider()
        orchestrator = OrchestratorProvider()

        # All should satisfy the protocol
        assert isinstance(effect, ProtocolCapabilityProvider)
        assert isinstance(compute, ProtocolCapabilityProvider)
        assert isinstance(orchestrator, ProtocolCapabilityProvider)


# =============================================================================
# Protocol Export Tests
# =============================================================================


@pytest.mark.unit
class TestProtocolCapabilityProviderExport:
    """Tests for protocol export and module structure."""

    def test_protocol_is_exported_in_all(self) -> None:
        """Test that protocol is included in module __all__."""
        from omnibase_core.protocols.capabilities import protocol_capability_provider

        assert hasattr(protocol_capability_provider, "__all__"), (
            "Module should have __all__ defined"
        )
        assert "ProtocolCapabilityProvider" in protocol_capability_provider.__all__, (
            "ProtocolCapabilityProvider should be in __all__"
        )

    def test_protocol_importable_from_capabilities_module(self) -> None:
        """Test that protocol can be imported from capabilities module."""
        from omnibase_core.protocols.capabilities import ProtocolCapabilityProvider

        assert ProtocolCapabilityProvider is not None
