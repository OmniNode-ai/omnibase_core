"""
Shared fixtures for invariant model tests.

Provides reusable fixtures for:
- Common invariant instances
- Configuration objects for testing
"""

import pytest


@pytest.fixture
def sample_latency_config() -> dict:
    """Provide sample latency invariant config."""
    return {"max_ms": 5000}


@pytest.fixture
def sample_cost_config() -> dict:
    """Provide sample cost invariant config."""
    return {"max_cost": 0.10, "per": "request"}


@pytest.fixture
def sample_field_presence_config() -> dict:
    """Provide sample field presence invariant config."""
    return {"fields": ["response", "model", "usage"]}


@pytest.fixture
def sample_schema_config() -> dict:
    """Provide sample schema invariant config."""
    return {
        "json_schema": {
            "type": "object",
            "required": ["response"],
            "properties": {"response": {"type": "string"}},
        }
    }


@pytest.fixture
def sample_threshold_config() -> dict:
    """Provide sample threshold invariant config."""
    return {"metric_name": "accuracy", "min_value": 0.95}


@pytest.fixture
def sample_yaml_invariant_set() -> str:
    """Provide sample YAML content for invariant set."""
    return """
name: "Test Invariant Set"
target: "node_llm_call"
invariants:
  - name: "Response has required fields"
    type: field_presence
    severity: critical
    config:
      fields: ["response", "model"]
  - name: "Latency under 5s"
    type: latency
    severity: warning
    config:
      max_ms: 5000
"""
