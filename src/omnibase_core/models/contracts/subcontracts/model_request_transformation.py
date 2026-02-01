"""
Request Transformation Model.

Individual model for request transformation configuration.
Part of the Routing Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_header_transformation import ModelHeaderTransformation
from .model_query_parameter_rule import ModelQueryParameterRule
from .model_response_header_rule import ModelResponseHeaderRule


class ModelRequestTransformation(BaseModel):
    """
    Request transformation configuration.

    Defines request/response transformation rules,
    header manipulation, and payload modification.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    transformation_enabled: bool = Field(
        default=False,
        description="Enable request transformation",
    )

    header_transformations: list[ModelHeaderTransformation] = Field(
        default_factory=list,
        description="Strongly-typed header transformation rules",
    )

    path_rewrite_rules: list[str] = Field(
        default_factory=list,
        description="Path rewrite patterns",
    )

    query_parameter_rules: list[ModelQueryParameterRule] = Field(
        default_factory=list,
        description="Strongly-typed query parameter transformation rules",
    )

    payload_transformation: str | None = Field(
        default=None,
        description="Payload transformation template",
    )

    response_transformation: bool = Field(
        default=False,
        description="Enable response transformation",
    )

    response_header_rules: list[ModelResponseHeaderRule] = Field(
        default_factory=list,
        description="Strongly-typed response header transformation rules",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
