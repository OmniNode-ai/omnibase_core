"""ModelSubcontractConstraintValidator - Shared Subcontract Validation Logic.

Provides unified validation logic for subcontract architectural constraints
across all contract node types, eliminating code duplication and ensuring
consistent ONEX compliance.

Strict typing is enforced - no Any types allowed in implementation.
"""

from .model_contract_data import ModelContractData
from .model_subcontract_constraint_validator_class import (
    ModelSubcontractConstraintValidator,
)

__all__ = [
    "ModelContractData",
    "ModelSubcontractConstraintValidator",
]
