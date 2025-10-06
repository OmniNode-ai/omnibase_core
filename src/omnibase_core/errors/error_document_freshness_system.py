"""
Document Freshness System Error

Error class for system-level operations in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class DocumentFreshnessSystemError(DocumentFreshnessError):
    """Error related to system-level operations."""
