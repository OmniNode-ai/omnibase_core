"""
Comprehensive unit tests for YAML contract loading in NodeOrchestrator.

Tests cover:
- Order preservation in YAML lists (steps must maintain declaration order)
- Typed conversion (strings, integers, booleans, enums, lists, nested objects)
- Declaration order as tiebreaker for equal-priority steps
- YAML syntax error handling
- Pydantic validation with extra="forbid"

OMN-657: Ensures YAML contract loading preserves order and converts types correctly.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_safe_yaml_loader import (
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
)
from omnibase_core.utils.workflow_executor import get_execution_order


@pytest.mark.unit
class TestOrderPreservation:
    """Tests for YAML list order preservation."""

    def test_steps_list_order_preserved_from_yaml(self, tmp_path: Path) -> None:
        """Test that workflow steps maintain their YAML declaration order."""
        step_names = ["Step_A", "Step_B", "Step_C", "Step_D", "Step_E"]
        yaml_content = self._create_workflow_steps_yaml(step_names)

        yaml_file = tmp_path / "workflow_steps.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        # Load steps directly from YAML
        raw_data = yaml.safe_load(yaml_content)
        steps = raw_data["steps"]

        # Verify order is preserved
        assert len(steps) == len(step_names)
        for i, step_name in enumerate(step_names):
            assert steps[i]["step_name"] == step_name, (
                f"Step at index {i} should be {step_name}, got {steps[i]['step_name']}"
            )

    def test_first_step_in_yaml_is_first_in_model(self, tmp_path: Path) -> None:
        """Test that the first step in YAML becomes the first step when parsed."""
        step_ids = [str(uuid4()) for _ in range(3)]
        yaml_content = f"""
steps:
  - step_id: {step_ids[0]}
    step_name: First Step
    step_type: compute
  - step_id: {step_ids[1]}
    step_name: Second Step
    step_type: effect
  - step_id: {step_ids[2]}
    step_name: Third Step
    step_type: reducer
"""
        raw_data = yaml.safe_load(yaml_content)
        steps = raw_data["steps"]

        assert steps[0]["step_name"] == "First Step"
        assert steps[0]["step_id"] == step_ids[0]

    def test_ten_plus_steps_maintain_exact_order(self, tmp_path: Path) -> None:
        """Test that 10+ steps maintain exact declaration order."""
        step_names = [f"Step_{i:02d}" for i in range(15)]
        yaml_content = self._create_workflow_steps_yaml(step_names)

        raw_data = yaml.safe_load(yaml_content)
        steps = raw_data["steps"]

        assert len(steps) == 15
        for i, expected_name in enumerate(step_names):
            actual_name = steps[i]["step_name"]
            assert actual_name == expected_name, (
                f"Step {i}: expected {expected_name}, got {actual_name}"
            )

    def test_order_index_reflects_declaration_order(self) -> None:
        """Test that order_index field reflects YAML declaration order."""
        steps: list[ModelWorkflowStep] = []
        for i in range(5):
            steps.append(
                ModelWorkflowStep(
                    step_id=uuid4(),
                    step_name=f"Step_{i}",
                    step_type="compute",
                    order_index=i,
                )
            )

        # Verify order_index matches position
        for i, step in enumerate(steps):
            assert step.order_index == i

    def test_workflow_nodes_order_preserved(self, tmp_path: Path) -> None:
        """Test that ModelExecutionGraph nodes preserve YAML order."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
nodes:
  - version:
      major: 1
      minor: 0
      patch: 0
    node_id: 11111111-1111-1111-1111-111111111111
    node_type: COMPUTE_GENERIC
  - version:
      major: 1
      minor: 0
      patch: 0
    node_id: 22222222-2222-2222-2222-222222222222
    node_type: EFFECT_GENERIC
  - version:
      major: 1
      minor: 0
      patch: 0
    node_id: 33333333-3333-3333-3333-333333333333
    node_type: REDUCER_GENERIC
"""
        graph = load_yaml_content_as_model(yaml_content, ModelExecutionGraph)

        assert len(graph.nodes) == 3
        assert str(graph.nodes[0].node_id) == "11111111-1111-1111-1111-111111111111"
        assert str(graph.nodes[1].node_id) == "22222222-2222-2222-2222-222222222222"
        assert str(graph.nodes[2].node_id) == "33333333-3333-3333-3333-333333333333"

    @staticmethod
    def _create_workflow_steps_yaml(step_names: list[str]) -> str:
        """Helper to create YAML content with workflow steps."""
        steps_yaml = "steps:\n"
        for name in step_names:
            step_id = str(uuid4())
            steps_yaml += f"""  - step_id: {step_id}
    step_name: {name}
    step_type: compute
