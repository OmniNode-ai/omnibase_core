# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a runtime did with, or has observed of, one registry change (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadStatus(UtilStrValueHelper, str, Enum):
    """The outcome of one registry change at one runtime instance.

    Used by the applied event and by the ``observed`` entry of the runtime state
    record (plan section 3.2): ``materialized``, ``adopted``, ``replaced``,
    ``removed``, ``refused`` (with a reason), ``not_ready`` and ``failed``.
    """

    MATERIALIZED = "materialized"
    ADOPTED = "adopted"
    REPLACED = "replaced"
    REMOVED = "removed"
    REFUSED = "refused"
    NOT_READY = "not_ready"
    FAILED = "failed"
