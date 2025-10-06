"""
Document Freshness Database Error

Error class for database operations in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class ModelDocumentFreshnessDatabaseError(DocumentFreshnessError):
    """Error related to database operations."""
