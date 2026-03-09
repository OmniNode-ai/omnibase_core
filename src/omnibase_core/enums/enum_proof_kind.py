# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Proof kind enum for criterion-level proof linkage (OMN-4339).

Defines the kinds of proof references used in ``ModelProofRequirement``.
Each kind determines the reference format and whether the proof is
machine-verifiable.

Ref semantics by kind:

- ``unit_test`` / ``integration_test``: pytest node ID
  (``path/to/test.py::test_function_name``)
- ``static_check``: registered validator ID
  (see ``static_checks_registry.yaml``)
- ``artifact``: file path relative to repo root
- ``manual``: human-readable description — satisfies traceability only,
  NOT machine-verifiable proof
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumProofKind"]


class EnumProofKind(str, Enum):
    """Kind of proof reference in a ModelProofRequirement."""

    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    STATIC_CHECK = "static_check"
    ARTIFACT = "artifact"
    MANUAL = "manual"  # traceability only; not machine-verifiable
