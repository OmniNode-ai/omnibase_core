from enum import Enum


class EnumValidationType(str, Enum):
    CLI_NODE_PARITY = "cli_node_parity"
    SCHEMA_CONFORMANCE = "schema_conformance"
    ERROR_CODE_USAGE = "error_code_usage"
    CONTRACT_COMPLIANCE = "contract_compliance"
    INTROSPECTION_VALIDITY = "introspection_validity"
