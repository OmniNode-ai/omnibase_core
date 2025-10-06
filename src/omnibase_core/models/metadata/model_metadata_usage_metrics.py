from __future__ import annotations

from datetime import datetime
from typing import Dict, TypedDict

from pydantic import Field

from omnibase_core.models.core.model_sem_ver import ModelSemVer

"""
Metadata usage metrics model for tracking node performance.
"""


from datetime import UTC, datetime
from typing import TypedDict

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_semver import ModelSemVer
from omnibase_core.types.constraints import BasicValueType

from .model_metadatausagemetrics import ModelMetadataUsageMetrics


# TypedDict for protocol method parameters
class TypedDictUsageMetadataDict(TypedDict, total=False):
    """Typed structure for usage metadata dict[str, Any]ionary in protocol methods."""

    name: str
    description: str
    version: ModelSemVer | str
    tags: list[str]
    metadata: dict[str, str]
