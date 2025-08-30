"""
Pipeline Stage Enumeration for the metadata processing pipeline.

Defines the stages in the metadata processing pipeline that integrates
Kafka, Postgres, Qdrant, file stamps, and LangExtract processing.
"""

from enum import Enum


class EnumPipelineStage(str, Enum):
    """Stages in the metadata processing pipeline."""

    FILE_DISCOVERY = "FILE_DISCOVERY"
    STAMP_VALIDATION = "STAMP_VALIDATION"
    CONTENT_EXTRACTION = "CONTENT_EXTRACTION"
    LANGEXTRACT_PROCESSING = "LANGEXTRACT_PROCESSING"
    VECTOR_EMBEDDING = "VECTOR_EMBEDDING"
    DATABASE_STORAGE = "DATABASE_STORAGE"
    EVENT_PUBLISHING = "EVENT_PUBLISHING"
    VALIDATION_COMPLETE = "VALIDATION_COMPLETE"
