# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Regression tests for complete ModelToolHealth forward-reference wiring."""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_tool_type import EnumToolType
from omnibase_core.models.core.model_generic_properties import ModelGenericProperties
from omnibase_core.models.core.model_monitoring_metrics import ModelMonitoringMetrics
from omnibase_core.models.health.model_tool_health import ModelToolHealth

pytestmark = pytest.mark.unit


def test_model_tool_health_resolves_and_accepts_typed_nested_models() -> None:
    """The model is complete before callers construct nested configuration data."""
    assert ModelToolHealth.__pydantic_complete__ is True
    configuration = ModelGenericProperties.from_flat_dict({"enabled": True})
    metrics = ModelMonitoringMetrics(response_time_ms=12.0)
    result = ModelToolHealth(
        tool_name="example_tool",
        status=EnumHealthStatus.AVAILABLE,
        tool_type=EnumToolType.FUNCTION,
        is_callable=True,
        configuration=configuration,
        metrics=metrics,
    )
    assert result.configuration is configuration
    assert result.metrics is metrics


def test_model_tool_health_import_order_resolves_in_fresh_process() -> None:
    """Importing the health package from a clean process leaves the model complete."""
    script = textwrap.dedent(
        """
        from omnibase_core.enums.enum_health_status import EnumHealthStatus
        from omnibase_core.enums.enum_tool_type import EnumToolType
        from omnibase_core.models.health.model_tool_health import ModelToolHealth

        assert ModelToolHealth.__pydantic_complete__ is True
        result = ModelToolHealth(
            tool_name="fresh_process_tool",
            status=EnumHealthStatus.AVAILABLE,
            tool_type=EnumToolType.FUNCTION,
            is_callable=True,
        )
        assert result.tool_name == "fresh_process_tool"
        """
    )
    subprocess.run([sys.executable, "-c", script], check=True)
