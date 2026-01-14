from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

from omnibase_core.enums.enum_base_status import EnumBaseStatus
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.enums.enum_function_lifecycle_status import (
    EnumFunctionLifecycleStatus,
)
from omnibase_core.enums.enum_general_status import EnumGeneralStatus
from omnibase_core.enums.enum_scenario_status_v2 import EnumScenarioStatusV2

"""
Status Enum Migration Utilities.

Provides utilities for migrating from the old conflicting status enums to the
new unified status hierarchy.

Usage:
    # Migrate enum values
    migrator = ModelEnumStatusMigrator()
    new_status = migrator.migrate_execution_status(old_value)
"""

# Legacy enum value mappings for migration
LEGACY_ENUM_STATUS_VALUES = {
    "active",
    "inactive",
    "pending",
    "processing",
    "completed",
    "failed",
    "created",
    "updated",
    "deleted",
    "archived",
    "valid",
    "invalid",
    "unknown",
    "approved",
    "rejected",
    "under_review",
    "available",
    "unavailable",
    "maintenance",
    "draft",
    "published",
    "deprecated",
    "enabled",
    "disabled",
    "suspended",
}

LEGACY_EXECUTION_STATUS_VALUES = {
    "pending",
    "running",
    "completed",
    "success",
    "failed",
    "skipped",
    "cancelled",
    "timeout",
}

LEGACY_SCENARIO_STATUS_VALUES = {
    "not_executed",
    "queued",
    "running",
    "completed",
    "failed",
    "skipped",
}

LEGACY_FUNCTION_STATUS_VALUES = {
    "active",
    "deprecated",
    "disabled",
    "experimental",
    "maintenance",
}

LEGACY_METADATA_NODE_STATUS_VALUES = {
    "active",
    "deprecated",
    "disabled",
    "experimental",
    "stable",
    "beta",
    "alpha",
}


def _get_core_error_code() -> type[EnumCoreErrorCode]:
    """Get EnumCoreErrorCode class at runtime to avoid circular import."""
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

    return EnumCoreErrorCode


def _get_onex_error() -> type[ModelOnexError]:
    """Get ModelOnexError class at runtime to avoid circular import."""
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

    return ModelOnexError


class ModelEnumStatusMigrator:
    """
    Migrates status values from old enums to new unified hierarchy.
    """

    @staticmethod
    def migrate_general_status(old_value: str) -> EnumGeneralStatus:
        """
        Migrate from legacy EnumStatus to EnumGeneralStatus.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumGeneralStatus value

        Raises:
            ModelOnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_ENUM_STATUS_VALUES:
            raise _get_onex_error()(
                code=_get_core_error_code().VALIDATION_ERROR,
                message=f"Unknown legacy status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumGeneralStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=_get_core_error_code().CONVERSION_ERROR,
                message=f"Cannot migrate status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_execution_status(old_value: str) -> EnumExecutionStatus:
        """
        Migrate from legacy EnumExecutionStatus to EnumExecutionStatus.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumExecutionStatus value

        Raises:
            ModelOnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_EXECUTION_STATUS_VALUES:
            raise _get_onex_error()(
                code=_get_core_error_code().VALIDATION_ERROR,
                message=f"Unknown legacy execution status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumExecutionStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=_get_core_error_code().CONVERSION_ERROR,
                message=f"Cannot migrate execution status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_scenario_status(old_value: str) -> EnumScenarioStatusV2:
        """
        Migrate from legacy EnumScenarioStatus to EnumScenarioStatusV2.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumScenarioStatusV2 value

        Raises:
            ModelOnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_SCENARIO_STATUS_VALUES:
            raise _get_onex_error()(
                code=_get_core_error_code().VALIDATION_ERROR,
                message=f"Unknown legacy scenario status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumScenarioStatusV2(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=_get_core_error_code().CONVERSION_ERROR,
                message=f"Cannot migrate scenario status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_function_status(old_value: str) -> EnumFunctionLifecycleStatus:
        """
        Migrate from legacy EnumFunctionStatus to EnumFunctionLifecycleStatus.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumFunctionLifecycleStatus value

        Raises:
            ModelOnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_FUNCTION_STATUS_VALUES:
            raise _get_onex_error()(
                code=_get_core_error_code().VALIDATION_ERROR,
                message=f"Unknown legacy function status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumFunctionLifecycleStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=_get_core_error_code().CONVERSION_ERROR,
                message=f"Cannot migrate function status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_metadata_node_status(old_value: str) -> EnumFunctionLifecycleStatus:
        """
        Migrate from legacy EnumMetadataNodeStatus to EnumFunctionLifecycleStatus.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumFunctionLifecycleStatus value

        Raises:
            ModelOnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_METADATA_NODE_STATUS_VALUES:
            raise _get_onex_error()(
                code=_get_core_error_code().VALIDATION_ERROR,
                message=f"Unknown legacy metadata node status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumFunctionLifecycleStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=_get_core_error_code().CONVERSION_ERROR,
                message=f"Cannot migrate metadata node status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_to_base_status(old_value: str, source_enum: str) -> EnumBaseStatus:
        """
        Migrate any status value to base status for universal operations.

        Args:
            old_value: String value from legacy enum
            source_enum: Name of source enum for context

        Returns:
            Corresponding EnumBaseStatus value
        """
        # Migrate to appropriate new enum and convert to base status directly
        if source_enum.lower() == "enumstatus":
            return ModelEnumStatusMigrator.migrate_general_status(
                old_value
            ).to_base_status()
        if source_enum.lower() == "enumexecutionstatus":
            return ModelEnumStatusMigrator.migrate_execution_status(
                old_value,
            ).to_base_status()
        if source_enum.lower() == "enumscenariostatus":
            return ModelEnumStatusMigrator.migrate_scenario_status(
                old_value,
            ).to_base_status()
        if source_enum.lower() in ["enumfunctionstatus", "enummetadatanodestatus"]:
            return ModelEnumStatusMigrator.migrate_function_status(
                old_value,
            ).to_base_status()

        raise _get_onex_error()(
            code=_get_core_error_code().VALIDATION_ERROR,
            message=f"Unknown source enum: {source_enum}",
        )


# Export for use
__all__ = [
    "LEGACY_ENUM_STATUS_VALUES",
    "LEGACY_EXECUTION_STATUS_VALUES",
    "LEGACY_FUNCTION_STATUS_VALUES",
    "LEGACY_METADATA_NODE_STATUS_VALUES",
    "LEGACY_SCENARIO_STATUS_VALUES",
    "ModelEnumStatusMigrator",
]
