"""Framework integration model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.agents.model_domain_queries import ModelDomainQueries
from omnibase_core.types.typed_dict_pattern_catalog import TypedDictPatternCatalog


class ModelFrameworkIntegration(BaseModel):
    """Framework integration configuration.

    Defines how the agent integrates with external frameworks, references,
    and pattern catalogs.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    yaml_framework_references: list[str] | None = None
    domain_queries: ModelDomainQueries | None = None
    mandatory_functions: list[str] | None = None
    pattern_catalog: TypedDictPatternCatalog | None = None


__all__ = ["ModelFrameworkIntegration"]
