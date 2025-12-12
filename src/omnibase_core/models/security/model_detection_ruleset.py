"""
Detection RuleSet Model.

Collection of detection patterns organized by type for sensitive information detection.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_language_code import EnumLanguageCode
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)
from omnibase_core.models.security.model_detection_pattern import ModelDetectionPattern
from omnibase_core.models.security.model_security_summaries import (
    ModelDetectionRuleSetSummary,
)


class ModelDetectionRuleSet(BaseModel):
    """
    Collection of detection patterns organized by type.
    """

    ruleset_id: UUID = Field(description="Unique identifier for this ruleset")
    ruleset_name: str = Field(description="Human-readable name for this ruleset")
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Version of this ruleset",
    )
    patterns: list[ModelDetectionPattern] = Field(
        default_factory=list, description="Detection patterns in this ruleset"
    )
    detection_types: list[EnumDetectionType] = Field(
        default_factory=list, description="Types of detection covered by this ruleset"
    )
    supported_languages: list[EnumLanguageCode] = Field(
        default_factory=list, description="Languages supported by this ruleset"
    )
    performance_target_docs_per_minute: int | None = Field(
        default=None, description="Target processing speed for this ruleset"
    )
    memory_limit_mb: int | None = Field(
        default=None, description="Memory limit for processing with this ruleset"
    )
    created_date: str | None = Field(
        default=None, description="Creation date (ISO format)"
    )
    last_updated: str | None = Field(
        default=None, description="Last update date (ISO format)"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorizing this ruleset"
    )
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, extra="forbid"
    )

    def add_pattern(self, pattern: ModelDetectionPattern) -> "ModelDetectionRuleSet":
        """Add a pattern to the ruleset."""
        new_patterns = [*self.patterns, pattern]
        return self.model_copy(update={"patterns": new_patterns})

    def remove_pattern(self, pattern_id: UUID) -> "ModelDetectionRuleSet":
        """Remove a pattern from the ruleset."""
        new_patterns = [p for p in self.patterns if p.pattern_id != pattern_id]
        return self.model_copy(update={"patterns": new_patterns})

    def supports_language(self, language: EnumLanguageCode) -> bool:
        """Check if ruleset supports a specific language."""
        return language in self.supported_languages

    def get_patterns_by_type(
        self, detection_type: EnumDetectionType
    ) -> list[ModelDetectionPattern]:
        """Get patterns for a specific detection type."""
        return [p for p in self.patterns if p.detection_type == detection_type]

    def get_enabled_patterns(self) -> list[ModelDetectionPattern]:
        """Get all enabled patterns."""
        return [p for p in self.patterns if p.is_enabled()]

    def get_summary(self) -> ModelDetectionRuleSetSummary:
        """Get ruleset summary."""
        return ModelDetectionRuleSetSummary(
            ruleset_id=self.ruleset_id,
            ruleset_name=self.ruleset_name,
            version=self.version,
            pattern_count=len(self.patterns),
            enabled_pattern_count=len(self.get_enabled_patterns()),
            detection_types=[t.value for t in self.detection_types],
            supported_languages=[lang.value for lang in self.supported_languages],
            tags=self.tags,
        )
