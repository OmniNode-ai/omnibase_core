# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PostgreSQL privileges supported by typed deployment topology grants."""

from enum import StrEnum, unique

__all__ = ["EnumDatabasePrivilege"]


@unique
class EnumDatabasePrivilege(StrEnum):
    """Explicit privilege that may be granted to a workload principal."""

    CONNECT = "CONNECT"
    CREATE = "CREATE"
    TEMPORARY = "TEMPORARY"
    USAGE = "USAGE"
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    TRUNCATE = "TRUNCATE"
    REFERENCES = "REFERENCES"
    TRIGGER = "TRIGGER"
    EXECUTE = "EXECUTE"
