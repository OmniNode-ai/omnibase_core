# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Detection metadata model for security pattern matching.

This module provides ModelDetectionMetadata, a typed model for security
detection match metadata that replaces untyped dict[str, str] fields. It
captures pattern categorization, detection source, and remediation hints.

Thread Safety:
    ModelDetectionMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.detection: Detection match models
    - omnibase_core.models.context.model_audit_metadata: Audit metadata
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumLikelihood
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_enum_normalizer import create_enum_normalizer

__all__ = ["ModelDetectionMetadata"]


class ModelDetectionMetadata(BaseModel):
    """Security detection match metadata.

    Provides typed metadata for security pattern detection results. Supports
    pattern categorization, false positive assessment, and remediation guidance.

    Attributes:
        pattern_category: Category of the detected pattern for classification
            (e.g., "injection", "xss", "credential_exposure", "malware").
        detection_source: Source or engine that detected the pattern
            (e.g., "regex_scanner", "ml_classifier", "signature_match").
        rule_version: Version of the detection rule that matched. Used for
            tracking rule updates and detection accuracy analysis.
        false_positive_likelihood: Estimated likelihood of false positive
            (e.g., "low", "medium", "high"). Helps prioritize investigation.
        remediation_hint: Suggested remediation action or reference to
            remediation documentation.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelDetectionMetadata
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>>
        >>> detection = ModelDetectionMetadata(
        ...     pattern_category="credential_exposure",
        ...     detection_source="regex_scanner",
        ...     rule_version=ModelSemVer(major=2, minor=1, patch=0),
        ...     false_positive_likelihood="low",
        ...     remediation_hint="Rotate exposed credentials immediately",
        ... )
        >>> detection.pattern_category
        'credential_exposure'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pattern_category: str | None = Field(
        default=None,
        description="Detection pattern category",
    )
    detection_source: str | None = Field(
        default=None,
        description="Source of detection",
    )
    rule_version: ModelSemVer | None = Field(
        default=None,
        description="Detection rule version",
    )
    false_positive_likelihood: EnumLikelihood | str | None = Field(
        default=None,
        description=(
            "FP likelihood (e.g., low, medium, high, very_low, very_high). "
            "Accepts EnumLikelihood or string."
        ),
    )
    remediation_hint: str | None = Field(
        default=None,
        description="Suggested remediation",
    )

    @field_validator("false_positive_likelihood", mode="before")
    @classmethod
    def normalize_false_positive_likelihood(
        cls, v: EnumLikelihood | str | None
    ) -> EnumLikelihood | str | None:
        """Normalize likelihood value from string or enum input.

        Args:
            v: The likelihood value, either as EnumLikelihood, string, or None.

        Returns:
            The normalized value - EnumLikelihood if valid enum value,
            otherwise the original string for extensibility.
        """
        return create_enum_normalizer(EnumLikelihood)(v)
