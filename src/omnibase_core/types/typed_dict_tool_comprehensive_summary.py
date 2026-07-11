# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
    from omnibase_core.types.type_semver import ProtocolSemVer


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
    current_stable_version: ProtocolSemVer
    current_development_version: ProtocolSemVer | None
    version_count: int
    active_version_count: int
    capability_count: int
    dependency_count: int
    required_dependencies: int
    optional_dependencies: int
    resource_requirements: TypedDictToolResourceSummary
    security_compliant: bool
    # OMN-14337: recommended_version/security_assessment carry the tool-version /
    # tool-security-assessment domain models at runtime; widened to object to
    # sever the types->models import-layering back-edge (immovable domain models;
    # no consumer reads structured attributes off these fields).
    recommended_version: object | None
    security_assessment: object
    testing_requirements: TypedDictToolTestingSummary


__all__ = ["TypedDictToolComprehensiveSummary"]
