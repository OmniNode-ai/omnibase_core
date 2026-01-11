"""
Conftest for health model tests.

Provides shared fixtures for testing baseline health report models
and related health calculation components.
"""

from datetime import datetime

import pytest


@pytest.fixture
def sample_config() -> dict:
    """Create a sample LLM configuration."""
    return {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 1.0,
    }


@pytest.fixture
def sample_date_range() -> tuple[datetime, datetime]:
    """Create a sample date range for corpus data."""
    return (datetime(2024, 1, 1, 0, 0, 0), datetime(2024, 1, 14, 23, 59, 59))


@pytest.fixture
def generated_timestamp() -> datetime:
    """Create a sample report generation timestamp."""
    return datetime(2024, 1, 15, 10, 0, 0)
