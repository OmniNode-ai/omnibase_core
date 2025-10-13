from pydantic import BaseModel, Field


class ModelAgentOnexSettings(BaseModel):
    """ONEX-specific agent settings."""

    enforce_naming_conventions: bool = Field(
        description="Whether to enforce ONEX naming conventions",
    )
    enforce_strong_typing: bool = Field(
        description="Whether to enforce strong typing (no Any)",
    )
    require_contract_compliance: bool = Field(
        description="Whether to require contract compliance",
    )
    generate_documentation: bool = Field(
        description="Whether to automatically generate documentation",
    )
    validate_imports: bool = Field(description="Whether to validate import structure")
