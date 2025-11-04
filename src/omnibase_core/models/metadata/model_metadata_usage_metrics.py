"""Metadata usage metrics model for tracking node performance."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.constraints import BasicValueType
from omnibase_core.types.typed_dict_usage_metadata import TypedDictUsageMetadata

from .model_metadatausagemetrics import ModelMetadataUsageMetrics

__all__ = [
    "ModelMetadataUsageMetrics",
]
