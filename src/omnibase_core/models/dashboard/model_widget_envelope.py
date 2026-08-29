# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""WidgetEnvelope — one object that is a whole widget (OMN-16883, Phase C2).

Two shipped contracts each held half a widget and neither held the other half
(plan §1.4.2):

* ``ModelComponentContract`` — identity, kind, contract version, bindings,
  actions, permission, evidence, empty-state reasons. **No config.**
* ``ModelWidgetDefinition`` — config and grid placement. **No bindings, no
  actions, no component-contract version, no provenance, no hash.**

So "a pack ships a widget contract" named no object, and half a widget had to
travel out-of-band. ``ModelWidgetEnvelope`` is the missing whole: the unit
Plane 1 distributes.

**What it deliberately does not carry: grid placement.** Row/column/span are a
*dashboard's* facts about where it put a widget, not the widget's own facts, and
D9 assigns layout to the frame. ``ModelWidgetDefinition`` therefore keeps its
placement role and is neither subsumed nor shimmed here; what moves into the
envelope is the *contract* half — config, bindings, actions, versions, origin.

**The seal.** ``content_digest`` covers every other field, so a consumer can
decide whether a discovered widget is the bytes its publisher sealed without
trusting the publisher to say so. It is computed over the envelope's canonical
JSON with ``content_digest`` excluded — a hash cannot cover itself. Use
``omnibase_core.utils.util_widget_envelope.seal_widget_envelope`` to build one
and ``verify_widget_envelope`` to check one; a mismatch is an error, never a
recomputation.
"""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_widget_definition import ModelWidgetConfig
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelWidgetEnvelope", "WIDGET_ENVELOPE_DIGEST_PATTERN"]

#: Seals are ``sha256:<64 lowercase hex chars>``.
WIDGET_ENVELOPE_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ModelWidgetEnvelope(BaseModel):
    """A complete, versioned, sealed widget contract.

    Three versions live here and they answer different questions:
    ``envelope_version`` is the version of *this format*, ``widget_version`` is
    the version of *this widget as published*, and
    ``component.contract_version`` is the version of the *component contract*
    the widget binds. A consumer that must reject an envelope it cannot parse
    reads the first; a consumer choosing between two published widgets reads the
    second; a renderer deciding whether it can render at all reads the third.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    envelope_version: ModelSemVer = Field(
        ...,
        description="Version of the envelope format itself, not of any widget",
    )
    widget_id: str = Field(  # string-id-ok: namespaced widget label, not a UUID
        ...,
        description="Stable, namespaced widget identifier (e.g. 'onex.widget.system_health')",
        min_length=1,
    )
    widget_version: ModelSemVer = Field(
        ...,
        description="Version of this widget as published by its pack",
    )
    component: ModelComponentContract = Field(
        ...,
        description=(
            "Component contract half: identity, kind, bindings, actions, "
            "permission, evidence requirements, empty-state reasons"
        ),
    )
    config: ModelWidgetConfig = Field(
        ...,
        description="Discriminated widget configuration, keyed by config_kind",
    )
    provenance: ModelWidgetProvenance = Field(
        ...,
        description="Which pack published this widget, at which source revision",
    )
    content_digest: str = Field(
        ...,
        description=(
            "SHA-256 over this envelope's canonical JSON excluding this field, "
            "as 'sha256:<hex>'. Lets a consumer validate a discovered widget "
            "without trusting the publisher."
        ),
    )

    @field_validator("content_digest")
    @classmethod
    def validate_content_digest(cls, value: str) -> str:
        """Reject anything that is not a ``sha256:<hex>`` seal.

        Raises:
            ValueError: If ``value`` does not match the digest pattern.
        """
        if not WIDGET_ENVELOPE_DIGEST_PATTERN.match(value):
            raise ValueError(
                f"content_digest must match 'sha256:<64 hex chars>', got '{value}'"
            )
        return value

    @model_validator(mode="after")
    def validate_component_kind_matches_config(self) -> Self:
        """Fail closed when the declared kind and the config disagree.

        The component kind is what a renderer gates on; the config discriminator
        is what a parser keys on. An envelope where they disagree renders one
        thing and validates as another, which is precisely the out-of-band
        half-widget this model exists to end.

        Raises:
            ValueError: If ``component.component_kind`` does not equal the
                config's ``config_kind``.
        """
        if self.component.component_kind.value != self.config.config_kind:
            raise ValueError(
                f"component_kind '{self.component.component_kind.value}' does not "
                f"match config_kind '{self.config.config_kind}'"
            )
        return self
