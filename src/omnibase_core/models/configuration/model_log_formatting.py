from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.types import SerializedDict


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
    message_template: str = Field(default="", description="Custom message template")
    json_indent: int = Field(
        default=0,
        description="JSON indentation for pretty printing",
        ge=0,
        le=8,
    )
    custom_fields: ModelCustomFields = Field(
        default_factory=lambda: ModelCustomFields(
            schema_version=ModelSemVer(major=1, minor=0, patch=0)
        ),
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
        **kwargs: object,
    ) -> str:
        """Format a log message according to configuration."""
        truncated_message = self._apply_truncation(message)

        if self.format_type == "json":
            return self._create_json_output(
                level, logger_name, truncated_message, **kwargs
            )
        if self.format_type == "structured":
            return self._create_structured_output(
                level, logger_name, truncated_message, **kwargs
            )
        return self._create_text_output(level, logger_name, truncated_message, **kwargs)

    def _apply_truncation(self, message: str) -> str:
        """Apply message truncation if configured."""
        if not self.truncate_long_messages or len(message) <= self.max_message_length:
            return message
        return message[: self.max_message_length - 3] + "..."

    def _create_text_output(
        self, level: str, logger_name: str, message: str, **kwargs: object
    ) -> str:
        """Create text format output."""
        import datetime as dt

        field_map = {
            "timestamp": (
                dt.datetime.now().strftime(self.timestamp_format)
                if self.include_timestamp
                else None
            ),
            "level": f"[{level}]" if self.include_level else None,
            "logger": logger_name if self.include_logger_name else None,
            "message": message,
        }

        parts: list[str] = [
            str(field_map[field])
            for field in self.field_order
            if field_map.get(field) is not None
        ]
        return self.field_separator.join(parts)

    def _create_json_output(
        self, level: str, logger_name: str, message: str, **kwargs: object
    ) -> str:
        """Create JSON format output."""
        import json

        base_data = {"message": message}

        if self.include_timestamp:
            base_data["timestamp"] = datetime.now().isoformat()
        if self.include_level:
            base_data["level"] = level
        if self.include_logger_name:
            base_data["logger"] = logger_name

        # Merge all data sources
        final_data = {**base_data, **kwargs}
        if self.custom_fields and self.custom_fields.field_values:
            final_data.update(self.custom_fields.model_dump())

        return json.dumps(final_data, indent=self.effective_json_indent)

    def _create_structured_output(
        self, level: str, logger_name: str, message: str, **kwargs: object
    ) -> str:
        """Create structured key-value format output."""

        base_parts = []
        if self.include_timestamp:
            base_parts.append(
                f"timestamp={datetime.now().strftime(self.timestamp_format)}"
            )
        if self.include_level:
            base_parts.append(f"level={level}")
        if self.include_logger_name:
            base_parts.append(f"logger={logger_name}")

        base_parts.append(f'message="{message}"')
        base_parts.extend(f"{key}={value}" for key, value in kwargs.items())

        return " ".join(base_parts)

    @property
    def format_analysis(self) -> SerializedDict:
        """Comprehensive format analysis and configuration."""
        return {
            "format_type": self.format_type,
            "format_checks": {
                "is_text": self.format_type == "text",
                "is_json": self.format_type == "json",
                "is_structured": self.format_type == "structured",
            },
            "timestamp_config": {
                "format": self.timestamp_format,
                "enabled": self.include_timestamp,
            },
            "field_inclusion": {
                "level": self.include_level,
                "logger_name": self.include_logger_name,
                "thread_id": self.include_thread_id,
                "process_id": self.include_process_id,
            },
            "formatting_options": {
                # Convert list[str] to list for JsonType compatibility
                "field_order": list(self.field_order),
                "field_separator": self.field_separator,
                "message_template": self.message_template,
                "json_indent": max(0, self.json_indent),
                "effective_indent": max(0, self.json_indent),
            },
            "message_handling": {
                "truncation_enabled": self.truncate_long_messages,
                "max_length": self.max_message_length,
                "has_custom_fields": bool(
                    self.custom_fields and self.custom_fields.field_values
                ),
            },
        }

    @property
    def effective_json_indent(self) -> int:
        """Get effective JSON indentation value."""
        return max(0, self.json_indent)
