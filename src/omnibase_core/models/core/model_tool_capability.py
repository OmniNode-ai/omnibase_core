"""
Tool Capability Model.

Tool capability definition with supported input/output types and operations.
"""

from pydantic import BaseModel, Field


class ModelToolCapability(BaseModel):
    """Tool capability definition."""

    name: str = Field(description="Capability name")
    description: str = Field(description="Capability description")
    input_types: list[str] = Field(
        default_factory=list,
        description="Input data types supported",
    )
    output_types: list[str] = Field(
        default_factory=list,
        description="Output data types produced",
    )
    operations: list[str] = Field(
        default_factory=list,
        description="Operations provided by capability",
    )

    def supports_input_type(self, input_type: str) -> bool:
        """Check if capability supports a specific input type."""
        return input_type in self.input_types

    def produces_output_type(self, output_type: str) -> bool:
        """Check if capability produces a specific output type."""
        return output_type in self.output_types

    def provides_operation(self, operation: str) -> bool:
        """Check if capability provides a specific operation."""
        return operation in self.operations

    def get_type_compatibility(self, input_type: str, output_type: str) -> bool:
        """Check if capability supports input-output type combination."""
        return self.supports_input_type(input_type) and self.produces_output_type(
            output_type
        )

    def get_operation_count(self) -> int:
        """Get number of operations provided."""
        return len(self.operations)

    def get_input_type_count(self) -> int:
        """Get number of input types supported."""
        return len(self.input_types)

    def get_output_type_count(self) -> int:
        """Get number of output types produced."""
        return len(self.output_types)

    def get_summary(self) -> dict[str, object]:
        """Get capability summary."""
        return {
            "name": self.name,
            "description": self.description,
            "input_types": self.input_types,
            "output_types": self.output_types,
            "operations": self.operations,
            "input_type_count": self.get_input_type_count(),
            "output_type_count": self.get_output_type_count(),
            "operation_count": self.get_operation_count(),
        }
