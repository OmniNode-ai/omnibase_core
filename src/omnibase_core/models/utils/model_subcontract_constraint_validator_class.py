"""ModelSubcontractConstraintValidator Class.

Shared utility for validating subcontract architectural constraints.
"""

from __future__ import annotations

from typing import cast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_contract_data import ModelContractData
from omnibase_core.types.typed_dict_node_rule_structure import (
    TypedDictNodeRuleStructure,
)


class ModelSubcontractConstraintValidator:
    """
    Shared utility for validating subcontract architectural constraints.

    Eliminates code duplication across contract models by providing
    consistent subcontract validation logic based on ONEX 4-node architecture.
    """

    # Node-specific subcontract rules based on ONEX architecture
    NODE_SUBCONTRACT_RULES: dict[str, TypedDictNodeRuleStructure] = {
        "compute": {
            "forbidden": ["state_management", "aggregation", "state_transitions"],
            "forbidden_messages": {
                "state_management": "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_management subcontracts",
                "aggregation": "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have aggregation subcontracts",
                "state_transitions": "❌ SUBCONTRACT VIOLATION: COMPUTE nodes cannot have state_transitions subcontracts",
            },
            "forbidden_suggestions": {
                "state_management": "   💡 Use REDUCER nodes for stateful operations",
                "aggregation": "   💡 Use REDUCER nodes for data aggregation",
                "state_transitions": "   💡 Use REDUCER nodes for state machine workflows",
            },
        },
        "effect": {
            "forbidden": ["state_management", "aggregation"],
            "forbidden_messages": {
                "state_management": "❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have state_management subcontracts",
                "aggregation": "❌ SUBCONTRACT VIOLATION: EFFECT nodes should not have aggregation subcontracts",
            },
            "forbidden_suggestions": {
                "state_management": "   💡 Delegate state management to REDUCER nodes",
                "aggregation": "   💡 Use REDUCER nodes for data aggregation",
            },
        },
        "reducer": {
            "forbidden": [],  # Reducers can have most subcontracts
            "forbidden_messages": {},
            "forbidden_suggestions": {},
        },
        "orchestrator": {
            "forbidden": [
                "state_management",  # Orchestrators coordinate, don't manage state directly
            ],
            "forbidden_messages": {
                "state_management": "❌ SUBCONTRACT VIOLATION: ORCHESTRATOR nodes should delegate state_management to REDUCER nodes",
            },
            "forbidden_suggestions": {
                "state_management": "   💡 Use REDUCER nodes for state management, orchestrators coordinate",
            },
        },
    }

    @staticmethod
    def _normalize_contract_data(
        data: object,
    ) -> dict[str, ModelSchemaValue] | None:
        """
        Normalize contract data to use ModelSchemaValue for consistent processing.

        Args:
            data: Contract data in any supported format

        Returns:
            dict[str, ModelSchemaValue] | None: Normalized contract data
        """
        if data is None:
            return None

        # Handle ModelContractData instances
        if isinstance(data, ModelContractData):
            return data.to_schema_values()

        # Handle dict[str, Any]types
        if isinstance(data, dict):
            # If it's already dict[str, ModelSchemaValue], return as-is
            if data and isinstance(next(iter(data.values())), ModelSchemaValue):
                return cast("dict[str, ModelSchemaValue]", data)
            # Convert dict[str, object] to dict[str, ModelSchemaValue]
            return {k: ModelSchemaValue.from_value(v) for k, v in data.items()}

        # Note: All type cases handled above; this is unreachable but kept for type safety
        return None

    @staticmethod
    def validate_node_subcontract_constraints(
        node_type: str,
        contract_data: object,
        original_contract_data: object = None,
    ) -> None:
        """
        Validate subcontract constraints for a specific node type.

        Args:
            node_type: The node type ('compute', 'effect', 'reducer', 'orchestrator')
            contract_data: The contract data to validate
            original_contract_data: Optional original contract data for lazy evaluation

        Raises:
            ModelOnexError: If subcontract constraints are violated
        """
        # Use provided contract data or original data for validation
        data_to_validate = (
            original_contract_data
            if original_contract_data is not None
            else contract_data
        )

        # Normalize to consistent format for validation
        normalized_data = ModelSubcontractConstraintValidator._normalize_contract_data(
            data_to_validate,
        )

        violations = []

        # Get rules for this node type
        default_rules: TypedDictNodeRuleStructure = {
            "forbidden": [],
            "forbidden_messages": {},
            "forbidden_suggestions": {},
        }
        node_rules = ModelSubcontractConstraintValidator.NODE_SUBCONTRACT_RULES.get(
            node_type.lower(),
            default_rules,
        )

        # Check forbidden subcontracts - only if normalized_data exists
        if normalized_data is not None:
            for forbidden_subcontract in node_rules["forbidden"]:
                if forbidden_subcontract in normalized_data:
                    violations.append(
                        node_rules["forbidden_messages"][forbidden_subcontract],
                    )
                    violations.append(
                        node_rules["forbidden_suggestions"][forbidden_subcontract],
                    )

        # Check for missing recommended subcontracts
        ModelSubcontractConstraintValidator._validate_recommended_subcontracts(
            normalized_data,
            violations,
        )

        # Raise validation error if any violations found
        if violations:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="\n".join(violations),
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                    },
                ),
            )

    @staticmethod
    def _validate_recommended_subcontracts(
        normalized_data: dict[str, ModelSchemaValue] | None,
        violations: list[str],
    ) -> None:
        """
        Validate recommended subcontracts are present.

        Args:
            normalized_data: The normalized contract data to validate (ModelSchemaValue format)
            violations: List to append violations to
        """
        # All nodes should have event_type subcontracts for event-driven architecture
        # Only check if normalized_data exists
        if normalized_data is not None and "event_type" not in normalized_data:
            violations.append(
                "⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts",
            )
            violations.append(
                "   💡 Add event_type configuration for event-driven architecture",
            )

    @staticmethod
    def get_allowed_subcontracts_for_node(node_type: str) -> list[str]:
        """
        Get list[Any]of allowed subcontracts for a specific node type.

        Args:
            node_type: The node type to get allowed subcontracts for

        Returns:
            list[str]: List of allowed subcontract names
        """
        all_subcontracts = [
            "event_type",
            "caching",
            "routing",
            "state_management",
            "aggregation",
            "state_transitions",
            "fsm",
            "configuration",
        ]

        node_rules: TypedDictNodeRuleStructure = (
            ModelSubcontractConstraintValidator.NODE_SUBCONTRACT_RULES.get(
                node_type.lower(),
                {
                    "forbidden": [],
                    "forbidden_messages": {},
                    "forbidden_suggestions": {},
                },
            )
        )

        return [sc for sc in all_subcontracts if sc not in node_rules["forbidden"]]

    @staticmethod
    def get_forbidden_subcontracts_for_node(node_type: str) -> list[str]:
        """
        Get list[Any]of forbidden subcontracts for a specific node type.

        Args:
            node_type: The node type to get forbidden subcontracts for

        Returns:
            list[str]: List of forbidden subcontract names
        """
        node_rules: TypedDictNodeRuleStructure = (
            ModelSubcontractConstraintValidator.NODE_SUBCONTRACT_RULES.get(
                node_type.lower(),
                {
                    "forbidden": [],
                    "forbidden_messages": {},
                    "forbidden_suggestions": {},
                },
            )
        )

        return node_rules["forbidden"]
