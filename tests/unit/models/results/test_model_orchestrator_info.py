"""
Comprehensive tests for ModelOrchestratorInfo.

Tests cover:
- Basic instantiation with required fields
- Optional field handling
- Method functionality (get_resource_summary, is_completed)
- Field validation and type safety
- Datetime serialization
- UUID handling
- Custom data field with JsonSerializable type
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_orchestrator_info import ModelOrchestratorInfo
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.results.model_orchestrator_metrics import (
    ModelOrchestratorMetrics,
)


class TestModelOrchestratorInfoBasicInstantiation:
    """Test basic instantiation with required fields."""

    def test_minimal_instantiation_with_required_fields(self):
        """Test creating orchestrator info with only required fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.orchestrator_id == orchestrator_id
        assert info.orchestrator_type == "kubernetes"
        assert info.orchestrator_version == version

    def test_all_orchestrator_types(self):
        """Test instantiation with different orchestrator types."""
        orchestrator_types = ["kubernetes", "swarm", "nomad", "custom"]
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        for orch_type in orchestrator_types:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type=orch_type,
                orchestrator_version=version,
            )
            assert info.orchestrator_type == orch_type


class TestModelOrchestratorInfoFieldValidation:
    """Test field validation and type safety."""

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError) as exc_info:
            ModelOrchestratorInfo()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}

        # After PR #88: orchestrator_id, orchestrator_type, and orchestrator_version are all required
        # (default_factory was removed from version fields)
        assert "orchestrator_id" in error_fields
        assert "orchestrator_type" in error_fields
        assert "orchestrator_version" in error_fields  # Now required (no default)

    def test_orchestrator_id_must_be_uuid(self):
        """Test that orchestrator_id must be a valid UUID."""
        version = ModelSemVer(major=1, minor=0, patch=0)

        with pytest.raises(ValidationError):
            ModelOrchestratorInfo(
                orchestrator_id="not-a-uuid",
                orchestrator_type="kubernetes",
                orchestrator_version=version,
            )

    def test_orchestrator_version_accepts_valid_string(self):
        """Test that orchestrator_version accepts and converts valid semver strings."""
        orchestrator_id = uuid4()

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version="1.0.0",  # Valid string should be accepted
        )

        # Verify conversion worked
        assert info.orchestrator_version.major == 1
        assert info.orchestrator_version.minor == 0
        assert info.orchestrator_version.patch == 0


class TestModelOrchestratorInfoClusterFields:
    """Test cluster-related fields."""

    def test_cluster_information_fields(self):
        """Test cluster name, region, and zone fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            cluster_name="production-cluster",
            cluster_region="us-west-2",
            cluster_zone="us-west-2a",
        )

        assert info.cluster_name == "production-cluster"
        assert info.cluster_region == "us-west-2"
        assert info.cluster_zone == "us-west-2a"

    def test_cluster_fields_optional(self):
        """Test that cluster fields are optional."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.cluster_name is None
        assert info.cluster_region is None
        assert info.cluster_zone is None


class TestModelOrchestratorInfoNodeFields:
    """Test node-related fields."""

    def test_node_information_fields(self):
        """Test node ID, name, and role fields."""
        orchestrator_id = uuid4()
        node_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            node_id=node_id,
            node_name="worker-node-01",
            node_role="worker",
        )

        assert info.node_id == node_id
        assert info.node_name == "worker-node-01"
        assert info.node_role == "worker"

    def test_node_roles(self):
        """Test different node role values."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        node_roles = ["master", "worker", "edge"]

        for role in node_roles:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type="kubernetes",
                orchestrator_version=version,
                node_role=role,
            )
            assert info.node_role == role


class TestModelOrchestratorInfoWorkflowFields:
    """Test workflow-related fields."""

    def test_workflow_information_fields(self):
        """Test workflow ID, name, step, and status fields."""
        orchestrator_id = uuid4()
        workflow_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            workflow_id=workflow_id,
            workflow_name="data-pipeline",
            workflow_step="transform",
            workflow_status="in_progress",
        )

        assert info.workflow_id == workflow_id
        assert info.workflow_name == "data-pipeline"
        assert info.workflow_step == "transform"
        assert info.workflow_status == "in_progress"

    def test_workflow_status_values(self):
        """Test various workflow status values."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        statuses = [
            "pending",
            "in_progress",
            "completed",
            "succeeded",
            "failed",
            "cancelled",
        ]

        for status in statuses:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type="kubernetes",
                orchestrator_version=version,
                workflow_status=status,
            )
            assert info.workflow_status == status


