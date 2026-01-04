"""
Shared fixtures for comparison model tests.

Provides reusable fixtures for:
- Sample execution data for baseline/replay comparison
- Invariant result samples
- Output hashes and diffs
"""

from typing import Any
from uuid import UUID

import pytest

from omnibase_core.models.comparison import ModelOutputDiff, ModelValueChange

# Sample UUIDs for testing - centralized constants for all comparison tests
TEST_BASELINE_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_REPLAY_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_COMPARISON_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_INVARIANT_ID_1 = UUID("44444444-4444-4444-4444-444444444444")
TEST_INVARIANT_ID_2 = UUID("55555555-5555-5555-5555-555555555555")


@pytest.fixture
def sample_input_hash() -> str:
    """Provide deterministic input hash for testing.

    Returns:
        SHA256 hash string representing a sample input fingerprint.
    """
    return "sha256:abc123def456789012345678901234567890123456789012345678901234"


@pytest.fixture
def sample_matching_output_hashes() -> tuple[str, str]:
    """Provide matching output hashes for identical outputs.

    Returns:
        Tuple of two identical SHA256 hash strings for baseline and replay.
    """
    hash_value = "sha256:xyz789012345678901234567890123456789012345678901234567890123"
    return (hash_value, hash_value)


@pytest.fixture
def sample_different_output_hashes() -> tuple[str, str]:
    """Provide different output hashes for differing outputs.

    Returns:
        Tuple of two different SHA256 hash strings for baseline and replay.
    """
    return (
        "sha256:baseline123456789012345678901234567890123456789012345678901234",
        "sha256:replay456789012345678901234567890123456789012345678901234567890",
    )


@pytest.fixture
def sample_latency_metrics() -> dict[str, float]:
    """Provide sample latency metrics for comparison.

    Returns:
        Dictionary with baseline_latency_ms and replay_latency_ms keys.
    """
    return {
        "baseline_latency_ms": 150.0,
        "replay_latency_ms": 180.0,
    }


@pytest.fixture
def sample_cost_metrics() -> dict[str, float | None]:
    """Provide sample cost metrics for comparison.

    Returns:
        Dictionary with baseline_cost and replay_cost keys.
    """
    return {
        "baseline_cost": 0.05,
        "replay_cost": 0.04,
    }


@pytest.fixture
def sample_output_diff() -> ModelOutputDiff:
    """Provide sample structured diff for testing.

    Returns:
        ModelOutputDiff with sample value changes.
    """
    return ModelOutputDiff(
        values_changed={
            "root['response']['text']": ModelValueChange(
                old_value="Original response",
                new_value="Updated response",
            )
        },
        has_differences=True,
    )


@pytest.fixture
def sample_invariant_comparison_summary() -> dict[str, Any]:
    """Provide sample invariant comparison summary data.

    Returns:
        Dictionary with invariant comparison metrics including totals,
        pass/fail counts, and regression detection flag.
    """
    return {
        "total_invariants": 5,
        "both_passed": 3,
        "both_failed": 0,
        "new_violations": 1,
        "fixed_violations": 1,
        "regression_detected": True,
    }


@pytest.fixture
def sample_baseline_execution_id() -> UUID:
    """Provide sample baseline execution ID for testing.

    Returns:
        UUID representing a baseline execution identifier.
    """
    return TEST_BASELINE_ID


@pytest.fixture
def sample_replay_execution_id() -> UUID:
    """Provide sample replay execution ID for testing.

    Returns:
        UUID representing a replay execution identifier.
    """
    return TEST_REPLAY_ID


@pytest.fixture
def sample_execution_metadata() -> dict[str, Any]:
    """Provide sample execution metadata for comparison tests.

    Returns:
        Dictionary with common execution metadata fields.
    """
    return {
        "node_id": "node_llm_call_gpt4",
        "node_version": "1.0.0",
        "environment": "test",
        "timestamp": "2025-01-04T12:00:00Z",
    }
