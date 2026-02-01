import pytest

# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for workflow contract model hardening (OMN-654).

Tests verify frozen=True behavior and extra field handling per OMN-490 patterns.

These tests ensure:
- Models are immutable after creation (frozen=True)
- Extra fields are handled appropriately:
  - extra="forbid" for most models (extra fields rejected at instantiation)
  - extra="ignore" for reserved field models (v1.0.5 Fix 54: Reserved Fields Governance)
    Models with extra="ignore": ModelWorkflowDefinition, ModelCoordinationRules,
    ModelExecutionGraph, ModelWorkflowNode
- Valid instantiation works with required fields
- Field constraints are properly enforced
- Edge cases are handled (empty strings, boundary values, unicode, etc.)

v1.0.5 Reserved Fields Governance:
    Some workflow contract models use extra="ignore" instead of extra="forbid" to support
    reserved fields for forward compatibility. Reserved fields (execution_graph, saga fields,
    compensation fields, etc.) are preserved during round-trip serialization but are NOT
    validated beyond structural type checking and MUST NOT influence any runtime decision in v1.0.
"""

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
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
from omnibase_core.models.contracts.subcontracts.model_workflow_node import (
    ModelWorkflowNode,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

# =============================================================================
# Pytest Fixtures - DRY refactor for common test data
# =============================================================================


@pytest.fixture
def default_version() -> ModelSemVer:
    """Reusable default version fixture."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def default_metadata(default_version: ModelSemVer) -> ModelWorkflowDefinitionMetadata:
    """Reusable metadata fixture."""
    return ModelWorkflowDefinitionMetadata(
        version=default_version,
        workflow_name="test-workflow",
        workflow_version=default_version,
        description="A test workflow",
    )


@pytest.fixture
def default_execution_graph(default_version: ModelSemVer) -> ModelExecutionGraph:
    """Reusable execution graph fixture."""
    return ModelExecutionGraph(version=default_version, nodes=[])


@pytest.fixture
def default_coordination_rules(default_version: ModelSemVer) -> ModelCoordinationRules:
    """Reusable coordination rules fixture."""
    return ModelCoordinationRules(version=default_version)


@pytest.fixture
def default_workflow_definition(
    default_version: ModelSemVer,
    default_metadata: ModelWorkflowDefinitionMetadata,
    default_execution_graph: ModelExecutionGraph,
    default_coordination_rules: ModelCoordinationRules,
) -> ModelWorkflowDefinition:
    """Reusable workflow definition fixture."""
    return ModelWorkflowDefinition(
        version=default_version,
        workflow_metadata=default_metadata,
        execution_graph=default_execution_graph,
        coordination_rules=default_coordination_rules,
    )


@pytest.fixture
def default_workflow_step() -> ModelWorkflowStep:
    """Reusable workflow step fixture."""
    return ModelWorkflowStep(
        step_name="test-step",
        step_type="compute",
    )


@pytest.fixture
def default_workflow_node(default_version: ModelSemVer) -> ModelWorkflowNode:
    """Reusable workflow node fixture."""
    return ModelWorkflowNode(
        version=default_version,
        node_type=EnumNodeType.COMPUTE_GENERIC,
    )


# Module-level constant for tests that don't use fixtures
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# Helper Functions - DRY refactor for common assertions
# =============================================================================


def assert_model_is_frozen(model: BaseModel, field_name: str, new_value: Any) -> None:
    """Assert that a model field cannot be modified (frozen behavior)."""
    with pytest.raises(ValidationError):
        setattr(model, field_name, new_value)


def assert_extra_fields_forbidden(
    model_class: type[BaseModel], valid_kwargs: dict[str, Any]
) -> None:
    """Assert that extra fields are rejected at instantiation."""
    with pytest.raises(ValidationError) as exc_info:
        model_class(**valid_kwargs, unknown_field="should_fail")  # type: ignore[call-arg]
    error_str = str(exc_info.value).lower()
    assert "extra" in error_str or "unexpected" in error_str


def assert_model_config_hardening(model_class: type[BaseModel]) -> None:
    """Assert that model_config has frozen=True and extra='forbid'."""
    config = model_class.model_config
    assert config.get("frozen") is True, f"{model_class.__name__} should be frozen"
    assert config.get("extra") == "forbid", (
        f"{model_class.__name__} should forbid extra fields"
    )


