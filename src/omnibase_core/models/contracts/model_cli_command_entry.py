# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Command Entry Model — a single CLI command advertised by a node.

Part of the cli.contribution.v1 contract schema.

.. versionadded:: 0.19.0  (OMN-2536)
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_cli_command_visibility import EnumCliCommandVisibility
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_cli_command_example import (
    ModelCliCommandExample,
)
from omnibase_core.models.contracts.model_cli_invocation import ModelCliInvocation
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ModelCliCommandEntry"]

# Globally namespaced command ID pattern: at least two dot-separated segments,
# each segment composed of lowercase letters, digits, and hyphens.
# Examples: "com.omninode.memory.query", "io.onex.cli.run"
_COMMAND_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*){1,}$")


class ModelCliCommandEntry(BaseModel):
    """A single CLI command advertised by a node.

    Command IDs are globally namespaced and MUST be immutable across versions.
    Display names and descriptions may change; the ``id`` field must not.

    Attributes:
        id: Globally namespaced, immutable command identifier.
            Format: ``<reverse-domain-prefix>.<command-name>``
            Example: ``com.omninode.memory.query``
        display_name: Human-readable name shown in help and catalogs.
        description: Full description of what the command does.
        group: Logical grouping for catalog organization (e.g., "memory").
        args_schema_ref: Registry reference to the command's argument schema.
            Must point to a schema registered in the ONEX schema registry.
        output_schema_ref: Registry reference to the command's output schema.
        invocation: How the runtime dispatches this command.
        permissions: List of permission strings required to execute this command.
        risk: Risk classification governing HITL and audit requirements.
        requires_hitl: Whether human confirmation is required before execution.
        visibility: Controls surfacing in help output and discovery.
        examples: Usage examples for documentation and testing.
    """

    id: str = Field(
        ...,
        min_length=5,
        description="Globally namespaced, immutable command ID (dot notation).",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable display name.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Full description of the command.",
    )
    group: str = Field(
        ...,
        min_length=1,
        description="Logical grouping for catalog organization.",
    )
    args_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to argument schema (not inline).",
    )
    output_schema_ref: str = Field(
        ...,
        min_length=1,
        description="Registry reference to output schema (not inline).",
    )
    invocation: ModelCliInvocation = Field(
        ...,
        description="Dispatch specification for this command.",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Permission strings required to execute this command.",
    )
    risk: EnumCliCommandRisk = Field(
        default=EnumCliCommandRisk.LOW,
        description="Risk classification for HITL and audit.",
    )
    requires_hitl: bool = Field(
        default=False,
        description="Whether human confirmation is required before execution.",
    )
    visibility: EnumCliCommandVisibility = Field(
        default=EnumCliCommandVisibility.PUBLIC,
        description="Controls surfacing in help and discovery.",
    )
    examples: list[ModelCliCommandExample] = Field(
        default_factory=list,
        description="Usage examples for documentation.",
    )

    @field_validator("id", mode="after")
    @classmethod
    def validate_command_id_namespace(cls, v: str) -> str:
        """Validate that command ID is globally namespaced (dot notation).

        At least two dot-separated segments are required, each composed of
        lowercase letters, digits, and hyphens. Collisions at the registry
        level are a hard failure — IDs must be unique across all publishers.

        Args:
            v: Command ID string.

        Returns:
            Validated command ID.

        Raises:
            ModelOnexError: If the ID does not match the required format.
        """
        if not _COMMAND_ID_PATTERN.match(v):
            raise ModelOnexError(
                message=(
                    f"Command ID '{v}' is not globally namespaced. "
                    "Required format: '<segment>.<segment>[.<segment>...]' "
                    "where each segment is lowercase letters, digits, and hyphens. "
                    "Example: 'com.omninode.memory.query'"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                command_id=v,
                expected_format="<reverse-domain>.<command-name>",
                example="com.omninode.memory.query",
            )
        return v

    @model_validator(mode="after")
    def validate_hitl_consistency(self) -> ModelCliCommandEntry:
        """Ensure requires_hitl is True when risk is CRITICAL."""
        if self.risk == EnumCliCommandRisk.CRITICAL and not self.requires_hitl:
            raise ModelOnexError(
                message=(
                    f"Command '{self.id}' has risk=CRITICAL but requires_hitl=False. "
                    "CRITICAL commands must require HITL."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                command_id=self.id,
                risk=self.risk,
            )
        return self

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )
