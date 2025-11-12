"""
Base model configuration module for events - re-exports BaseModel.

This module re-exports BaseModel from model_event_config.
The actual implementation is in model_event_config.py to avoid collision
with workflows/model_config.py.
"""

from omnibase_core.models.events.model_event_config import BaseModel

__all__ = ["BaseModel"]
