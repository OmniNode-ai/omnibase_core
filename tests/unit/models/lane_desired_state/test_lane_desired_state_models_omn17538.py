# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DoD tests for the lane desired-state identity models (OMN-17538, core half).

Authored before the models, RED on origin/dev: every import below fails there.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.lane_desired_state import (
    ModelImperativeOverride,
    ModelLaneDesiredStateIdentity,
    ModelMigrationBundleId,
    ModelResolvedImage,
    ModelSecretsSyncIdentity,
    ModelUnresolvedField,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
GIT_SHA = "0123456789abcdef0123456789abcdef01234567"  # pragma: allowlist secret


def _image(reference: str = DIGEST_A) -> ModelResolvedImage:
    return ModelResolvedImage(
        repository="ghcr.io/omninode/runtime", reference=reference
    )


def _bundle() -> ModelMigrationBundleId:
    return ModelMigrationBundleId(
        bundle_name="omnibase-infra-migrate",
        image_digest=DIGEST_A,
        built_for_head_sha=GIT_SHA,
    )


def _secrets() -> ModelSecretsSyncIdentity:
    return ModelSecretsSyncIdentity(
        machine_identity_ref="infisical://identities/lab-sync",
        project_slug="onex",
        environment_slug="dev",
        applied_cr_generation=7,
    )


def _override(*, replayed: bool = True) -> ModelImperativeOverride:
    return ModelImperativeOverride(
        plane="api",
        resource="Deployment/onex-api/api",
        command_summary="kubectl set image deployment/onex-api api=<digest>",
        replayed=replayed,
    )


def _identity(
    *, jobs_digest: str = DIGEST_A, images: object | None = None
) -> ModelLaneDesiredStateIdentity:
    resolved = (
        images
        if images is not None
        else {
            "Deployment/runtime/runtime": _image(DIGEST_A),
            "CronJob/jobs/runtime": _image(jobs_digest),
        }
    )
    return ModelLaneDesiredStateIdentity.model_validate(
        {
            "lane_id": "onex-lab",
            "lane_class": "golden",
            "source_git_sha": GIT_SHA,
            "rendered_manifest_hash": DIGEST_B,
            "resolved_images": resolved,
            "migration_bundle_ids": [_bundle()],
            "overlay_schema_version": ModelSemVer(major=1, minor=0, patch=0),
            "config_schema_version": ModelSemVer(major=1, minor=2, patch=0),
            "secrets_sync_identity": _secrets(),
            "imperative_overrides": [_override()],
        }
    )


# DoD1 -- every model round-trips through JSON unchanged.
@pytest.mark.parametrize(
    "model",
    [
        _image(),
        _bundle(),
        _secrets(),
        _override(),
        ModelUnresolvedField(field_name="resolved_images", reason="registry timeout"),
    ],
    ids=lambda m: type(m).__name__,
)
def test_roundtrip_leaf_models(model: object) -> None:
    cls = type(model)
    dumped = model.model_dump(mode="json")  # type: ignore[attr-defined]
    assert cls.model_validate(dumped) == model  # type: ignore[attr-defined]


def test_roundtrip_identity() -> None:
    identity = _identity()
    dumped = identity.model_dump(mode="json", exclude={"identity_hash"})
    again = ModelLaneDesiredStateIdentity.model_validate(dumped)
    assert again == identity
    assert again.identity_hash == identity.identity_hash


# DoD2 -- frozen and closed.
def test_strict_models_are_frozen_and_forbid_extra() -> None:
    image = _image()
    with pytest.raises(ValidationError):
        image.repository = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ModelResolvedImage(repository="r", reference=DIGEST_A, tag="x")  # type: ignore[call-arg]


def test_strict_digest_and_sha_shapes_are_validated() -> None:
    with pytest.raises(ValidationError):
        ModelMigrationBundleId(
            bundle_name="omnibase-infra-migrate",
            image_digest="a" * 64,
            built_for_head_sha=GIT_SHA,
        )
    with pytest.raises(ValidationError):
        ModelMigrationBundleId(
            bundle_name="omnibase-infra-migrate",
            image_digest=DIGEST_A,
            built_for_head_sha="abc123",
        )
    with pytest.raises(ValidationError):
        ModelMigrationBundleId(
            bundle_name="some-other-migrate",  # type: ignore[arg-type]
            image_digest=DIGEST_A,
            built_for_head_sha=GIT_SHA,
        )


def test_strict_mutable_tag_is_detected() -> None:
    assert _image("latest").is_mutable_tag() is True
    assert _image("placeholder").is_mutable_tag() is True
    assert _image(DIGEST_A).is_mutable_tag() is False


# DoD3 (AC5) -- an unresolved field serializes as the marker and the hash computes.
def test_unresolved_field_still_hashes() -> None:
    marker = ModelUnresolvedField(
        field_name="resolved_images", reason="registry timeout"
    )
    identity = _identity(images=marker)
    assert isinstance(identity.resolved_images, ModelUnresolvedField)
    assert identity.identity_hash.startswith("sha256:")
    assert len(identity.identity_hash) == len("sha256:") + 64
    dumped = identity.model_dump(mode="json", exclude={"identity_hash"})
    again = ModelLaneDesiredStateIdentity.model_validate(dumped)
    assert isinstance(again.resolved_images, ModelUnresolvedField)
    assert again.identity_hash == identity.identity_hash


def test_unresolved_marker_requires_a_reason() -> None:
    with pytest.raises(ValidationError):
        ModelUnresolvedField(field_name="resolved_images", reason="")


# DoD4 (AC8) -- secrets are references only.
def test_secrets_fields_are_references_only() -> None:
    assert set(ModelSecretsSyncIdentity.model_fields) == {
        "machine_identity_ref",
        "project_slug",
        "environment_slug",
        "applied_cr_generation",
    }
    with pytest.raises(ValidationError):
        ModelSecretsSyncIdentity(
            machine_identity_ref="infisical://identities/lab-sync",
            project_slug="onex",
            environment_slug="dev",
            applied_cr_generation=1,
            client_secret="inline-value",  # type: ignore[call-arg]  # pragma: allowlist secret
        )


# DoD5 -- the identity hash is whole-plane and deterministic.
def test_hash_is_deterministic() -> None:
    assert _identity().identity_hash == _identity().identity_hash


def test_hash_moves_on_a_single_jobs_digest() -> None:
    assert _identity().identity_hash != _identity(jobs_digest=DIGEST_B).identity_hash


def test_hash_ignores_dict_insertion_order() -> None:
    forward = _identity(images={"A/a/a": _image(DIGEST_A), "B/b/b": _image(DIGEST_B)})
    backward = _identity(images={"B/b/b": _image(DIGEST_B), "A/a/a": _image(DIGEST_A)})
    assert forward.identity_hash == backward.identity_hash
