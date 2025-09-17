"""Workflow types and enums for Reducer Pattern Engine."""

from enum import Enum


class WorkflowType(Enum):
    """Supported workflow types for multi-workflow support."""

    DOCUMENT_REGENERATION = "document_regeneration"
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    ROUTING = "routing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
