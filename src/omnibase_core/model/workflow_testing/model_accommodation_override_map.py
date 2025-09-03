#!/usr/bin/env python3
"""
ONEX Accommodation Override Map Model

Model for mapping dependency names to their accommodation type overrides in workflow testing.
"""

from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_testing import EnumAccommodationType


class ModelAccommodationOverrideMap(BaseModel):
    """Model for accommodation override mapping"""

    overrides: dict[str, EnumAccommodationType]
