#!/usr/bin/env python3
"""
ONEX Dependency Accommodation Map Model

Model for mapping dependency names to their accommodation options in workflow testing.
"""

from pydantic import BaseModel

from omnibase_core.model.workflow_testing.model_workflow_testing_configuration import (
    ModelAccommodationOptions,
)


class ModelDependencyAccommodationMap(BaseModel):
    """Model for dependency accommodation mapping"""

    accommodations: dict[str, ModelAccommodationOptions]
