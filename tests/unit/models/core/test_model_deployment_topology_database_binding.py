# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract tests for the store-resolved topology database binding (OMN-17556).

A binding names a workload identity and says WHERE that identity's DSN comes
from. Two carriers exist and exactly one may be declared per binding:

``dsn_env``
    The legacy carrier: a process environment variable holding the full DSN.
    Delivering it requires materializing the credential into a container env,
    manifest, or host -- precisely what
    ``feedback_no_required_env_secrets_from_store_only`` forbids.

``secret_ref``
    The store carrier: a dotted logical secret name the runtime resolves
    through ``SecretResolver`` at the binding boundary (connect time), never at
    process-env read time. The checked-in topology carries the REF; the store
    carries the VALUE.

Exactly-one is a hard structural invariant, not a preference:

* Both set -- two carriers for one credential means the deployed lane decides
  which one wins at runtime, and a stale env var silently shadows the store.
  That is the "works by convention" surface this ticket exists to remove.
* Neither set -- a binding with no credential source is unresolvable, and
  under ``ONEX_WIRING_STRICT_MODE`` it must fail at contract-load time with the
  binding named, not at first connect.

There is deliberately NO default on either field. A defaulted carrier would
reintroduce the silent-fallback class (cf. OMN-14951's convention-fallback
defect) at the layer above.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_deployment_topology_database_binding import (
    ModelDeploymentTopologyDatabaseBinding,
)

pytestmark = pytest.mark.unit

# Logical secret NAMES and deliberately-synthetic DSN literals used as negative
# fixtures. No real credential appears in this file; the pragmas mark that fact
# once, here, instead of on every use site.
_SECRET_REF = "database.application.tenant_projection.dsn"  # pragma: allowlist secret
_OTHER_SECRET_REF = "database.application.other.dsn"  # pragma: allowlist secret
_DSN_SHAPED_REF = "postgresql://user:pw@host:5432/db"  # pragma: allowlist secret
_PASTED_DSN = (
    "postgresql://tenant_projection_writer:pw@host:5432/db"  # pragma: allowlist secret
)


class TestDsnEnvCarrier:
    """The legacy env carrier keeps working, unchanged, on its own."""

    def test_dsn_env_alone_is_accepted(self) -> None:
        binding = ModelDeploymentTopologyDatabaseBinding(
            database_ref="application",
            principal="tenant_projection_writer",
            dsn_env="ONEX_TENANT_DB_URL",
        )
        assert binding.dsn_env == "ONEX_TENANT_DB_URL"
        assert binding.secret_ref is None

    def test_dsn_env_still_rejects_a_lowercase_name(self) -> None:
        with pytest.raises(ValidationError):
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
                dsn_env="onex_tenant_db_url",
            )


class TestSecretRefCarrier:
    """The store carrier is a dotted logical name, never a value."""

    def test_secret_ref_alone_is_accepted(self) -> None:
        binding = ModelDeploymentTopologyDatabaseBinding(
            database_ref="application",
            principal="tenant_projection_writer",
            secret_ref=_SECRET_REF,
        )
        assert binding.secret_ref == _SECRET_REF
        assert binding.dsn_env is None

    @pytest.mark.parametrize(
        "bad_ref",
        [
            "nodots",
            "Database.Application.dsn",
            "database..dsn",
            "database.application.",
            ".database.application",
            _DSN_SHAPED_REF,
            "database.application.tenant projection.dsn",
        ],
    )
    def test_secret_ref_rejects_a_non_logical_name(self, bad_ref: str) -> None:
        """A DSN value, a bare word, or a malformed dotted path is refused.

        The DSN-shaped case is the one that matters: the pattern is what stops
        a resolved credential from being pasted into the checked-in topology.
        """
        with pytest.raises(ValidationError):
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
                secret_ref=bad_ref,
            )


class TestExactlyOneCarrier:
    """Neither carrier and both carriers are equally rejected."""

    def test_both_carriers_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
                dsn_env="ONEX_TENANT_DB_URL",
                secret_ref=_SECRET_REF,
            )
        message = str(excinfo.value)
        assert "exactly one" in message
        assert "dsn_env" in message
        assert "secret_ref" in message

    def test_neither_carrier_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
            )
        message = str(excinfo.value)
        assert "exactly one" in message

    def test_neither_carrier_names_the_principal_it_could_not_resolve(self) -> None:
        """The error must be legible without opening the topology file."""
        with pytest.raises(ValidationError) as excinfo:
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
            )
        assert "tenant_projection_writer" in str(excinfo.value)


class TestBindingStaysSecretFree:
    """Structural guarantees the rest of the topology layer relies on."""

    def test_binding_is_frozen(self) -> None:
        binding = ModelDeploymentTopologyDatabaseBinding(
            database_ref="application",
            principal="tenant_projection_writer",
            secret_ref=_SECRET_REF,
        )
        with pytest.raises(ValidationError):
            binding.secret_ref = _OTHER_SECRET_REF  # type: ignore[misc]

    def test_binding_forbids_unknown_fields(self) -> None:
        """An unmodelled carrier (e.g. a pasted `dsn:`) cannot slip through."""
        with pytest.raises(ValidationError):
            ModelDeploymentTopologyDatabaseBinding(
                database_ref="application",
                principal="tenant_projection_writer",
                secret_ref=_SECRET_REF,
                dsn=_PASTED_DSN,
            )
