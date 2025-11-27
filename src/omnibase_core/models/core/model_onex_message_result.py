from __future__ import annotations

from omnibase_core.models.core.model_orchestrator_info import ModelOrchestratorInfo

from .model_onex_batch_result import ModelOnexBatchResult
from .model_onex_message import ModelOnexMessage

# Import separated models
from .model_onex_result import ModelOnexResult
from .model_onex_result_metadata import ModelOnexResultMetadata
from .model_unified_run_metadata import ModelUnifiedRunMetadata
from .model_unified_summary import ModelUnifiedSummary
from .model_unified_summary_details import ModelUnifiedSummaryDetails
from .model_unified_version import ModelUnifiedVersion

# Compatibility aliases (maintain old names for any existing imports)
UnifiedSummaryDetailsModel = ModelUnifiedSummaryDetails
OnexResultModelMetadata = ModelOnexResultMetadata
OrchestratorInfoModel = ModelOrchestratorInfo  # Use proper orchestrator info model
UnifiedSummaryModel = ModelUnifiedSummary
UnifiedVersionModel = ModelUnifiedVersion
UnifiedRunModelMetadata = ModelUnifiedRunMetadata
OnexResultModel = ModelOnexResult
OnexBatchResultModel = ModelOnexBatchResult

# Re-export
__all__ = [
    "ModelOnexBatchResult",
    "ModelOnexMessage",
    "ModelOnexResult",
    "ModelOnexResultMetadata",
    "ModelUnifiedRunMetadata",
    "ModelUnifiedSummary",
    "ModelUnifiedSummaryDetails",
    "ModelUnifiedVersion",
]