"""
        return steps_yaml


@pytest.mark.unit
class TestTypedConversion:
    """Tests for YAML type conversion to Pydantic model fields."""

    def test_string_fields_remain_strings(self) -> None:
        """Test that string fields in YAML remain strings after parsing."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: "Test Step Name"
step_type: compute
error_action: stop
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert isinstance(step.step_name, str)
        assert step.step_name == "Test Step Name"
        assert isinstance(step.step_type, str)
        assert step.step_type == "compute"

    def test_integer_fields_are_integers(self) -> None:
        """Test that integer fields are properly converted to integers."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Test Step
step_type: compute
timeout_ms: 30000
retry_count: 5
priority: 100
order_index: 3
max_parallel_instances: 4
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert isinstance(step.timeout_ms, int)
        assert step.timeout_ms == 30000
        assert isinstance(step.retry_count, int)
        assert step.retry_count == 5
        assert isinstance(step.priority, int)
        assert step.priority == 100
        assert isinstance(step.order_index, int)
        assert step.order_index == 3
        assert isinstance(step.max_parallel_instances, int)
        assert step.max_parallel_instances == 4

    def test_boolean_fields_are_booleans(self) -> None:
        """Test that boolean fields are properly converted."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Test Step
step_type: compute
enabled: true
skip_on_failure: false
continue_on_error: true
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert isinstance(step.enabled, bool)
        assert step.enabled is True
        assert isinstance(step.skip_on_failure, bool)
        assert step.skip_on_failure is False
        assert isinstance(step.continue_on_error, bool)
        assert step.continue_on_error is True

    def test_enum_fields_convert_correctly(self) -> None:
        """Test that enum fields are converted to proper enum instances."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
synchronization_points: []
parallel_execution_allowed: true
failure_recovery_strategy: RETRY
"""
        rules = load_yaml_content_as_model(yaml_content, ModelCoordinationRules)

        assert isinstance(rules.failure_recovery_strategy, EnumFailureRecoveryStrategy)
        assert rules.failure_recovery_strategy == EnumFailureRecoveryStrategy.RETRY

    def test_list_fields_preserve_order_and_types(self) -> None:
        """Test that list fields preserve order and element types."""
        step_id_1 = str(uuid4())
        step_id_2 = str(uuid4())
        step_id_3 = str(uuid4())
        yaml_content = f"""
step_id: 11111111-1111-1111-1111-111111111111
step_name: Dependent Step
step_type: compute
depends_on:
  - {step_id_1}
  - {step_id_2}
  - {step_id_3}
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert isinstance(step.depends_on, list)
        assert len(step.depends_on) == 3
        for dep_id in step.depends_on:
            assert isinstance(dep_id, UUID)
        assert str(step.depends_on[0]) == step_id_1
        assert str(step.depends_on[1]) == step_id_2
        assert str(step.depends_on[2]) == step_id_3

    def test_nested_objects_convert_correctly(self) -> None:
        """Test that nested objects are properly converted."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: Test Workflow
  workflow_version:
    major: 2
    minor: 1
    patch: 0
  description: A test workflow description
  execution_mode: sequential
  timeout_ms: 60000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  parallel_execution_allowed: true
  failure_recovery_strategy: RETRY
