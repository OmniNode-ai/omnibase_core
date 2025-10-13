from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class ModelUnifiedRunMetadata(BaseModel):
    """
    Run metadata model for unified results
    """

    start_time: datetime
    end_time: datetime | None = None
    duration: float | None = None
    run_id: UUID | None = None
