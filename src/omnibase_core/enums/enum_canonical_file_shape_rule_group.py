# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Rule groups the canonical-file-shape node runs (OMN-21515)."""

from enum import StrEnum, unique


@unique
class EnumCanonicalFileShapeRuleGroup(StrEnum):
    """The groups of rules a run of the canonical-file-shape node selects from."""

    FILE_SHAPE = "file-shape"
    NODE_HOME = "node-home"
