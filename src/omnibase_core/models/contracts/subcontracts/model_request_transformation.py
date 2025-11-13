from typing import Any

from pydantic import Field

"""
Request Transformation Model - ONEX Standards Compliant.

Individual model for request transformation configuration.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel

from .model_header_transformation import ModelHeaderTransformation
from .model_query_parameter_rule import ModelQueryParameterRule
from .model_response_header_rule import ModelResponseHeaderRule


class ModelRequestTransformation(BaseModel):
    """
    Request transformation configuration.

    Defines request/response transformation rules,
    header manipulation, and payload modification.
    """

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
