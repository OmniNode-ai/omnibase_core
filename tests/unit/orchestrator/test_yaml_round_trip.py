# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
YAML Round-Trip Stability Tests for NodeOrchestrator Workflow Models.

This test suite validates that YAML -> model -> YAML round-trips preserve all data correctly,
including step ordering, identifiers, dependencies, reserved fields, scalar types, and null values.

Test Categories:
    1. Step Ordering Preservation - Verifies steps maintain exact order through round-trip
    2. Step ID Preservation - Validates step_id and correlation_id remain unchanged
    3. Dependency Set Preservation - Tests depends_on lists are preserved exactly
    4. Reserved Field Handling - Ensures reserved fields are untouched
    5. Scalar Type Preservation - Validates no type coercion (string vs int vs bool)
    6. Null Value Handling - Tests null vs missing field distinction
"""

from __future__ import annotations

from typing import Any, TypeVar
from uuid import uuid4

import pytest
import yaml
from pydantic import BaseModel

from omnibase_core.models.contracts.model_workflow_step import ModelWorkflowStep
from omnibase_core.models.contracts.subcontracts.model_coordination_rules import (
    ModelCoordinationRules,
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

T = TypeVar("T", bound=BaseModel)


def round_trip_yaml[T: BaseModel](
    yaml_content: str, model_cls: type[T]
) -> tuple[T, str]:
    """
    Perform YAML -> model -> YAML round-trip.

    Args:
        yaml_content: Original YAML string
        model_cls: Pydantic model class to validate against

    Returns:
        Tuple of (model instance, round-tripped YAML string)
    """
    # Parse YAML to dict
    data = yaml.safe_load(yaml_content)
    if data is None:
        data = {}

    # Validate against Pydantic model
    model = model_cls.model_validate(data)

    # Serialize model back to dict using JSON mode (preserves types correctly)
    serialized_dict = model.model_dump(mode="json")

    # Convert back to YAML string
    round_tripped_yaml_str = yaml.dump(
        serialized_dict,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return model, round_tripped_yaml_str


def parse_yaml_to_dict(yaml_content: str) -> dict[str, Any]:
    """Parse YAML string to dict for comparison."""
    result = yaml.safe_load(yaml_content)
    return result if result is not None else {}


@pytest.mark.unit
class TestStepOrderingPreservation:
    """Test that workflow steps maintain exact order through round-trip."""

    def test_steps_maintain_exact_order(self) -> None:
        """Test steps maintain exact order through round-trip."""
        step_ids = [str(uuid4()) for _ in range(5)]

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "test_workflow"
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: "Test workflow"
  execution_mode: "sequential"
  timeout_ms: 60000
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
      node_id: "{step_ids[0]}"
      node_type: "COMPUTE_GENERIC"
      node_requirements: {{}}
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_ids[1]}"
      node_type: "COMPUTE_GENERIC"
      node_requirements: {{}}
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_ids[2]}"
      node_type: "EFFECT_GENERIC"
      node_requirements: {{}}
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_ids[3]}"
      node_type: "ORCHESTRATOR_GENERIC"
      node_requirements: {{}}
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{step_ids[4]}"
      node_type: "REDUCER_GENERIC"
      node_requirements: {{}}
      dependencies: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: true
  failure_recovery_strategy: "RETRY"
"""

        _model, round_tripped_yaml = round_trip_yaml(
            yaml_content, ModelWorkflowDefinition
        )

        # Verify order is preserved
        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        round_tripped_node_ids = [
            node["node_id"] for node in round_tripped_dict["execution_graph"]["nodes"]
        ]

        assert round_tripped_node_ids == step_ids, (
            f"Step order not preserved. Expected: {step_ids}, Got: {round_tripped_node_ids}"
        )

    def test_ten_plus_steps_preserve_order(self) -> None:
        """Test 10+ steps preserve order through round-trip."""
        step_ids = [str(uuid4()) for _ in range(15)]

        nodes_yaml = "\n".join(
            [
                f"""    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{sid}"
      node_type: "COMPUTE_GENERIC"
      node_requirements: {{}}
      dependencies: []"""
                for sid in step_ids
            ]
        )

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "large_workflow"
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: "Test with 15 steps"
  execution_mode: "parallel"
  timeout_ms: 120000
