import re

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_log_filter_config import (
    ModelLogFilterConfig,
)


class ModelLogFilter(BaseModel):
    """Log message filtering configuration."""

    filter_name: str = Field(default=..., description="Unique filter identifier")
    filter_type: str = Field(
        default=...,
        description="Filter type",
        pattern="^(regex|field_match|level_range|keyword|custom)$",
    )
    enabled: bool = Field(default=True, description="Whether this filter is enabled")
    action: str = Field(
        default="include",
        description="Filter action",
        pattern="^(include|exclude)$",
    )
    regex_pattern: str | None = Field(
        default=None,
        description="Regex pattern for regex filters",
    )
    field_name: str | None = Field(
        default=None,
        description="Field name for field-based filters",
    )
    field_value: str | int | float | bool | None = Field(
        default=None, description="Field value to match"
    )
    min_level: int | None = Field(
        default=None,
        description="Minimum log level (numeric value)",
        ge=0,
        le=100,
    )
    max_level: int | None = Field(
        default=None,
        description="Maximum log level (numeric value)",
        ge=0,
        le=100,
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to match for keyword filters",
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether matching is case-sensitive",
    )
    configuration: ModelLogFilterConfig = Field(
        default_factory=lambda: ModelLogFilterConfig(),
        description="Additional filter-specific configuration",
    )

    def matches_message(
        self,
        level_value: int,
        message: str,
        fields: dict[str, object],
    ) -> bool:
        """Check if this filter matches a log message."""
        if not self.enabled:
            return True  # Disabled filters don't filter anything

        if self.filter_type == "regex":
            return self._matches_regex(message)
        if self.filter_type == "field_match":
            return self._matches_field(fields)
        if self.filter_type == "level_range":
            return self._matches_level_range(level_value)
        if self.filter_type == "keyword":
            return self._matches_keywords(message)
        if self.filter_type == "custom":
            return self._matches_custom(message, fields)

        return True  # Unknown filter type, don't filter

    def _matches_regex(self, message: str) -> bool:
        """Check if message matches regex pattern."""
        if not self.regex_pattern:
            return False

        try:
            compiled_pattern = self.configuration.compile_regex(self.regex_pattern)
            return bool(compiled_pattern.search(message))
        except (ValueError, re.error):
            return False

    def _matches_field(self, fields: dict[str, object]) -> bool:
        """Check if field matches the specified value."""
        if not self.field_name or self.field_name not in fields:
            return False

        field_value = fields[self.field_name]
        if self.field_value is None:
            return field_value is not None

        return str(field_value) == str(self.field_value)

    def _matches_level_range(self, level_value: int) -> bool:
        """Check if level is within the specified range."""
        if self.min_level is not None and level_value < self.min_level:
            return False
        if self.max_level is not None and level_value > self.max_level:
            return False
        return True

    def _matches_keywords(self, message: str) -> bool:
        """Check if message contains any of the specified keywords."""
        if not self.keywords:
            return False

        search_message = message if self.case_sensitive else message.lower()
        keywords = (
            self.keywords if self.case_sensitive else [k.lower() for k in self.keywords]
        )

        return any(keyword in search_message for keyword in keywords)

    def _matches_custom(self, message: str, fields: dict[str, object]) -> bool:
        """Check using custom filter logic."""
        if not self.configuration.custom_filter_function:
            return False

        # For now, return False - custom filtering would need
        # dynamic function loading and execution
        return False

    def apply_filter(self, log_entry: dict[str, object]) -> dict[str, object] | None:
        """Apply this filter to a log entry."""
        level_value_raw = log_entry.get("level", 0)
        level_value = (
            int(level_value_raw) if isinstance(level_value_raw, (int, float)) else 0
        )
        message_raw = log_entry.get("message", "")
        message = str(message_raw) if message_raw is not None else ""
        fields: dict[str, object] = {
            k: v for k, v in log_entry.items() if k not in ("level", "message")
        }

        if not self.matches_message(level_value, message, fields):
            return None  # Filtered out

        # Apply field filtering if configured
        filtered_fields = self.configuration.filter_excluded_fields(fields)

        # Check required fields
        if not self.configuration.has_required_fields(filtered_fields):
            return None

        # Check sampling
        if not self.configuration.should_sample():
            return None

        # Check message length
        if not self.configuration.validate_message_length(message):
            return None

        # Return filtered entry
        result: dict[str, object] = {
            "level": level_value,
            "message": message,
            **filtered_fields,
        }

        return result
