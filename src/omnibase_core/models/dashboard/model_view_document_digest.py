# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Sealing and verifying view documents (OMN-21997).

The document digest sits beside ``compute_widget_envelope_digest``: where the
envelope seal covers a widget's contract half (config, bindings, actions), the
document digest covers the whole document, rows included. Both are ``sha256``
over the canonical JSON (``compute_canonical_hash``) of the wire form with the
digest field excluded, so a changed row fails the document digest and a changed
config fails the envelope seal.

``verify_view_document`` checks the envelope seals first, so a document
re-sealed over an edited config still fails, on the envelope.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_view_document import (
    ModelViewDocument,
    ModelViewSection,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
from omnibase_core.utils.util_widget_envelope import verify_widget_envelope

__all__ = [
    "compute_view_document_digest",
    "seal_view_document",
    "verify_view_document",
]

#: The seal cannot cover itself.
_UNSEALED_FIELDS: set[str] = {"document_digest"}

#: Placeholder used only to build the pre-seal draft; excluded from the digest.
_PLACEHOLDER_DIGEST = f"sha256:{'0' * 64}"


def _digest_payload(payload: Mapping[str, object]) -> str:
    """Return the ``sha256:<hex>`` digest of an unsealed document payload."""
    return f"sha256:{compute_canonical_hash(payload)}"


def compute_view_document_digest(document: ModelViewDocument) -> str:
    """Return the seal a document's content implies.

    Args:
        document: The document to digest. Its own ``document_digest`` is
            excluded from the computation.

    Returns:
        The digest as ``sha256:<64 lowercase hex chars>``.
    """
    return _digest_payload(document.model_dump(mode="json", exclude=_UNSEALED_FIELDS))


def seal_view_document(
    *,
    view_id: str,
    contract_version: ModelSemVer,
    generated_at: datetime,
    sections: Sequence[ModelViewSection],
) -> ModelViewDocument:
    """Build a sealed document from its parts.

    Every cross-field rule (section kind, body, row identity) is enforced on the
    draft before the seal is computed, so a sealed document is never a sealed
    contradiction.

    Args:
        view_id: Slug of the view.
        contract_version: Version of the view contract the rows were built for.
        generated_at: When the rows were read.
        sections: The sections, in display order.

    Returns:
        The sealed document.

    Raises:
        pydantic.ValidationError: If the parts do not form a valid document.
    """
    draft = ModelViewDocument(
        view_id=view_id,
        contract_version=contract_version,
        generated_at=generated_at,
        sections=tuple(sections),
        document_digest=_PLACEHOLDER_DIGEST,
    )
    payload = draft.model_dump(mode="json", exclude=_UNSEALED_FIELDS)
    return ModelViewDocument.model_validate(
        {**payload, "document_digest": _digest_payload(payload)}
    )


def verify_view_document(document: ModelViewDocument) -> None:
    """Check that a document's envelopes and rows still match their seals.

    Args:
        document: The document to verify.

    Raises:
        ModelOnexError: If a section's envelope fails its seal (its config was
            edited), or if the recomputed document digest differs from the
            declared one (a row, or anything else, was edited after sealing).
    """
    for section in document.sections:
        try:
            verify_widget_envelope(section.envelope)
        except ModelOnexError as exc:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"section '{section.section_id}' envelope: {exc.message}",
            ) from exc
    recomputed = compute_view_document_digest(document)
    if recomputed != document.document_digest:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=(
                f"view '{document.view_id}' fails its document digest: declared "
                f"document_digest {document.document_digest} but its content "
                f"digests to {recomputed}; the document was edited after sealing"
            ),
        )
