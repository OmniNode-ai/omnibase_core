#!/usr/bin/env python3
"""
Hub Configuration Model - ONEX Standards Compliant.

Strongly-typed model for unified hub configuration supporting both contract formats.
"""

import hashlib
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from omnibase_core.enums.enum_coordination_mode import EnumCoordinationMode
from omnibase_core.enums.enum_hub_capability import EnumHubCapability

if TYPE_CHECKING:
    pass


class ModelHubConfiguration(BaseModel):
    """Unified hub configuration supporting both contract formats."""

    # Core hub identity
    domain_id: UUID = Field(
        ...,
        description="UUID of the hub domain",
    )

    domain_display_name: str | None = Field(
        None,
        description="Human-readable domain name (e.g., 'generation', 'ai')",
    )

    # Service configuration
    service_port: int | None = Field(
        None,
        description="Port for hub HTTP service",
        ge=1024,
        le=65535,
    )

    # Hub capabilities and behavior
    coordination_mode: EnumCoordinationMode | None = Field(
        EnumCoordinationMode.EVENT_ROUTER,
        description="Hub coordination strategy",
    )

    @classmethod
    def create_with_legacy_domain(
        cls,
        domain_name: str,
        service_port: int | None = None,
        managed_tool_names: list[str] | None = None,
        **kwargs: Any,
    ) -> "ModelHubConfiguration":
        """Factory method to create hub configuration with legacy domain name."""
        # Generate UUID for domain
        domain_hash = hashlib.sha256(domain_name.encode()).hexdigest()
        domain_id = UUID(
            f"{domain_hash[:8]}-{domain_hash[8:12]}-{domain_hash[12:16]}-{domain_hash[16:20]}-{domain_hash[20:32]}"
        )

        # Generate UUIDs for managed tools
        managed_tool_ids = []
        tool_display_names = managed_tool_names or []
        for tool_name in tool_display_names:
            tool_hash = hashlib.sha256(tool_name.encode()).hexdigest()
            tool_id = UUID(
                f"{tool_hash[:8]}-{tool_hash[8:12]}-{tool_hash[12:16]}-{tool_hash[16:20]}-{tool_hash[20:32]}"
            )
            managed_tool_ids.append(tool_id)

        return cls(
            domain_id=domain_id,
            domain_display_name=domain_name,
            service_port=service_port,
            managed_tool_ids=managed_tool_ids,
            managed_tool_display_names=tool_display_names,
            **kwargs,
        )

    capabilities: list[EnumHubCapability] | None = Field(
        default_factory=list,
        description="Hub capabilities",
    )

    priority: str | None = Field("normal", description="Hub execution priority")

    docker_enabled: bool | None = Field(
        False,
        description="Enable Docker container isolation",
    )

    # Tool management
    managed_tool_ids: list[UUID] | None = Field(
        default_factory=list,
        description="UUIDs of tools managed by this hub",
    )

    managed_tool_display_names: list[str] | None = Field(
        default_factory=list,
        description="Human-readable names of managed tools",
    )

    # Service registry configuration
    introspection_timeout: int | None = Field(
        30,
        description="Introspection timeout in seconds",
    )

    service_ttl: int | None = Field(300, description="Service TTL in seconds")

    auto_cleanup_interval: int | None = Field(
        60,
        description="Auto cleanup interval in seconds",
    )
