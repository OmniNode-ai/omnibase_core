from typing import Any

from pydantic import Field

"""
Request Transformation Model - ONEX Standards Compliant.

Individual model for request transformation configuration.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel


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

    header_transformations: dict[str, str] = Field(
        default_factory=dict,
        description="Header transformation rules",
    )

    path_rewrite_rules: list[str] = Field(
        default_factory=list,
        description="Path rewrite patterns",
    )

    query_parameter_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameter transformation",
    )

    payload_transformation: str | None = Field(
        default=None,
        description="Payload transformation template",
    )

    response_transformation: bool = Field(
        default=False,
        description="Enable response transformation",
    )

    response_header_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Response header transformation",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
