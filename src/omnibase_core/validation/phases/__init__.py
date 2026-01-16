"""
Contract Validation Pipeline Phases.

This module contains validators for each phase of the contract validation pipeline:
    - Phase 1 (PATCH): Validates individual patches before merge
    - Phase 2 (MERGE): Validates merged contracts before expansion
    - Phase 3 (EXPANDED): Validates fully expanded contracts

Pipeline Flow:
    PATCH -> MERGE -> EXPANDED

Each validator produces a ModelValidationResult with:
    - is_valid: Overall validation status
    - issues: List of validation issues with severity and codes
    - summary: Human-readable validation summary

Related:
    - OMN-1128: Contract Validation Pipeline
    - ContractPatchValidator: Phase 1 validation (in parent directory)
    - MergeValidator: Phase 2 validation (this package)
    - ExpandedContractValidator: Phase 3 validation (this package)
    - EnumValidationPhase: Pipeline phase enumeration
    - EnumContractValidationErrorCode: Error codes for phases 2 and 3

.. versionadded:: 0.4.1
"""

from omnibase_core.validation.phases.validator_expanded_contract import (
    ExpandedContractValidator,
)
from omnibase_core.validation.phases.validator_expanded_contract_graph import (
    ExpandedContractGraphValidator,
)
from omnibase_core.validation.phases.validator_merge import MergeValidator

__all__ = [
    # Phase 2 Validators
    "MergeValidator",
    # Phase 3 Validators
    "ExpandedContractValidator",
    "ExpandedContractGraphValidator",
]
