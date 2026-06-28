# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""FSM handler drift severity and kind enums (OMN-13735)."""

from __future__ import annotations

from enum import StrEnum


class EnumFsmHandlerDriftSeverity(StrEnum):
    """Severity of a FSM handler drift finding."""

    ERROR = "error"


class EnumFsmHandlerDriftKind(StrEnum):
    """Classification of a FSM handler drift finding."""

    TRANSITION_MISSING_IN_HANDLER = "transition_missing_in_handler"
    TRANSITION_EXTRA_IN_HANDLER = "transition_extra_in_handler"
    TRANSITION_TO_STATE_MISMATCH = "transition_to_state_mismatch"
    GUARD_MISSING_IN_HANDLER = "guard_missing_in_handler"
    GUARD_FIELD_MISMATCH = "guard_field_mismatch"
    GUARD_VALUE_MISMATCH = "guard_value_mismatch"
    HANDLER_FILE_NOT_FOUND = "handler_file_not_found"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    SYMBOL_PARSE_ERROR = "symbol_parse_error"
    CONTRACT_SCHEMA_ERROR = "contract_schema_error"
