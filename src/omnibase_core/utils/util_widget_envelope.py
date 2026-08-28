# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Sealing and verifying widget envelopes (OMN-16883, Phase C2).

The seal is what makes a discovered widget judgeable without trusting whoever
published it: a consumer recomputes the digest over the bytes it received and
compares. A mismatch is an error — never a silent re-seal, because re-sealing
tampered bytes is exactly how a supply chain launders an edit.

Digest — ``sha256`` over the RFC-8785-compatible canonical JSON of the envelope
with ``content_digest`` excluded (``compute_canonical_hash``), never over raw
transport bytes. Two consumers that received the same envelope through different
JSON writers must agree, and formatting churn must not read as an edit.
"""

from __future__ import annotations

from collections.abc import Mapping

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_widget_definition import ModelWidgetConfig
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

__all__ = [
    "WIDGET_ENVELOPE_FORMAT_VERSION",
    "compute_widget_envelope_digest",
    "seal_widget_envelope",
    "verify_widget_envelope",
]

#: Version of the envelope FORMAT — bumped when envelope fields change, never
#: when a widget's own content does.
WIDGET_ENVELOPE_FORMAT_VERSION: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0)

#: The seal cannot cover itself.
_UNSEALED_FIELDS: set[str] = {"content_digest"}

#: Placeholder used only to build the pre-seal draft; excluded from the digest.
_PLACEHOLDER_DIGEST = f"sha256:{'0' * 64}"


def _digest_payload(payload: Mapping[str, object]) -> str:
    """Return the ``sha256:<hex>`` digest of an unsealed envelope payload."""
    return f"sha256:{compute_canonical_hash(payload)}"


def compute_widget_envelope_digest(envelope: ModelWidgetEnvelope) -> str:
    """Return the seal an envelope's content implies.

    Args:
        envelope: The envelope to digest. Its own ``content_digest`` is excluded
            from the computation.

    Returns:
        The digest as ``sha256:<64 lowercase hex chars>``.
    """
    return _digest_payload(envelope.model_dump(mode="json", exclude=_UNSEALED_FIELDS))


def seal_widget_envelope(
    *,
    widget_id: str,
    widget_version: ModelSemVer,
    component: ModelComponentContract,
    config: ModelWidgetConfig,
    provenance: ModelWidgetProvenance,
    envelope_version: ModelSemVer = WIDGET_ENVELOPE_FORMAT_VERSION,
) -> ModelWidgetEnvelope:
    """Build a sealed envelope from a widget's parts.

    Every cross-field rule (kind/config agreement, provenance shape) is enforced
    on the draft before the seal is computed, so a sealed envelope is never a
    sealed contradiction.

    Args:
        widget_id: Stable, namespaced widget identifier.
        widget_version: Version of this widget as published.
        component: The component contract half — bindings, actions, permission.
        config: Discriminated widget configuration.
        provenance: Publishing pack and source revision.
        envelope_version: Envelope format version; defaults to the current one.

    Returns:
        The sealed envelope.

    Raises:
        pydantic.ValidationError: If the parts do not form a valid widget.
    """
    draft = ModelWidgetEnvelope(
        envelope_version=envelope_version,
        widget_id=widget_id,
        widget_version=widget_version,
        component=component,
        config=config,
        provenance=provenance,
        content_digest=_PLACEHOLDER_DIGEST,
    )
    payload = draft.model_dump(mode="json", exclude=_UNSEALED_FIELDS)
    return ModelWidgetEnvelope.model_validate(
        {**payload, "content_digest": _digest_payload(payload)}
    )


def verify_widget_envelope(envelope: ModelWidgetEnvelope) -> None:
    """Check that an envelope's content still matches its seal.

    Args:
        envelope: The envelope to verify.

    Raises:
        ModelOnexError: If the recomputed digest differs from the declared one —
            the envelope was edited after it was sealed.
    """
    recomputed = compute_widget_envelope_digest(envelope)
    if recomputed != envelope.content_digest:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"widget '{envelope.widget_id}' fails its seal: declared "
                f"content_digest {envelope.content_digest} but its content "
                f"digests to {recomputed}; the envelope was edited after sealing"
            ),
        )