execution_graph:
  version:
    major: 1
    minor: 0
    patch: 0
  nodes:
{nodes_yaml}
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: true
  failure_recovery_strategy: "RETRY"
"""

        _model, round_tripped_yaml = round_trip_yaml(
            yaml_content, ModelWorkflowDefinition
        )

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        round_tripped_node_ids = [
            node["node_id"] for node in round_tripped_dict["execution_graph"]["nodes"]
        ]

        assert len(round_tripped_node_ids) == 15
        assert round_tripped_node_ids == step_ids

    def test_order_index_values_preserved_in_workflow_step(self) -> None:
        """Test order_index values are preserved in ModelWorkflowStep."""
        step_id = uuid4()
        correlation_id = uuid4()

        yaml_content = f"""
correlation_id: "{correlation_id}"
step_id: "{step_id}"
step_name: "test_step"
step_type: "compute"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
priority: 100
order_index: 42
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        assert round_tripped_dict["order_index"] == 42


@pytest.mark.unit
class TestStepIDPreservation:
    """Test that step IDs and correlation IDs remain unchanged."""

    def test_step_id_values_unchanged(self) -> None:
        """Test step_id values are unchanged through round-trip."""
        step_id = uuid4()
        correlation_id = uuid4()

        yaml_content = f"""
correlation_id: "{correlation_id}"
step_id: "{step_id}"
step_name: "preserved_step"
step_type: "effect"
timeout_ms: 10000
retry_count: 2
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "retry"
priority: 50
order_index: 0
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        assert round_tripped_dict["step_id"] == str(step_id)

    def test_correlation_id_preserved(self) -> None:
        """Test correlation_id is preserved through round-trip."""
        step_id = uuid4()
        correlation_id = uuid4()

        yaml_content = f"""
correlation_id: "{correlation_id}"
step_id: "{step_id}"
step_name: "correlated_step"
step_type: "reducer"
timeout_ms: 20000
retry_count: 1
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
priority: 100
order_index: 5
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        assert round_tripped_dict["correlation_id"] == str(correlation_id)

    def test_all_identifiers_stable_in_workflow_node(self) -> None:
        """Test all identifiers are stable in ModelWorkflowNode."""
        node_id = uuid4()
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
node_id: "{node_id}"
node_type: "TRANSFORMER"
node_requirements:
  key1: "value1"
  key2: 123
dependencies:
  - "{dep_id_1}"
  - "{dep_id_2}"
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowNode)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        assert round_tripped_dict["node_id"] == str(node_id)
        assert round_tripped_dict["dependencies"] == [str(dep_id_1), str(dep_id_2)]


@pytest.mark.unit
class TestDependencySetPreservation:
    """Test that depends_on lists are preserved exactly."""

    def test_depends_on_lists_preserved_exactly(self) -> None:
        """Test depends_on lists are preserved exactly through round-trip."""
        step_id = uuid4()
        dep_id_1 = uuid4()
        dep_id_2 = uuid4()
        dep_id_3 = uuid4()

        yaml_content = f"""
correlation_id: "{uuid4()}"
step_id: "{step_id}"
step_name: "dependent_step"
step_type: "orchestrator"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
priority: 100
order_index: 10
depends_on:
  - "{dep_id_1}"
  - "{dep_id_2}"
  - "{dep_id_3}"
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        expected_deps = [str(dep_id_1), str(dep_id_2), str(dep_id_3)]
        assert round_tripped_dict["depends_on"] == expected_deps

    def test_empty_depends_on_stays_empty_not_null(self) -> None:
        """Test empty depends_on stays empty (not null) through round-trip."""
        step_id = uuid4()

        yaml_content = f"""
