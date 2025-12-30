# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ManifestObserver.

Tests the observer's ability to attach, retrieve, and detach generators
from pipeline context.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.manifest import ModelContractIdentity, ModelNodeIdentity
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.pipeline import ManifestGenerator, ManifestObserver


@pytest.fixture
def sample_node_identity() -> ModelNodeIdentity:
    """Create a sample node identity."""
    return ModelNodeIdentity(
        node_id="test-node",
        node_kind=EnumNodeKind.COMPUTE,
        node_version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.fixture
def sample_contract_identity() -> ModelContractIdentity:
    """Create a sample contract identity."""
    return ModelContractIdentity(contract_id="test-contract")


@pytest.mark.unit
class TestManifestObserverAttach:
    """Test ManifestObserver.attach()."""

    def test_attach_creates_generator(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test that attach creates a generator."""
        context_data: dict = {}
        generator = ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        assert isinstance(generator, ManifestGenerator)
        assert ManifestObserver.CONTEXT_KEY in context_data

    def test_attach_with_correlation_id(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test attach with correlation ID."""
        context_data: dict = {}
        correlation_id = uuid4()
        generator = ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
            correlation_id=correlation_id,
        )

        manifest = generator.build()
        assert manifest.correlation_id == correlation_id


@pytest.mark.unit
class TestManifestObserverGet:
    """Test ManifestObserver.get_generator()."""

    def test_get_generator_returns_attached(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test getting attached generator."""
        context_data: dict = {}
        attached = ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        retrieved = ManifestObserver.get_generator(context_data)
        assert retrieved is attached

    def test_get_generator_returns_none_when_empty(self) -> None:
        """Test getting generator from empty context."""
        context_data: dict = {}
        result = ManifestObserver.get_generator(context_data)
        assert result is None


@pytest.mark.unit
class TestManifestObserverHasGenerator:
    """Test ManifestObserver.has_generator()."""

    def test_has_generator_true(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test has_generator returns True when attached."""
        context_data: dict = {}
        ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        assert ManifestObserver.has_generator(context_data) is True

    def test_has_generator_false(self) -> None:
        """Test has_generator returns False when empty."""
        context_data: dict = {}
        assert ManifestObserver.has_generator(context_data) is False


@pytest.mark.unit
class TestManifestObserverBuildManifest:
    """Test ManifestObserver.build_manifest()."""

    def test_build_manifest_returns_manifest(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test building manifest from context."""
        context_data: dict = {}
        ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        manifest = ManifestObserver.build_manifest(context_data)
        assert manifest is not None
        assert manifest.node_identity.node_id == sample_node_identity.node_id

    def test_build_manifest_returns_none_when_empty(self) -> None:
        """Test building manifest from empty context."""
        context_data: dict = {}
        manifest = ManifestObserver.build_manifest(context_data)
        assert manifest is None


@pytest.mark.unit
class TestManifestObserverDetach:
    """Test ManifestObserver.detach()."""

    def test_detach_removes_generator(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test detaching generator."""
        context_data: dict = {}
        attached = ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        detached = ManifestObserver.detach(context_data)
        assert detached is attached
        assert ManifestObserver.has_generator(context_data) is False

    def test_detach_from_empty_returns_none(self) -> None:
        """Test detaching from empty context."""
        context_data: dict = {}
        result = ManifestObserver.detach(context_data)
        assert result is None


@pytest.mark.unit
class TestManifestObserverIntegration:
    """Integration tests for observer usage pattern."""

    def test_full_workflow(
        self,
        sample_node_identity: ModelNodeIdentity,
        sample_contract_identity: ModelContractIdentity,
    ) -> None:
        """Test full observer workflow."""
        context_data: dict = {}

        # Attach at pipeline start
        generator = ManifestObserver.attach(
            context_data,
            node_identity=sample_node_identity,
            contract_identity=sample_contract_identity,
        )

        # Record during execution
        generator.record_event("TestEvent")

        # Build at pipeline end
        manifest = ManifestObserver.build_manifest(context_data)
        assert manifest is not None
        assert manifest.emissions_summary.events_count == 1

        # Cleanup
        ManifestObserver.detach(context_data)
        assert ManifestObserver.has_generator(context_data) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
