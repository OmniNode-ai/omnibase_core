"""
Node Action Model.

Structured model for node actions that provides better metadata than simple enums.
Enhanced for tool-as-a-service architecture with MCP/GraphQL compatibility.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field, field_validator

from omnibase.model.core.model_action_category import ModelActionCategory
from omnibase.model.core.model_node_action_type import ModelNodeActionType
from omnibase.model.core.predefined_categories import LIFECYCLE, VALIDATION

from .model_action_base import ModelActionBase


class ModelNodeAction(ModelActionBase):
    """
    Structured node action model with tool-as-a-service support.

    Provides rich metadata about actions beyond simple enum values.
    Enhanced for MCP/GraphQL compatibility and service composition.
    """

    action_name: str = Field(
        ..., description="Unique action identifier (human-readable name)"
    )
    action_type: ModelNodeActionType = Field(
        ..., description="Rich action type with embedded metadata"
    )
    category: ModelActionCategory = Field(..., description="Action category")
    display_name: str = Field(..., description="Human-readable action name")
    description: str = Field(
        ..., description="Detailed description of what this action does"
    )

    # Action metadata
    is_destructive: bool = Field(
        default=False, description="Whether this action modifies data"
    )
    requires_confirmation: bool = Field(
        default=False, description="Whether this action requires user confirmation"
    )
    estimated_duration_ms: Optional[int] = Field(
        None, description="Estimated execution time in milliseconds"
    )

    # Parameters and validation with strong typing
    required_parameters: List[str] = Field(
        default_factory=list, description="Required parameter names"
    )
    optional_parameters: List[str] = Field(
        default_factory=list, description="Optional parameter names"
    )
    parameter_schemas: Dict[str, Dict[str, Union[str, List[str], bool, int, float]]] = (
        Field(
            default_factory=dict,
            description="JSON schemas for parameters with strong typing",
        )
    )

    # Documentation and examples
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    documentation_url: Optional[str] = Field(
        None, description="URL to action documentation"
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing actions"
    )

    # Tool-as-a-Service enhancements
    mcp_endpoint: Optional[str] = Field(
        None, description="MCP endpoint for executing this action"
    )
    graphql_endpoint: Optional[str] = Field(
        None, description="GraphQL endpoint for executing this action"
    )
    composition_compatible: bool = Field(
        default=True, description="Whether action supports composition patterns"
    )
    service_dependencies: List[str] = Field(
        default_factory=list, description="Required service dependencies"
    )

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: ModelNodeActionType) -> ModelNodeActionType:
        """Validate that action_type is a valid ModelNodeActionType."""
        if not isinstance(v, ModelNodeActionType):
            raise ValueError(
                f"action_type must be a ModelNodeActionType, got {type(v)}"
            )
        return v

    @classmethod
    def create_lifecycle_action(
        cls,
        action_type: ModelNodeActionType,
        action_name: str,
        display_name: str,
        description: str,
        **kwargs: Any,
    ) -> "ModelNodeAction":
        """Create lifecycle actions like health_check."""
        if action_type.category != LIFECYCLE:
            raise ValueError(
                f"Action type {action_type.name} is not a lifecycle action"
            )
        return cls(
            action_name=action_name,
            action_type=action_type,
            category=action_type.category,
            display_name=display_name,
            description=description,
            **kwargs,
        )

    @classmethod
    def create_validation_action(
        cls,
        action_type: ModelNodeActionType,
        action_name: str,
        display_name: str,
        description: str,
        **kwargs: Any,
    ) -> "ModelNodeAction":
        """Create validation actions."""
        if action_type.category != VALIDATION:
            raise ValueError(
                f"Action type {action_type.name} is not a validation action"
            )
        return cls(
            action_name=action_name,
            action_type=action_type,
            category=action_type.category,
            display_name=display_name,
            description=description,
            **kwargs,
        )

    @classmethod
    def create_typed_action(
        cls,
        action_type: ModelNodeActionType,
        action_name: str,
        display_name: str,
        description: str,
        **kwargs: Any,
    ) -> "ModelNodeAction":
        """Create actions with specific ModelNodeActionType."""
        # Action type already contains all metadata including category
        return cls(
            action_name=action_name,
            action_type=action_type,
            category=action_type.category,
            display_name=display_name,
            description=description,
            # Inherit behavioral flags from action type if not overridden
            is_destructive=kwargs.get("is_destructive", action_type.is_destructive),
            requires_confirmation=kwargs.get(
                "requires_confirmation", action_type.requires_confirmation
            ),
            estimated_duration_ms=kwargs.get(
                "estimated_duration_ms", action_type.estimated_duration_ms
            ),
            **{
                k: v
                for k, v in kwargs.items()
                if k
                not in [
                    "is_destructive",
                    "requires_confirmation",
                    "estimated_duration_ms",
                ]
            },
        )

    def to_service_metadata(
        self,
    ) -> Dict[str, Union[str, bool, List[str], Optional[int], Dict[str, Any]]]:
        """Generate service metadata for tool discovery with strong typing."""
        return {
            "action_name": self.action_name,
            "action_type": self.action_type.name,
            "category": self.category.name,
            "display_name": self.display_name,
            "mcp_endpoint": self.mcp_endpoint,
            "graphql_endpoint": self.graphql_endpoint,
            "composition_compatible": self.composition_compatible,
            "service_dependencies": self.service_dependencies,
            "tags": self.tags + self.tool_discovery_tags,
            "estimated_duration_ms": self.estimated_duration_ms,
            "requires_confirmation": self.requires_confirmation,
            "is_destructive": self.is_destructive,
            # Include action type metadata
            "action_type_metadata": self.action_type.to_service_metadata(),
        }