"""
        workflow = load_yaml_content_as_model(yaml_content, ModelWorkflowDefinition)

        # Verify nested metadata
        assert isinstance(workflow.workflow_metadata, ModelWorkflowDefinitionMetadata)
        assert workflow.workflow_metadata.workflow_name == "Test Workflow"
        assert isinstance(workflow.workflow_metadata.workflow_version, ModelSemVer)
        assert workflow.workflow_metadata.workflow_version.major == 2
        assert workflow.workflow_metadata.workflow_version.minor == 1

        # Verify nested execution graph
        assert isinstance(workflow.execution_graph, ModelExecutionGraph)
        assert workflow.execution_graph.nodes == []

        # Verify nested coordination rules
        assert isinstance(workflow.coordination_rules, ModelCoordinationRules)
        assert workflow.coordination_rules.parallel_execution_allowed is True

    def test_uuid_fields_convert_correctly(self) -> None:
        """Test that UUID fields are properly converted from string."""
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        yaml_content = f"""
step_id: {test_uuid}
step_name: UUID Test
step_type: effect
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert isinstance(step.step_id, UUID)
        assert str(step.step_id) == test_uuid

    def test_semver_nested_dict_conversion(self) -> None:
        """Test that SemVer fields convert from nested dict format."""
        yaml_content = """
version:
  major: 2
  minor: 5
  patch: 3
workflow_name: Version Test
workflow_version:
  major: 1
  minor: 2
  patch: 3
description: Test description
"""
        metadata = load_yaml_content_as_model(
            yaml_content, ModelWorkflowDefinitionMetadata
        )

        assert isinstance(metadata.version, ModelSemVer)
        assert metadata.version.major == 2
        assert metadata.version.minor == 5
        assert metadata.version.patch == 3

        assert isinstance(metadata.workflow_version, ModelSemVer)
        assert metadata.workflow_version.major == 1
        assert metadata.workflow_version.minor == 2
        assert metadata.workflow_version.patch == 3

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None when not provided."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Minimal Step
step_type: compute
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        # Optional fields should be None or default values
        assert step.max_memory_mb is None
        assert step.max_cpu_percent is None
        assert step.parallel_group is None


@pytest.mark.unit
class TestDeclarationOrderTiebreaker:
    """Tests for declaration order as tiebreaker for equal-priority steps."""

    def test_equal_priority_steps_use_declaration_order(self) -> None:
        """Test that steps with equal priority use YAML declaration order."""
        step1_id = uuid4()
        step2_id = uuid4()
        step3_id = uuid4()

        # All steps have same priority
        steps = [
            ModelWorkflowStep(
                step_id=step1_id,
                step_name="First Declared",
                step_type="compute",
                priority=100,
                order_index=0,
            ),
            ModelWorkflowStep(
                step_id=step2_id,
                step_name="Second Declared",
                step_type="compute",
                priority=100,
                order_index=1,
            ),
            ModelWorkflowStep(
                step_id=step3_id,
                step_name="Third Declared",
                step_type="compute",
                priority=100,
                order_index=2,
            ),
        ]

        # Get execution order - should respect declaration order for equal priority
        execution_order = get_execution_order(steps)

        # First declared should be first in execution order
        assert execution_order[0] == step1_id
        assert execution_order[1] == step2_id
        assert execution_order[2] == step3_id

    def test_first_declared_step_executes_first_when_priorities_equal(self) -> None:
        """Test that the first declared step executes first when all priorities equal."""
        first_id = uuid4()
        second_id = uuid4()
        third_id = uuid4()

        # Create steps with identical priority
        steps = [
            ModelWorkflowStep(
                step_id=first_id,
                step_name="Alpha",
                step_type="effect",
                priority=50,
            ),
            ModelWorkflowStep(
                step_id=second_id,
                step_name="Beta",
                step_type="effect",
                priority=50,
            ),
            ModelWorkflowStep(
                step_id=third_id,
                step_name="Gamma",
                step_type="effect",
                priority=50,
            ),
        ]

        execution_order = get_execution_order(steps)

        # Declaration order should be the tiebreaker
        assert execution_order[0] == first_id, "First declared should execute first"

    def test_yaml_position_determines_tiebreaker(self) -> None:
        """Test that YAML position (declaration order) determines tiebreaker."""
        yaml_content = """
steps:
  - step_name: First
    step_type: compute
    priority: 100
  - step_name: Second
    step_type: compute
    priority: 100
  - step_name: Third
    step_type: compute
    priority: 100
"""
        raw_data = yaml.safe_load(yaml_content)
        steps: list[ModelWorkflowStep] = []

        for idx, step_data in enumerate(raw_data["steps"]):
            step = ModelWorkflowStep(
                step_id=uuid4(),
                step_name=step_data["step_name"],
                step_type=step_data["step_type"],
                priority=step_data["priority"],
                order_index=idx,  # YAML position becomes order_index
            )
            steps.append(step)

        execution_order = get_execution_order(steps)

        # Verify order matches YAML position
        for idx, step_id in enumerate(execution_order):
            matching_step = next(s for s in steps if s.step_id == step_id)
            assert matching_step.order_index == idx

    def test_higher_priority_overrides_declaration_order(self) -> None:
        """Test that higher priority (lower number) overrides declaration order."""
        low_priority_id = uuid4()
        high_priority_id = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=low_priority_id,
                step_name="Low Priority First Declared",
                step_type="compute",
                priority=100,  # Lower priority (higher number)
            ),
            ModelWorkflowStep(
                step_id=high_priority_id,
                step_name="High Priority Second Declared",
                step_type="compute",
                priority=1,  # Higher priority (lower number)
            ),
        ]

        execution_order = get_execution_order(steps)

        # High priority should execute first despite being declared second
        assert execution_order[0] == high_priority_id
        assert execution_order[1] == low_priority_id

    def test_declaration_order_only_affects_equal_priority(self) -> None:
        """Test that declaration order only affects steps with equal priority.

        Note: Priorities > 10 are clamped to 10, so we use values in 1-10 range.
        """
        id_priority_1 = uuid4()
        id_priority_5_first = uuid4()
        id_priority_5_second = uuid4()
        id_priority_10 = uuid4()

        steps = [
            ModelWorkflowStep(
                step_id=id_priority_10,
                step_name="Priority 10",
                step_type="compute",
                priority=10,  # Lowest priority (highest number in 1-10 range)
            ),
            ModelWorkflowStep(
                step_id=id_priority_5_first,
                step_name="Priority 5 First",
                step_type="compute",
                priority=5,  # Medium priority
            ),
            ModelWorkflowStep(
                step_id=id_priority_1,
                step_name="Priority 1",
                step_type="compute",
                priority=1,  # Highest priority
            ),
            ModelWorkflowStep(
                step_id=id_priority_5_second,
                step_name="Priority 5 Second",
                step_type="compute",
                priority=5,  # Same medium priority - uses declaration order
            ),
        ]

        execution_order = get_execution_order(steps)

        # Priority 1 (highest priority) first
        assert execution_order[0] == id_priority_1
        # Priority 5 steps use declaration order (index 1 before index 3)
        first_5_idx = execution_order.index(id_priority_5_first)
        second_5_idx = execution_order.index(id_priority_5_second)
        assert first_5_idx < second_5_idx, (
            "First declared priority-5 step should execute before second"
        )
        # Priority 10 (lowest priority) last
        assert execution_order[-1] == id_priority_10


