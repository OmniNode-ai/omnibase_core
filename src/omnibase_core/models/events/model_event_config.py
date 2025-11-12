"""
Base model configuration module for events.

This module provides a simple re-export of Pydantic's BaseModel
for consistent imports across the events package.
"""

from pydantic import BaseModel

__all__ = ["BaseModel"]
