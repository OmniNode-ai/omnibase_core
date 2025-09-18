"""
YAML item models for structured YAML content.

Provides strongly typed models for common YAML item patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelYamlRegistryItem(BaseModel):
    """Generic registry item for YAML registries."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(
        ...,
        description="Item name identifier",
    )
    type: str | None = Field(
        None,
        description="Item type classification",
    )
    description: str | None = Field(
        None,
        description="Item description",
    )
    enabled: bool = Field(
        default=True,
        description="Whether item is enabled",
    )
    version: str | None = Field(
        None,
        description="Item version",
    )


class ModelYamlEntry(BaseModel):
    """Generic entry for YAML entry lists."""

    model_config = ConfigDict(extra="allow")

    key: str = Field(
        ...,
        description="Entry key",
    )
    value: str | int | float | bool | None = Field(
        None,
        description="Entry value",
    )
    metadata: dict[str, str] | None = Field(
        None,
        description="Entry metadata",
    )


class ModelYamlCommand(BaseModel):
    """YAML command specification."""

    model_config = ConfigDict(extra="allow")

    command: str = Field(
        ...,
        description="Command name or instruction",
    )
    args: list[str] | None = Field(
        None,
        description="Command arguments",
    )
    description: str | None = Field(
        None,
        description="Command description",
    )
    enabled: bool = Field(
        default=True,
        description="Whether command is enabled",
    )
    timeout_seconds: int | None = Field(
        None,
        description="Command timeout in seconds",
        ge=0,
    )


class ModelYamlExample(BaseModel):
    """YAML example specification."""

    model_config = ConfigDict(extra="allow")

    title: str | None = Field(
        None,
        description="Example title",
    )
    description: str | None = Field(
        None,
        description="Example description",
    )
    input: dict[str, str] | None = Field(
        None,
        description="Example input data",
    )
    output: dict[str, str] | None = Field(
        None,
        description="Expected output data",
    )
    code: str | None = Field(
        None,
        description="Example code snippet",
    )


class ModelYamlRule(BaseModel):
    """YAML rule specification for policies."""

    model_config = ConfigDict(extra="allow")

    rule_name: str = Field(
        ...,
        description="Rule identifier",
    )
    condition: str | None = Field(
        None,
        description="Rule condition",
    )
    action: str | None = Field(
        None,
        description="Rule action to take",
    )
    priority: int = Field(
        default=0,
        description="Rule priority",
    )
    enabled: bool = Field(
        default=True,
        description="Whether rule is enabled",
    )


class ModelYamlOptions(BaseModel):
    """Options configuration for YAML files."""

    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(
        default=True,
        description="Whether options are enabled",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode flag",
    )
    verbose: bool = Field(
        default=False,
        description="Verbose output flag",
    )
    timeout_seconds: int | None = Field(
        None,
        description="Timeout in seconds",
        ge=0,
    )
    max_retries: int = Field(
        default=0,
        description="Maximum retry attempts",
        ge=0,
    )


class ModelYamlParameters(BaseModel):
    """Parameters configuration for YAML files."""

    model_config = ConfigDict(extra="allow")

    name: str | None = Field(
        None,
        description="Parameter set name",
    )
    version: str | None = Field(
        None,
        description="Parameter version",
    )
    values: dict[str, str] | None = Field(
        None,
        description="Parameter values",
    )
    defaults: dict[str, str] | None = Field(
        None,
        description="Default parameter values",
    )


class ModelYamlPermissions(BaseModel):
    """Permissions specification for policies."""

    model_config = ConfigDict(extra="allow")

    read: bool = Field(
        default=False,
        description="Read permission",
    )
    write: bool = Field(
        default=False,
        description="Write permission",
    )
    execute: bool = Field(
        default=False,
        description="Execute permission",
    )
    delete: bool = Field(
        default=False,
        description="Delete permission",
    )
    admin: bool = Field(
        default=False,
        description="Admin permission",
    )
    roles: list[str] | None = Field(
        None,
        description="Required roles",
    )


class ModelYamlState(BaseModel):
    """State specification for YAML state files."""

    model_config = ConfigDict(extra="allow")

    status: str = Field(
        ...,
        description="Current state status",
    )
    timestamp: str | None = Field(
        None,
        description="State timestamp",
    )
    data: dict[str, str] | None = Field(
        None,
        description="State data",
    )
    metadata: dict[str, str] | None = Field(
        None,
        description="State metadata",
    )
    version: str | None = Field(
        None,
        description="State version",
    )
