# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a contract hot-load request or record does to one contract name (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadOperation(UtilStrValueHelper, str, Enum):
    """What a request or registry record does to one contract name.

    Plan section 4 names the three: ``register`` (a name the registry has not
    held, ``expected_version: 0``), ``replace`` (a new hash for a held name)
    and ``remove``.
    """

    REGISTER = "register"
    REPLACE = "replace"
    REMOVE = "remove"
