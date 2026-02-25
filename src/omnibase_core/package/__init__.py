# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ONCP contract package module.

Provides the ``.oncp`` content-addressed zip bundle format for packaging
contract overlays, scenarios, and invariants into a distributable unit.

This module exposes three primary surfaces:

- :class:`ModelOncpManifest` — Pydantic model for ``manifest.yaml``
- :class:`OncpBuilder` — assembles a ``.oncp`` zip from overlays and artefacts
- :class:`OncpReader` — reads and validates a ``.oncp`` zip bundle

MVP scope: local file export only. No distribution registry.

See Also:
    - OMN-2758: Phase 5 — .oncp contract package MVP
    - OMN-2754: ``compute_canonical_hash`` utility
    - OMN-2757: Overlay stacking pipeline

.. versionadded:: 0.19.0
"""

from omnibase_core.package.model_oncp_invariant_entry import ModelOncpInvariantEntry
from omnibase_core.package.model_oncp_manifest import ModelOncpManifest
from omnibase_core.package.model_oncp_overlay_entry import ModelOncpOverlayEntry
from omnibase_core.package.model_oncp_scenario_entry import ModelOncpScenarioEntry
from omnibase_core.package.service_oncp_builder import OncpBuilder
from omnibase_core.package.service_oncp_reader import OncpReader

__all__ = [
    "ModelOncpInvariantEntry",
    "ModelOncpManifest",
    "ModelOncpOverlayEntry",
    "ModelOncpScenarioEntry",
    "OncpBuilder",
    "OncpReader",
]