def assert_model_config_hardening_with_ignore(model_class: type[BaseModel]) -> None:
    """Assert that model_config has frozen=True and extra='ignore'.

    v1.0.5 Fix 54: Some models use extra='ignore' for Reserved Fields Governance.
    Reserved fields are preserved during round-trip serialization for forward compatibility.
    """
    config = model_class.model_config
    assert config.get("frozen") is True, f"{model_class.__name__} should be frozen"
    assert config.get("extra") == "ignore", (
        f"{model_class.__name__} should ignore extra fields (v1.0.5 Reserved Fields)"
    )


# =============================================================================
# Parametrized Tests - DRY refactor for testing multiple models with same pattern
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelConfigHardening:
    """Parametrized tests for model_config hardening across all models."""

    @pytest.mark.parametrize(
        "model_class",
        [
            ModelWorkflowDefinitionMetadata,
            ModelWorkflowStep,
        ],
    )
    def test_model_config_has_frozen_and_extra_forbid(
        self, model_class: type[BaseModel]
    ) -> None:
        """Verify workflow models have frozen=True and extra='forbid'."""
        assert_model_config_hardening(model_class)

    @pytest.mark.parametrize(
        "model_class",
        [
            ModelWorkflowDefinition,
            ModelCoordinationRules,
            ModelExecutionGraph,
            ModelWorkflowNode,
        ],
    )
    def test_model_config_has_frozen_and_extra_ignore(
        self, model_class: type[BaseModel]
    ) -> None:
        """Verify workflow models have frozen=True and extra='ignore'.

        v1.0.5 Fix 54: These models use extra='ignore' for Reserved Fields Governance.
        Reserved fields are preserved during round-trip serialization for forward compatibility.
        """
        assert_model_config_hardening_with_ignore(model_class)


