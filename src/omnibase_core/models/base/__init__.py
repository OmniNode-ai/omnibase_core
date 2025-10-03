"""
Base Model Classes.

Abstract base classes for typed collections, factories, and processors
following ONEX one-model-per-file architecture.
"""

from .model_collection import ModelBaseCollection
from .model_factory import ModelBaseFactory
from .model_processor import ModelServiceBaseProcessor

__all__ = [
    "ModelBaseCollection",
    "ModelBaseFactory",
    "ModelServiceBaseProcessor",
]
