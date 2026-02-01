"""Typed rule configurations for cross-repo validation.

Each rule has its own typed config model. No dict[str, Any] allowed.
Rule IDs are fixed in core; repos supply parameters via these configs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumSeverity


class ModelRuleConfigBase(BaseModel):
    """Base configuration for all validation rules.

    All rule configs inherit from this and add rule-specific parameters.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(default=True, description="Whether this rule is enabled")
    severity: EnumSeverity = Field(
        default=EnumSeverity.ERROR,
        description="Severity level for violations from this rule",
    )


class ModelRuleRepoBoundariesConfig(ModelRuleConfigBase):
    """Configuration for repo_boundaries rule.

    Enforces that code is in the correct repository and layer.
    The 'where code lives' gate.
    """

    ownership: dict[str, str] = Field(
        default_factory=dict,
        description="Module prefix to owning repo mapping (e.g., 'omnibase_infra.services.': 'omnibase_infra')",
    )

    forbidden_import_prefixes: list[str] = Field(
        default_factory=list,
        description="Import prefixes that are forbidden (e.g., 'omnibase_infra.services')",
    )

    allowed_cross_repo_prefixes: list[str] = Field(
        default_factory=list,
        description="Import prefixes allowed for cross-repo use (e.g., 'omnibase_core.protocols')",
    )

    forbidden_paths: list[str] = Field(
        default_factory=list,
        description="Glob patterns for paths where certain code cannot exist",
    )

    allowed_paths: list[str] = Field(
        default_factory=list,
        description="Glob patterns for allowed paths",
    )


class ModelRuleForbiddenImportsConfig(ModelRuleConfigBase):
    """Configuration for forbidden_imports rule.

    Enforces import restrictions at a granular level.
    """

    forbidden_prefixes: list[str] = Field(
        default_factory=list,
        description="Module prefixes that cannot be imported",
    )

    forbidden_modules: list[str] = Field(
        default_factory=list,
        description="Specific modules that cannot be imported",
    )

    exceptions: list[str] = Field(
        default_factory=list,
        description="Modules allowed despite matching forbidden patterns",
    )


class ModelRuleTopicNamingConfig(ModelRuleConfigBase):
    """Configuration for topic_naming rule.

    Enforces Kafka topic naming conventions.
    """

    require_env_prefix: bool = Field(
        default=True,
        description="Whether topics must have environment prefix",
    )

    allowed_patterns: list[str] = Field(
        default_factory=lambda: [r"^[a-z]+\.evt\..+\.v[0-9]+$"],
        description="Regex patterns that topic names must match",
    )

    forbidden_patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns that topic names must not match",
    )


class ModelRuleErrorTaxonomyConfig(ModelRuleConfigBase):
    """Configuration for error_taxonomy rule.

    Enforces canonical error module usage.
    """

    canonical_error_modules: list[str] = Field(
        default_factory=list,
        description="Modules that define canonical error types",
    )

    forbidden_error_modules: list[str] = Field(
        default_factory=list,
        description="Modules that should not define custom errors",
    )

    require_error_code: bool = Field(
        default=True,
        description="Whether errors must have error codes",
    )


class ModelRuleContractSchemaConfig(ModelRuleConfigBase):
    """Configuration for contract_schema_valid rule.

    Validates YAML contract files against schema.
    """

    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version to validate against",
    )

    required_fields: list[str] = Field(
        default_factory=lambda: ["name", "version", "node_type"],
        description="Fields required in all contracts",
    )


__all__ = [
    "ModelRuleConfigBase",
    "ModelRuleContractSchemaConfig",
    "ModelRuleErrorTaxonomyConfig",
    "ModelRuleForbiddenImportsConfig",
    "ModelRuleRepoBoundariesConfig",
    "ModelRuleTopicNamingConfig",
]
