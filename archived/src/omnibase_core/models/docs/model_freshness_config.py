"""
Freshness configuration models for document monitoring.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.docs.model_document_freshness import (
    EnumDocumentType,
    ModelFreshnessTimeThresholds,
)


class ModelFreshnessConfiguration(BaseModel):
    """Configuration for document freshness monitoring."""

    thresholds: dict[EnumDocumentType, ModelFreshnessTimeThresholds] = Field(
        ...,
        description="Time thresholds by document type",
    )

    @classmethod
    def get_default_config(cls) -> "ModelFreshnessConfiguration":
        """Get default freshness configuration."""
        return cls(
            thresholds={
                EnumDocumentType.README: ModelFreshnessTimeThresholds(
                    fresh=30,
                    stale=90,
                    critical=180,
                ),
                EnumDocumentType.API_DOCUMENTATION: ModelFreshnessTimeThresholds(
                    fresh=14,
                    stale=60,
                    critical=120,
                ),
                EnumDocumentType.TUTORIAL: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
                EnumDocumentType.ARCHITECTURE: ModelFreshnessTimeThresholds(
                    fresh=90,
                    stale=180,
                    critical=365,
                ),
                EnumDocumentType.CONFIGURATION: ModelFreshnessTimeThresholds(
                    fresh=30,
                    stale=90,
                    critical=180,
                ),
                EnumDocumentType.TROUBLESHOOTING: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
                EnumDocumentType.DEVELOPER_NOTES: ModelFreshnessTimeThresholds(
                    fresh=90,
                    stale=180,
                    critical=365,
                ),
                EnumDocumentType.BUSINESS_REQUIREMENTS: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
                EnumDocumentType.TECHNICAL_SPECIFICATION: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
                EnumDocumentType.DEPLOYMENT_GUIDE: ModelFreshnessTimeThresholds(
                    fresh=30,
                    stale=90,
                    critical=180,
                ),
                EnumDocumentType.CHANGELOG: ModelFreshnessTimeThresholds(
                    fresh=7,
                    stale=30,
                    critical=60,
                ),
                EnumDocumentType.USER_GUIDE: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
                EnumDocumentType.UNKNOWN: ModelFreshnessTimeThresholds(
                    fresh=60,
                    stale=120,
                    critical=240,
                ),
            },
        )
