# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract Graph IR import + round-trip (OMN-13132 — Phase 2, epic OMN-13129).

Read-only import of heterogeneous source contracts (backend node contracts and
UI component contracts) into the canonical Contract Graph IR
(``omnibase_core.models.contract_graph``), plus a no-op round-trip back to
canonical normalized contract form verified through the shipped semantic-diff
spine (``omnibase_core.cli.cli_contract_diff``).

This package holds pure import/round-trip functions and stable hashing only.
STRICTLY READ-ONLY this phase: no authoring UI, no contract mutation.
"""

from omnibase_core.contract_graph.adapter_node_contract import (
    import_node_contract,
    node_contract_adapter_version,
    round_trip_node_node,
    supports_node_contract,
)
from omnibase_core.contract_graph.adapter_ui_component import (
    import_ui_component,
    round_trip_ui_component,
    supports_ui_component,
    ui_component_adapter_version,
)
from omnibase_core.contract_graph.canonical_hash import (
    adapter_version_sha256,
    canonical_contract_sha256,
    canonicalize_contract,
)
from omnibase_core.contract_graph.importer import (
    EXCLUDED_DISCOVERY_DIRS,
    IR_SCHEMA_VERSION,
    discover_contract_paths,
    import_paths,
    normalize_node_contract,
    normalize_ui_component,
    round_trip_node_diff,
    round_trip_ui_component_diff,
    round_trip_zero_diff,
)

__all__ = [
    # canonical hashing
    "canonicalize_contract",
    "canonical_contract_sha256",
    "adapter_version_sha256",
    # node-contract dialect adapter
    "supports_node_contract",
    "import_node_contract",
    "round_trip_node_node",
    "node_contract_adapter_version",
    # ui-component dialect adapter
    "supports_ui_component",
    "import_ui_component",
    "round_trip_ui_component",
    "ui_component_adapter_version",
    # importer + round-trip
    "IR_SCHEMA_VERSION",
    "EXCLUDED_DISCOVERY_DIRS",
    "discover_contract_paths",
    "normalize_node_contract",
    "normalize_ui_component",
    "import_paths",
    "round_trip_node_diff",
    "round_trip_ui_component_diff",
    "round_trip_zero_diff",
]
