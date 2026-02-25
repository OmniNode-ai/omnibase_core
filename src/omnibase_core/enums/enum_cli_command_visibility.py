# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
CLI Command Visibility Enum.

Controls whether a command appears in help output, catalogs, and
discovery surfaces for the registry-driven CLI system.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCliCommandVisibility(StrValueHelper, str, Enum):
    """
    Visibility classifications for CLI commands in cli.contribution.v1 contracts.

    Governs which commands appear in help output, CLI catalogs, and
    discovery surfaces. Hidden and deprecated commands are still executable
    but not surfaced to end users by default.

    Values:
        PUBLIC: Fully visible in help, catalog, and discovery.
        HIDDEN: Executable but not surfaced in help or catalogs.
        EXPERIMENTAL: Visible with a warning label; not for production use.
        DEPRECATED: Visible with deprecation notice; scheduled for removal.
    """

    PUBLIC = "public"
    HIDDEN = "hidden"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"

    @classmethod
    def is_surfaced(cls, visibility: "EnumCliCommandVisibility") -> bool:
        """Return True if the command should appear in standard help output."""
        return visibility in {cls.PUBLIC, cls.EXPERIMENTAL, cls.DEPRECATED}

    @classmethod
    def is_production_ready(cls, visibility: "EnumCliCommandVisibility") -> bool:
        """Return True if the command is safe for production use."""
        return visibility in {cls.PUBLIC, cls.HIDDEN}


__all__ = ["EnumCliCommandVisibility"]
