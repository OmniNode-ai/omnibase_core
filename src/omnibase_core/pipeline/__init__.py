# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
ONEX Pipeline Module.

This module provides pipeline execution infrastructure and observability:

- **ManifestGenerator**: Accumulates observations during pipeline execution
  and builds immutable execution manifests.
- **ManifestObserver**: Attaches to pipeline context for non-invasive
  instrumentation.
- **ManifestLogger**: Outputs manifests in various formats (JSON, YAML,
  Markdown, text).

Example:
    >>> from omnibase_core.pipeline import ManifestGenerator, ManifestObserver
    >>> from omnibase_core.models.manifest import ModelNodeIdentity, ModelContractIdentity
    >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> # Create generator
    >>> generator = ManifestGenerator(
    ...     node_identity=ModelNodeIdentity(
    ...         node_id="compute-001",
    ...         node_kind=EnumNodeKind.COMPUTE,
    ...         node_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     ),
    ...     contract_identity=ModelContractIdentity(contract_id="contract-001"),
    ... )
    >>>
    >>> # Record execution events
    >>> generator.start_hook("hook-1", "handler-1", EnumHandlerExecutionPhase.EXECUTE)
    >>> generator.complete_hook("hook-1", EnumExecutionStatus.SUCCESS)
    >>>
    >>> # Build final manifest
    >>> manifest = generator.build()

See Also:
    - :mod:`omnibase_core.models.manifest`: Manifest model definitions

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from omnibase_core.pipeline.manifest_generator import ManifestGenerator
from omnibase_core.pipeline.manifest_logger import ManifestLogger
from omnibase_core.pipeline.manifest_observer import ManifestObserver

__all__ = [
    "ManifestGenerator",
    "ManifestObserver",
    "ManifestLogger",
]
