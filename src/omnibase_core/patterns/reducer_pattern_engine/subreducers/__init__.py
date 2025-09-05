"""Subreducers for Reducer Pattern Engine.

Phase 1: Single subreducer implementation
- ReducerDocumentRegenerationSubreducer: Reference implementation for document workflows
"""

from .reducer_document_regeneration import ReducerDocumentRegenerationSubreducer

__all__ = [
    "ReducerDocumentRegenerationSubreducer",
]
