"""
Status Enum Migration Utilities.

Provides utilities for migrating from the old conflicting status enums to the
new unified status hierarchy.

Usage:
    # Migrate enum values
    migrator = EnumStatusMigrator()
    new_status = migrator.migrate_execution_status(old_status)

    # Validate migration
    validator = EnumStatusMigrationValidator()
    issues = validator.validate_model_migration(model_class)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypedDict, TypeVar

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

from .enum_execution_status_v2 import EnumExecutionStatusV2
from .enum_function_lifecycle_status import EnumFunctionLifecycleStatus
from .enum_general_status import EnumGeneralStatus
from .enum_scenario_status_v2 import EnumScenarioStatusV2

if TYPE_CHECKING:
    from .enum_base_status import EnumBaseStatus


def _get_onex_error() -> type:
    """Get OnexError class at runtime to avoid circular import."""
    from omnibase_core.exceptions.onex_error import OnexError

    return OnexError


class EnumStatusProtocol(Protocol):
    """Protocol for status enums that can be migrated and converted to base status."""

    value: str

    def to_base_status(self) -> EnumBaseStatus:
        """Convert this status to its base status equivalent."""
        ...


# TypeVar for type-safe enum migration (ONEX compliant)
StatusEnumType = TypeVar("StatusEnumType", bound=EnumStatusProtocol)


# TypedDict for validation result structure
class ValidationResult(TypedDict):
    """Typed dictionary for migration validation results."""

    success: bool
    old_value: str
    old_enum: str
    new_enum: str
    migrated_value: str | None
    base_status_equivalent: str | None
    warnings: list[str]
    errors: list[str]


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


class EnumStatusMigrator:
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
            OnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_ENUM_STATUS_VALUES:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown legacy status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumGeneralStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.CONVERSION_ERROR,
                message=f"Cannot migrate status value: {old_value}",
                cause=e,
            ) from e

    @staticmethod
    def migrate_execution_status(old_value: str) -> EnumExecutionStatusV2:
        """
        Migrate from legacy EnumExecutionStatus to EnumExecutionStatusV2.

        Args:
            old_value: String value from legacy enum

        Returns:
            Corresponding EnumExecutionStatusV2 value

        Raises:
            OnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_EXECUTION_STATUS_VALUES:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown legacy execution status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumExecutionStatusV2(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.CONVERSION_ERROR,
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
            OnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_SCENARIO_STATUS_VALUES:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown legacy scenario status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumScenarioStatusV2(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.CONVERSION_ERROR,
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
            OnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_FUNCTION_STATUS_VALUES:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown legacy function status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumFunctionLifecycleStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.CONVERSION_ERROR,
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
            OnexError: If old_value cannot be migrated
        """
        if old_value not in LEGACY_METADATA_NODE_STATUS_VALUES:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unknown legacy metadata node status value: {old_value}",
            )

        # Direct mapping for values that exist in both
        try:
            return EnumFunctionLifecycleStatus(old_value)
        except ValueError as e:
            raise _get_onex_error()(
                code=EnumCoreErrorCode.CONVERSION_ERROR,
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
            return EnumStatusMigrator.migrate_general_status(old_value).to_base_status()
        if source_enum.lower() == "enumexecutionstatus":
            return EnumStatusMigrator.migrate_execution_status(
                old_value,
            ).to_base_status()
        if source_enum.lower() == "enumscenariostatus":
            return EnumStatusMigrator.migrate_scenario_status(
                old_value,
            ).to_base_status()
        if source_enum.lower() in ["enumfunctionstatus", "enummetadatanodestatus"]:
            return EnumStatusMigrator.migrate_function_status(
                old_value,
            ).to_base_status()

        raise _get_onex_error()(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Unknown source enum: {source_enum}",
        )


class EnumStatusMigrationValidator:
    """
    Validates status enum migrations and identifies potential issues.
    """

    @staticmethod
    def validate_value_migration(
        old_value: str,
        old_enum_name: str,
        expected_new_enum: type,
    ) -> ValidationResult:
        """
        Validate that a value can be safely migrated.

        Args:
            old_value: Original status value
            old_enum_name: Name of original enum
            expected_new_enum: Expected target enum class

        Returns:
            Validation result with success status and details
        """
        result: ValidationResult = {
            "success": False,
            "old_value": old_value,
            "old_enum": old_enum_name,
            "new_enum": expected_new_enum.__name__,
            "migrated_value": None,
            "base_status_equivalent": None,
            "warnings": [],
            "errors": [],
        }

        try:
            # Attempt migration
            migrator = EnumStatusMigrator()

            if old_enum_name.lower() == "enumstatus":
                general_migrated = migrator.migrate_general_status(old_value)
                result["success"] = True
                result["migrated_value"] = general_migrated.value
                result["base_status_equivalent"] = (
                    general_migrated.to_base_status().value
                )

                # Check for semantic changes
                base_status = general_migrated.to_base_status()
                if base_status.value != old_value:
                    result["warnings"].append(
                        f"Base status mapping changed: "
                        f"{old_value} -> {base_status.value}",
                    )

            if old_enum_name.lower() == "enumexecutionstatus":
                execution_migrated = migrator.migrate_execution_status(old_value)
                result["success"] = True
                result["migrated_value"] = execution_migrated.value
                result["base_status_equivalent"] = (
                    execution_migrated.to_base_status().value
                )

                # Check for semantic changes
                base_status = execution_migrated.to_base_status()
                if base_status.value != old_value:
                    result["warnings"].append(
                        f"Base status mapping changed: "
                        f"{old_value} -> {base_status.value}",
                    )

            if old_enum_name.lower() == "enumscenariostatus":
                scenario_migrated = migrator.migrate_scenario_status(old_value)
                result["success"] = True
                result["migrated_value"] = scenario_migrated.value
                result["base_status_equivalent"] = (
                    scenario_migrated.to_base_status().value
                )

                # Check for semantic changes
                base_status = scenario_migrated.to_base_status()
                if base_status.value != old_value:
                    result["warnings"].append(
                        f"Base status mapping changed: "
                        f"{old_value} -> {base_status.value}",
                    )

            if old_enum_name.lower() in [
                "enumfunctionstatus",
                "enummetadatanodestatus",
            ]:
                function_migrated = migrator.migrate_function_status(old_value)
                result["success"] = True
                result["migrated_value"] = function_migrated.value
                result["base_status_equivalent"] = (
                    function_migrated.to_base_status().value
                )

                # Check for semantic changes
                base_status = function_migrated.to_base_status()
                if base_status.value != old_value:
                    result["warnings"].append(
                        f"Base status mapping changed: "
                        f"{old_value} -> {base_status.value}",
                    )

            if not result["success"]:
                result["errors"].append(f"Unknown source enum: {old_enum_name}")
                return result

        except ValueError as e:
            result["errors"].append(str(e))

        return result

    @staticmethod
    def find_enum_conflicts() -> dict[str, list[str]]:
        """
        Find all conflicting values across the old enum system.

        Returns:
            Dictionary mapping conflicting values to the enums that contain them
        """
        conflicts = {}

        # Check for value conflicts
        all_values = {
            "EnumStatus": LEGACY_ENUM_STATUS_VALUES,
            "EnumExecutionStatus": LEGACY_EXECUTION_STATUS_VALUES,
            "EnumScenarioStatus": LEGACY_SCENARIO_STATUS_VALUES,
            "EnumFunctionStatus": LEGACY_FUNCTION_STATUS_VALUES,
            "EnumMetadataNodeStatus": LEGACY_METADATA_NODE_STATUS_VALUES,
        }

        for value in set().union(*all_values.values()):
            containing_enums = [
                enum_name for enum_name, values in all_values.items() if value in values
            ]
            if len(containing_enums) > 1:
                conflicts[value] = containing_enums

        return conflicts

    @staticmethod
    def generate_migration_report() -> dict[str, Any]:
        """
        Generate a comprehensive migration report.

        Returns:
            Detailed report on migration status and recommendations
        """
        conflicts = EnumStatusMigrationValidator.find_enum_conflicts()

        return {
            "summary": {
                "total_conflicts": len(conflicts),
                "conflicting_values": list(conflicts.keys()),
                "affected_enums": (
                    set().union(*conflicts.values()) if conflicts else set()
                ),
            },
            "conflicts": conflicts,
            "migration_mapping": {
                "EnumStatus -> EnumGeneralStatus": (
                    "All values preserved with enhanced categorization"
                ),
                "EnumExecutionStatus -> EnumExecutionStatusV2": (
                    "All values preserved with base status integration"
                ),
                "EnumScenarioStatus -> EnumScenarioStatusV2": (
                    "All values preserved with base status integration"
                ),
                "EnumFunctionStatus -> EnumFunctionLifecycleStatus": (
                    "All values preserved with lifecycle focus"
                ),
                "EnumMetadataNodeStatus -> EnumFunctionLifecycleStatus": (
                    "All values preserved with enhanced lifecycle states"
                ),
            },
            "recommendations": [
                "Update model imports to use new enum classes",
                "Replace string status fields with proper enum types",
                (
                    "Use domain-specific enums instead of general "
                    "EnumStatus where appropriate"
                ),
                "Leverage base status conversions for cross-domain operations",
                "Add type hints for all status fields",
            ],
        }


# Export for use
__all__ = [
    "LEGACY_ENUM_STATUS_VALUES",
    "LEGACY_EXECUTION_STATUS_VALUES",
    "LEGACY_FUNCTION_STATUS_VALUES",
    "LEGACY_METADATA_NODE_STATUS_VALUES",
    "LEGACY_SCENARIO_STATUS_VALUES",
    "EnumStatusMigrationValidator",
    "EnumStatusMigrator",
]
