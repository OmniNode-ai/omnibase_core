# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidationType(UtilStrValueHelper, str, Enum):
    CLI_NODE_PARITY = "cli_node_parity"
    SCHEMA_CONFORMANCE = "schema_conformance"
    ERROR_CODE_USAGE = "error_code_usage"
    CONTRACT_COMPLIANCE = "contract_compliance"
    INTROSPECTION_VALIDITY = "introspection_validity"


__all__ = ["EnumValidationType"]
