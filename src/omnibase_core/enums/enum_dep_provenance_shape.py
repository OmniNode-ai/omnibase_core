# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shapes a package source may take in a dependency provenance contract (OMN-22011)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumDepProvenanceShape"]


@unique
class EnumDepProvenanceShape(UtilStrValueHelper, str, Enum):
    """How a package is sourced: the contract lists the admitted ones per package."""

    REGISTRY = "registry"
    WORKSPACE = "workspace"
    SIBLING_DEV_TAG = "sibling_dev_tag"
