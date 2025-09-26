#!/usr/bin/env python3
"""
ModelSubcontractConstraintValidator - Shared Subcontract Validation Logic.

Provides unified validation logic for subcontract architectural constraints
across all contract node types, eliminating code duplication and ensuring
consistent ONEX compliance.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import TypedDict, Union

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Type alias for contract data input - includes all possible contract data types
# Using ModelSchemaValue and specific types instead of Any for ONEX compliance
ContractData = Union[
    dict[
        str,
        Union[
            str,
            int,
            float,
            bool,
            list[object],
            dict[str, object],
            ModelSchemaValue,
            None,
        ],
    ],
    dict[str, ModelSchemaValue],
    dict[str, object],
]


class NodeRuleStructure(TypedDict):
    """Structure for node subcontract rules."""

    forbidden: list[str]
    forbidden_messages: dict[str, str]
    forbidden_suggestions: dict[str, str]


class ModelSubcontractConstraintValidator:
    """
    Shared utility for validating subcontract architectural constraints.

    Eliminates code duplication across contract models by providing
    consistent subcontract validation logic based on ONEX 4-node architecture.
    """

    # Node-specific subcontract rules based on ONEX architecture
    NODE_SUBCONTRACT_RULES: dict[str, NodeRuleStructure] = {
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
                "state_management"  # Orchestrators coordinate, don't manage state directly
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
    def validate_node_subcontract_constraints(
        node_type: str,
        contract_data: ContractData,
        original_contract_data: ContractData | None = None,
    ) -> None:
        """
        Validate subcontract constraints for a specific node type.

        Args:
            node_type: The node type ('compute', 'effect', 'reducer', 'orchestrator')
            contract_data: The contract data to validate
            original_contract_data: Optional original contract data for lazy evaluation

        Raises:
            ValueError: If subcontract constraints are violated
        """
        # Use provided contract data or original data for validation
        data_to_validate = (
            original_contract_data
            if original_contract_data is not None
            else contract_data
        )

        violations = []

        # Get rules for this node type
        default_rules: NodeRuleStructure = {
            "forbidden": [],
            "forbidden_messages": {},
            "forbidden_suggestions": {},
        }
        node_rules = ModelSubcontractConstraintValidator.NODE_SUBCONTRACT_RULES.get(
            node_type.lower(), default_rules
        )

        # Check forbidden subcontracts - only if data_to_validate is a dictionary
        if isinstance(data_to_validate, dict):
            for forbidden_subcontract in node_rules["forbidden"]:
                if forbidden_subcontract in data_to_validate:
                    violations.append(
                        node_rules["forbidden_messages"][forbidden_subcontract]
                    )
                    violations.append(
                        node_rules["forbidden_suggestions"][forbidden_subcontract]
                    )

        # Check for missing recommended subcontracts
        ModelSubcontractConstraintValidator._validate_recommended_subcontracts(
            data_to_validate, violations
        )

        # Raise validation error if any violations found
        if violations:
            raise ValueError("\n".join(violations))

    @staticmethod
    def _validate_recommended_subcontracts(
        contract_data: ContractData,
        violations: list[str],
    ) -> None:
        """
        Validate recommended subcontracts are present.

        Args:
            contract_data: The contract data to validate
            violations: List to append violations to
        """
        # All nodes should have event_type subcontracts for event-driven architecture
        # Only check if contract_data is a dictionary
        if isinstance(contract_data, dict) and "event_type" not in contract_data:
            violations.append(
                "⚠️ MISSING SUBCONTRACT: All nodes should define event_type subcontracts"
            )
            violations.append(
                "   💡 Add event_type configuration for event-driven architecture"
            )

    @staticmethod
    def get_allowed_subcontracts_for_node(node_type: str) -> list[str]:
        """
        Get list of allowed subcontracts for a specific node type.

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

        node_rules: NodeRuleStructure = (
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
        Get list of forbidden subcontracts for a specific node type.

        Args:
            node_type: The node type to get forbidden subcontracts for

        Returns:
            list[str]: List of forbidden subcontract names
        """
        node_rules: NodeRuleStructure = (
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