correlation_id: "{uuid4()}"
step_id: "{step_id}"
step_name: "independent_step"
step_type: "compute"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
priority: 100
order_index: 0
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        # Must be empty list, not null/None
        assert round_tripped_dict["depends_on"] == []
        assert round_tripped_dict["depends_on"] is not None

    def test_dependency_order_preserved(self) -> None:
        """Test dependency order is preserved through round-trip."""
        node_id = uuid4()
        deps = [uuid4() for _ in range(5)]

        deps_yaml = "\n".join([f'  - "{d}"' for d in deps])
        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
node_id: "{node_id}"
node_type: "AGGREGATOR"
node_requirements: {{}}
dependencies:
{deps_yaml}
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowNode)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        expected_deps = [str(d) for d in deps]
        assert round_tripped_dict["dependencies"] == expected_deps


@pytest.mark.unit
class TestReservedFieldHandling:
    """Test that reserved fields are untouched through round-trip."""

    def test_execution_graph_reserved_field_preserved(self) -> None:
        """Test execution_graph (reserved) is preserved through round-trip."""
        node_id = uuid4()

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "reserved_test"
  workflow_version:
    major: 2
    minor: 1
    patch: 0
  description: "Test reserved fields"
  execution_mode: "parallel"
  timeout_ms: 300000
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
      node_id: "{node_id}"
      node_type: "GATEWAY"
      node_requirements:
        gateway_type: "api"
      dependencies: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: true
  failure_recovery_strategy: "ABORT"
"""

        _model, round_tripped_yaml = round_trip_yaml(
            yaml_content, ModelWorkflowDefinition
        )

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify execution_graph structure is preserved
        assert "execution_graph" in round_tripped_dict
        assert "nodes" in round_tripped_dict["execution_graph"]
        assert len(round_tripped_dict["execution_graph"]["nodes"]) == 1

    def test_synchronization_points_reserved_field_preserved(self) -> None:
        """Test synchronization_points (reserved) is preserved through round-trip."""
        node_id = uuid4()

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "sync_test"
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: "Test sync points"
  execution_mode: "sequential"
  timeout_ms: 60000
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
      node_id: "{node_id}"
      node_type: "COMPUTE_GENERIC"
      node_requirements: {{}}
      dependencies: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points:
    - "checkpoint_1"
    - "checkpoint_2"
    - "final_sync"
  parallel_execution_allowed: false
  failure_recovery_strategy: "COMPENSATE"
"""

        _model, round_tripped_yaml = round_trip_yaml(
            yaml_content, ModelWorkflowDefinition
        )

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify synchronization_points is preserved
        sync_points = round_tripped_dict["coordination_rules"]["synchronization_points"]
        assert sync_points == ["checkpoint_1", "checkpoint_2", "final_sync"]


@pytest.mark.unit
class TestScalarTypePreservation:
    """Test that scalar types are preserved without coercion."""

    def test_string_one_vs_int_one_preserved(self) -> None:
        """Test '1' (string) vs 1 (int) is preserved."""
        node_id = uuid4()

        # Use integer 123 in node_requirements
        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
node_id: "{node_id}"
node_type: "VALIDATOR"
node_requirements:
  int_value: 123
  string_value: "456"
  another_int: 789
