"""
Entity type enumeration for knowledge graph entities.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnumEntityType(str, Enum):
    """Enumeration of entity types in the knowledge graph."""

    # Documentation entities
    CONCEPT = "concept"
    TUTORIAL = "tutorial"
    GUIDE = "guide"
    REFERENCE = "reference"
    FAQ = "faq"

    # API entities
    API_ENDPOINT = "api_endpoint"
    API_MODEL = "api_model"
    API_SCHEMA = "api_schema"

    # Code entities
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    PACKAGE = "package"

    # Tool entities
    TOOL = "tool"
    COMMAND = "command"
    WORKFLOW = "workflow"
    SCRIPT = "script"

    # Configuration entities
    CONFIG_SETTING = "config_setting"
    ENVIRONMENT_VAR = "environment_var"
    PARAMETER = "parameter"

    # Domain entities
    BUSINESS_PROCESS = "business_process"
    USE_CASE = "use_case"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"

    # Infrastructure entities
    SERVICE = "service"
    COMPONENT = "component"
    INTERFACE = "interface"
    PROTOCOL = "protocol"


class ModelEntityType(BaseModel):
    """Model for entity type with additional metadata."""

    type_enum: EnumEntityType = Field(..., description="Primary entity type")
    category: str = Field(..., description="High-level category grouping")
    is_abstract: bool = Field(
        False,
        description="Whether this is an abstract/conceptual entity",
    )
    requires_implementation: bool = Field(
        False,
        description="Whether this entity needs implementation",
    )

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        use_enum_values=True,  # Ensure proper enum serialization
    )
