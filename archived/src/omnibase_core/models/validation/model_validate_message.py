"""
Validation message model.
"""

import datetime
import hashlib
import uuid

from pydantic import Field

from omnibase_core.enums import EnumLogLevel
from omnibase_core.models.core.model_base_error import ModelBaseError

from .model_validate_message_context import ModelValidateMessageContext


class ModelValidateMessage(ModelBaseError):
    """Model for validation messages."""

    file: str | None = None
    line: int | None = None
    severity: EnumLogLevel = Field(
        default=EnumLogLevel.ERROR,
        description="error|warning|info|debug|critical|success|unknown",
    )
    code: str = "unknown"
    context: ModelValidateMessageContext | None = None
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hash: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat(),
    )
    # message is inherited from ModelBaseError and must always be str (not Optional)
    # All instantiations must provide a non-None str for message

    def compute_hash(self) -> str:
        # Compute a hash of the message content for integrity
        h = hashlib.sha256()
        h.update(self.message.encode("utf-8"))
        if self.file:
            h.update(self.file.encode("utf-8"))
        if self.code:
            h.update(self.code.encode("utf-8"))
        h.update(self.severity.value.encode("utf-8"))
        if self.context:
            h.update(str(self.context).encode("utf-8"))
        return h.hexdigest()

    def with_hash(self) -> "ModelValidateMessage":
        self.hash = self.compute_hash()
        return self

    def to_json(self) -> str:
        """Return the message as a JSON string."""
        return self.model_dump_json()

    def to_text(self) -> str:
        """Return the message as a plain text string."""
        parts = [f"[{self.severity.value.upper()}] {self.message}"]
        if self.file:
            parts.append(f"File: {self.file}")
        if self.line is not None:
            parts.append(f"Line: {self.line}")
        if self.code:
            parts.append(f"Code: {self.code}")
        if self.context:
            parts.append(f"Context: {self.context}")
        parts.append(f"UID: {self.uid}")
        parts.append(f"Hash: {self.hash or self.compute_hash()}")
        parts.append(f"Timestamp: {self.timestamp}")
        return " | ".join(parts)

    def to_ci(self) -> str:
        """Return a CI-friendly string (e.g., for GitHub Actions annotations)."""
        loc = (
            f"file={self.file},line={self.line}"
            if self.file and self.line is not None
            else ""
        )
        return f"::{self.severity.value} {loc}::{self.message}"
