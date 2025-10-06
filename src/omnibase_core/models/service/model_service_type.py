from typing import Any, Generic, List

from pydantic import Field, field_validator

from omnibase_core.enums.enum_service_type_category import EnumServiceTypeCategory

"""
Service Type Model for ONEX Configuration-Driven Registry System.

This module provides the ModelServiceType for defining service types with extensible configuration.
Extracted from model_service_configuration.py for modular architecture compliance.

Author: OmniNode Team
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.core import ModelGenericMetadata


class ModelServiceType(BaseModel):
    """Scalable service type configuration model."""

    type_category: EnumServiceTypeCategory = Field(
        ...,
        description="The category of service type",
    )

    custom_type_name: str | None = Field(
        None,
        description="Custom service type name (required when type_category is CUSTOM)",
    )

    protocol: str | None = Field(
        None,
        description="Primary protocol used by this service type (http, tcp, kafka, etc.)",
    )

    default_port: int | None = Field(
        None,
        description="Default port for this service type",
        ge=1,
        le=65535,
    )

    supports_health_checks: bool = Field(
        True,
        description="Whether this service type supports health checking",
    )

    supports_load_balancing: bool = Field(
        True,
        description="Whether this service type supports load balancing",
    )

    connection_pooling: bool = Field(
        False,
        description="Whether this service type benefits from connection pooling",
    )

    required_capabilities: list[str] = Field(
        default_factory=list,
        description="List of capabilities required for this service type",
    )

    metadata: ModelGenericMetadata | None = Field(
        default_factory=lambda: ModelGenericMetadata(),
        description="Additional service type configuration",
    )

    @field_validator("custom_type_name", mode="before")
    @classmethod
    def validate_custom_name_consistency(cls, v, info):
        """Ensure custom_type_name is provided when type_category is CUSTOM"""
        if hasattr(info, "data") and info.data:
            type_category = info.data.get("type_category")
            if type_category == EnumServiceTypeCategory.CUSTOM and not v:
                msg = "custom_type_name is required when type_category is CUSTOM"
                raise ValueError(
                    msg,
                )
        return v

    def get_effective_type_name(self) -> str:
        """Get the effective service type name."""
        if (
            self.type_category == EnumServiceTypeCategory.CUSTOM
            and self.custom_type_name
        ):
            return self.custom_type_name
        return self.type_category.value

    def is_custom_type(self) -> bool:
        """Check if this is a custom service type."""
        return self.type_category == EnumServiceTypeCategory.CUSTOM

    def requires_protocol_config(self) -> bool:
        """Check if this service type requires protocol configuration."""
        return self.type_category in [
            EnumServiceTypeCategory.EVENT_BUS,
            EnumServiceTypeCategory.DATABASE,
            EnumServiceTypeCategory.CUSTOM,
        ]

    def get_default_capabilities(self) -> list[str]:
        """Get default capabilities for this service type."""
        defaults = {
            EnumServiceTypeCategory.SERVICE_DISCOVERY: ["discovery", "registration"],
            EnumServiceTypeCategory.EVENT_BUS: ["publish", "subscribe", "stream"],
            EnumServiceTypeCategory.CACHE: ["get", "set", "delete", "expire"],
            EnumServiceTypeCategory.DATABASE: ["read", "write", "transaction"],
            EnumServiceTypeCategory.REST_API: [
                "http_get",
                "http_post",
                "http_put",
                "http_delete",
            ],
            EnumServiceTypeCategory.CUSTOM: self.required_capabilities,
        }
        return defaults.get(self.type_category, [])
