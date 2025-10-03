"""Log context model for structured logging."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel

# Type alias for logging infrastructure (BOUNDARY_LAYER_EXCEPTION)
# Uses Any to support flexible identifiers (UUID/str/None) when strict UUID
# context is unavailable during logging infrastructure operations
LogNodeIdentifier = Any


class ModelLogContext(BaseModel):
    """Strongly typed context for ONEX structured log events.

    Note: node_id accepts UUID | str | None as a boundary layer exception.
    String fallbacks (e.g., "unknown", module names) are used when UUID
    context is unavailable during logging infrastructure operations.
    """

    calling_module: str
    calling_function: str
    calling_line: int
    timestamp: str
    node_id: LogNodeIdentifier | None = None
    correlation_id: UUID | None = None


# Compatibility alias
LogModelContext = ModelLogContext

__all__ = ["ModelLogContext", "LogModelContext"]
