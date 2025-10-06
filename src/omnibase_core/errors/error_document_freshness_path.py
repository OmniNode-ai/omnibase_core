"""
Document Freshness Path Error

Error class for file path operations in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class DocumentFreshnessPathError(DocumentFreshnessError):
    """Error related to file path operations."""
