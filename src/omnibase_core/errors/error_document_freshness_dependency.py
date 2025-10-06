"""
Document Freshness Dependency Error

Error class for dependency analysis in document freshness monitoring.
"""

from omnibase_core.errors.error_document_freshness import DocumentFreshnessError


class DocumentFreshnessDependencyError(DocumentFreshnessError):
    """Error related to dependency analysis."""
