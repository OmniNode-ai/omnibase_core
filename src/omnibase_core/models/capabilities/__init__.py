# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Capability models for ONEX nodes.

Models for:
1. Vendor-agnostic capability dependencies - declaring what capabilities are needed
   without binding to specific vendors
2. Contract-derived capabilities - capability-based auto-discovery and registration
3. Capability metadata - documentation and discovery metadata for capabilities

Core Principle
--------------
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

ModelContractCapabilities
    Contract-derived capabilities for auto-discovery. Captures what capabilities
    a node provides based on its contract definition.

ModelCapabilityMetadata
    Capability metadata for documentation and discovery. Provides human-readable
    name, description, version, tags, and required features for a capability.

Type System
-----------
Requirement values use ``JsonType`` from ``omnibase_core.types.type_json``.
Requirement dictionaries are typed as ``dict[str, JsonType]``.

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

Contract-derived capabilities for auto-discovery:

    >>> from omnibase_core.models.capabilities import ModelContractCapabilities
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> capabilities = ModelContractCapabilities(
    ...     contract_type="compute",
    ...     contract_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     intent_types=["ProcessData"],
    ...     protocols=["ProtocolCompute"],
    ...     capability_tags=["pure", "cacheable"],
    ... )

Capability metadata for documentation/discovery:

    >>> from omnibase_core.models.capabilities import ModelCapabilityMetadata
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> metadata = ModelCapabilityMetadata(
    ...     capability="database.relational",
    ...     name="Relational Database",
    ...     version=ModelSemVer(major=1, minor=0, patch=0),
    ...     description="SQL-based relational database operations",
    ...     tags=("storage", "sql"),
    ...     required_features=("query", "transactions"),
    ... )

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
    ModelCapabilityDependency, ModelRequirementSet, ModelContractCapabilities

OMN-1124: Capabilities models package.
OMN-1156: ModelCapabilityMetadata for documentation/discovery.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.capabilities.model_capability_dependency import (
        ModelCapabilityDependency,
        SelectionPolicy,
    )
    from omnibase_core.models.capabilities.model_capability_metadata import (
        ModelCapabilityMetadata,
    )
    from omnibase_core.models.capabilities.model_capability_requirement_set import (
        ModelRequirementSet,
        is_json_primitive,
        is_requirement_dict,
        is_requirement_list,
        is_requirement_value,
    )
    from omnibase_core.models.capabilities.model_contract_capabilities import (
        ModelContractCapabilities,
    )

__all__ = [
    "ModelCapabilityDependency",
    "ModelCapabilityMetadata",
    "ModelContractCapabilities",
    "ModelRequirementSet",
    "SelectionPolicy",
    # TypeGuard functions for runtime type narrowing
    "is_json_primitive",
    "is_requirement_dict",
    "is_requirement_list",
    "is_requirement_value",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCapabilityDependency": (
        "omnibase_core.models.capabilities.model_capability_dependency",
        "ModelCapabilityDependency",
    ),
    "SelectionPolicy": (
        "omnibase_core.models.capabilities.model_capability_dependency",
        "SelectionPolicy",
    ),
    "ModelCapabilityMetadata": (
        "omnibase_core.models.capabilities.model_capability_metadata",
        "ModelCapabilityMetadata",
    ),
    "ModelRequirementSet": (
        "omnibase_core.models.capabilities.model_capability_requirement_set",
        "ModelRequirementSet",
    ),
    "is_json_primitive": (
        "omnibase_core.models.capabilities.model_capability_requirement_set",
        "is_json_primitive",
    ),
    "is_requirement_dict": (
        "omnibase_core.models.capabilities.model_capability_requirement_set",
        "is_requirement_dict",
    ),
    "is_requirement_list": (
        "omnibase_core.models.capabilities.model_capability_requirement_set",
        "is_requirement_list",
    ),
    "is_requirement_value": (
        "omnibase_core.models.capabilities.model_capability_requirement_set",
        "is_requirement_value",
    ),
    "ModelContractCapabilities": (
        "omnibase_core.models.capabilities.model_contract_capabilities",
        "ModelContractCapabilities",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
