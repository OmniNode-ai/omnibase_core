# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Compose-contract drift kind enumeration.

Classifies violations found by ValidatorBannedComposeVars when comparing
Docker compose / k8s manifest environment blocks against contract.yaml
event_bus.subscribe_topics / publish_topics declarations.

Related ticket: OMN-9062 (trigger: OMN-8840, parent: OMN-9048).
"""

import enum

__all__ = ["EnumComposeDriftKind"]


@enum.unique
class EnumComposeDriftKind(enum.StrEnum):
    """Kind of compose↔contract drift violation."""

    BANNED_VAR = "BANNED_VAR"
    MISSING_VAR = "MISSING_VAR"
