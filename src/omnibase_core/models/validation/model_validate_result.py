"""
Validation result model.
"""

import datetime
import hashlib
import uuid

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

from .model_validate_message import ModelValidateMessage


class ModelValidateResult(BaseModel):
    """Model for validation results."""

    messages: list[ModelValidateMessage]
    status: EnumOnexStatus = Field(
        default=EnumOnexStatus.ERROR,
        description="success|warning|error|skipped|fixed|partial|info|unknown",
    )
    summary: str | None = None
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hash: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat(),
    )

    def compute_hash(self) -> str:
        h = hashlib.sha256()
        for msg in self.messages:
            h.update(
                msg.hash.encode("utf-8") if msg.hash else msg.message.encode("utf-8"),
            )
        h.update(self.status.value.encode("utf-8"))
        if self.summary:
            h.update(self.summary.encode("utf-8"))
        return h.hexdigest()

    def with_hash(self) -> "ModelValidateResult":
        self.hash = self.compute_hash()
        return self

    def to_json(self) -> str:
        """Return the result as a JSON string."""
        return self.model_dump_json()

    def to_text(self) -> str:
        """Return the result as a plain text string."""
        lines = [
            f"Status: {self.status.value}",
            f"Summary: {self.summary or ''}",
            f"UID: {self.uid}",
            f"Hash: {self.hash or self.compute_hash()}",
            f"Timestamp: {self.timestamp}",
        ]
        for msg in self.messages:
            lines.append(msg.to_text())
        return "\n".join(lines)

    def to_ci(self) -> str:
        """Return a CI-friendly string for the result."""
        return "\n".join(msg.to_ci() for msg in self.messages)
