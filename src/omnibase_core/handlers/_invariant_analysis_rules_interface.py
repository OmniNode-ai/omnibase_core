# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container-resolved interface of the pure invariant-analysis rule function (OMN-21565)."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

__all__ = ["InvariantAnalysisRulesInterface"]

TRequest_contra = TypeVar("TRequest_contra", contravariant=True)
TRules_contra = TypeVar("TRules_contra", contravariant=True)
TFindings_co = TypeVar("TFindings_co", covariant=True)


@runtime_checkable
class InvariantAnalysisRulesInterface(
    Protocol[TRequest_contra, TRules_contra, TFindings_co]
):
    """Judge one document against supplied facts and typed rules, without I/O."""

    def __call__(self, request: TRequest_contra, rules: TRules_contra) -> TFindings_co:
        """Return one finding per violation."""
        ...
