from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumValidationType(StrValueHelper, str, Enum):
    CLI_NODE_PARITY = "cli_node_parity"
    SCHEMA_CONFORMANCE = "schema_conformance"
    ERROR_CODE_USAGE = "error_code_usage"
    CONTRACT_COMPLIANCE = "contract_compliance"
    INTROSPECTION_VALIDITY = "introspection_validity"


__all__ = ["EnumValidationType"]
