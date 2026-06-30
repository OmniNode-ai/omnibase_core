# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-Driven UI Platform enums (OMN-13129 / OMN-13131).

UI-platform-scoped enums for the action-gate policy. These are intentionally
distinct from the routing/overseer ``EnumRiskLevel`` definitions and are not
re-exported from the top-level ``omnibase_core.enums`` package to avoid a name
collision; import them from ``omnibase_core.enums.ui``.
"""

from omnibase_core.enums.ui.enum_commit_level import EnumCommitLevel
from omnibase_core.enums.ui.enum_risk_level import EnumRiskLevel

__all__: list[str] = [
    "EnumCommitLevel",
    "EnumRiskLevel",
]
