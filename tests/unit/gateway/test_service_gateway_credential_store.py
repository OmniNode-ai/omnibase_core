# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail-closed reads of the ``~/.onex`` gateway credential (OMN-15922).

Every test here asserts a REFUSAL. That is the point: the credential store's
whole job at launch is that a missing, malformed, world-readable, or
secret-in-plaintext configuration produces a named error and no credential,
rather than an anonymous call that the operator believes is authenticated.
The one happy-path test exists to prove the refusals are not vacuous.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.services.gateway.service_gateway_credential_store import (
    ServiceGatewayCredentialStore,
)

pytestmark = pytest.mark.unit

_SECRET = "s3cr3t-not-a-real-value"  # pragma: allowlist secret


def _write_config(root: Path, body: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(body)


def _write_credentials(
    root: Path, mapping: dict[str, str], *, mode: int = 0o600
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "credentials.json"
    path.write_text(json.dumps(mapping))
    path.chmod(mode)


_GOOD_CONFIG = """\
mode: standalone

gateway:
  tenant_slug: acme
  client_id: ga-acme
  client_secret_ref: acme-gateway
  token_endpoint: https://keycloak.invalid/realms/acme/protocol/openid-connect/token
  base_url: https://api.invalid
  edge_instance_id: test-edge
"""


def _store(root: Path) -> ServiceGatewayCredentialStore:
    return ServiceGatewayCredentialStore(onex_home=root)


def test_a_complete_credential_loads_and_keeps_the_secret_out_of_repr(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path, _GOOD_CONFIG)
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    credential = _store(tmp_path).load()

    assert credential.client_id == "ga-acme"
    assert credential.tenant_slug == "acme"
    assert credential.base_url == "https://api.invalid"
    assert credential.client_secret.get_secret_value() == _SECRET
    # The secret must not leak through the model's own string forms -- those
    # are what end up in tracebacks, receipts and log lines.
    assert _SECRET not in repr(credential)
    assert _SECRET not in str(credential)


def test_a_missing_config_file_refuses_and_names_the_remediation(
    tmp_path: Path,
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert "onex auth login" in str(caught.value)


def test_a_config_without_a_gateway_block_refuses(tmp_path: Path) -> None:
    _write_config(tmp_path, "mode: standalone\n")
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert "gateway" in str(caught.value)


@pytest.mark.parametrize(
    "missing_key",
    ["tenant_slug", "client_id", "client_secret_ref", "token_endpoint", "base_url"],
)
def test_every_required_field_is_individually_load_bearing(
    tmp_path: Path, missing_key: str
) -> None:
    lines = [
        line for line in _GOOD_CONFIG.splitlines() if f"{missing_key}:" not in line
    ]
    _write_config(tmp_path, "\n".join(lines) + "\n")
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert missing_key in str(caught.value)


def test_a_blank_required_field_refuses_rather_than_being_treated_as_absent(
    tmp_path: Path,
) -> None:
    _write_config(tmp_path, _GOOD_CONFIG.replace("client_id: ga-acme", 'client_id: ""'))
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    with pytest.raises(ModelOnexError):
        _store(tmp_path).load()


def test_an_inline_client_secret_in_config_is_refused_outright(tmp_path: Path) -> None:
    """A secret VALUE in config.yaml is a defect, not a supported shortcut.

    config.yaml is world-readable by default and is the file operators paste
    into issues. Accepting a literal here -- even as a convenience fallback --
    would make the by-reference rule advisory.
    """
    _write_config(tmp_path, _GOOD_CONFIG + f"  client_secret: {_SECRET}\n")
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    message = str(caught.value)
    assert "client_secret" in message
    assert _SECRET not in message


def test_a_missing_credentials_file_refuses(tmp_path: Path) -> None:
    _write_config(tmp_path, _GOOD_CONFIG)

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert "credentials.json" in str(caught.value)


def test_a_dangling_secret_ref_refuses(tmp_path: Path) -> None:
    _write_config(tmp_path, _GOOD_CONFIG)
    _write_credentials(tmp_path, {"some-other-tenant": _SECRET})

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert "acme-gateway" in str(caught.value)


def test_a_group_or_world_readable_credentials_file_refuses(tmp_path: Path) -> None:
    _write_config(tmp_path, _GOOD_CONFIG)
    _write_credentials(tmp_path, {"acme-gateway": _SECRET}, mode=0o644)

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert "0600" in str(caught.value)


def test_no_refusal_ever_carries_the_secret_value(tmp_path: Path) -> None:
    """The failure ladder is where secrets leak, so sweep the whole ladder."""
    _write_config(tmp_path, _GOOD_CONFIG)
    _write_credentials(tmp_path, {"acme-gateway": _SECRET}, mode=0o644)

    with pytest.raises(ModelOnexError) as caught:
        _store(tmp_path).load()

    assert _SECRET not in str(caught.value)
    assert _SECRET not in repr(caught.value)


def test_save_writes_a_0600_credentials_file_and_a_reference_only_config(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)

    store.save(
        tenant_slug="acme",
        client_id="ga-acme",
        client_secret=_SECRET,
        token_endpoint="https://keycloak.invalid/realms/acme/protocol/openid-connect/token",
        base_url="https://api.invalid",
        edge_instance_id="test-edge",
    )

    config_text = (tmp_path / "config.yaml").read_text()
    assert _SECRET not in config_text
    assert "client_secret_ref" in config_text

    credentials_path = tmp_path / "credentials.json"
    mode = stat.S_IMODE(credentials_path.stat().st_mode)
    assert mode == 0o600

    # Round trip: what save wrote is what load accepts.
    assert store.load().client_secret.get_secret_value() == _SECRET


def test_save_preserves_unrelated_config_keys(tmp_path: Path) -> None:
    """``onex auth login`` must not silently rewrite the rest of config.yaml."""
    _write_config(
        tmp_path, "mode: standalone\nkafka:\n  bootstrap_servers: localhost:19092\n"
    )

    _store(tmp_path).save(
        tenant_slug="acme",
        client_id="ga-acme",
        client_secret=_SECRET,
        token_endpoint="https://keycloak.invalid/realms/acme/protocol/openid-connect/token",
        base_url="https://api.invalid",
        edge_instance_id="test-edge",
    )

    text = (tmp_path / "config.yaml").read_text()
    assert "bootstrap_servers" in text
    assert "mode: standalone" in text


def test_logout_removes_both_the_reference_and_the_secret(tmp_path: Path) -> None:
    _write_config(tmp_path, _GOOD_CONFIG)
    _write_credentials(tmp_path, {"acme-gateway": _SECRET})

    _store(tmp_path).clear()

    assert _SECRET not in (tmp_path / "credentials.json").read_text()
    assert "gateway" not in (tmp_path / "config.yaml").read_text()
    with pytest.raises(ModelOnexError):
        _store(tmp_path).load()
