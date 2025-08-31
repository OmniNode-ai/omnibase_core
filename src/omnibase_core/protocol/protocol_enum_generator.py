"""
Protocol for Enum Generator functionality.

Defines the interface for discovering and generating enum classes
from contract definitions.
"""

import ast
from dataclasses import dataclass
from typing import Protocol

from omnibase_core.model.core.model_schema import ModelSchema
from omnibase_core.model.generation.model_contract_document import ModelContractDocument


@dataclass
class EnumInfo:
    """Information about a discovered enum."""

    name: str
    values: list[str]
    source_location: str


class ProtocolEnumGenerator(Protocol):
    """Protocol for enum generation functionality.

    This protocol defines the interface for discovering enums
    from contracts and generating corresponding enum classes.
    """

    def discover_enums_from_contract(
        self,
        contract_data: ModelContractDocument | dict,
    ) -> list[EnumInfo]:
        """Discover all enum definitions from a contract document.

        Args:
            contract_data: Contract data (ModelContractDocument or dict)

        Returns:
            List of discovered enum information
        """
        ...

    def discover_enums_from_schema(
        self,
        schema: ModelSchema | dict,
        path: str = "root",
    ) -> list[EnumInfo]:
        """Recursively discover enums from a schema definition.

        Args:
            schema: Schema to search (ModelSchema or dict)
            path: Current path in schema for tracking

        Returns:
            List of discovered enums
        """
        ...

    def generate_enum_name_from_values(self, enum_values: list[str]) -> str:
        """Generate an enum class name from enum values.

        Args:
            enum_values: List of enum values

        Returns:
            Generated enum class name
        """
        ...

    def generate_enum_name_from_schema(self, schema: ModelSchema | dict) -> str:
        """Generate enum name from a schema with enum values.

        Args:
            schema: Schema containing enum values

        Returns:
            Generated enum class name
        """
        ...

    def deduplicate_enums(self, enum_infos: list[EnumInfo]) -> list[EnumInfo]:
        """Remove duplicate enums based on their values.

        Args:
            enum_infos: List of enum information

        Returns:
            Deduplicated list of enums
        """
        ...

    def generate_enum_classes(self, enum_infos: list[EnumInfo]) -> list[ast.ClassDef]:
        """Generate AST enum class definitions.

        Args:
            enum_infos: List of enum information

        Returns:
            List of AST ClassDef nodes for enums
        """
        ...

    def get_enum_member_name(self, value: str) -> str:
        """Convert enum value to valid Python enum member name.

        Args:
            value: Enum value string

        Returns:
            Valid Python identifier for enum member
        """
        ...

    def is_enum_schema(self, schema: ModelSchema | dict) -> bool:
        """Check if a schema defines an enum.

        Args:
            schema: Schema to check

        Returns:
            True if schema has enum values
        """
        ...

    def get_enum_values(self, schema: ModelSchema | dict) -> list[str] | None:
        """Extract enum values from a schema.

        Args:
            schema: Schema to extract from

        Returns:
            List of enum values or None
        """
        ...
