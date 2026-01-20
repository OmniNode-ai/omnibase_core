"""
TypedDicts for demo CLI data structures.

This module provides type definitions for the demo CLI's data structures,
including corpus samples, evaluation results, configuration, and summaries.

Related:
    - OMN-1396: Demo V1 CLI

.. versionadded:: 0.7.0
"""

from __future__ import annotations

__all__ = [
    "TypedDictCorpusSample",
    "TypedDictDemoConfig",
    "TypedDictDemoResult",
    "TypedDictDemoSummary",
    "TypedDictInvariantResult",
]

from typing import NotRequired, TypedDict


class TypedDictInvariantResult(TypedDict):
    """TypedDict for individual invariant evaluation results.

    Required Fields:
        passed: Number of samples that passed this invariant.
        total: Total number of samples checked against this invariant.
    """

    passed: int
    total: int


class TypedDictDemoResult(TypedDict):
    """TypedDict for individual sample evaluation results.

    Required Fields:
        sample_id: Identifier for the sample.
        passed: Whether the sample passed all invariants.
        invariants_checked: List of invariant names that were checked.
    """

    sample_id: str
    passed: bool
    invariants_checked: list[str]


class TypedDictDemoSummary(TypedDict):
    """TypedDict for demo run summary results.

    Required Fields:
        total: Total number of samples evaluated.
        passed: Number of samples that passed.
        failed: Number of samples that failed.
        pass_rate: Pass rate as a float (0.0 to 1.0).
        verdict: Overall verdict (PASS, REVIEW REQUIRED, FAIL).
        invariant_results: Per-invariant results.
    """

    total: int
    passed: int
    failed: int
    pass_rate: float
    verdict: str
    invariant_results: dict[str, TypedDictInvariantResult]


class TypedDictDemoConfig(TypedDict):
    """TypedDict for demo run configuration.

    Required Fields:
        scenario: Name of the scenario being run.
        live: Whether using live LLM calls (vs mock).
        timestamp: Timestamp of the run.

    Optional Fields:
        seed: Random seed for deterministic execution.
        repeat: Number of times to repeat corpus.
    """

    scenario: str
    live: bool
    timestamp: str
    seed: NotRequired[int | None]
    repeat: NotRequired[int]


class TypedDictCorpusSample(TypedDict, total=False):
    """TypedDict for corpus sample data.

    This is a partial TypedDict (total=False) as corpus samples have dynamic
    fields depending on the scenario. The fields below are common metadata
    added during loading.

    Common Fields:
        _source_file: Relative path to the source YAML file.
        _category: Category subdirectory (e.g., 'golden', 'edge-cases').
        ticket_id: Optional ticket ID from the sample data.
    """

    _source_file: str
    _category: str
    ticket_id: str
