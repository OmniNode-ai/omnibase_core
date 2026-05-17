# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


# Enum for node registry execution modes (ONEX Standard)
@unique
class EnumRegistryExecutionMode(UtilStrValueHelper, str, Enum):
    MEMORY = "memory"
    CONTAINER = "container"
    EXTERNAL = "external"


__all__ = ["EnumRegistryExecutionMode"]