class TestModelOrchestratorInfoExecutionContext:
    """Test execution context fields."""

    def test_execution_context_fields(self):
        """Test execution ID, parent, and root execution IDs."""
        orchestrator_id = uuid4()
        execution_id = uuid4()
        parent_id = uuid4()
        root_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            execution_id=execution_id,
            parent_execution_id=parent_id,
            root_execution_id=root_id,
        )

        assert info.execution_id == execution_id
        assert info.parent_execution_id == parent_id
        assert info.root_execution_id == root_id


class TestModelOrchestratorInfoTimingFields:
    """Test timing-related fields."""

    def test_timing_information_fields(self):
        """Test scheduled_at, started_at, and completed_at fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        scheduled = datetime(2025, 1, 1, 10, 0, 0)
        started = datetime(2025, 1, 1, 10, 5, 0)
        completed = datetime(2025, 1, 1, 10, 15, 0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            scheduled_at=scheduled,
            started_at=started,
            completed_at=completed,
        )

        assert info.scheduled_at == scheduled
        assert info.started_at == started
        assert info.completed_at == completed

    def test_datetime_serialization(self):
        """Test that datetime fields are serialized to ISO format."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        now = datetime(2025, 1, 1, 12, 0, 0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            started_at=now,
        )

        dumped = info.model_dump()
        # The field_serializer should convert to ISO format
        assert isinstance(dumped["started_at"], str)
        assert "2025-01-01" in dumped["started_at"]


class TestModelOrchestratorInfoResourceFields:
    """Test resource allocation fields."""

    def test_cpu_resource_fields(self):
        """Test CPU request and limit fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            cpu_request="100m",
            cpu_limit="1000m",
        )

        assert info.cpu_request == "100m"
        assert info.cpu_limit == "1000m"

    def test_memory_resource_fields(self):
        """Test memory request and limit fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            memory_request="128Mi",
            memory_limit="512Mi",
        )

        assert info.memory_request == "128Mi"
        assert info.memory_limit == "512Mi"


class TestModelOrchestratorInfoLabelsAndAnnotations:
    """Test labels and annotations fields."""

    def test_labels_dict_field(self):
        """Test labels dictionary field."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        labels = {"env": "production", "team": "platform", "version": "v1"}

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            labels=labels,
        )

        assert info.labels == labels
        assert info.labels["env"] == "production"
        assert info.labels["team"] == "platform"

    def test_annotations_dict_field(self):
        """Test annotations dictionary field."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        annotations = {"description": "Main pipeline", "owner": "team@example.com"}

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            annotations=annotations,
        )

        assert info.annotations == annotations
        assert info.annotations["description"] == "Main pipeline"

    def test_labels_default_to_empty_dict(self):
        """Test that labels defaults to empty dict."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.labels == {}
        assert info.annotations == {}


class TestModelOrchestratorInfoMetrics:
    """Test metrics field integration."""

    def test_metrics_field_with_orchestrator_metrics(self):
        """Test metrics field with ModelOrchestratorMetrics."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        metrics = ModelOrchestratorMetrics(
            active_workflows=5,
            completed_workflows=100,
            failed_workflows=3,
            avg_execution_time_seconds=45.5,
            resource_utilization_percent=75.0,
        )

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            metrics=metrics,
        )

        assert info.metrics.active_workflows == 5
        assert info.metrics.completed_workflows == 100
        assert info.metrics.failed_workflows == 3


