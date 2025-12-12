import random
import re

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelLogFilterConfig(BaseModel):
    """Configuration for custom log filters."""

    # Rate limiting
    max_matches_per_minute: int | None = Field(
        default=None,
        description="Maximum matches allowed per minute",
        ge=1,
    )

    # Advanced regex options
    case_sensitive: bool = Field(default=False, description="Case sensitive matching")
    multiline_mode: bool = Field(default=False, description="Multiline regex mode")
    dot_matches_all: bool = Field(
        default=False, description="Dot matches all characters"
    )

    # Time-based filtering
    time_window_minutes: int | None = Field(
        default=None,
        description="Time window in minutes for filtering",
        ge=1,
    )

    # Content-based filtering
    required_fields: list[str] = Field(
        default_factory=list,
        description="Required fields in log message",
    )
    excluded_fields: list[str] = Field(
        default_factory=list,
        description="Fields to exclude from log message",
    )

    # Performance tuning
    max_message_length: int | None = Field(
        default=None,
        description="Maximum message length to process",
        ge=1,
    )
    use_compiled_regex: bool = Field(
        default=True, description="Use compiled regex patterns"
    )

    # Custom filter logic
    custom_filter_function: str | None = Field(
        default=None,
        description="Fully qualified function name for custom filter",
    )
    custom_filter_config: SerializedDict | None = Field(
        default=None,
        description="Configuration for custom filter function",
    )

    # Sampling
    sample_rate: float = Field(
        default=1.0,
        description="Sample rate (0.0-1.0) for probabilistic filtering",
        ge=0.0,
        le=1.0,
    )

    def compile_regex(self, pattern: str) -> re.Pattern[str]:
        """Compile regex pattern with configuration options."""
        flags = 0
        if not self.case_sensitive:
            flags |= re.IGNORECASE
        if self.multiline_mode:
            flags |= re.MULTILINE
        if self.dot_matches_all:
            flags |= re.DOTALL

        try:
            return re.compile(pattern, flags)
        except re.error as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid regex pattern '{pattern}': {e}",
            )

    def should_sample(self) -> bool:
        """Determine if this message should be sampled."""
        return random.random() < self.sample_rate

    def validate_message_length(self, message: str) -> bool:
        """Validate message length against configured limit."""
        if self.max_message_length is None:
            return True
        return len(message) <= self.max_message_length

    def has_required_fields(self, log_data: dict[str, object]) -> bool:
        """Check if log data contains all required fields."""
        return all(field in log_data for field in self.required_fields)

    def filter_excluded_fields(self, log_data: dict[str, object]) -> dict[str, object]:
        """Remove excluded fields from log data."""
        return {k: v for k, v in log_data.items() if k not in self.excluded_fields}
