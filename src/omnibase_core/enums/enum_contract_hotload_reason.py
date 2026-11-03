# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reason carried by a reply, an applied event or a state entry (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadReason(UtilStrValueHelper, str, Enum):
    """Why the registry rejected a request or a runtime did not apply a change.

    The values are the tokens plan sections 3.2 and 4 spell in capitals. Registry
    side: ``VERSION_CONFLICT``, ``REQUEST_ID_REUSED``, ``BASELINE_PROTECTED``,
    ``OWNER_FORBIDDEN``, ``OWNER_MISMATCH``, ``REGISTRY_FROZEN``,
    ``ALREADY_REGISTERED``, and the four rejection causes of error chain E1
    (``NOT_INSTALLED``, ``HASH_NOT_INSTALLED``, ``HANDLER_OUTSIDE_PREFIX``,
    ``PROFILE_NOT_LOADED``). Runtime side: ``PACKAGE_HASH_MISMATCH``,
    ``NO_PROVISIONER``, ``CORE_RUNTIME_OWNED``, ``DUPLICATE_COMMAND_OWNER``,
    ``TOPIC_SPEC_CONFLICT``, ``STORE_UNAVAILABLE``. First-request ingress:
    ``CONTRACT_NOT_ANNOUNCED``, ``NOT_ADMITTED``, ``HASH_DRIFT``.
    """

    VERSION_CONFLICT = "VERSION_CONFLICT"
    REQUEST_ID_REUSED = "REQUEST_ID_REUSED"
    BASELINE_PROTECTED = "BASELINE_PROTECTED"
    OWNER_FORBIDDEN = "OWNER_FORBIDDEN"
    OWNER_MISMATCH = "OWNER_MISMATCH"
    REGISTRY_FROZEN = "REGISTRY_FROZEN"
    ALREADY_REGISTERED = "ALREADY_REGISTERED"
    NOT_INSTALLED = "NOT_INSTALLED"
    HASH_NOT_INSTALLED = "HASH_NOT_INSTALLED"
    HANDLER_OUTSIDE_PREFIX = "HANDLER_OUTSIDE_PREFIX"
    PROFILE_NOT_LOADED = "PROFILE_NOT_LOADED"
    PACKAGE_HASH_MISMATCH = "PACKAGE_HASH_MISMATCH"
    NO_PROVISIONER = "NO_PROVISIONER"
    CORE_RUNTIME_OWNED = "CORE_RUNTIME_OWNED"
    DUPLICATE_COMMAND_OWNER = "DUPLICATE_COMMAND_OWNER"
    TOPIC_SPEC_CONFLICT = "TOPIC_SPEC_CONFLICT"
    STORE_UNAVAILABLE = "STORE_UNAVAILABLE"
    CONTRACT_NOT_ANNOUNCED = "CONTRACT_NOT_ANNOUNCED"
    NOT_ADMITTED = "NOT_ADMITTED"
    HASH_DRIFT = "HASH_DRIFT"
