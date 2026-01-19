"""MCP parameter mapping model.

Maps ONEX contract fields to MCP tool parameters.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_mcp_parameter_type import EnumMCPParameterType


class ModelMCPParameterMapping(BaseModel):
    """Maps an ONEX field to an MCP tool parameter.

    This model defines how ONEX input model fields are exposed as MCP tool
    parameters, including type information, descriptions, and validation.

    Attributes:
        name: Parameter name as exposed to MCP clients.
        parameter_type: JSON Schema type for the parameter.
        description: Human-readable description for AI agents.
        required: Whether the parameter is required.
        default_value: Default value if not provided.
        onex_field: Source field path in ONEX input model (e.g., "input.query").
        mcp_param_name: Override name for MCP (if different from name).
        enum_values: Allowed values for enum parameters.
        min_value: Minimum value for numeric parameters.
        max_value: Maximum value for numeric parameters.
        min_length: Minimum length for string parameters.
        max_length: Maximum length for string parameters.
        pattern: Regex pattern for string validation.
        examples: Example values for documentation.
    """

    name: str = Field(..., description="Parameter name as exposed to MCP clients")
    parameter_type: EnumMCPParameterType = Field(
        default=EnumMCPParameterType.STRING,
        description="JSON Schema type for the parameter",
    )
    description: str = Field(
        default="", description="Human-readable description for AI agents"
    )
    required: bool = Field(
        default=True, description="Whether the parameter is required"
    )
    default_value: object | None = Field(
        default=None, description="Default value if not provided"
    )
    onex_field: str | None = Field(
        default=None,
        description="Source field path in ONEX input model (e.g., 'input.query')",
    )
    mcp_param_name: str | None = Field(
        default=None, description="Override name for MCP (if different from name)"
    )
    enum_values: list[str] | None = Field(
        default=None, description="Allowed values for enum parameters"
    )
    min_value: float | None = Field(
        default=None, description="Minimum value for numeric parameters"
    )
    max_value: float | None = Field(
        default=None, description="Maximum value for numeric parameters"
    )
    min_length: int | None = Field(
        default=None, description="Minimum length for string parameters"
    )
    max_length: int | None = Field(
        default=None, description="Maximum length for string parameters"
    )
    pattern: str | None = Field(
        default=None, description="Regex pattern for string validation"
    )
    examples: list[object] | None = Field(
        default=None, description="Example values for documentation"
    )

    model_config = {"frozen": True}

    def get_effective_name(self) -> str:
        """Get the effective parameter name for MCP.

        Returns:
            The mcp_param_name if set, otherwise the name.
        """
        return self.mcp_param_name or self.name

    def to_json_schema(self) -> dict[str, object]:
        """Convert to JSON Schema property definition.

        Returns:
            JSON Schema dict for this parameter.
        """
        schema: dict[str, object] = {
            "type": self.parameter_type.value,
            "description": self.description,
        }

        if self.default_value is not None:
            schema["default"] = self.default_value
        if self.enum_values:
            schema["enum"] = self.enum_values
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.examples:
            schema["examples"] = self.examples

        return schema


__all__ = ["ModelMCPParameterMapping"]
