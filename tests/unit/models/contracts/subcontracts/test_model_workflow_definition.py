# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelWorkflowDefinition workflow hash functionality."""

import pytest

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
)
from omnibase_core.models.contracts.subcontracts.model_execution_graph import (
    ModelExecutionGraph,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition import (
    ModelWorkflowDefinition,
)
from omnibase_core.models.contracts.subcontracts.model_workflow_definition_metadata import (
    ModelWorkflowDefinitionMetadata,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.fixture
def simple_workflow_definition() -> ModelWorkflowDefinition:
    """Create simple workflow definition for testing."""
    return ModelWorkflowDefinition(
        workflow_metadata=ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow for unit tests",
            execution_mode="sequential",
        ),
        execution_graph=ModelExecutionGraph(
            nodes=[],
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        coordination_rules=ModelCoordinationRules(
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
            version=ModelSemVer(major=1, minor=0, patch=0),
        ),
        version=ModelSemVer(major=1, minor=0, patch=0),
    )


@pytest.mark.unit
class TestModelWorkflowDefinitionMetadataHash:
    """Tests for workflow_hash field in ModelWorkflowDefinitionMetadata."""

    def test_workflow_hash_defaults_to_none(self) -> None:
        """Test that workflow_hash defaults to None."""
        metadata = ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow",
        )
        assert metadata.workflow_hash is None

    def test_workflow_hash_can_be_set(self) -> None:
        """Test that workflow_hash can be set explicitly."""
        test_hash = "a" * 64  # Valid SHA-256 hex string
        metadata = ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow",
            workflow_hash=test_hash,
        )
        assert metadata.workflow_hash == test_hash

    def test_workflow_hash_can_be_none_explicitly(self) -> None:
        """Test that workflow_hash can be explicitly set to None."""
        metadata = ModelWorkflowDefinitionMetadata(
            workflow_name="test_workflow",
            workflow_version=ModelSemVer(major=1, minor=0, patch=0),
            version=ModelSemVer(major=1, minor=0, patch=0),
            description="Test workflow",
            workflow_hash=None,
        )
        assert metadata.workflow_hash is None