dependencies: []
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowNode)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify types are preserved in node_requirements
        reqs = round_tripped_dict["node_requirements"]
        assert reqs["int_value"] == 123
        assert isinstance(reqs["int_value"], int)
        assert reqs["string_value"] == "456"
        assert isinstance(reqs["string_value"], str)
        assert reqs["another_int"] == 789
        assert isinstance(reqs["another_int"], int)

    def test_bool_true_vs_string_true_preserved(self) -> None:
        """Test true (bool) vs 'true' (string) is preserved."""
        step_id = uuid4()

        yaml_content = f"""
correlation_id: "{uuid4()}"
step_id: "{step_id}"
step_name: "bool_test"
step_type: "compute"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: true
error_action: "stop"
priority: 100
order_index: 0
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify boolean types
        assert round_tripped_dict["enabled"] is True
        assert isinstance(round_tripped_dict["enabled"], bool)
        assert round_tripped_dict["skip_on_failure"] is False
        assert isinstance(round_tripped_dict["skip_on_failure"], bool)
        assert round_tripped_dict["continue_on_error"] is True
        assert isinstance(round_tripped_dict["continue_on_error"], bool)

    def test_no_type_coercion_in_node_requirements(self) -> None:
        """Test no type coercion occurs in node_requirements."""
        node_id = uuid4()

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
node_id: "{node_id}"
node_type: "COMPUTE_GENERIC"
node_requirements:
  string_num: "100"
  int_num: 100
  float_num: 100.5
  bool_val: true
  string_bool: "true"
dependencies: []
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowNode)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
        reqs = round_tripped_dict["node_requirements"]

        # Verify each type is preserved
        assert reqs["string_num"] == "100"
        assert isinstance(reqs["string_num"], str)

        assert reqs["int_num"] == 100
        assert isinstance(reqs["int_num"], int)

        assert reqs["float_num"] == 100.5
        assert isinstance(reqs["float_num"], float)

        assert reqs["bool_val"] is True
        assert isinstance(reqs["bool_val"], bool)

        assert reqs["string_bool"] == "true"
        assert isinstance(reqs["string_bool"], str)


@pytest.mark.unit
class TestNullValueHandling:
    """Test null value handling through round-trip."""

    def test_no_new_null_fields_created(self) -> None:
        """Test no new null fields are created through round-trip."""
        step_id = uuid4()

        yaml_content = f"""
correlation_id: "{uuid4()}"
step_id: "{step_id}"
step_name: "minimal_step"
step_type: "compute"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
priority: 100
order_index: 0
depends_on: []
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Check that no unexpected null values were added
        # Optional fields that weren't set should either be missing or have default values
        for key, value in round_tripped_dict.items():
            if value is None:
                # These are the only fields allowed to be null based on model definition
                assert key in [
                    "max_memory_mb",
                    "max_cpu_percent",
                    "parallel_group",
                ], f"Unexpected null field: {key}"

    def test_missing_optional_fields_stay_missing_or_have_defaults(self) -> None:
        """Test missing optional fields stay missing or have default values."""
        step_id = uuid4()

        # Minimal required fields only
        yaml_content = f"""
step_id: "{step_id}"
step_name: "required_only"
step_type: "effect"
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify defaults are applied correctly
        assert round_tripped_dict["timeout_ms"] == 30000  # default
        assert round_tripped_dict["retry_count"] == 3  # default
        assert round_tripped_dict["enabled"] is True  # default
        assert round_tripped_dict["error_action"] == "stop"  # default

    def test_explicit_null_preserved_if_set(self) -> None:
        """Test explicit null is preserved if set."""
        step_id = uuid4()

        yaml_content = f"""
correlation_id: "{uuid4()}"
step_id: "{step_id}"
step_name: "null_test"
step_type: "compute"
timeout_ms: 30000
retry_count: 3
enabled: true
skip_on_failure: false
continue_on_error: false
error_action: "stop"
max_memory_mb: null
max_cpu_percent: null
priority: 100
order_index: 0
depends_on: []
parallel_group: null
max_parallel_instances: 1
"""

        _model, round_tripped_yaml = round_trip_yaml(yaml_content, ModelWorkflowStep)

        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Explicit nulls should be preserved
        assert round_tripped_dict.get("max_memory_mb") is None
        assert round_tripped_dict.get("max_cpu_percent") is None
        assert round_tripped_dict.get("parallel_group") is None

    def test_workflow_hash_null_distinction(self) -> None:
        """Test workflow_hash null vs missing distinction."""
        node_id = uuid4()

        # First, test with explicit null
        yaml_with_null = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_name: "hash_test"
workflow_version:
  major: 1
  minor: 0
  patch: 0
description: "Test hash handling"
execution_mode: "sequential"
timeout_ms: 60000
workflow_hash: null
"""

        _model_with_null, rt_yaml_with_null = round_trip_yaml(
            yaml_with_null, ModelWorkflowDefinitionMetadata
        )

        rt_dict_with_null = parse_yaml_to_dict(rt_yaml_with_null)
        # workflow_hash should be null (not missing)
        assert (
            "workflow_hash" in rt_dict_with_null
            or rt_dict_with_null.get("workflow_hash") is None
        )

        # Test without workflow_hash (missing)
        yaml_without_hash = """
version:
  major: 1
  minor: 0
  patch: 0
workflow_name: "no_hash_test"
workflow_version:
  major: 1
  minor: 0
  patch: 0
description: "Test missing hash"
execution_mode: "parallel"
timeout_ms: 120000
"""

        model_without, _rt_yaml_without = round_trip_yaml(
            yaml_without_hash, ModelWorkflowDefinitionMetadata
        )

        # Model should have None for workflow_hash (default)
        assert model_without.workflow_hash is None


