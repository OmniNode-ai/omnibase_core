from pydantic import BaseModel, Field

from omnibase_core.model.core.model_custom_fields import ModelCustomFields


class ModelLogFormatting(BaseModel):
    """Log message formatting configuration."""

    format_type: str = Field(
        default="text",
        description="Log format type",
        pattern="^(text|json|structured|custom)$",
    )
    timestamp_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Timestamp format string",
    )
    include_timestamp: bool = Field(
        default=True,
        description="Whether to include timestamps",
    )
    include_level: bool = Field(
        default=True,
        description="Whether to include log level",
    )
    include_logger_name: bool = Field(
        default=True,
        description="Whether to include logger name",
    )
    include_thread_id: bool = Field(
        default=False,
        description="Whether to include thread ID",
    )
    include_process_id: bool = Field(
        default=False,
        description="Whether to include process ID",
    )
    field_order: list[str] = Field(
        default_factory=lambda: ["timestamp", "level", "logger", "message"],
        description="Order of fields in log output",
    )
    field_separator: str = Field(
        default=" | ",
        description="Separator between fields in text format",
    )
    message_template: str | None = Field(None, description="Custom message template")
    json_indent: int | None = Field(
        None,
        description="JSON indentation for pretty printing",
        ge=0,
        le=8,
    )
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Additional custom fields to include",
    )
    truncate_long_messages: bool = Field(
        default=False,
        description="Whether to truncate very long messages",
    )
    max_message_length: int = Field(
        default=10000,
        description="Maximum message length before truncation",
        ge=100,
    )

    def format_message(
        self,
        level: str,
        logger_name: str,
        message: str,
        **kwargs,
    ) -> str:
        """Format a log message according to configuration."""
        if self.format_type == "json":
            return self._format_json(level, logger_name, message, **kwargs)
        if self.format_type == "structured":
            return self._format_structured(level, logger_name, message, **kwargs)
        return self._format_text(level, logger_name, message, **kwargs)

    def _format_text(self, level: str, logger_name: str, message: str, **kwargs) -> str:
        """Format as plain text."""
        import datetime

        parts = []

        for field in self.field_order:
            if field == "timestamp" and self.include_timestamp:
                parts.append(datetime.datetime.now().strftime(self.timestamp_format))
            elif field == "level" and self.include_level:
                parts.append(f"[{level}]")
            elif field == "logger" and self.include_logger_name:
                parts.append(logger_name)
            elif field == "message":
                truncated_message = self._truncate_message(message)
                parts.append(truncated_message)

        return self.field_separator.join(parts)

    def _format_json(self, level: str, logger_name: str, message: str, **kwargs) -> str:
        """Format as JSON."""
        import datetime
        import json

        log_data = {}

        if self.include_timestamp:
            log_data["timestamp"] = datetime.datetime.now().isoformat()
        if self.include_level:
            log_data["level"] = level
        if self.include_logger_name:
            log_data["logger"] = logger_name

        log_data["message"] = self._truncate_message(message)
        if self.custom_fields:
            log_data.update(self.custom_fields.to_dict())
        log_data.update(kwargs)

        return json.dumps(log_data, indent=self.json_indent)

    def _format_structured(
        self,
        level: str,
        logger_name: str,
        message: str,
        **kwargs,
    ) -> str:
        """Format as structured key-value pairs."""
        import datetime

        parts = []

        if self.include_timestamp:
            timestamp = datetime.datetime.now().strftime(self.timestamp_format)
            parts.append(f"timestamp={timestamp}")
        if self.include_level:
            parts.append(f"level={level}")
        if self.include_logger_name:
            parts.append(f"logger={logger_name}")

        truncated_message = self._truncate_message(message)
        parts.append(f'message="{truncated_message}"')

        for key, value in kwargs.items():
            parts.append(f"{key}={value}")

        return " ".join(parts)

    def _truncate_message(self, message: str) -> str:
        """Truncate message if needed."""
        if not self.truncate_long_messages:
            return message

        if len(message) <= self.max_message_length:
            return message

        return message[: self.max_message_length - 3] + "..."

    @classmethod
    def create_text(cls) -> "ModelLogFormatting":
        """Factory method for text formatting."""
        return cls(format_type="text")

    @classmethod
    def create_json(cls, indent: int | None = None) -> "ModelLogFormatting":
        """Factory method for JSON formatting."""
        return cls(format_type="json", json_indent=indent)

    @classmethod
    def create_structured(cls) -> "ModelLogFormatting":
        """Factory method for structured formatting."""
        return cls(format_type="structured")
