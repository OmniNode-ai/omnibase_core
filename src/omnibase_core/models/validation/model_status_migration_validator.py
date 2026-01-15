"""
Status Migration Validation Utilities.

Validates status enum migrations and identifies potential issues.

Usage:
    # Validate migration
    validator = ModelEnumStatusMigrationValidator()
    issues = validator.validate_model_migration(model_class)
"""

from __future__ import annotations

from omnibase_core.models.core.model_status_migrator import ModelEnumStatusMigrator
from omnibase_core.types import TypedDictStatusMigrationResult
from omnibase_core.types.typed_dict_migration_report import TypedDictMigrationReport


class ModelEnumStatusMigrationValidator:
    """
    Validates status enum migrations and identifies potential issues.
    """

    @staticmethod
    def validate_value_migration(
        old_value: str,
        old_enum_name: str,
        expected_new_enum: type,
    ) -> TypedDictStatusMigrationResult:
        """
        Validate that a value can be safely migrated.

        Args:
            old_value: Original status value
            old_enum_name: Name of original enum
            expected_new_enum: Expected target enum class

        Returns:
            Validation result with success status and details
        """
        result: TypedDictStatusMigrationResult = {
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
            migrator = ModelEnumStatusMigrator()

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
        from omnibase_core.models.core.model_status_migrator import (
            LEGACY_ENUM_STATUS_VALUES,
            LEGACY_EXECUTION_STATUS_VALUES,
            LEGACY_FUNCTION_STATUS_VALUES,
            LEGACY_METADATA_NODE_STATUS_VALUES,
            LEGACY_SCENARIO_STATUS_VALUES,
        )

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
    def generate_migration_report() -> TypedDictMigrationReport:
        """
        Generate a comprehensive migration report.

        Returns:
            Detailed report on migration status and recommendations
        """
        conflicts = ModelEnumStatusMigrationValidator.find_enum_conflicts()

        result: TypedDictMigrationReport = {
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
        return result


# Export for use
__all__ = [
    "ModelEnumStatusMigrationValidator",
]