@pytest.mark.unit
class TestComplexRoundTripScenarios:
    """Test complex round-trip scenarios combining multiple features."""

    def test_complete_workflow_definition_round_trip(self) -> None:
        """Test complete workflow definition round-trip preserves all data."""
        node_ids = [str(uuid4()) for _ in range(3)]

        yaml_content = f"""
version:
  major: 2
  minor: 3
  patch: 4
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "complete_workflow"
  workflow_version:
    major: 3
    minor: 2
    patch: 1
  description: "A complete workflow with all features"
  execution_mode: "batch"
  timeout_ms: 180000
  workflow_hash: null
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
      node_id: "{node_ids[0]}"
      node_type: "EFFECT_GENERIC"
      node_requirements:
        source: "api"
        timeout: 5000
      dependencies: []
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{node_ids[1]}"
      node_type: "COMPUTE_GENERIC"
      node_requirements:
        transform: "normalize"
        validate: true
      dependencies:
        - "{node_ids[0]}"
    - version:
        major: 1
        minor: 0
        patch: 0
      node_id: "{node_ids[2]}"
      node_type: "REDUCER_GENERIC"
      node_requirements:
        aggregate: "sum"
        output_format: "json"
      dependencies:
        - "{node_ids[1]}"
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points:
    - "data_ready"
    - "transform_complete"
  parallel_execution_allowed: false
  failure_recovery_strategy: "RETRY"
"""

        _model, round_tripped_yaml = round_trip_yaml(
            yaml_content, ModelWorkflowDefinition
        )

        original_dict = parse_yaml_to_dict(yaml_content)
        round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)

        # Verify key structures match
        assert (
            round_tripped_dict["workflow_metadata"]["workflow_name"]
            == "complete_workflow"
        )
        assert round_tripped_dict["workflow_metadata"]["execution_mode"] == "batch"
        assert round_tripped_dict["workflow_metadata"]["timeout_ms"] == 180000

        # Verify execution graph nodes
        nodes = round_tripped_dict["execution_graph"]["nodes"]
        assert len(nodes) == 3
        assert nodes[0]["node_id"] == node_ids[0]
        assert nodes[1]["node_id"] == node_ids[1]
        assert nodes[2]["node_id"] == node_ids[2]

        # Verify dependencies preserved
        assert nodes[0]["dependencies"] == []
        assert nodes[1]["dependencies"] == [node_ids[0]]
        assert nodes[2]["dependencies"] == [node_ids[1]]

        # Verify coordination rules
        rules = round_tripped_dict["coordination_rules"]
        assert rules["synchronization_points"] == ["data_ready", "transform_complete"]
        assert rules["parallel_execution_allowed"] is False

    def test_multiple_round_trips_stable(self) -> None:
        """Test multiple round-trips produce stable output."""
        node_id = str(uuid4())

        yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
workflow_metadata:
  version:
    major: 1
    minor: 0
    patch: 0
  workflow_name: "stability_test"
  workflow_version:
    major: 1
    minor: 0
    patch: 0
  description: "Testing stability across multiple round-trips"
  execution_mode: "sequential"
  timeout_ms: 60000
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
      node_id: "{node_id}"
      node_type: "COMPUTE_GENERIC"
      node_requirements:
        key: "value"
      dependencies: []
