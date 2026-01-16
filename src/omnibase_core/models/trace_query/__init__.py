"""Trace query models module.

This module provides query and summary models for trace recording operations.

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
from omnibase_core.models.trace_query.model_trace_summary import ModelTraceSummary

__all__ = [
    "ModelTraceQuery",
    "ModelTraceSummary",
]
