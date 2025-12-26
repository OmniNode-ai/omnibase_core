# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Context models for typed metadata in ONEX operations.

This module provides typed Pydantic models that replace untyped dict[str, str]
metadata fields throughout the ONEX codebase. Each model is frozen (immutable)
and thread-safe for concurrent read access.

Models:
    - ModelSessionContext: Session identification and client context
    - ModelHttpRequestMetadata: HTTP-specific request metadata
    - ModelAuthorizationContext: RBAC/ABAC authorization information
    - ModelAuditMetadata: Compliance and audit trail metadata
    - ModelCheckpointMetadata: Checkpoint state persistence metadata
    - ModelDetectionMetadata: Security pattern detection metadata
    - ModelNodeInitMetadata: Node initialization tracking metadata

Thread Safety:
    All models in this module are frozen (immutable) after creation.
    Safe for concurrent read access across threads.

Usage Notes:
    Checkpoint Metadata Models:
        There are two checkpoint metadata models with distinct purposes:

        - ModelCheckpointMetadata (this module):
            For workflow state tracking. Use when you need to capture checkpoint
            state within a workflow context, including trigger events, workflow
            stage, and checkpoint version. This model is part of the typed context
            system and focuses on operational metadata.

        - ModelStorageCheckpointMetadata (omnibase_core.models.core):
            For storage backend persistence. Use when implementing checkpoint
            storage backends that need retention policies, storage labels, and
            blob store integration. This model focuses on persistence concerns
            like TTL, storage tier, and backend-specific metadata.

Example:
    >>> from omnibase_core.models.context import (
    ...     ModelSessionContext,
    ...     ModelAuthorizationContext,
    ... )
    >>>
    >>> session = ModelSessionContext(
    ...     session_id="sess_123",
    ...     locale="en-US",
    ... )
    >>> auth = ModelAuthorizationContext(
    ...     roles=["admin"],
    ...     permissions=["read:all", "write:all"],
    ... )
"""

from omnibase_core.models.context.model_audit_metadata import ModelAuditMetadata
from omnibase_core.models.context.model_authorization_context import (
    ModelAuthorizationContext,
)
from omnibase_core.models.context.model_checkpoint_metadata import (
    ModelCheckpointMetadata,
)
from omnibase_core.models.context.model_detection_metadata import ModelDetectionMetadata
from omnibase_core.models.context.model_http_request_metadata import (
    ModelHttpRequestMetadata,
)
from omnibase_core.models.context.model_node_init_metadata import ModelNodeInitMetadata
from omnibase_core.models.context.model_session_context import ModelSessionContext

__all__ = [
    "ModelAuditMetadata",
    "ModelAuthorizationContext",
    "ModelCheckpointMetadata",
    "ModelDetectionMetadata",
    "ModelHttpRequestMetadata",
    "ModelNodeInitMetadata",
    "ModelSessionContext",
]
