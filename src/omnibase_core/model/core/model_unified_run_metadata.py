from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModelUnifiedRunMetadata(BaseModel):
    """
    Run metadata model for unified results
    """

    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    run_id: Optional[str] = None
