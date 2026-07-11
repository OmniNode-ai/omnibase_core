# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict for default output state from contract state reducer."""

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.enums.enum_onex_status import EnumOnexStatus
    from omnibase_core.types.type_semver import ProtocolSemVer


class TypedDictDefaultOutputState(TypedDict):
    status: "EnumOnexStatus"
    message: str
    version: "ProtocolSemVer"