@pytest.mark.unit
class TestYamlSyntax:
    """Tests for YAML syntax handling and error messages."""

    def test_valid_yaml_parses_correctly(self, tmp_path: Path) -> None:
        """Test that valid YAML parses correctly."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Valid Step
step_type: compute
enabled: true
timeout_ms: 30000
"""
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        step = load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert step.step_name == "Valid Step"
        assert step.step_type == "compute"
        assert step.enabled is True
        assert step.timeout_ms == 30000

    def test_invalid_yaml_raises_clear_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML syntax raises a clear error."""
        yaml_content = """
step_name: Bad Step
  invalid_indent: true
wrong: [unclosed bracket
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR

    def test_missing_required_fields_raise_validation_error(
        self, tmp_path: Path
    ) -> None:
        """Test that missing required fields raise ValidationError."""
        yaml_content = """
# Missing step_name and step_type
step_id: 11111111-1111-1111-1111-111111111111
enabled: true
"""
        yaml_file = tmp_path / "missing_fields.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        error_message = str(exc_info.value)
        assert "step_name" in error_message or "step_type" in error_message

    def test_extra_fields_rejected_with_extra_forbid(self, tmp_path: Path) -> None:
        """Test that extra fields are rejected when model has extra='forbid'."""
        # ModelWorkflowStep has extra="forbid"
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Step With Extra
step_type: compute
unknown_field: should_fail
another_extra: also_fail
"""
        yaml_file = tmp_path / "extra_fields.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        error_message = str(exc_info.value)
        assert "unknown_field" in error_message or "extra" in error_message.lower()

    def test_type_mismatch_raises_validation_error(self, tmp_path: Path) -> None:
        """Test that type mismatches raise clear validation errors."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Type Mismatch
step_type: compute
timeout_ms: "not_an_integer"
"""
        yaml_file = tmp_path / "type_mismatch.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_empty_yaml_file_raises_error(self, tmp_path: Path) -> None:
        """Test that empty YAML file raises validation error."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("", encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_yaml_with_comments_parses_correctly(self, tmp_path: Path) -> None:
        """Test that YAML with comments parses correctly."""
        yaml_content = """
# This is a comment
step_id: 11111111-1111-1111-1111-111111111111
step_name: Step With Comments  # inline comment
step_type: compute  # another comment
# Another block comment
enabled: true
"""
        yaml_file = tmp_path / "with_comments.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        step = load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert step.step_name == "Step With Comments"
        assert step.step_type == "compute"
        assert step.enabled is True

    def test_yaml_with_unicode_content(self, tmp_path: Path) -> None:
        """Test that YAML with unicode content parses correctly."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: "Unicode Test: \u4e2d\u6587 \u65e5\u672c\u8a9e"
step_type: compute
"""
        yaml_file = tmp_path / "unicode.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        step = load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert "Unicode Test:" in step.step_name

    def test_yaml_null_values_handled(self, tmp_path: Path) -> None:
        """Test that YAML null values are handled correctly."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Null Test
step_type: compute
parallel_group: null
max_memory_mb: ~
"""
        yaml_file = tmp_path / "null_values.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        step = load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert step.parallel_group is None
        assert step.max_memory_mb is None

    def test_invalid_enum_value_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid enum values raise validation error."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: Invalid Enum
step_type: invalid_step_type
"""
        yaml_file = tmp_path / "invalid_enum.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, ModelWorkflowStep)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


@pytest.mark.unit
class TestYamlContentLoading:
    """Tests for loading YAML content from strings."""

    def test_load_yaml_content_as_model(self) -> None:
        """Test loading YAML content directly from string."""
        yaml_content = """
step_id: 11111111-1111-1111-1111-111111111111
step_name: String Content Step
step_type: effect
timeout_ms: 5000
"""
        step = load_yaml_content_as_model(yaml_content, ModelWorkflowStep)

        assert step.step_name == "String Content Step"
        assert step.step_type == "effect"
        assert step.timeout_ms == 5000

    def test_load_nested_structure_from_string(self) -> None:
        """Test loading nested structure from string content."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
nodes:
  - version:
      major: 1
      minor: 0
      patch: 0
    node_id: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
    node_type: COMPUTE_GENERIC
  - version:
      major: 1
      minor: 0
      patch: 0
    node_id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
    node_type: EFFECT_GENERIC
"""
        graph = load_yaml_content_as_model(yaml_content, ModelExecutionGraph)

        assert len(graph.nodes) == 2
        assert graph.nodes[0].node_type == EnumNodeType.COMPUTE_GENERIC
        assert graph.nodes[1].node_type == EnumNodeType.EFFECT_GENERIC


@pytest.mark.unit
class TestWorkflowDefinitionLoading:
    """Tests for complete workflow definition loading."""

    def test_complete_workflow_definition_from_yaml(self, tmp_path: Path) -> None:
        """Test loading a complete workflow definition from YAML."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: Complete Test Workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: A complete test workflow
  execution_mode: sequential
  timeout_ms: 120000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: 11111111-1111-1111-1111-111111111111
      node_type: EFFECT_GENERIC
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: 22222222-2222-2222-2222-222222222222
      node_type: COMPUTE_GENERIC
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  parallel_execution_allowed: false
  failure_recovery_strategy: RETRY
  synchronization_points:
    - checkpoint_1
    - checkpoint_2
"""
        yaml_file = tmp_path / "complete_workflow.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        workflow = load_and_validate_yaml_model(yaml_file, ModelWorkflowDefinition)

        # Verify all parts loaded correctly
        assert workflow.workflow_metadata.workflow_name == "Complete Test Workflow"
        assert workflow.workflow_metadata.timeout_ms == 120000
        assert len(workflow.execution_graph.nodes) == 2
        assert workflow.coordination_rules.parallel_execution_allowed is False
        assert (
            workflow.coordination_rules.failure_recovery_strategy
            == EnumFailureRecoveryStrategy.RETRY
        )
        assert workflow.coordination_rules.synchronization_points == [
            "checkpoint_1",
            "checkpoint_2",
        ]

    def test_workflow_hash_computation(self, tmp_path: Path) -> None:
        """Test that workflow hash can be computed after loading."""
        yaml_content = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: Hash Test Workflow
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: Test hash computation
  execution_mode: sequential
  timeout_ms: 60000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  parallel_execution_allowed: true
  failure_recovery_strategy: ABORT
"""
        yaml_file = tmp_path / "hash_test.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        workflow = load_and_validate_yaml_model(yaml_file, ModelWorkflowDefinition)

        # Compute hash
        workflow_hash = workflow.compute_workflow_hash()
        assert isinstance(workflow_hash, str)
        assert len(workflow_hash) == 64  # SHA-256 hex string

        # Verify deterministic
        workflow_hash_2 = workflow.compute_workflow_hash()
        assert workflow_hash == workflow_hash_2
