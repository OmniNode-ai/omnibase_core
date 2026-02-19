# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_operation_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_operation_type import EnumOperationType


@pytest.mark.unit
class TestEnumOperationType:
    """Test cases for EnumOperationType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumOperationType.INFO == "info"
        assert EnumOperationType.CONTRACT == "contract"
        assert EnumOperationType.HELP == "help"
        assert EnumOperationType.EXECUTE == "execute"
        assert EnumOperationType.VALIDATE == "validate"
        assert EnumOperationType.GENERATE == "generate"
        assert EnumOperationType.LIST == "list[Any]"
        assert EnumOperationType.STATUS == "status"
        assert EnumOperationType.WORKFLOW == "workflow"
        assert EnumOperationType.INTROSPECT == "introspect"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumOperationType, str)
        assert issubclass(EnumOperationType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumOperationType.INFO == "info"
        assert EnumOperationType.CONTRACT == "contract"
        assert EnumOperationType.HELP == "help"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumOperationType)
        assert len(values) == 10
        assert EnumOperationType.INFO in values
        assert EnumOperationType.INTROSPECT in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumOperationType.INFO in EnumOperationType
        assert "info" in EnumOperationType
        assert "invalid_value" not in EnumOperationType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumOperationType.INFO == EnumOperationType.INFO
        assert EnumOperationType.CONTRACT != EnumOperationType.INFO
        assert EnumOperationType.INFO == "info"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumOperationType.INFO.value == "info"
        assert EnumOperationType.CONTRACT.value == "contract"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumOperationType("info") == EnumOperationType.INFO
        assert EnumOperationType("contract") == EnumOperationType.CONTRACT

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumOperationType("invalid_value")

        with pytest.raises(ValueError):
            EnumOperationType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "info",
            "contract",
            "help",
            "execute",
            "validate",
            "generate",
            "list[Any]",
            "status",
            "workflow",
            "introspect",
        }
        actual_values = {member.value for member in EnumOperationType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert (
            "Standard operation types for CLI operations" in EnumOperationType.__doc__
        )

    def test_enum_operation_types(self):
        """Test specific operation types"""
        # Information operations
        assert EnumOperationType.INFO.value == "info"
        assert EnumOperationType.HELP.value == "help"
        assert EnumOperationType.STATUS.value == "status"

        # Contract operations
        assert EnumOperationType.CONTRACT.value == "contract"
        assert EnumOperationType.VALIDATE.value == "validate"

        # Execution operations
        assert EnumOperationType.EXECUTE.value == "execute"
        assert EnumOperationType.GENERATE.value == "generate"

        # List operations
        assert EnumOperationType.LIST.value == "list[Any]"

        # Workflow operations
        assert EnumOperationType.WORKFLOW.value == "workflow"

        # Introspection operations
        assert EnumOperationType.INTROSPECT.value == "introspect"

    def test_enum_operation_categories(self):
        """Test operation categories"""
        # Information operations
        info_operations = {
            EnumOperationType.INFO,
            EnumOperationType.HELP,
            EnumOperationType.STATUS,
        }

        # Contract operations
        contract_operations = {EnumOperationType.CONTRACT, EnumOperationType.VALIDATE}

        # Execution operations
        execution_operations = {EnumOperationType.EXECUTE, EnumOperationType.GENERATE}

        # List operations
        list_operations = {EnumOperationType.LIST}

        # Workflow operations
        workflow_operations = {EnumOperationType.WORKFLOW}

        # Introspection operations
        introspection_operations = {EnumOperationType.INTROSPECT}

        all_operations = set(EnumOperationType)
        assert (
            info_operations.union(contract_operations)
            .union(execution_operations)
            .union(list_operations)
            .union(workflow_operations)
            .union(introspection_operations)
        ) == all_operations

    def test_enum_cli_operations(self):
        """Test CLI operation types"""
        # Basic CLI operations
        basic_operations = {
            EnumOperationType.INFO,
            EnumOperationType.HELP,
            EnumOperationType.STATUS,
        }

        # Advanced CLI operations
        advanced_operations = {
            EnumOperationType.CONTRACT,
            EnumOperationType.VALIDATE,
            EnumOperationType.EXECUTE,
            EnumOperationType.GENERATE,
            EnumOperationType.LIST,
            EnumOperationType.WORKFLOW,
            EnumOperationType.INTROSPECT,
        }

        all_operations = set(EnumOperationType)
        assert basic_operations.union(advanced_operations) == all_operations

    def test_enum_operation_scope(self):
        """Test operation scope categories"""
        # Read-only operations
        read_operations = {
            EnumOperationType.INFO,
            EnumOperationType.HELP,
            EnumOperationType.STATUS,
            EnumOperationType.LIST,
            EnumOperationType.INTROSPECT,
        }

        # Write operations
        write_operations = {
            EnumOperationType.EXECUTE,
            EnumOperationType.GENERATE,
            EnumOperationType.WORKFLOW,
        }

        # Validation operations
        validation_operations = {EnumOperationType.CONTRACT, EnumOperationType.VALIDATE}

        all_operations = set(EnumOperationType)
        assert (
            read_operations.union(write_operations).union(validation_operations)
            == all_operations
        )
