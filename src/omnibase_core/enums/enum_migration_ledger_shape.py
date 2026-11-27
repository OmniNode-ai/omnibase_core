# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The column shapes a deployment database's migration ledger may declare."""

from enum import StrEnum, unique

__all__ = ["EnumMigrationLedgerShape"]


@unique
class EnumMigrationLedgerShape(StrEnum):
    """Which identity columns a migration ledger carries."""

    STREAM_DOMAIN_VERSION_CHECKSUM = "stream_domain_version_checksum"
    VERSION_CHECKSUM = "version_checksum"
