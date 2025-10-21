"""Centralized ModelProcessingResult implementation."""

from pydantic import BaseModel, ConfigDict


class ModelProcessingResult(BaseModel):
    """Generic processingresult model for common use."""

    model_config = ConfigDict(extra="allow")