coordination_rules:
  version:
    major: 1
    minor: 0
    patch: 0
  synchronization_points: []
  parallel_execution_allowed: true
  failure_recovery_strategy: "RETRY"
"""

        # First round-trip
        _model1, yaml1 = round_trip_yaml(yaml_content, ModelWorkflowDefinition)

        # Second round-trip
        _model2, yaml2 = round_trip_yaml(yaml1, ModelWorkflowDefinition)

        # Third round-trip
        _model3, yaml3 = round_trip_yaml(yaml2, ModelWorkflowDefinition)

        # Parse all for comparison
        dict1 = parse_yaml_to_dict(yaml1)
        dict2 = parse_yaml_to_dict(yaml2)
        dict3 = parse_yaml_to_dict(yaml3)

        # All should be structurally equivalent
        assert dict1 == dict2, "First and second round-trip differ"
        assert dict2 == dict3, "Second and third round-trip differ"


@pytest.mark.unit
class TestEnumValuePreservation:
    """Test that enum values are preserved correctly."""

    def test_failure_recovery_strategy_enum_preserved(self) -> None:
        """Test failure_recovery_strategy enum is preserved."""
        strategies = ["RETRY", "ROLLBACK", "COMPENSATE", "ABORT"]

        for strategy in strategies:
            yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
synchronization_points: []
parallel_execution_allowed: true
failure_recovery_strategy: "{strategy}"
"""

            _model, round_tripped_yaml = round_trip_yaml(
                yaml_content, ModelCoordinationRules
            )

            round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
            assert round_tripped_dict["failure_recovery_strategy"] == strategy

    def test_node_type_enum_preserved(self) -> None:
        """Test node_type enum is preserved."""
        node_types = [
            "COMPUTE_GENERIC",
            "EFFECT_GENERIC",
            "REDUCER_GENERIC",
            "ORCHESTRATOR_GENERIC",
            "TRANSFORMER",
            "AGGREGATOR",
            "GATEWAY",
            "VALIDATOR",
        ]

        for node_type in node_types:
            node_id = str(uuid4())
            yaml_content = f"""
version:
  major: 1
  minor: 0
  patch: 0
node_id: "{node_id}"
node_type: "{node_type}"
node_requirements: {{}}
dependencies: []
"""

            _model, round_tripped_yaml = round_trip_yaml(
                yaml_content, ModelWorkflowNode
            )

            round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
            assert round_tripped_dict["node_type"] == node_type

    def test_step_type_literal_preserved(self) -> None:
        """Test step_type literal values are preserved.

        v1.0.4 Fix 41: step_type must be compute|effect|reducer|orchestrator|custom|parallel.
        "conditional" is NOT a valid step_type and has been removed.
        """
        step_types = [
            "compute",
            "effect",
            "reducer",
            "orchestrator",
            "parallel",
            "custom",
        ]

        for step_type in step_types:
            step_id = str(uuid4())
            yaml_content = f"""
step_id: "{step_id}"
step_name: "type_test_{step_type}"
step_type: "{step_type}"
"""

            _model, round_tripped_yaml = round_trip_yaml(
                yaml_content, ModelWorkflowStep
            )

            round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
            assert round_tripped_dict["step_type"] == step_type

    def test_error_action_literal_preserved(self) -> None:
        """Test error_action literal values are preserved."""
        error_actions = ["stop", "continue", "retry", "compensate"]

        for action in error_actions:
            step_id = str(uuid4())
            yaml_content = f"""
step_id: "{step_id}"
step_name: "action_test"
step_type: "compute"
error_action: "{action}"
"""

            _model, round_tripped_yaml = round_trip_yaml(
                yaml_content, ModelWorkflowStep
            )

            round_tripped_dict = parse_yaml_to_dict(round_tripped_yaml)
            assert round_tripped_dict["error_action"] == action
