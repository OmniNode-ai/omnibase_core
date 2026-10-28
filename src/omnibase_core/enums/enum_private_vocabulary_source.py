# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Sources of operator-private vocabulary paths (OMN-21433)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumPrivateVocabularySource"]


@unique
class EnumPrivateVocabularySource(UtilStrValueHelper, str, Enum):
    """The setting that supplied a resolved vocabulary path."""

    EXPLICIT = "explicit"
    ENVIRONMENT = "environment"
    WORKSPACE_CONFIG_ROOT = "workspace_config_root"
