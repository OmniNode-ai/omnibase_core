# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""EnumStableProofKind: stable proof categories for contract evidence."""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumStableProofKind"]


class EnumStableProofKind(str, Enum):
    """Stable proof categories for ModelContractEvidenceProof.

    These proof kinds validate artifacts or behaviors. PR-state checks are
    intentionally excluded — PR metadata belongs in ModelEvidenceProvenance.
    """

    MODEL_IMPORT = "model_import"
    ARTIFACT_VALIDATION = "artifact_validation"
    SCHEMA_VALIDATION = "schema_validation"
    FILE_EXISTS = "file_exists"
    TEST_PASSES = "test_passes"
    RECEIPT_VALIDATION = "receipt_validation"
    EVIDENCE_BUNDLE_VALIDATION = "evidence_bundle_validation"
    RUNTIME_PROJECTION_PROOF = "runtime_projection_proof"
    COMMAND = "command"
