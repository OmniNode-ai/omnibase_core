#!/usr/bin/env python3
"""
ONEX Service Availability Map Model

Model for mapping service names to their availability status in workflow testing.
"""

from typing import Dict

from pydantic import BaseModel


class ModelServiceAvailabilityMap(BaseModel):
    """Model for service availability mapping"""

    services: Dict[str, bool]
