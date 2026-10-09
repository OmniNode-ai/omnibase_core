# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Diff Models for Semantic Contract Diffing.

Pydantic models for computing and representing
semantic differences between contract versions. The diff system supports:

- Field-level diffing for scalar values
- List-level diffing with identity-based element tracking
- Configurable field exclusions and identity keys
- Bidirectional diff reversal
- Markdown table output for human-readable reports

Key Model Components:
    ModelDiffConfiguration:
        Configuration for diff operations including field exclusions,
        identity keys for list elements, and normalization settings.

    ModelContractFieldDiff:
        Represents a single field-level difference including change type,
        old/new values, and positional information for list moves.

    ModelContractListDiff:
        Aggregates changes to list field elements, organized by change type
        (added, removed, modified, moved).

    ModelContractDiff:
        Complete diff result containing field diffs, list diffs, fingerprints,
        and computed summary statistics.

Example:
    Computing and analyzing a contract diff:

    >>> from omnibase_core.models.contracts.diff import (
    ...     ModelContractDiff,
    ...     ModelDiffConfiguration,
    ... )
    >>> from omnibase_core.contracts.contract_diff_computer import compute_contract_diff
    >>> config = ModelDiffConfiguration(
    ...     exclude_fields=frozenset({"computed_at"}),
    ...     identity_keys={"transitions": "name"},
    ... )
    >>> diff = compute_contract_diff(before_contract, after_contract, config)
    >>> diff.has_changes
    True
    >>> print(diff.change_summary)
    {'added': 2, 'removed': 1, 'modified': 3, 'moved': 0, 'unchanged': 5}
    >>> print(diff.to_markdown_table())
    ## Contract Diff...

See Also:
    - EnumContractDiffChangeType: Enum for change types
    - docs/architecture/CONTRACT_DIFFING.md: Architecture documentation
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.contracts.diff.model_contract_diff import (
        ModelContractDiff,
    )
    from omnibase_core.models.contracts.diff.model_contract_field_diff import (
        ModelContractFieldDiff,
    )
    from omnibase_core.models.contracts.diff.model_contract_list_diff import (
        ModelContractListDiff,
    )
    from omnibase_core.models.contracts.diff.model_diff_configuration import (
        ModelDiffConfiguration,
    )

__all__ = [
    # Configuration
    "ModelDiffConfiguration",
    # Field-level diff
    "ModelContractFieldDiff",
    # List-level diff
    "ModelContractListDiff",
    # Complete diff result
    "ModelContractDiff",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelContractDiff": (
        "omnibase_core.models.contracts.diff.model_contract_diff",
        "ModelContractDiff",
    ),
    "ModelContractFieldDiff": (
        "omnibase_core.models.contracts.diff.model_contract_field_diff",
        "ModelContractFieldDiff",
    ),
    "ModelContractListDiff": (
        "omnibase_core.models.contracts.diff.model_contract_list_diff",
        "ModelContractListDiff",
    ),
    "ModelDiffConfiguration": (
        "omnibase_core.models.contracts.diff.model_diff_configuration",
        "ModelDiffConfiguration",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
