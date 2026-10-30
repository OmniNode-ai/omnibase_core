# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reasons an announcement is refused (OMN-21589)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumAnnounceRefusalReason(UtilStrValueHelper, str, Enum):
    """Why an announcement did not become an admitted catalog entry.

    The first four are raised by the announcer before anything is published; the
    rest are raised by admission or by the catalog, and are the same on every bus.

    Attributes:
        CONTRACT_FILE_MISSING: The package metadata lists a contract the package does not hold.
        CONTRACT_UNREADABLE: The file could not be read or is not a YAML mapping.
        CONTRACT_NAME_MISSING: The contract declares no name.
        ACKNOWLEDGEMENT_TIMEOUT: The catalog never acknowledged the announcement.
        INSTALLED_FILE_MISSING: Admission could not find the installed file.
        HASH_MISMATCH: The installed file's canonical hash is not the announced hash.
        HANDLER_OUTSIDE_TRUSTED_PREFIXES: A handler module is outside the trusted prefixes.
        PROFILE_NOT_OWNED: The contract's runtime profiles do not include one the lane owns.
        STALE_GENERATION: An older or equal generation than the one held.
        NON_AUTHORITATIVE_ANNOUNCER: A withdrawal from an announcer the overlay does not name.
    """

    CONTRACT_FILE_MISSING = "contract_file_missing"
    CONTRACT_UNREADABLE = "contract_unreadable"
    CONTRACT_NAME_MISSING = "contract_name_missing"
    ACKNOWLEDGEMENT_TIMEOUT = "acknowledgement_timeout"
    INSTALLED_FILE_MISSING = "installed_file_missing"
    HASH_MISMATCH = "hash_mismatch"
    HANDLER_OUTSIDE_TRUSTED_PREFIXES = "handler_outside_trusted_prefixes"
    PROFILE_NOT_OWNED = "profile_not_owned"
    STALE_GENERATION = "stale_generation"
    NON_AUTHORITATIVE_ANNOUNCER = "non_authoritative_announcer"