# =============================================================================
# Edge Case Tests - Boundary conditions, empty values, unicode, etc.
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests for workflow contract models."""

    # -------------------------------------------------------------------------
    # Empty String Handling
    # -------------------------------------------------------------------------

    def test_empty_workflow_name_accepted(self, default_version: ModelSemVer) -> None:
        """Empty workflow_name is accepted (no min_length constraint)."""
        # workflow_name has no explicit min_length in model
        metadata = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="",  # Empty string
            workflow_version=default_version,
            description="A test workflow",
        )
        assert metadata.workflow_name == ""

    def test_empty_description_accepted(self, default_version: ModelSemVer) -> None:
        """Empty description should be accepted (no min_length constraint)."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="test-workflow",
            workflow_version=default_version,
            description="",  # Empty string
        )
        assert metadata.description == ""

    def test_empty_step_name_rejected(self) -> None:
        """Empty step_name should fail validation (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStep(
                step_name="",  # min_length=1 violated
                step_type="compute",
            )
        # Verify it's a string length error
        errors = exc_info.value.errors()
        assert len(errors) >= 1
        # Should contain string_too_short or similar
        assert any(
            "string_too_short" in str(e.get("type", "")).lower()
            or "min_length" in str(e).lower()
            for e in errors
        )

    def test_empty_parallel_group_accepted(self) -> None:
        """Empty string for parallel_group should be accepted (no min_length)."""
        step = ModelWorkflowStep(
            step_name="test-step",
            step_type="compute",
            parallel_group="",  # Empty string
        )
        assert step.parallel_group == ""

    # -------------------------------------------------------------------------
    # Maximum Boundary Values
    # -------------------------------------------------------------------------

    def test_step_name_at_max_length(self) -> None:
        """step_name at exactly max_length (255) should be accepted."""
        max_name = "x" * 255
        step = ModelWorkflowStep(
            step_name=max_name,
            step_type="compute",
        )
        assert len(step.step_name) == 255

    def test_step_name_exceeds_max_length(self) -> None:
        """step_name exceeding max_length (255) should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="x" * 256,
                step_type="compute",
            )

    def test_timeout_ms_at_exact_minimum_metadata(
        self, default_version: ModelSemVer
    ) -> None:
        """timeout_ms at exactly ge=1000 should be accepted for metadata."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="test",
            workflow_version=default_version,
            description="test",
            timeout_ms=1000,  # Exactly at minimum
        )
        assert metadata.timeout_ms == 1000

    def test_timeout_ms_at_exact_minimum_step(self) -> None:
        """timeout_ms at exactly ge=100 should be accepted for step."""
        step = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            timeout_ms=100,  # Exactly at minimum
        )
        assert step.timeout_ms == 100

    def test_timeout_ms_at_exact_maximum_step(self) -> None:
        """timeout_ms at exactly le=300000 should be accepted for step."""
        step = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            timeout_ms=300000,  # Exactly at maximum (5 minutes)
        )
        assert step.timeout_ms == 300000

    def test_retry_count_at_exact_boundaries(self) -> None:
        """retry_count at exact boundaries (0 and 10) should be accepted."""
        # Minimum boundary
        step_min = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            retry_count=0,  # Exactly at minimum
        )
        assert step_min.retry_count == 0

        # Maximum boundary
        step_max = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            retry_count=10,  # Exactly at maximum
        )
        assert step_max.retry_count == 10

    def test_priority_at_exact_boundaries(self) -> None:
        """priority at exact boundaries (1 and 1000) should be accepted."""
        # Minimum boundary
        step_min = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            priority=1,  # Exactly at minimum
        )
        assert step_min.priority == 1

        # Maximum boundary
        step_max = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            priority=1000,  # Exactly at maximum
        )
        assert step_max.priority == 1000

    def test_max_parallel_instances_at_exact_boundaries(self) -> None:
        """max_parallel_instances at exact boundaries (1 and 100) should be accepted."""
        # Minimum boundary
        step_min = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_parallel_instances=1,  # Exactly at minimum
        )
        assert step_min.max_parallel_instances == 1

        # Maximum boundary
        step_max = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_parallel_instances=100,  # Exactly at maximum
        )
        assert step_max.max_parallel_instances == 100

    def test_max_memory_mb_at_exact_boundaries(self) -> None:
        """max_memory_mb at exact boundaries (1 and 32768) should be accepted."""
        # Minimum boundary
        step_min = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_memory_mb=1,  # Exactly at minimum
        )
        assert step_min.max_memory_mb == 1

        # Maximum boundary
        step_max = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_memory_mb=32768,  # Exactly at maximum (32GB)
        )
        assert step_max.max_memory_mb == 32768

    def test_max_cpu_percent_at_exact_boundaries(self) -> None:
        """max_cpu_percent at exact boundaries (1 and 100) should be accepted."""
        # Minimum boundary
        step_min = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_cpu_percent=1,  # Exactly at minimum
        )
        assert step_min.max_cpu_percent == 1

        # Maximum boundary
        step_max = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_cpu_percent=100,  # Exactly at maximum
        )
        assert step_max.max_cpu_percent == 100

    def test_order_index_at_minimum_boundary(self) -> None:
        """order_index at minimum boundary (0) should be accepted."""
        step = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            order_index=0,  # Exactly at minimum
        )
        assert step.order_index == 0

    def test_order_index_large_value(self) -> None:
        """order_index with large value should be accepted (no upper bound)."""
        step = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            order_index=999999,  # Large value - no upper bound
        )
        assert step.order_index == 999999

    def test_parallel_group_at_max_length(self) -> None:
        """parallel_group at exactly max_length (100) should be accepted."""
        max_group = "x" * 100
        step = ModelWorkflowStep(
            step_name="test-step",
            step_type="compute",
            parallel_group=max_group,
        )
        assert len(step.parallel_group) == 100  # type: ignore[arg-type]

    def test_parallel_group_exceeds_max_length(self) -> None:
        """parallel_group exceeding max_length (100) should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test-step",
                step_type="compute",
                parallel_group="x" * 101,
            )

    # -------------------------------------------------------------------------
    # Values Exceeding Boundaries
    # -------------------------------------------------------------------------

    def test_max_memory_mb_exceeds_maximum(self) -> None:
        """max_memory_mb exceeding 32768 should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_memory_mb=32769,  # Exceeds maximum
            )

    def test_max_cpu_percent_exceeds_maximum(self) -> None:
        """max_cpu_percent exceeding 100 should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_cpu_percent=101,  # Exceeds maximum
            )

    def test_max_memory_mb_below_minimum(self) -> None:
        """max_memory_mb below 1 should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_memory_mb=0,  # Below minimum
            )

    def test_max_cpu_percent_below_minimum(self) -> None:
        """max_cpu_percent below 1 should be rejected."""
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_cpu_percent=0,  # Below minimum
            )

    # -------------------------------------------------------------------------
    # Empty Collections
    # -------------------------------------------------------------------------

    def test_empty_nodes_list_accepted(self, default_version: ModelSemVer) -> None:
        """Empty nodes list should be accepted (default behavior)."""
        graph = ModelExecutionGraph(
            version=default_version,
            nodes=[],  # Explicitly empty
        )
        assert graph.nodes == []

    def test_empty_dependencies_list_accepted(
        self, default_version: ModelSemVer
    ) -> None:
        """Empty dependencies list should be accepted (default behavior)."""
        node = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            dependencies=[],  # Explicitly empty
        )
        assert node.dependencies == []

    def test_empty_depends_on_list_accepted(self) -> None:
        """Empty depends_on list should be accepted (default behavior)."""
        step = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            depends_on=[],  # Explicitly empty
        )
        assert step.depends_on == []

    def test_empty_synchronization_points_accepted(
        self, default_version: ModelSemVer
    ) -> None:
        """Empty synchronization_points list should be accepted (default behavior)."""
        rules = ModelCoordinationRules(
            version=default_version,
            synchronization_points=[],  # Explicitly empty
        )
        assert rules.synchronization_points == []

    def test_empty_node_requirements_accepted(
        self, default_version: ModelSemVer
    ) -> None:
        """Empty node_requirements dict should be accepted (default behavior)."""
        node = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            node_requirements={},  # Explicitly empty
        )
        assert node.node_requirements == {}

    # -------------------------------------------------------------------------
    # Unicode String Handling
    # -------------------------------------------------------------------------

    def test_unicode_workflow_name(self, default_version: ModelSemVer) -> None:
        """Workflow name with unicode characters should be accepted."""
        unicode_names = [
            "workflow-\u4e2d\u6587",  # Chinese
            "workflow-\u65e5\u672c\u8a9e",  # Japanese
            "workflow-\ud55c\uad6d\uc5b4",  # Korean
            "workflow-\u0420\u0443\u0441\u0441\u043a\u0438\u0439",  # Russian
            "workflow-\u03b1\u03b2\u03b3\u03b4",  # Greek
            "workflow-\u00e9\u00e0\u00fc\u00f1",  # Accented Latin
            "workflow-\U0001f680",  # Emoji (rocket)
        ]
        for name in unicode_names:
            metadata = ModelWorkflowDefinitionMetadata(
                version=default_version,
                workflow_name=name,
                workflow_version=default_version,
                description="Unicode test",
            )
            assert metadata.workflow_name == name

    def test_unicode_step_name(self) -> None:
        """Step name with unicode characters should be accepted."""
        unicode_name = "step-\u4e2d\u6587-\U0001f680"  # Chinese + emoji
        step = ModelWorkflowStep(
            step_name=unicode_name,
            step_type="compute",
        )
        assert step.step_name == unicode_name

    def test_unicode_description(self, default_version: ModelSemVer) -> None:
        """Description with unicode characters should be accepted."""
        unicode_desc = "This is a \u4e2d\u6587 description with \U0001f680 emoji"
        metadata = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="test",
            workflow_version=default_version,
            description=unicode_desc,
        )
        assert metadata.description == unicode_desc

    def test_unicode_synchronization_point(self, default_version: ModelSemVer) -> None:
        """Synchronization point with unicode should be accepted."""
        rules = ModelCoordinationRules(
            version=default_version,
            synchronization_points=["checkpoint-\u4e2d\u6587", "\U0001f680-sync"],
        )
        assert len(rules.synchronization_points) == 2

    # -------------------------------------------------------------------------
    # None vs Missing Optional Fields
    # -------------------------------------------------------------------------

    def test_none_vs_missing_max_memory_mb(self) -> None:
        """Explicit None vs missing max_memory_mb should both result in None."""
        # Explicit None
        step_explicit = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_memory_mb=None,
        )
        assert step_explicit.max_memory_mb is None

        # Not provided (uses default)
        step_missing = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
        )
        assert step_missing.max_memory_mb is None

    def test_none_vs_missing_max_cpu_percent(self) -> None:
        """Explicit None vs missing max_cpu_percent should both result in None."""
        # Explicit None
        step_explicit = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_cpu_percent=None,
        )
        assert step_explicit.max_cpu_percent is None

        # Not provided (uses default)
        step_missing = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
        )
        assert step_missing.max_cpu_percent is None

    def test_none_vs_missing_parallel_group(self) -> None:
        """Explicit None vs missing parallel_group should both result in None."""
        # Explicit None
        step_explicit = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            parallel_group=None,
        )
        assert step_explicit.parallel_group is None

        # Not provided (uses default)
        step_missing = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
        )
        assert step_missing.parallel_group is None

    def test_optional_coordination_rules(
        self,
        default_version: ModelSemVer,
        default_metadata: ModelWorkflowDefinitionMetadata,
        default_execution_graph: ModelExecutionGraph,
    ) -> None:
        """ModelWorkflowDefinition without coordination_rules uses default."""
        definition = ModelWorkflowDefinition(
            version=default_version,
            workflow_metadata=default_metadata,
            execution_graph=default_execution_graph,
            # coordination_rules not provided - should use default
        )
        # Default should be None or auto-generated - verify not causing error
        # and definition is valid
        assert definition.version == default_version


# =============================================================================
# Original Test Classes - Refactored to use fixtures
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionHardening:
    """Tests for ModelWorkflowDefinition frozen and extra=forbid behavior."""

    def test_valid_instantiation(
        self,
        default_version: ModelSemVer,
        default_metadata: ModelWorkflowDefinitionMetadata,
        default_execution_graph: ModelExecutionGraph,
        default_coordination_rules: ModelCoordinationRules,
    ) -> None:
        """Verify ModelWorkflowDefinition can be created with valid data."""
        definition = ModelWorkflowDefinition(
            version=default_version,
            workflow_metadata=default_metadata,
            execution_graph=default_execution_graph,
            coordination_rules=default_coordination_rules,
        )

        assert definition.version == default_version
        assert definition.workflow_metadata.workflow_name == "test-workflow"
        assert definition.execution_graph.nodes == []
        assert (
            definition.coordination_rules.failure_recovery_strategy
            == EnumFailureRecoveryStrategy.RETRY
        )

    def test_is_frozen(
        self,
        default_version: ModelSemVer,
        default_metadata: ModelWorkflowDefinitionMetadata,
        default_execution_graph: ModelExecutionGraph,
    ) -> None:
        """Verify ModelWorkflowDefinition is immutable after creation."""
        definition = ModelWorkflowDefinition(
            version=default_version,
            workflow_metadata=default_metadata,
            execution_graph=default_execution_graph,
        )

        with pytest.raises(ValidationError):
            definition.version = ModelSemVer(major=2, minor=0, patch=0)  # type: ignore[misc]

    def test_extra_fields_ignored(
        self,
        default_version: ModelSemVer,
        default_metadata: ModelWorkflowDefinitionMetadata,
        default_execution_graph: ModelExecutionGraph,
    ) -> None:
        """Verify extra fields are silently ignored (v1.0.5 Fix 54: Reserved Fields).

        v1.0.5 Reserved Fields Governance: Extra fields are allowed for forward compatibility.
        Reserved fields are preserved during round-trip serialization but are NOT validated.
        """
        # Should NOT raise - extra fields are ignored for forward compatibility
        definition = ModelWorkflowDefinition(
            version=default_version,
            workflow_metadata=default_metadata,
            execution_graph=default_execution_graph,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )
        assert definition.version == default_version
        # Extra field should not be accessible as an attribute
        assert not hasattr(definition, "unknown_field")

    def test_model_copy_for_modifications(
        self,
        default_version: ModelSemVer,
        default_metadata: ModelWorkflowDefinitionMetadata,
        default_execution_graph: ModelExecutionGraph,
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelWorkflowDefinition(
            version=default_version,
            workflow_metadata=default_metadata,
            execution_graph=default_execution_graph,
        )

        new_version = ModelSemVer(major=2, minor=0, patch=0)
        modified = original.model_copy(update={"version": new_version})

        assert original.version == default_version  # Original unchanged
        assert modified.version == new_version  # Copy has new value


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowDefinitionMetadataHardening:
    """Tests for ModelWorkflowDefinitionMetadata frozen and extra=forbid behavior."""

    def test_valid_instantiation(
        self, default_metadata: ModelWorkflowDefinitionMetadata
    ) -> None:
        """Verify ModelWorkflowDefinitionMetadata can be created with valid data."""
        assert default_metadata.workflow_name == "test-workflow"
        assert default_metadata.description == "A test workflow"
        assert default_metadata.execution_mode == "sequential"  # Default
        assert default_metadata.timeout_ms == 600000  # Default

    def test_valid_instantiation_with_custom_values(
        self, default_version: ModelSemVer
    ) -> None:
        """Verify ModelWorkflowDefinitionMetadata accepts custom values."""
        metadata = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="parallel-workflow",
            workflow_version=ModelSemVer(major=2, minor=1, patch=0),
            description="A parallel workflow",
            execution_mode="parallel",
            timeout_ms=300000,
        )

        assert metadata.execution_mode == "parallel"
        assert metadata.timeout_ms == 300000

    def test_is_frozen(self, default_metadata: ModelWorkflowDefinitionMetadata) -> None:
        """Verify ModelWorkflowDefinitionMetadata is immutable after creation."""
        with pytest.raises(ValidationError):
            default_metadata.workflow_name = "new-name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self, default_version: ModelSemVer) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowDefinitionMetadata(
                version=default_version,
                workflow_name="test-workflow",
                workflow_version=default_version,
                description="A test workflow",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert "unknown_field" in errors[0]["loc"]

    def test_timeout_ms_bounds(self, default_version: ModelSemVer) -> None:
        """Verify timeout_ms constraint (ge=1000)."""
        # Valid timeout
        valid = ModelWorkflowDefinitionMetadata(
            version=default_version,
            workflow_name="test-workflow",
            workflow_version=default_version,
            description="A test workflow",
            timeout_ms=1000,
        )
        assert valid.timeout_ms == 1000

        # Too small (must be >= 1000)
        with pytest.raises(ValidationError):
            ModelWorkflowDefinitionMetadata(
                version=default_version,
                workflow_name="test-workflow",
                workflow_version=default_version,
                description="A test workflow",
                timeout_ms=999,
            )

    def test_model_copy_for_modifications(
        self, default_metadata: ModelWorkflowDefinitionMetadata
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        # Create with custom timeout first
        original = default_metadata.model_copy(update={"timeout_ms": 60000})
        modified = original.model_copy(update={"timeout_ms": 120000})

        assert original.timeout_ms == 60000  # Original unchanged
        assert modified.timeout_ms == 120000  # Copy has new value


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowStepHardening:
    """Tests for ModelWorkflowStep frozen and extra=forbid behavior."""

    def test_valid_instantiation(
        self, default_workflow_step: ModelWorkflowStep
    ) -> None:
        """Verify ModelWorkflowStep can be created with valid data."""
        assert default_workflow_step.step_name == "test-step"
        assert default_workflow_step.step_type == "compute"
        assert default_workflow_step.timeout_ms == 30000  # Default
        assert default_workflow_step.retry_count == 3  # Default
        assert default_workflow_step.enabled is True  # Default
        assert default_workflow_step.priority == 100  # Default

    def test_valid_instantiation_with_custom_values(self) -> None:
        """Verify ModelWorkflowStep accepts custom values."""
        step_id = uuid4()
        correlation_id = uuid4()
        depends_on = [uuid4(), uuid4()]

        step = ModelWorkflowStep(
            correlation_id=correlation_id,
            step_id=step_id,
            step_name="complex-step",
            step_type="orchestrator",
            timeout_ms=60000,
            retry_count=5,
            enabled=True,
            skip_on_failure=True,
            continue_on_error=True,
            error_action="retry",
            max_memory_mb=2048,
            max_cpu_percent=80,
            priority=200,
            order_index=5,
            depends_on=depends_on,
            parallel_group="group-a",
            max_parallel_instances=4,
        )

        assert step.correlation_id == correlation_id
        assert step.step_id == step_id
        assert step.step_name == "complex-step"
        assert step.step_type == "orchestrator"
        assert step.timeout_ms == 60000
        assert step.retry_count == 5
        assert step.skip_on_failure is True
        assert step.continue_on_error is True
        assert step.error_action == "retry"
        assert step.max_memory_mb == 2048
        assert step.max_cpu_percent == 80
        assert step.priority == 200
        assert step.order_index == 5
        assert step.depends_on == depends_on
        assert step.parallel_group == "group-a"
        assert step.max_parallel_instances == 4

    def test_is_frozen(self, default_workflow_step: ModelWorkflowStep) -> None:
        """Verify ModelWorkflowStep is immutable after creation."""
        with pytest.raises(ValidationError):
            default_workflow_step.step_name = "new-name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Verify extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelWorkflowStep(
                step_name="process-data",
                step_type="compute",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"
        assert "unknown_field" in errors[0]["loc"]

    def test_step_name_length_bounds(self) -> None:
        """Verify step_name length constraints (min=1, max=255)."""
        # Valid step_name
        valid = ModelWorkflowStep(
            step_name="valid-name",
            step_type="compute",
        )
        assert valid.step_name == "valid-name"

        # Too short (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="",
                step_type="compute",
            )

        # Too long (must be <= 255)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="x" * 256,
                step_type="compute",
            )

    def test_timeout_ms_bounds(self) -> None:
        """Verify timeout_ms constraints (ge=100, le=300000)."""
        # Valid timeout
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            timeout_ms=60000,
        )
        assert valid.timeout_ms == 60000

        # Too small (must be >= 100)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=99,
            )

        # Too large (must be <= 300000)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                timeout_ms=300001,
            )

    def test_retry_count_bounds(self) -> None:
        """Verify retry_count constraints (ge=0, le=10)."""
        # Valid retry count
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            retry_count=5,
        )
        assert valid.retry_count == 5

        # Negative (must be >= 0)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=-1,
            )

        # Too large (must be <= 10)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                retry_count=11,
            )

    def test_priority_bounds(self) -> None:
        """Verify priority constraints (ge=1, le=1000)."""
        # Valid priority
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            priority=500,
        )
        assert valid.priority == 500

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                priority=0,
            )

        # Too large (must be <= 1000)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                priority=1001,
            )

    def test_max_parallel_instances_bounds(self) -> None:
        """Verify max_parallel_instances constraints (ge=1, le=100)."""
        # Valid value
        valid = ModelWorkflowStep(
            step_name="test",
            step_type="compute",
            max_parallel_instances=50,
        )
        assert valid.max_parallel_instances == 50

        # Too small (must be >= 1)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_parallel_instances=0,
            )

        # Too large (must be <= 100)
        with pytest.raises(ValidationError):
            ModelWorkflowStep(
                step_name="test",
                step_type="compute",
                max_parallel_instances=101,
            )

    def test_model_copy_for_modifications(
        self, default_workflow_step: ModelWorkflowStep
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        modified = default_workflow_step.model_copy(update={"priority": 200})

        assert default_workflow_step.priority == 100  # Original unchanged
        assert modified.priority == 200  # Copy has new value


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelCoordinationRulesHardening:
    """Tests for ModelCoordinationRules frozen and extra=forbid behavior."""

    def test_valid_instantiation(
        self, default_coordination_rules: ModelCoordinationRules
    ) -> None:
        """Verify ModelCoordinationRules can be created with valid data."""
        assert default_coordination_rules.synchronization_points == []  # Default
        assert default_coordination_rules.parallel_execution_allowed is True  # Default
        assert (
            default_coordination_rules.failure_recovery_strategy
            == EnumFailureRecoveryStrategy.RETRY
        )

    def test_valid_instantiation_with_custom_values(
        self, default_version: ModelSemVer
    ) -> None:
        """Verify ModelCoordinationRules accepts custom values."""
        rules = ModelCoordinationRules(
            version=default_version,
            synchronization_points=["checkpoint-1", "checkpoint-2"],
            parallel_execution_allowed=False,
            failure_recovery_strategy=EnumFailureRecoveryStrategy.ABORT,
        )

        assert rules.synchronization_points == ["checkpoint-1", "checkpoint-2"]
        assert rules.parallel_execution_allowed is False
        assert rules.failure_recovery_strategy == EnumFailureRecoveryStrategy.ABORT

    def test_is_frozen(
        self, default_coordination_rules: ModelCoordinationRules
    ) -> None:
        """Verify ModelCoordinationRules is immutable after creation."""
        with pytest.raises(ValidationError):
            default_coordination_rules.parallel_execution_allowed = False  # type: ignore[misc]

    def test_extra_fields_ignored(self, default_version: ModelSemVer) -> None:
        """Verify extra fields are silently ignored (v1.0.5 Fix 54: Reserved Fields).

        v1.0.5 Reserved Fields Governance: Extra fields are allowed for forward compatibility.
        Reserved fields are preserved during round-trip serialization but are NOT validated.
        """
        # Should NOT raise - extra fields are ignored for forward compatibility
        rules = ModelCoordinationRules(
            version=default_version,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )
        assert rules.version == default_version
        # Extra field should not be accessible as an attribute
        assert not hasattr(rules, "unknown_field")

    def test_model_copy_for_modifications(
        self, default_coordination_rules: ModelCoordinationRules
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        modified = default_coordination_rules.model_copy(
            update={"parallel_execution_allowed": False}
        )

        assert (
            default_coordination_rules.parallel_execution_allowed is True
        )  # Original unchanged
        assert modified.parallel_execution_allowed is False  # Copy has new value

    def test_all_failure_recovery_strategies(
        self, default_version: ModelSemVer
    ) -> None:
        """Verify all EnumFailureRecoveryStrategy values are accepted."""
        strategies = [
            EnumFailureRecoveryStrategy.RETRY,
            EnumFailureRecoveryStrategy.ROLLBACK,
            EnumFailureRecoveryStrategy.COMPENSATE,
            EnumFailureRecoveryStrategy.ABORT,
        ]

        for strategy in strategies:
            rules = ModelCoordinationRules(
                version=default_version,
                failure_recovery_strategy=strategy,
            )
            assert rules.failure_recovery_strategy == strategy


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelExecutionGraphHardening:
    """Tests for ModelExecutionGraph frozen and extra=ignore behavior (v1.0.5 Fix 54)."""

    def test_valid_instantiation(
        self, default_execution_graph: ModelExecutionGraph
    ) -> None:
        """Verify ModelExecutionGraph can be created with valid data."""
        assert default_execution_graph.nodes == []  # Default

    def test_valid_instantiation_with_nodes(self, default_version: ModelSemVer) -> None:
        """Verify ModelExecutionGraph accepts nodes."""
        node1 = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        node2 = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.TRANSFORMER,
        )

        graph = ModelExecutionGraph(
            version=default_version,
            nodes=[node1, node2],
        )

        assert len(graph.nodes) == 2
        assert graph.nodes[0].node_type == EnumNodeType.COMPUTE_GENERIC
        assert graph.nodes[1].node_type == EnumNodeType.TRANSFORMER

    def test_is_frozen(self, default_execution_graph: ModelExecutionGraph) -> None:
        """Verify ModelExecutionGraph is immutable after creation."""
        with pytest.raises(ValidationError):
            default_execution_graph.version = ModelSemVer(major=2, minor=0, patch=0)  # type: ignore[misc]

    def test_extra_fields_ignored(self, default_version: ModelSemVer) -> None:
        """Verify extra fields are silently ignored (v1.0.5 Fix 54: Reserved Fields).

        v1.0.5 Reserved Fields Governance: Extra fields are allowed for forward compatibility.
        Reserved fields are preserved during round-trip serialization but are NOT validated.
        """
        # Should NOT raise - extra fields are ignored for forward compatibility
        graph = ModelExecutionGraph(
            version=default_version,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )
        assert graph.version == default_version
        # Extra field should not be accessible as an attribute
        assert not hasattr(graph, "unknown_field")

    def test_model_copy_for_modifications(
        self, default_version: ModelSemVer, default_execution_graph: ModelExecutionGraph
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        new_node = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.COMPUTE_GENERIC,
        )
        modified = default_execution_graph.model_copy(update={"nodes": [new_node]})

        assert default_execution_graph.nodes == []  # Original unchanged
        assert len(modified.nodes) == 1  # Copy has new value


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelWorkflowNodeHardening:
    """Tests for ModelWorkflowNode frozen and extra=ignore behavior (v1.0.5 Fix 54)."""

    def test_valid_instantiation(
        self, default_workflow_node: ModelWorkflowNode
    ) -> None:
        """Verify ModelWorkflowNode can be created with valid data."""
        assert default_workflow_node.node_type == EnumNodeType.COMPUTE_GENERIC
        assert default_workflow_node.node_requirements == {}  # Default
        assert default_workflow_node.dependencies == []  # Default
        # node_id is auto-generated by uuid4

    def test_valid_instantiation_with_custom_values(
        self, default_version: ModelSemVer
    ) -> None:
        """Verify ModelWorkflowNode accepts custom values."""
        node_id = uuid4()
        dep1 = uuid4()
        dep2 = uuid4()

        node = ModelWorkflowNode(
            version=default_version,
            node_id=node_id,
            node_type=EnumNodeType.TRANSFORMER,
            node_requirements={"cpu": 2, "memory": "4GB"},
            dependencies=[dep1, dep2],
        )

        assert node.node_id == node_id
        assert node.node_type == EnumNodeType.TRANSFORMER
        assert node.node_requirements == {"cpu": 2, "memory": "4GB"}
        assert node.dependencies == [dep1, dep2]

    def test_is_frozen(self, default_workflow_node: ModelWorkflowNode) -> None:
        """Verify ModelWorkflowNode is immutable after creation."""
        with pytest.raises(ValidationError):
            default_workflow_node.node_type = EnumNodeType.TRANSFORMER  # type: ignore[misc]

    def test_extra_fields_ignored(self, default_version: ModelSemVer) -> None:
        """Verify extra fields are silently ignored (v1.0.5 Fix 54: Reserved Fields).

        v1.0.5 Reserved Fields Governance: Extra fields are allowed for forward compatibility.
        Reserved fields are preserved during round-trip serialization but are NOT validated.
        """
        # Should NOT raise - extra fields are ignored for forward compatibility
        node = ModelWorkflowNode(
            version=default_version,
            node_type=EnumNodeType.COMPUTE_GENERIC,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )
        assert node.version == default_version
        # Extra field should not be accessible as an attribute
        assert not hasattr(node, "unknown_field")

    def test_model_copy_for_modifications(
        self, default_workflow_node: ModelWorkflowNode
    ) -> None:
        """Verify model_copy can be used to create modified copies."""
        modified = default_workflow_node.model_copy(
            update={"node_type": EnumNodeType.TRANSFORMER}
        )

        assert (
            default_workflow_node.node_type == EnumNodeType.COMPUTE_GENERIC
        )  # Original unchanged
        assert modified.node_type == EnumNodeType.TRANSFORMER  # Copy has new value

    def test_various_node_types(self, default_version: ModelSemVer) -> None:
        """Verify various EnumNodeType values are accepted."""
        node_types = [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
        ]

        for node_type in node_types:
            node = ModelWorkflowNode(
                version=default_version,
                node_type=node_type,
            )
            assert node.node_type == node_type
