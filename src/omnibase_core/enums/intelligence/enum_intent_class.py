# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent class enumeration for the Intent Intelligence Framework.

Defines the canonical set of intent classes used by classification,
drift detection, forecasting, graph, and commit binding subsystems.
These classes represent the primary action categories derived from
user prompt and session analysis.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumIntentClass(StrValueHelper, str, Enum):
    """Canonical intent classes for the Intent Intelligence Framework.

    These classes classify user intent at a higher abstraction level than
    ``EnumIntentCategory``, targeting engineering workflow semantics.

    Values:
        REFACTOR: Structural code improvements without behavior change.
        BUGFIX: Diagnosing and resolving defects.
        FEATURE: Implementing new capabilities or user-facing functionality.
        ANALYSIS: Reviewing, inspecting, or evaluating code or systems.
        CONFIGURATION: Modifying settings, environment, or build files.
        DOCUMENTATION: Creating or updating docs, comments, or guides.
        MIGRATION: Moving code, data, or infrastructure between states.
        SECURITY: Addressing vulnerabilities, hardening, or compliance.
    """

    REFACTOR = "refactor"
    """Structural code improvements without behavior change."""

    BUGFIX = "bugfix"
    """Diagnosing and resolving defects."""

    FEATURE = "feature"
    """Implementing new capabilities or user-facing functionality."""

    ANALYSIS = "analysis"
    """Reviewing, inspecting, or evaluating code or systems."""

    CONFIGURATION = "configuration"
    """Modifying settings, environment, or build files."""

    DOCUMENTATION = "documentation"
    """Creating or updating documentation, comments, or guides."""

    MIGRATION = "migration"
    """Moving code, data, or infrastructure between states."""

    SECURITY = "security"
    """Addressing vulnerabilities, hardening, or compliance."""


__all__ = ["EnumIntentClass"]
