# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Theme catalog loading, digesting, and the activate/rollback pointer moves.

OMN-16882 (Phase C1). See ``ModelThemeCatalog`` for the OD-2 resolution this
module implements: published revisions are packaged, immutable, digested data;
the active pointer is separate, mutable, per-surface state.

Catalog layout — ``<catalog root>/<theme_id>/<instance_revision>.yaml``. The
filename carries the revision so a published revision is addressable without
opening it, and ``build_theme_catalog`` fails closed when a document's declared
revision disagrees with the filename it was published under.

Digest — ``sha256`` over the RFC-8785-compatible canonical JSON of the instance
(``compute_canonical_hash``), never over raw file bytes. Two surfaces that load
one entry through different YAML writers must still agree (GC.2), and formatting
churn must not read as a value change.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_theme_activation import ModelThemeActivation
from omnibase_core.models.dashboard.model_theme_catalog import ModelThemeCatalog
from omnibase_core.models.dashboard.model_theme_catalog_entry import (
    ModelThemeCatalogEntry,
)
from omnibase_core.models.dashboard.model_theme_instance import ModelThemeInstance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

__all__ = [
    "THEME_CATALOG_ROOT",
    "THEME_CATALOG_VERSION",
    "activate_theme",
    "build_theme_catalog",
    "compute_theme_content_digest",
    "load_packaged_theme_catalog",
    "load_theme_instance",
    "roll_back_theme",
]

#: Packaged instance documents. Data shipped with the library, not code.
THEME_CATALOG_ROOT: Path = (
    Path(__file__).resolve().parent.parent / "contracts" / "themes"
)

#: Version of the catalog *format* — not of any theme in it.
THEME_CATALOG_VERSION: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0)


def compute_theme_content_digest(instance: ModelThemeInstance) -> str:
    """Return the ``sha256:<hex>`` digest of a theme instance's published form.

    Args:
        instance: The theme instance to digest.

    Returns:
        The digest as ``sha256:<64 lowercase hex chars>``.
    """
    return f"sha256:{compute_canonical_hash(instance.model_dump(mode='json'))}"


def load_theme_instance(path: Path) -> ModelThemeInstance:
    """Load and schema-validate one theme instance document.

    Args:
        path: Path to a serialized ``ModelThemeInstance`` YAML document.

    Returns:
        The validated instance.

    Raises:
        ModelOnexError: If the file is missing, unparseable, or fails schema
            validation.
    """
    return load_and_validate_yaml_model(path, ModelThemeInstance)


def build_theme_catalog(root: Path) -> ModelThemeCatalog:
    """Build a catalog from every instance document under ``root``.

    Args:
        root: Catalog root containing ``<theme_id>/<revision>.yaml`` documents.

    Returns:
        A catalog with one entry per published revision, ordered by
        (theme_id, revision string) so the result is deterministic.

    Raises:
        ModelOnexError: If ``root`` is not a directory, or a document's declared
            revision disagrees with the filename it is published under.
    """
    if not root.is_dir():
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
            message=f"theme catalog root does not exist: {root}",
        )

    entries: list[ModelThemeCatalogEntry] = []
    for document in sorted(root.rglob("*.yaml")):
        instance = load_theme_instance(document)
        declared_revision = str(instance.instance_revision)
        if document.stem != declared_revision:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"theme instance {document} declares revision "
                    f"{declared_revision} but is published as '{document.stem}'; "
                    f"a published revision must be addressable by its filename"
                ),
            )
        if document.parent.name != instance.theme_id:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=(
                    f"theme instance {document} declares theme_id "
                    f"'{instance.theme_id}' but is published under directory "
                    f"'{document.parent.name}'"
                ),
            )
        entries.append(
            ModelThemeCatalogEntry(
                theme_id=instance.theme_id,
                schema_version=instance.schema_version,
                instance_revision=instance.instance_revision,
                content_digest=compute_theme_content_digest(instance),
                source_path=document.relative_to(root).as_posix(),
            )
        )

    return ModelThemeCatalog(
        catalog_version=THEME_CATALOG_VERSION,
        entries=tuple(entries),
    )


def load_packaged_theme_catalog() -> ModelThemeCatalog:
    """Build the catalog from the instance documents shipped with omnibase_core.

    Returns:
        The packaged theme catalog.

    Raises:
        ModelOnexError: If the packaged catalog is missing or invalid.
    """
    return build_theme_catalog(THEME_CATALOG_ROOT)


def activate_theme(
    *,
    catalog: ModelThemeCatalog,
    surface_id: str,
    theme_id: str,
    instance_revision: ModelSemVer,
    current: ModelThemeActivation | None = None,
) -> ModelThemeActivation:
    """Point ``surface_id`` at a published revision.

    This is the only operation that changes rendered pixels. Publishing does
    not; it only adds an immutable revision the pointer may later name.

    Args:
        catalog: Catalog the revision must already be published in.
        surface_id: Surface whose pointer moves.
        theme_id: Theme to activate.
        instance_revision: Exact revision to activate.
        current: The surface's existing activation, if any. Supplies the
            sequence to increment and the revision a rollback returns to.

    Returns:
        The new activation pointer, carrying the digest resolved from the
        catalog.

    Raises:
        ModelOnexError: If the revision is not published, or ``current``
            belongs to a different surface.
    """
    if current is not None and current.surface_id != surface_id:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            message=(
                f"current activation belongs to surface '{current.surface_id}', "
                f"not '{surface_id}'"
            ),
        )

    entry = catalog.entry_for(theme_id, instance_revision)
    return ModelThemeActivation(
        surface_id=surface_id,
        theme_id=theme_id,
        instance_revision=entry.instance_revision,
        content_digest=entry.content_digest,
        activation_sequence=1 if current is None else current.activation_sequence + 1,
        superseded_revision=None if current is None else current.instance_revision,
    )


def roll_back_theme(
    *,
    catalog: ModelThemeCatalog,
    current: ModelThemeActivation,
) -> ModelThemeActivation:
    """Move a surface's pointer back to the revision ``current`` superseded.

    Rollback is a pointer move, not a rebuild: the returned activation carries
    the digest read from the catalog entry for the superseded revision, so a
    caller can prove the old bytes came back rather than a fresh compile that
    happens to look similar.

    Args:
        catalog: Catalog holding the superseded revision.
        current: The activation being rolled back.

    Returns:
        The restored activation pointer.

    Raises:
        ModelOnexError: If ``current`` has no superseded revision — a first
            activation has nowhere to roll back to and must fail rather than
            silently no-op.
    """
    if current.superseded_revision is None:
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_STATE,
            message=(
                f"surface '{current.surface_id}' has no superseded revision for "
                f"theme '{current.theme_id}'; there is nothing to roll back to"
            ),
        )

    entry = catalog.entry_for(current.theme_id, current.superseded_revision)
    return ModelThemeActivation(
        surface_id=current.surface_id,
        theme_id=current.theme_id,
        instance_revision=entry.instance_revision,
        content_digest=entry.content_digest,
        activation_sequence=current.activation_sequence + 1,
        superseded_revision=current.instance_revision,
    )
