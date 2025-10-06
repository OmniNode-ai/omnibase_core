"""
Document Freshness Validation Error

Error class for input/output validation in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class DocumentFreshnessValidationError(DocumentFreshnessError):
    """Error related to input/output validation."""
