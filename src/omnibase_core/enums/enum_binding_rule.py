# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The rules the binding conformance check can refuse a source or contract for."""

from __future__ import annotations

from enum import StrEnum


class EnumBindingRule(StrEnum):
    """One value per way a checked node can fail."""

    NO_TABLE_ROW = "no_table_row"
    NO_CONTRACT = "no_contract"
    NO_SOURCE = "no_source"
    CONTRACT_UNREADABLE = "contract_unreadable"
    SOURCE_UNPARSEABLE = "source_unparseable"
    CONTRACT_MISSING_PROTOCOL = "contract_missing_protocol"
    CONTRACT_EXTRA_PROTOCOL = "contract_extra_protocol"
    CONTRACT_UNKNOWN_PROTOCOL = "contract_unknown_protocol"
    CONCRETE_BINDING = "concrete_binding"
    ENV_READ = "env_read"
    PATH_LITERAL = "path_literal"
    URL_LITERAL = "url_literal"
    PRIVATE_NAME = "private_name"
    PURE_LOADS_CONFIGURATION = "pure_loads_configuration"
