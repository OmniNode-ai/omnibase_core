"""
Document Freshness Change Detection Error

Error class for change detection in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class DocumentFreshnessChangeDetectionError(DocumentFreshnessError):
    """Error related to change detection."""