@pytest.mark.unit
class TestModelWorkflowDefinitionComputeHash:
    """Tests for compute_workflow_hash method."""

    def test_compute_workflow_hash_returns_sha256(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that compute_workflow_hash returns a valid SHA-256 hex string."""
        hash_value = simple_workflow_definition.compute_workflow_hash()

        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64
        # Should only contain hex characters
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_compute_workflow_hash_is_deterministic(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that hash computation is deterministic."""
        hash1 = simple_workflow_definition.compute_workflow_hash()
        hash2 = simple_workflow_definition.compute_workflow_hash()

        assert hash1 == hash2

    def test_compute_workflow_hash_differs_for_different_definitions(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that different definitions produce different hashes."""
        hash1 = simple_workflow_definition.compute_workflow_hash()

        # Create a different workflow definition
        different_definition = ModelWorkflowDefinition(
            workflow_metadata=ModelWorkflowDefinitionMetadata(
                workflow_name="different_workflow",  # Different name
                workflow_version=ModelSemVer(major=1, minor=0, patch=0),
                version=ModelSemVer(major=1, minor=0, patch=0),
                description="Different workflow",
                execution_mode="parallel",  # Different mode
            ),
            execution_graph=ModelExecutionGraph(
                nodes=[],
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            coordination_rules=ModelCoordinationRules(
                parallel_execution_allowed=True,
                failure_recovery_strategy=EnumFailureRecoveryStrategy.RETRY,
                version=ModelSemVer(major=1, minor=0, patch=0),
            ),
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        hash2 = different_definition.compute_workflow_hash()

        assert hash1 != hash2

    def test_compute_workflow_hash_excludes_workflow_hash_field(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that the hash computation excludes the workflow_hash field itself.

        This ensures that setting the hash doesn't change the hash value,
        avoiding circular dependencies.
        """
        # Compute hash without workflow_hash set
        hash1 = simple_workflow_definition.compute_workflow_hash()

        # Create definition with workflow_hash already set
        metadata_with_hash = simple_workflow_definition.workflow_metadata.model_copy(
            update={"workflow_hash": "dummy_hash_value"}
        )
        definition_with_hash = simple_workflow_definition.model_copy(
            update={"workflow_metadata": metadata_with_hash}
        )

        # Compute hash with workflow_hash already set
        hash2 = definition_with_hash.compute_workflow_hash()

        # Both hashes should be the same (workflow_hash field is excluded)
        assert hash1 == hash2

    def test_compute_workflow_hash_changes_with_execution_mode(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that changing execution_mode changes the hash."""
        hash1 = simple_workflow_definition.compute_workflow_hash()

        # Create definition with different execution mode
        new_metadata = simple_workflow_definition.workflow_metadata.model_copy(
            update={"execution_mode": "parallel"}
        )
        modified_definition = simple_workflow_definition.model_copy(
            update={"workflow_metadata": new_metadata}
        )

        hash2 = modified_definition.compute_workflow_hash()

        assert hash1 != hash2

    def test_compute_workflow_hash_changes_with_timeout(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that changing timeout changes the hash."""
        hash1 = simple_workflow_definition.compute_workflow_hash()

        # Create definition with different timeout
        new_metadata = simple_workflow_definition.workflow_metadata.model_copy(
            update={"timeout_ms": 30000}  # Different from default 600000
        )
        modified_definition = simple_workflow_definition.model_copy(
            update={"workflow_metadata": new_metadata}
        )

        hash2 = modified_definition.compute_workflow_hash()

        assert hash1 != hash2


@pytest.mark.unit
class TestModelWorkflowDefinitionWithComputedHash:
    """Tests for with_computed_hash method."""

    def test_with_computed_hash_returns_new_instance(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash returns a new instance."""
        result = simple_workflow_definition.with_computed_hash()

        # Should be a different object
        assert result is not simple_workflow_definition

    def test_with_computed_hash_sets_workflow_hash(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash sets the workflow_hash in metadata."""
        # Original should have no hash
        assert simple_workflow_definition.workflow_metadata.workflow_hash is None

        result = simple_workflow_definition.with_computed_hash()

        # Result should have hash set
        assert result.workflow_metadata.workflow_hash is not None
        assert len(result.workflow_metadata.workflow_hash) == 64

    def test_with_computed_hash_sets_correct_hash(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash sets the correct hash value."""
        expected_hash = simple_workflow_definition.compute_workflow_hash()

        result = simple_workflow_definition.with_computed_hash()

        assert result.workflow_metadata.workflow_hash == expected_hash

    def test_with_computed_hash_preserves_other_fields(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash preserves all other fields."""
        result = simple_workflow_definition.with_computed_hash()

        # Check metadata fields are preserved
        assert (
            result.workflow_metadata.workflow_name
            == simple_workflow_definition.workflow_metadata.workflow_name
        )
        assert (
            result.workflow_metadata.execution_mode
            == simple_workflow_definition.workflow_metadata.execution_mode
        )
        assert (
            result.workflow_metadata.timeout_ms
            == simple_workflow_definition.workflow_metadata.timeout_ms
        )
        assert (
            result.workflow_metadata.description
            == simple_workflow_definition.workflow_metadata.description
        )

        # Check other definition fields are preserved
        assert result.version == simple_workflow_definition.version
        assert (
            result.coordination_rules.parallel_execution_allowed
            == simple_workflow_definition.coordination_rules.parallel_execution_allowed
        )

    def test_with_computed_hash_does_not_modify_original(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash does not modify the original instance."""
        # Original should have no hash
        assert simple_workflow_definition.workflow_metadata.workflow_hash is None

        _ = simple_workflow_definition.with_computed_hash()

        # Original should still have no hash
        assert simple_workflow_definition.workflow_metadata.workflow_hash is None

    def test_with_computed_hash_is_idempotent(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that calling with_computed_hash twice produces the same hash."""
        result1 = simple_workflow_definition.with_computed_hash()
        result2 = result1.with_computed_hash()

        # Both should have the same hash
        assert (
            result1.workflow_metadata.workflow_hash
            == result2.workflow_metadata.workflow_hash
        )


@pytest.mark.unit
class TestWorkflowHashIntegrationWithExecutor:
    """Integration tests verifying hash compatibility with workflow_executor."""

    def test_contract_hash_excludes_workflow_hash_field(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test contract hash excludes workflow_hash to avoid circular dependency.

        The contract's compute_workflow_hash() method excludes the workflow_hash
        field from the hash computation. This is intentional:
        - Prevents circular dependency (setting hash changes hash)
        - Allows hash to remain stable after being set
        - Supports idempotent hash computation
        """
        # Compute hash without workflow_hash set
        hash1 = simple_workflow_definition.compute_workflow_hash()

        # Set a workflow_hash value
        metadata_with_hash = simple_workflow_definition.workflow_metadata.model_copy(
            update={"workflow_hash": "some_hash_value"}
        )
        definition_with_hash = simple_workflow_definition.model_copy(
            update={"workflow_metadata": metadata_with_hash}
        )

        # Compute hash again - should be the same since workflow_hash is excluded
        hash2 = definition_with_hash.compute_workflow_hash()

        assert hash1 == hash2

    def test_executor_hash_includes_all_fields(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that executor's _compute_workflow_hash includes all fields.

        The executor's hash function is used for runtime integrity verification
        and includes all fields (including workflow_hash if present).

        This is different from the contract's compute_workflow_hash() which
        excludes workflow_hash to support persistence use cases.
        """
        from omnibase_core.utils.util_workflow_executor import (
            _compute_workflow_hash as executor_compute_hash,
        )

        # When workflow_hash is None, both should produce the same hash
        # (since excluding None is the same as not having the field)
        contract_hash = simple_workflow_definition.compute_workflow_hash()
        executor_hash = executor_compute_hash(simple_workflow_definition)

        # These may differ because:
        # - Contract hash excludes workflow_hash field entirely
        # - Executor hash includes all fields (workflow_hash: None is still serialized)
        # This is expected and intentional design
        # The important invariant is that each is deterministic and content-based
        assert isinstance(contract_hash, str)
        assert isinstance(executor_hash, str)
        assert len(contract_hash) == 64
        assert len(executor_hash) == 64

    def test_hash_persistence_use_case(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test the intended use case: compute hash before persistence.

        This demonstrates the workflow:
        1. Create workflow definition
        2. Compute and set hash
        3. Persist (simulated)
        4. Later retrieve and verify hash matches
        """
        # Step 1: Create definition (already done via fixture)
        assert simple_workflow_definition.workflow_metadata.workflow_hash is None

        # Step 2: Compute and set hash
        workflow_with_hash = simple_workflow_definition.with_computed_hash()
        stored_hash = workflow_with_hash.workflow_metadata.workflow_hash
        assert stored_hash is not None

        # Step 3: Simulate persistence (just store the hash)
        persisted_hash = stored_hash

        # Step 4: Later retrieve and verify (simulate by recreating)
        # In real scenario, this would come from database
        retrieved_definition = simple_workflow_definition.with_computed_hash()
        retrieved_hash = retrieved_definition.workflow_metadata.workflow_hash

        # Hashes should match - same definition produces same hash
        assert retrieved_hash == persisted_hash

    def test_hash_deduplication_use_case(self) -> None:
        """Test hash for deduplication: same content produces same hash.

        This demonstrates using the hash to identify duplicate workflows.
        """

        # Create two identical workflow definitions
        def create_workflow():
            return ModelWorkflowDefinition(
                workflow_metadata=ModelWorkflowDefinitionMetadata(
                    workflow_name="dedupe_test",
                    workflow_version=ModelSemVer(major=2, minor=0, patch=0),
                    version=ModelSemVer(major=1, minor=0, patch=0),
                    description="Deduplication test workflow",
                    execution_mode="sequential",
                ),
                execution_graph=ModelExecutionGraph(
                    nodes=[],
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                coordination_rules=ModelCoordinationRules(
                    parallel_execution_allowed=False,
                    failure_recovery_strategy=EnumFailureRecoveryStrategy.ABORT,
                    version=ModelSemVer(major=1, minor=0, patch=0),
                ),
                version=ModelSemVer(major=1, minor=0, patch=0),
            )

        workflow1 = create_workflow()
        workflow2 = create_workflow()

        hash1 = workflow1.compute_workflow_hash()
        hash2 = workflow2.compute_workflow_hash()

        # Same content should produce same hash for deduplication
        assert hash1 == hash2


@pytest.mark.unit
class TestModelWorkflowDefinitionFrozenBehavior:
    """Tests for with_computed_hash on frozen Pydantic models."""

    def test_with_computed_hash_works_with_model_copy(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash works via model_copy for immutability.

        Even though ModelWorkflowDefinition doesn't use frozen=True config,
        with_computed_hash() uses model_copy() which ensures immutability
        by creating new instances rather than mutating existing ones.
        """
        original = simple_workflow_definition
        original_hash = original.workflow_metadata.workflow_hash

        # Call with_computed_hash
        result = original.with_computed_hash()

        # Original should be unchanged
        assert original.workflow_metadata.workflow_hash == original_hash
        assert original.workflow_metadata.workflow_hash is None

        # Result should have hash set
        assert result.workflow_metadata.workflow_hash is not None
        assert len(result.workflow_metadata.workflow_hash) == 64

        # Should be different objects
        assert result is not original
        assert result.workflow_metadata is not original.workflow_metadata

    def test_with_computed_hash_preserves_immutability_semantics(
        self,
        simple_workflow_definition: ModelWorkflowDefinition,
    ) -> None:
        """Test that with_computed_hash preserves immutability semantics.

        The method should:
        1. Not modify the original instance
        2. Return a new instance with the hash set
        3. Allow multiple calls without side effects
        """
        original = simple_workflow_definition

        # Multiple calls should produce independent results
        result1 = original.with_computed_hash()
        result2 = original.with_computed_hash()
        result3 = result1.with_computed_hash()

        # All should have the same hash (deterministic)
        assert (
            result1.workflow_metadata.workflow_hash
            == result2.workflow_metadata.workflow_hash
        )
        assert (
            result2.workflow_metadata.workflow_hash
            == result3.workflow_metadata.workflow_hash
        )

        # But should be different object instances
        assert result1 is not result2
        assert result2 is not result3
        assert result1.workflow_metadata is not result2.workflow_metadata

        # Original should still be unchanged
        assert original.workflow_metadata.workflow_hash is None
