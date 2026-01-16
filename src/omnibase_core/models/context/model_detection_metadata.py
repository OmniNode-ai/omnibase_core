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
from omnibase_core.models.errors.model_onex_error import ModelOnexError
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
        description=(
            "Category of the detected pattern for classification "
            "(e.g., 'injection', 'xss', 'credential_exposure', 'malware')"
        ),
    )
    detection_source: str | None = Field(
        default=None,
        description=(
            "Source or engine that detected the pattern "
            "(e.g., 'regex_scanner', 'ml_classifier', 'signature_match')"
        ),
    )
    rule_version: ModelSemVer | None = Field(
        default=None,
        description=(
            "Version of the detection rule that matched. Used for tracking "
            "rule updates and detection accuracy analysis. Accepts string "
            "format (e.g., '2.1.0') which is automatically converted to ModelSemVer."
        ),
    )
    false_positive_likelihood: EnumLikelihood | str | None = Field(
        default=None,
        description=(
            "Estimated likelihood of false positive (e.g., low, medium, high). "
            "Helps prioritize investigation. Accepts EnumLikelihood enum values "
            "or string representations."
        ),
    )
    remediation_hint: str | None = Field(
        default=None,
        description=(
            "Suggested remediation action or reference to remediation documentation "
            "(e.g., 'Rotate exposed credentials immediately')"
        ),
    )

    @field_validator("rule_version", mode="before")
    @classmethod
    def coerce_rule_version(
        cls, v: ModelSemVer | str | dict[str, object] | None
    ) -> ModelSemVer | None:
        """Coerce string or dict values to ModelSemVer.

        Provides flexible input handling for rule_version field:
        - String format "X.Y.Z" is parsed to ModelSemVer
        - Dict format {"major": X, "minor": Y, "patch": Z} is converted
        - ModelSemVer instances are passed through unchanged
        - None values are passed through unchanged

        Args:
            v: The rule version value as ModelSemVer, string, dict, or None.

        Returns:
            The coerced ModelSemVer value, or None if input is None.

        Raises:
            ValueError: If string format is invalid, dict is malformed, or value
                is not ModelSemVer, str, dict, or None.

        Example:
            >>> metadata = ModelDetectionMetadata(rule_version="2.1.0")
            >>> metadata.rule_version
            ModelSemVer(major=2, minor=1, patch=0)
        """
        if v is None:
            return None
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            # Use ModelSemVer.parse() for string parsing
            try:
                return ModelSemVer.parse(v)
            except ModelOnexError as e:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(f"Invalid rule_version string: {v!r}") from e
        if isinstance(v, dict):
            # Allow dict format like {"major": 1, "minor": 2, "patch": 3}
            try:
                # Extract and validate required fields explicitly
                major = v.get("major")
                minor = v.get("minor")
                patch = v.get("patch")
                if (
                    not isinstance(major, int)
                    or not isinstance(minor, int)
                    or not isinstance(patch, int)
                ):
                    # error-ok: Pydantic field_validator requires ValueError
                    raise ValueError(
                        "Invalid rule_version dict: major, minor, patch must be integers"
                    )
                return ModelSemVer(major=major, minor=minor, patch=patch)
            except (TypeError, ValueError) as e:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Invalid rule_version dict format: expected {{'major': int, "
                    f"'minor': int, 'patch': int}}, got {v}"
                ) from e
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(f"Expected ModelSemVer, str, or dict, got {type(v).__name__}")

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
