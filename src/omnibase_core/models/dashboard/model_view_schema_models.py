# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The widget envelope and the view models published as JSON Schema (OMN-21997).

``scripts/emit_ts_types.py`` merges this mapping into its model table. Keeping
these entries here, not in the script, lets the script shrink: it is on the
canonical-file-shape baseline, which only shrinks. The widget envelope and its
provenance (OMN-16883) moved here from the script because a view document embeds
envelopes, so the two are published together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.models.dashboard.model_view_contract import ModelViewContract
from omnibase_core.models.dashboard.model_view_document import ModelViewDocument
from omnibase_core.models.dashboard.model_view_field_map import ModelViewFieldMap
from omnibase_core.models.dashboard.model_view_manifest import ModelViewManifest
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["VIEW_SCHEMA_MODELS"]

#: Name -> model, in the form ``scripts/emit_ts_types.py`` publishes.
VIEW_SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "ModelViewDocument": ModelViewDocument,
    "ModelViewContract": ModelViewContract,
    "ModelViewManifest": ModelViewManifest,
    "ModelViewFieldMap": ModelViewFieldMap,
    "ModelWidgetEnvelope": ModelWidgetEnvelope,
    "ModelWidgetProvenance": ModelWidgetProvenance,
}
