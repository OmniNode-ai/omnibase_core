"""
TypedDict for tool comprehensive summary.

Strongly-typed representation for comprehensive tool summary data.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from omnibase_core.types.typed_dict_tool_resource_summary import (
    TypedDictToolResourceSummary,
)
from omnibase_core.types.typed_dict_tool_testing_summary import (
    TypedDictToolTestingSummary,
)

if TYPE_CHECKING:
    from omnibase_core.models.core.model_tool_security_assessment import (
        ModelToolSecurityAssessment,
    )
    from omnibase_core.models.core.model_tool_version import ModelToolVersion
    from omnibase_core.models.primitives.model_semver import ModelSemVer


class TypedDictToolComprehensiveSummary(TypedDict):
    """
    Strongly-typed dictionary for comprehensive tool summary.

    Replaces dict[str, Any] return type from get_comprehensive_summary()
    with proper type structure.
    """

    tool_name: str
    description: str
    author: str
    node_type: str
    business_logic_pattern: str
    status: str
    current_stable_version: ModelSemVer
    current_development_version: ModelSemVer | None
    version_count: int
    active_version_count: int
    capability_count: int
    dependency_count: int
    required_dependencies: int
    optional_dependencies: int
    resource_requirements: TypedDictToolResourceSummary
    security_compliant: bool
    recommended_version: ModelToolVersion | None
    security_assessment: ModelToolSecurityAssessment
    testing_requirements: TypedDictToolTestingSummary


__all__ = ["TypedDictToolComprehensiveSummary"]
