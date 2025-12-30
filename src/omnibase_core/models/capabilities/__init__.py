# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Capability models for vendor-agnostic dependency declaration.

This module provides models for declaring dependencies on capabilities
rather than specific vendors. The core principle is:

    "Contracts declare capabilities + constraints. Registry resolves to providers."

Key Models
----------
ModelCapabilityDependency
    Declares a dependency on a capability with requirements. Used in handler
    contracts to specify what capabilities are needed without binding to
    specific vendors. The registry resolves these to concrete providers
    at runtime.

ModelRequirementSet
    Structured constraint set with four tiers:
    - must: Hard constraints (filter)
    - prefer: Soft preferences (scoring)
    - forbid: Exclusion constraints (filter)
    - hints: Tie-breaking (advisory)

Capability Naming Convention
----------------------------
Capabilities follow the pattern: ``<domain>.<type>[.<variant>]``

Examples:
    - ``database.relational`` - Any relational database
    - ``database.document`` - Document/NoSQL database
    - ``storage.vector`` - Vector storage capability
    - ``cache.distributed`` - Distributed cache
    - ``messaging.eventbus`` - Event bus capability
    - ``secrets.vault`` - Secrets management

Example Usage
-------------
Declaring dependencies in a handler contract:

    >>> from omnibase_core.models.capabilities import (
    ...     ModelCapabilityDependency,
    ...     ModelRequirementSet,
    ... )
    >>>
    >>> dependencies = [
    ...     ModelCapabilityDependency(
    ...         alias="db",
    ...         capability="database.relational",
    ...         requirements=ModelRequirementSet(
    ...             must={"supports_transactions": True},
    ...             prefer={"max_latency_ms": 20},
    ...         ),
    ...         selection_policy="auto_if_unique",
    ...     ),
    ...     ModelCapabilityDependency(
    ...         alias="cache",
    ...         capability="cache.distributed",
    ...         requirements=ModelRequirementSet(
    ...             prefer={"region": "us-east-1"},
    ...         ),
    ...         selection_policy="best_score",
    ...         strict=False,
    ...     ),
    ... ]

Integration with ModelHandlerContract
-------------------------------------
Handler contracts can declare capability dependencies that are resolved
by the registry at runtime:

.. code-block:: yaml

    # handler_contract.yaml
    handler_name: "onex:my-handler"
    handler_version: "1.0.0"
    capability_dependencies:
      - alias: "db"
        capability: "database.relational"
        requirements:
          must:
            engine: "postgres"
          prefer:
            max_latency_ms: 20
        selection_policy: "best_score"
        strict: true
      - alias: "vectors"
        capability: "storage.vector"
        requirements:
          must:
            dimensions: 1536
          hints:
            engine_preference: ["qdrant", "milvus"]

The resolver then:
    1. Filters providers by must/forbid constraints
    2. Scores remaining providers by prefer constraints
    3. Breaks ties using hints
    4. Binds the selected provider to the alias for handler use

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access.

See Also
--------
omnibase_core.models.handlers.ModelHandlerDescriptor : Handler descriptors
omnibase_core.models.contracts : Contract models

.. versionadded:: 0.4.0
"""

from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
    SelectionPolicy,
)
from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet

__all__ = [
    "ModelCapabilityDependency",
    "ModelRequirementSet",
    "SelectionPolicy",
]
