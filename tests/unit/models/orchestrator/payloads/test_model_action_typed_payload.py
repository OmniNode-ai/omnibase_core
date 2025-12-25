"""
Unit tests for model_action_typed_payload module.

Tests the integration between EnumActionType and the semantic-category-based
SpecificActionPayload system.
"""

import pytest

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_custom_action_payload import (
    ModelCustomActionPayload,
)
from omnibase_core.models.core.model_data_action_payload import ModelDataActionPayload
from omnibase_core.models.core.model_filesystem_action_payload import (
    ModelFilesystemActionPayload,
)
from omnibase_core.models.core.model_lifecycle_action_payload import (
    ModelLifecycleActionPayload,
)
from omnibase_core.models.core.model_management_action_payload import (
    ModelManagementActionPayload,
)
from omnibase_core.models.core.model_monitoring_action_payload import (
    ModelMonitoringActionPayload,
)
from omnibase_core.models.core.model_operational_action_payload import (
    ModelOperationalActionPayload,
)
from omnibase_core.models.core.model_transformation_action_payload import (
    ModelTransformationActionPayload,
)
from omnibase_core.models.core.model_validation_action_payload import (
    ModelValidationActionPayload,
)
from omnibase_core.models.orchestrator.payloads.model_action_typed_payload import (
    ActionPayloadType,
    create_action_payload,
    get_payload_type_for_semantic_action,
    get_recommended_payloads_for_action_type,
)


@pytest.mark.unit
class TestActionPayloadType:
    """Test the ActionPayloadType type alias."""

    def test_type_alias_is_union(self):
        """Test that ActionPayloadType is a union of all payload types."""
        # Create instances of each payload type and verify they match ActionPayloadType
        from omnibase_core.models.core.model_action_payload_types import (
            SpecificActionPayload,
        )

        # ActionPayloadType should be the same as SpecificActionPayload
        assert ActionPayloadType is SpecificActionPayload


@pytest.mark.unit
class TestGetRecommendedPayloads:
    """Test get_recommended_payloads_for_action_type function."""

    @pytest.mark.parametrize(
        ("action_type", "expected_types"),
        [
            (
                EnumActionType.COMPUTE,
                [
                    ModelTransformationActionPayload,
                    ModelValidationActionPayload,
                    ModelOperationalActionPayload,
                ],
            ),
            (
                EnumActionType.EFFECT,
                [
                    ModelDataActionPayload,
                    ModelFilesystemActionPayload,
                ],
            ),
            (
                EnumActionType.REDUCE,
                [
                    ModelOperationalActionPayload,
                    ModelMonitoringActionPayload,
                ],
            ),
            (
                EnumActionType.ORCHESTRATE,
                [
                    ModelManagementActionPayload,
                    ModelOperationalActionPayload,
                ],
            ),
            (
                EnumActionType.CUSTOM,
                [ModelCustomActionPayload],
            ),
        ],
    )
    def test_recommended_payloads(self, action_type, expected_types):
        """Test that recommended payloads contain expected types."""
        payloads = get_recommended_payloads_for_action_type(action_type)

        for expected_type in expected_types:
            assert expected_type in payloads, (
                f"{expected_type.__name__} should be in recommendations for {action_type}"
            )


