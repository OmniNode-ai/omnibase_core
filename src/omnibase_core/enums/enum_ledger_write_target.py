# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The kinds of canonical ledger target the test-write guard refuses (OMN-19513)."""

from enum import StrEnum, unique

__all__ = ["EnumLedgerWriteTarget"]


@unique
class EnumLedgerWriteTarget(StrEnum):
    """What a write reaches: a ledger file, a ledger topic or a projection DSN."""

    FILE = "file"
    TOPIC = "topic"
    DSN = "dsn"
