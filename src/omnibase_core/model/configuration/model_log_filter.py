import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelLogFilterConfig(BaseModel):
    """Configuration for custom log filters."""

    # Rate limiting
    max_matches_per_minute: Optional[int] = Field(
        None, description="Maximum matches allowed per minute", ge=1
    )

    # Advanced regex options
    regex_timeout_ms: Optional[int] = Field(
        None, description="Regex match timeout in milliseconds", ge=100, le=10000
    )
    multiline_mode: bool = Field(False, description="Enable multiline regex matching")

    # Field matching options
    field_type_validation: bool = Field(
        True, description="Validate field types before comparison"
    )
    nested_field_separator: str = Field(
        ".", description="Separator for nested field access"
    )

    # Performance options
    cache_compiled_regex: bool = Field(
        True, description="Cache compiled regex patterns"
    )
    max_cache_size: int = Field(
        100, description="Maximum number of cached patterns", ge=1, le=1000
    )

    # Output modification
    redact_matched_content: bool = Field(
        False, description="Redact matched content in output"
    )
    redaction_pattern: str = Field(
        "[REDACTED]", description="Pattern to use for redaction"
    )

    # Custom script support
    custom_script_path: Optional[str] = Field(
        None, description="Path to custom filter script"
    )
    custom_script_timeout_ms: Optional[int] = Field(
        None, description="Custom script timeout in milliseconds", ge=100
    )


class ModelLogFilter(BaseModel):
    """Log message filtering configuration."""

    filter_name: str = Field(..., description="Unique filter identifier")
    filter_type: str = Field(
        ...,
        description="Filter type",
        pattern="^(regex|field_match|level_range|keyword|custom)$",
    )
    enabled: bool = Field(default=True, description="Whether this filter is enabled")
    action: str = Field(
        default="include", description="Filter action", pattern="^(include|exclude)$"
    )
    regex_pattern: Optional[str] = Field(
        None, description="Regex pattern for regex filters"
    )
    field_name: Optional[str] = Field(
        None, description="Field name for field-based filters"
    )
    field_value: Optional[Any] = Field(None, description="Field value to match")
    min_level: Optional[int] = Field(
        None, description="Minimum log level (numeric value)", ge=0, le=100
    )
    max_level: Optional[int] = Field(
        None, description="Maximum log level (numeric value)", ge=0, le=100
    )
    keywords: List[str] = Field(
        default_factory=list, description="Keywords to match for keyword filters"
    )
    case_sensitive: bool = Field(
        default=False, description="Whether matching is case-sensitive"
    )
    configuration: ModelLogFilterConfig = Field(
        default_factory=ModelLogFilterConfig,
        description="Additional filter-specific configuration",
    )

    def matches_message(
        self, level_value: int, message: str, fields: Dict[str, Any]
    ) -> bool:
        """Check if this filter matches a log message."""
        if not self.enabled:
            return True  # Disabled filters don't filter anything

        if self.filter_type == "regex":
            return self._matches_regex(message)
        elif self.filter_type == "field_match":
            return self._matches_field(fields)
        elif self.filter_type == "level_range":
            return self._matches_level_range(level_value)
        elif self.filter_type == "keyword":
            return self._matches_keywords(message)
        else:
            return True  # Unknown filter types pass everything

    def should_include_message(
        self, level_value: int, message: str, fields: Dict[str, Any]
    ) -> bool:
        """Determine if message should be included based on filter result."""
        matches = self.matches_message(level_value, message, fields)

        if self.action == "include":
            return matches
        else:  # exclude
            return not matches

    def _matches_regex(self, message: str) -> bool:
        """Check if message matches regex pattern."""
        if not self.regex_pattern:
            return True

        flags = 0 if self.case_sensitive else re.IGNORECASE
        try:
            return bool(re.search(self.regex_pattern, message, flags))
        except re.error:
            return True  # Invalid regex passes everything

    def _matches_field(self, fields: Dict[str, Any]) -> bool:
        """Check if field matches specified value."""
        if not self.field_name:
            return True

        field_value = fields.get(self.field_name)

        if field_value is None:
            return False

        if isinstance(field_value, str) and isinstance(self.field_value, str):
            if self.case_sensitive:
                return field_value == self.field_value
            else:
                return field_value.lower() == self.field_value.lower()

        return field_value == self.field_value

    def _matches_level_range(self, level_value: int) -> bool:
        """Check if level is within specified range."""
        if self.min_level is not None and level_value < self.min_level:
            return False

        if self.max_level is not None and level_value > self.max_level:
            return False

        return True

    def _matches_keywords(self, message: str) -> bool:
        """Check if message contains any of the specified keywords."""
        if not self.keywords:
            return True

        message_text = message if self.case_sensitive else message.lower()

        for keyword in self.keywords:
            keyword_text = keyword if self.case_sensitive else keyword.lower()
            if keyword_text in message_text:
                return True

        return False

    @classmethod
    def create_regex(
        cls, name: str, pattern: str, action: str = "include"
    ) -> "ModelLogFilter":
        """Factory method for regex filter."""
        return cls(
            filter_name=name, filter_type="regex", action=action, regex_pattern=pattern
        )

    @classmethod
    def create_level_range(
        cls,
        name: str,
        min_level: Optional[int] = None,
        max_level: Optional[int] = None,
        action: str = "include",
    ) -> "ModelLogFilter":
        """Factory method for level range filter."""
        return cls(
            filter_name=name,
            filter_type="level_range",
            action=action,
            min_level=min_level,
            max_level=max_level,
        )

    @classmethod
    def create_keyword(
        cls, name: str, keywords: List[str], action: str = "include"
    ) -> "ModelLogFilter":
        """Factory method for keyword filter."""
        return cls(
            filter_name=name, filter_type="keyword", action=action, keywords=keywords
        )

    @classmethod
    def create_field_match(
        cls, name: str, field_name: str, field_value: Any, action: str = "include"
    ) -> "ModelLogFilter":
        """Factory method for field matching filter."""
        return cls(
            filter_name=name,
            filter_type="field_match",
            action=action,
            field_name=field_name,
            field_value=field_value,
        )
