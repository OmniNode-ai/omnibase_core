"""
ONEX Execution Manifest Models Module.

This module provides models for pipeline execution manifests, which answer
"what ran and why" for every pipeline execution. The manifest captures:

- **Node Identity**: What node was executing
- **Contract Identity**: What contract drove execution
- **Activation Summary**: What capabilities were activated/skipped and why
- **Ordering Summary**: Resolved execution order and dependencies
- **Hook Traces**: Per-hook execution details (timing, status, errors)
- **Emissions Summary**: What outputs were produced (events, intents, projections)
- **Metrics Summary**: Optional performance metrics
- **Failures**: Any failures during execution

Example:
    >>> from omnibase_core.models.manifest import (
    ...     ModelExecutionManifest,
    ...     ModelNodeIdentity,
    ...     ModelContractIdentity,
    ... )
    >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
    >>> from omnibase_core.models.primitives.model_sem_ver import ModelSemVer
    >>>
    >>> manifest = ModelExecutionManifest(
    ...     node_identity=ModelNodeIdentity(
    ...         node_id="compute-text-transform",
    ...         node_kind=EnumNodeKind.COMPUTE,
    ...         node_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     ),
    ...     contract_identity=ModelContractIdentity(
    ...         contract_id="text-transform-contract",
    ...     ),
    ... )
    >>> manifest.is_successful()
    True

See Also:
    - :doc:`/docs/architecture/ONEX_FOUR_NODE_ARCHITECTURE`:
      The four-node architecture that manifests document

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from omnibase_core.models.manifest.model_activation_summary import (
    ModelActivationSummary,
)
from omnibase_core.models.manifest.model_capability_activation import (
    ModelCapabilityActivation,
)
from omnibase_core.models.manifest.model_contract_identity import ModelContractIdentity
from omnibase_core.models.manifest.model_dependency_edge import ModelDependencyEdge
from omnibase_core.models.manifest.model_emissions_summary import ModelEmissionsSummary
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.models.manifest.model_hook_trace import ModelHookTrace
from omnibase_core.models.manifest.model_manifest_failure import ModelManifestFailure
from omnibase_core.models.manifest.model_metrics_summary import ModelMetricsSummary
from omnibase_core.models.manifest.model_node_identity import ModelNodeIdentity
from omnibase_core.models.manifest.model_ordering_summary import ModelOrderingSummary

__all__ = [
    # Core Identity
    "ModelNodeIdentity",
    "ModelContractIdentity",
    # Activation
    "ModelCapabilityActivation",
    "ModelActivationSummary",
    # Ordering
    "ModelDependencyEdge",
    "ModelOrderingSummary",
    # Execution Trace
    "ModelHookTrace",
    # Emissions
    "ModelEmissionsSummary",
    # Metrics and Failures
    "ModelMetricsSummary",
    "ModelManifestFailure",
    # Top-Level Manifest
    "ModelExecutionManifest",
]
