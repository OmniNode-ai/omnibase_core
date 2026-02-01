"""Demo models for ONEX examples and validation scenarios."""

from __future__ import annotations

from omnibase_core.enums.enum_demo_recommendation import EnumDemoRecommendation
from omnibase_core.enums.enum_demo_verdict import EnumDemoVerdict
from omnibase_core.models.demo.model_demo_config import ModelDemoConfig
from omnibase_core.models.demo.model_demo_invariant_result import ModelInvariantResult
from omnibase_core.models.demo.model_demo_summary import ModelDemoSummary
from omnibase_core.models.demo.model_demo_validation_report import (
    DEMO_REPORT_SCHEMA_VERSION,
    ModelDemoValidationReport,
)
from omnibase_core.models.demo.model_failure_detail import ModelFailureDetail
from omnibase_core.models.demo.model_sample_result import ModelSampleResult
from omnibase_core.models.demo.model_validate import (
    ModelSupportClassificationResult,
    ModelSupportTicket,
)

__all__ = [
    "DEMO_REPORT_SCHEMA_VERSION",
    "EnumDemoRecommendation",
    "EnumDemoVerdict",
    "ModelDemoConfig",
    "ModelDemoSummary",
    "ModelDemoValidationReport",
    "ModelFailureDetail",
    "ModelInvariantResult",
    "ModelSampleResult",
    "ModelSupportClassificationResult",
    "ModelSupportTicket",
]