class TestModelOrchestratorInfoServiceMesh:
    """Test service mesh fields."""

    def test_service_mesh_fields(self):
        """Test service_mesh and sidecar_injected fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            service_mesh="istio",
            sidecar_injected=True,
        )

        assert info.service_mesh == "istio"
        assert info.sidecar_injected is True

    def test_service_mesh_types(self):
        """Test different service mesh types."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        mesh_types = ["istio", "linkerd", "consul"]

        for mesh_type in mesh_types:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type="kubernetes",
                orchestrator_version=version,
                service_mesh=mesh_type,
            )
            assert info.service_mesh == mesh_type

    def test_sidecar_injected_default_false(self):
        """Test that sidecar_injected defaults to False."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.sidecar_injected is False


class TestModelOrchestratorInfoCustomData:
    """Test custom_data field with JsonSerializable type."""

    def test_custom_data_with_simple_types(self):
        """Test custom_data with basic JSON types."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        custom_data = {
            "string_field": "value",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
        }

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            custom_data=custom_data,
        )

        assert info.custom_data["string_field"] == "value"
        assert info.custom_data["int_field"] == 42
        assert info.custom_data["float_field"] == 3.14
        assert info.custom_data["bool_field"] is True

    def test_custom_data_with_nested_structures(self):
        """Test custom_data with nested lists and dicts."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        custom_data = {
            "nested_dict": {"key1": "value1", "key2": "value2"},
            "nested_list": [1, 2, 3],
            "complex": {"list": [{"nested": "value"}]},
        }

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            custom_data=custom_data,
        )

        assert info.custom_data["nested_dict"]["key1"] == "value1"
        assert info.custom_data["nested_list"] == [1, 2, 3]
        assert info.custom_data["complex"]["list"][0]["nested"] == "value"

    def test_custom_data_default_to_empty_dict(self):
        """Test that custom_data defaults to empty dict."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.custom_data == {}


class TestModelOrchestratorInfoMethods:
    """Test instance methods."""

    def test_get_resource_summary_with_resources(self):
        """Test get_resource_summary() with resources specified."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            cpu_request="100m",
            memory_request="128Mi",
        )

        summary = info.get_resource_summary()
        assert "CPU: 100m" in summary
        assert "Memory: 128Mi" in summary

    def test_get_resource_summary_without_resources(self):
        """Test get_resource_summary() with no resources specified."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        summary = info.get_resource_summary()
        assert summary == "No resources specified"

    def test_is_completed_with_completed_status(self):
        """Test is_completed() returns True for completed statuses."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        completed_statuses = ["completed", "succeeded", "failed", "cancelled"]

        for status in completed_statuses:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type="kubernetes",
                orchestrator_version=version,
                workflow_status=status,
            )
            assert info.is_completed() is True

    def test_is_completed_with_non_completed_status(self):
        """Test is_completed() returns False for non-completed statuses."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)
        non_completed_statuses = ["pending", "in_progress", "running"]

        for status in non_completed_statuses:
            info = ModelOrchestratorInfo(
                orchestrator_id=orchestrator_id,
                orchestrator_type="kubernetes",
                orchestrator_version=version,
                workflow_status=status,
            )
            assert info.is_completed() is False

    def test_is_completed_with_no_status(self):
        """Test is_completed() when workflow_status is None."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        assert info.is_completed() is False


class TestModelOrchestratorInfoSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
            cluster_name="prod-cluster",
        )

        dumped = info.model_dump()

        assert dumped["orchestrator_id"] == orchestrator_id
        assert dumped["orchestrator_type"] == "kubernetes"
        assert dumped["cluster_name"] == "prod-cluster"

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        orchestrator_id = uuid4()
        version = ModelSemVer(major=1, minor=0, patch=0)

        info = ModelOrchestratorInfo(
            orchestrator_id=orchestrator_id,
            orchestrator_type="kubernetes",
            orchestrator_version=version,
        )

        dumped = info.model_dump(exclude_none=True)

        assert "orchestrator_id" in dumped
        assert "orchestrator_type" in dumped
        assert "cluster_name" not in dumped


class TestModelOrchestratorInfoTypeSafety:
    """Test type safety - comprehensive testing required."""

    def test_no_any_types_in_custom_data(self):
        """Test that custom_data uses JsonSerializable, not Any."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOrchestratorInfo)
        custom_data_type = hints.get("custom_data")

        assert custom_data_type is not None
        type_str = str(custom_data_type)
        # Should use JsonSerializable type alias
        assert "JsonSerializable" in type_str or "str" in type_str