@pytest.mark.unit
class TestCreateActionPayload:
    """Test create_action_payload factory function."""

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("read", ModelDataActionPayload),
            ("write", ModelDataActionPayload),
            ("create", ModelDataActionPayload),
            ("update", ModelDataActionPayload),
            ("delete", ModelDataActionPayload),
            ("search", ModelDataActionPayload),
            ("query", ModelDataActionPayload),
        ],
    )
    def test_data_actions(self, semantic_action, expected_type):
        """Test data semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.EFFECT,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)
        assert payload.action_type.name == semantic_action

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("scan", ModelFilesystemActionPayload),
            ("watch", ModelFilesystemActionPayload),
            ("sync", ModelFilesystemActionPayload),
        ],
    )
    def test_filesystem_actions(self, semantic_action, expected_type):
        """Test filesystem semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.EFFECT,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("transform", ModelTransformationActionPayload),
            ("convert", ModelTransformationActionPayload),
            ("parse", ModelTransformationActionPayload),
        ],
    )
    def test_transformation_actions(self, semantic_action, expected_type):
        """Test transformation semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.COMPUTE,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("validate", ModelValidationActionPayload),
            ("verify", ModelValidationActionPayload),
            ("check", ModelValidationActionPayload),
        ],
    )
    def test_validation_actions(self, semantic_action, expected_type):
        """Test validation semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.COMPUTE,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("health_check", ModelLifecycleActionPayload),
            ("initialize", ModelLifecycleActionPayload),
            ("shutdown", ModelLifecycleActionPayload),
            ("start", ModelLifecycleActionPayload),
            ("stop", ModelLifecycleActionPayload),
        ],
    )
    def test_lifecycle_actions(self, semantic_action, expected_type):
        """Test lifecycle semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.EFFECT,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            ("configure", ModelManagementActionPayload),
            ("deploy", ModelManagementActionPayload),
            ("migrate", ModelManagementActionPayload),
        ],
    )
    def test_management_actions(self, semantic_action, expected_type):
        """Test management semantic actions create correct payload type."""
        payload = create_action_payload(
            action_type=EnumActionType.ORCHESTRATE,
            semantic_action=semantic_action,
        )
        assert isinstance(payload, expected_type)

    def test_custom_action(self):
        """Test custom semantic action creates CustomActionPayload."""
        payload = create_action_payload(
            action_type=EnumActionType.CUSTOM,
            semantic_action="custom",
        )
        assert isinstance(payload, ModelCustomActionPayload)

    def test_default_semantic_action_compute(self):
        """Test default semantic action for COMPUTE is 'process'."""
        payload = create_action_payload(action_type=EnumActionType.COMPUTE)
        assert payload.action_type.name == "process"

    def test_default_semantic_action_effect(self):
        """Test default semantic action for EFFECT is 'execute'."""
        payload = create_action_payload(action_type=EnumActionType.EFFECT)
        assert payload.action_type.name == "execute"

    def test_default_semantic_action_reduce(self):
        """Test default semantic action for REDUCE is 'aggregate'."""
        payload = create_action_payload(action_type=EnumActionType.REDUCE)
        assert payload.action_type.name == "aggregate"

    def test_default_semantic_action_orchestrate(self):
        """Test default semantic action for ORCHESTRATE is 'coordinate'."""
        payload = create_action_payload(action_type=EnumActionType.ORCHESTRATE)
        assert payload.action_type.name == "coordinate"

    def test_kwargs_passed_to_payload(self):
        """Test that additional kwargs are passed to the payload."""
        payload = create_action_payload(
            action_type=EnumActionType.EFFECT,
            semantic_action="read",
            target_path="/data/users.json",
            limit=100,
        )
        assert isinstance(payload, ModelDataActionPayload)
        assert payload.target_path == "/data/users.json"
        assert payload.limit == 100


@pytest.mark.unit
class TestGetPayloadTypeForSemanticAction:
    """Test get_payload_type_for_semantic_action function."""

    @pytest.mark.parametrize(
        ("semantic_action", "expected_type"),
        [
            # Data actions
            ("read", ModelDataActionPayload),
            ("write", ModelDataActionPayload),
            ("create", ModelDataActionPayload),
            ("update", ModelDataActionPayload),
            ("delete", ModelDataActionPayload),
            ("search", ModelDataActionPayload),
            ("query", ModelDataActionPayload),
            # Filesystem actions
            ("scan", ModelFilesystemActionPayload),
            ("watch", ModelFilesystemActionPayload),
            ("sync", ModelFilesystemActionPayload),
            # Lifecycle actions
            ("health_check", ModelLifecycleActionPayload),
            ("initialize", ModelLifecycleActionPayload),
            ("shutdown", ModelLifecycleActionPayload),
            # Validation actions
            ("validate", ModelValidationActionPayload),
            ("verify", ModelValidationActionPayload),
            ("check", ModelValidationActionPayload),
            # Transformation actions
            ("transform", ModelTransformationActionPayload),
            ("convert", ModelTransformationActionPayload),
            ("parse", ModelTransformationActionPayload),
            # Management actions
            ("configure", ModelManagementActionPayload),
            ("deploy", ModelManagementActionPayload),
            ("migrate", ModelManagementActionPayload),
            # Monitoring actions
            ("monitor", ModelMonitoringActionPayload),
            ("collect", ModelMonitoringActionPayload),
            ("report", ModelMonitoringActionPayload),
            # Custom action
            ("custom", ModelCustomActionPayload),
        ],
    )
    def test_known_actions_return_correct_type(self, semantic_action, expected_type):
        """Test that known semantic actions return correct payload type."""
        payload_type = get_payload_type_for_semantic_action(semantic_action)
        assert payload_type is expected_type

    def test_unknown_action_returns_operational(self):
        """Test that unknown actions default to ModelOperationalActionPayload."""
        payload_type = get_payload_type_for_semantic_action("unknown_action")
        assert payload_type is ModelOperationalActionPayload


@pytest.mark.unit
class TestModuleImports:
    """Test that module imports work correctly from orchestrator.payloads."""

    def test_import_from_payloads_init(self):
        """Test importing from orchestrator.payloads package."""
        from omnibase_core.models.orchestrator.payloads import (
            ActionPayloadType,
            ModelActionPayloadBase,
            ModelCustomActionPayload,
            ModelDataActionPayload,
            ModelFilesystemActionPayload,
            ModelLifecycleActionPayload,
            ModelManagementActionPayload,
            ModelMonitoringActionPayload,
            ModelOperationalActionPayload,
            ModelRegistryActionPayload,
            ModelTransformationActionPayload,
            ModelValidationActionPayload,
            SpecificActionPayload,
            create_action_payload,
            create_specific_action_payload,
            get_recommended_payloads_for_action_type,
        )

        # Verify all imports work
        assert ActionPayloadType is not None
        assert ModelActionPayloadBase is not None
        assert SpecificActionPayload is not None
        assert create_action_payload is not None
        assert create_specific_action_payload is not None
        assert get_recommended_payloads_for_action_type is not None

        # Verify payload types
        assert ModelDataActionPayload is not None
        assert ModelFilesystemActionPayload is not None
        assert ModelLifecycleActionPayload is not None
        assert ModelTransformationActionPayload is not None
        assert ModelValidationActionPayload is not None
        assert ModelManagementActionPayload is not None
        assert ModelMonitoringActionPayload is not None
        assert ModelRegistryActionPayload is not None
        assert ModelOperationalActionPayload is not None
        assert ModelCustomActionPayload is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
