# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reason carried by a reply or a runtime applied event (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadReason(UtilStrValueHelper, str, Enum):
    """Typed reason carried by a reply or a runtime applied event."""

    NONE = "none"
    HASH_MISMATCH = "hash_mismatch"
    NOT_INSTALLED = "not_installed"
    VERSION_CONFLICT = "version_conflict"
    NOT_OWNER = "not_owner"
    UNTRUSTED_CONTRACT = "untrusted_contract"
    MALFORMED_CONTRACT = "malformed_contract"
    TOPIC_PROVISIONING_FAILED = "topic_provisioning_failed"
    WIRING_FAILED = "wiring_failed"
