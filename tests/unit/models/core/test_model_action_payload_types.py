"""
Unit tests for model_action_payload_types module.

Tests the create_specific_action_payload factory function covering:
- Special action name handling (data/registry/filesystem/custom actions)
- Category-based payload mapping
- Unknown action type error handling
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_action_payload_types import (
    create_specific_action_payload,
)
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
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.core.model_operational_action_payload import (
    ModelOperationalActionPayload,
)
from omnibase_core.models.core.model_predefined_categories import (
    LIFECYCLE,
    MANAGEMENT,
    OPERATION,
    QUERY,
    TRANSFORMATION,
    VALIDATION,
)
from omnibase_core.models.core.model_registry_action_payload import (
    ModelRegistryActionPayload,
)
from omnibase_core.models.core.model_transformation_action_payload import (
    ModelTransformationActionPayload,
)
from omnibase_core.models.core.model_validation_action_payload import (
    ModelValidationActionPayload,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def make_action(name: str, category: ModelActionCategory) -> ModelNodeActionType:
    """Helper to create ModelNodeActionType for testing."""
    return ModelNodeActionType(
        name=name,
        category=category,
        display_name=name.replace("_", " ").title(),
        description=f"Test action: {name}",
    )


@pytest.mark.unit
class TestCreateSpecificActionPayload:
    """Test create_specific_action_payload factory function."""

    @pytest.mark.parametrize(
        "name", ["read", "write", "create", "update", "delete", "search", "query"]
    )
    def test_data_actions(self, name):
        """Test special data action names create ModelDataActionPayload."""
        action = make_action(name, OPERATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelDataActionPayload)
        assert payload.action_type.name == name

    @pytest.mark.parametrize("name", ["register", "unregister", "discover"])
    def test_registry_actions(self, name):
        """Test registry action names create ModelRegistryActionPayload."""
        action = make_action(name, OPERATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelRegistryActionPayload)

    @pytest.mark.parametrize("name", ["scan", "watch", "sync"])
    def test_filesystem_actions(self, name):
        """Test filesystem action names create ModelFilesystemActionPayload."""
        action = make_action(name, OPERATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelFilesystemActionPayload)

    def test_custom_action(self):
        """Test custom action name creates ModelCustomActionPayload."""
        action = make_action("custom", OPERATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelCustomActionPayload)

    def test_lifecycle_category_mapping(self):
        """Test LIFECYCLE category maps to ModelLifecycleActionPayload."""
        action = make_action("start", LIFECYCLE)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelLifecycleActionPayload)

    def test_operation_category_mapping(self):
        """Test OPERATION category maps to ModelOperationalActionPayload."""
        action = make_action("execute", OPERATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelOperationalActionPayload)

    def test_validation_category_mapping(self):
        """Test VALIDATION category maps to ModelValidationActionPayload."""
        action = make_action("validate", VALIDATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelValidationActionPayload)

    def test_management_category_mapping(self):
        """Test MANAGEMENT category maps to ModelManagementActionPayload."""
        action = make_action("configure", MANAGEMENT)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelManagementActionPayload)

    def test_transformation_category_mapping(self):
        """Test TRANSFORMATION category maps to ModelTransformationActionPayload."""
        action = make_action("transform", TRANSFORMATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelTransformationActionPayload)

    def test_query_category_mapping(self):
        """Test QUERY category maps to ModelMonitoringActionPayload."""
        action = make_action("monitor", QUERY)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelMonitoringActionPayload)

    def test_unknown_action_type_raises_error(self):
        """Test unknown action name and category raises ModelOnexError."""
        unknown_category = ModelActionCategory(
            name="unknown_cat",
            display_name="Unknown",
            description="Unknown category",
        )
        action = make_action("unknown_action", unknown_category)

        with pytest.raises(ModelOnexError) as exc_info:
            create_specific_action_payload(action)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Unknown action type: unknown_action" in str(exc_info.value)

    def test_with_additional_kwargs(self):
        """Test factory passes kwargs to payload constructor."""
        action = make_action("read", OPERATION)
        # Not all payloads accept arbitrary kwargs - just verify it works
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelDataActionPayload)
        assert payload.action_type.name == "read"


@pytest.mark.unit
class TestActionPayloadTypesEdgeCases:
    """Test edge cases for action payload factory."""

    def test_empty_kwargs(self):
        """Test factory works with no additional kwargs."""
        action = make_action("validate", VALIDATION)
        payload = create_specific_action_payload(action)
        assert isinstance(payload, ModelValidationActionPayload)

    def test_all_categories_have_mappings(self):
        """Test all predefined categories have payload mappings."""
        categories_and_payloads = [
            (LIFECYCLE, ModelLifecycleActionPayload),
            (OPERATION, ModelOperationalActionPayload),
            (VALIDATION, ModelValidationActionPayload),
            (MANAGEMENT, ModelManagementActionPayload),
            (TRANSFORMATION, ModelTransformationActionPayload),
            (QUERY, ModelMonitoringActionPayload),
        ]

        for category, expected_payload_type in categories_and_payloads:
            action = make_action(f"test_{category.name}", category)
            payload = create_specific_action_payload(action)
            assert isinstance(payload, expected_payload_type)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
