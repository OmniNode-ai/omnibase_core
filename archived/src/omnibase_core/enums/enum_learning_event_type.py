"""
Enum for learning event types that trigger rule generation or updates.
"""

from enum import Enum


class EnumLearningEventType(str, Enum):
    """Types of learning events that trigger rule generation or updates."""

    DEVELOPER_CORRECTION = "developer_correction"
    CONTEXT_SUCCESS = "context_success"
    CONTEXT_FAILURE = "context_failure"
    PATTERN_DETECTED = "pattern_detected"
    RULE_GENERATED = "rule_generated"
    RULE_VALIDATED = "rule_validated"
    RULE_PROMOTED = "rule_promoted"
    RULE_DEPRECATED = "rule_deprecated"
    WORKFLOW_STARTED = "workflow_started"
    INTELLIGENCE_EXTRACTED = "intelligence_extracted"
