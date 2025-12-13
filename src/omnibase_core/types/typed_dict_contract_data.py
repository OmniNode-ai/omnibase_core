"""
TypedDict for YAML contract data parsed from contract files.

Used by contract_validator.py to represent the structure of parsed YAML contracts.
"""

from typing import TypedDict


class TypedDictContractData(TypedDict, total=False):
    """
    Represents parsed YAML contract data for ONEX node contracts.

    All fields are optional (total=False) since contracts may have varying structures.

    Attributes:
        name: The contract/node name
        input_model: The fully-qualified input model path (e.g., "module.ModelEffectInput")
        output_model: The fully-qualified output model path (e.g., "module.ModelEffectOutput")
        version: Version information (may be dict or ModelSemVer)
        description: Human-readable description of the contract
        node_type: The ONEX node type (effect, compute, reducer, orchestrator)
        dependencies: List of dependency specifications
    """

    name: str
    input_model: str
    output_model: str
    version: object  # Can be dict or ModelSemVer - validated separately
    description: str
    node_type: str
    dependencies: list[object]


__all__ = ["TypedDictContractData"]
