# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ServiceGatewayCredentialStore — the ``~/.onex`` gateway credential (OMN-15922).

Two files, split on exactly one axis: whether the content is a secret.

``~/.onex/config.yaml`` (the surface ``onex config get`` already reads, same
reader shape -- ``yaml.safe_load`` over the same path) carries a ``gateway:``
block of references and endpoints. It never carries a secret VALUE. That is not
a style preference: config.yaml is world-readable by default and is the file
operators paste into issues and screen-shares. A literal ``client_secret`` here
is refused outright rather than accepted-with-a-warning, because a convenience
fallback would make the by-reference rule advisory and every future credential
would take the easy path.

``~/.onex/credentials.json`` (mode 0600, enforced on read as well as on write)
holds ``{<ref>: <secret>}``. Enforcing the mode on READ matters more than on
write: the file survives ``chmod``, backup/restore, and ``scp``, so a write-time
check alone proves nothing about the file actually being loaded.

Every failure path raises ``ModelOnexError``. There is no "return None and let
the caller decide" branch, because the caller that decides wrong makes an
anonymous call the operator believes is authenticated -- the single failure
this store exists to prevent (OMN-15680 AC-e restated at the auth layer).

Schema note (OMN-16037): ``config.yaml`` currently has two divergent writers,
``cli_config.py`` (``mode``/``kafka``/``logging``) and ``cli_init.py``
(``version``/``credentials``/``paths``). This store deliberately does not pick
a side and does not widen the drift: it reads and writes ONLY its own
``gateway:`` block, preserves every other top-level key byte-for-byte through a
load/mutate/dump round trip, and follows ``cli_config.py``'s reader shape.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Final

import yaml
from pydantic import SecretStr

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_credential import ModelGatewayCredential

__all__ = ["ServiceGatewayCredentialStore"]

_GATEWAY_BLOCK: Final[str] = "gateway"
_SECRET_REF_KEY: Final[str] = "client_secret_ref"
_REMEDIATION: Final[str] = (
    "run 'onex auth login --tenant-slug <slug> --client-id <principal_id> "
    "--client-secret-stdin'"
)
# Field name -> config key. tenant_slug/client_id/token_endpoint/base_url are
# the four the mint and the attach both need; edge_instance_id is bookkeeping
# only and so is the one key with a defensible default (the hostname is not
# available to a transport-free package, so login always writes it).
_REQUIRED_KEYS: Final[tuple[str, ...]] = (
    "tenant_slug",
    "client_id",
    _SECRET_REF_KEY,
    "token_endpoint",
    "base_url",
)


class ServiceGatewayCredentialStore:
    """Reads and writes the gateway credential under an ``~/.onex`` root."""

    def __init__(self, *, onex_home: Path) -> None:
        """Bind the store to a directory.

        Args:
            onex_home: Directory holding ``config.yaml`` and
                ``credentials.json``. Injected rather than derived from
                ``Path.home()`` inside the class so tests drive a real
                directory instead of patching the home lookup.
        """
        self._onex_home = onex_home

    @property
    def config_path(self) -> Path:
        return self._onex_home / "config.yaml"

    @property
    def credentials_path(self) -> Path:
        return self._onex_home / "credentials.json"

    # -- read --------------------------------------------------------------

    def load(self) -> ModelGatewayCredential:
        """Resolve the credential, or raise naming what to do about it.

        Raises:
            ModelOnexError: On any missing, blank, malformed, mis-permissioned
                or secret-carrying configuration. Never returns a partially
                resolved credential.
        """
        block = self._load_gateway_block()

        if "client_secret" in block:
            raise ModelOnexError(
                f"{self.config_path} carries an inline 'client_secret'. The "
                "secret value must live only in "
                f"{self.credentials_path} (mode 0600), referenced from config "
                f"by '{_SECRET_REF_KEY}'. Remove it and {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )

        values: dict[str, str] = {}
        for key in _REQUIRED_KEYS:
            values[key] = self._require_text(block, key)

        edge_instance_id = self._require_text(block, "edge_instance_id")
        secret = self._read_secret(values[_SECRET_REF_KEY])

        return ModelGatewayCredential(
            tenant_slug=values["tenant_slug"],
            client_id=values["client_id"],
            client_secret=SecretStr(secret),
            token_endpoint=values["token_endpoint"],
            base_url=values["base_url"],
            edge_instance_id=edge_instance_id,
        )

    def _load_gateway_block(self) -> dict[str, object]:
        document = self._load_config_document(must_exist=True)
        block = document.get(_GATEWAY_BLOCK)
        if block is None:
            raise ModelOnexError(
                f"{self.config_path} has no '{_GATEWAY_BLOCK}:' block -- this "
                f"machine holds no gateway credential. To create one, {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
            )
        if not isinstance(block, dict):
            raise ModelOnexError(
                f"{self.config_path}: '{_GATEWAY_BLOCK}' must be a mapping, "
                f"found {type(block).__name__}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            )
        return {str(key): value for key, value in block.items()}

    def _load_config_document(self, *, must_exist: bool) -> dict[str, object]:
        if not self.config_path.exists():
            if not must_exist:
                return {}
            raise ModelOnexError(
                f"no ONEX config at {self.config_path} -- this machine holds no "
                f"gateway credential. To create one, {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
            )
        # yaml-ok: user-authored config file with two divergent writers
        # (OMN-16037); a Pydantic model here would either reject the other
        # writer's keys or silently drop them on the round trip.
        document = yaml.safe_load(self.config_path.read_text())
        if document is None:
            return {}
        if not isinstance(document, dict):
            raise ModelOnexError(
                f"{self.config_path} must be a YAML mapping, found "
                f"{type(document).__name__}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            )
        return {str(key): value for key, value in document.items()}

    def _require_text(self, block: dict[str, object], key: str) -> str:
        """Read one non-blank string, treating blank as absent-and-wrong."""
        if key not in block:
            raise ModelOnexError(
                f"{self.config_path}: '{_GATEWAY_BLOCK}.{key}' is missing. "
                f"To rewrite the block, {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.MISSING_REQUIRED_PARAMETER,
            )
        value = block[key]
        if not isinstance(value, str) or not value.strip():
            raise ModelOnexError(
                f"{self.config_path}: '{_GATEWAY_BLOCK}.{key}' must be a "
                f"non-empty string. To rewrite the block, {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
        return value

    def _read_secret(self, secret_ref: str) -> str:
        """Resolve the referenced secret from the 0600 credentials file."""
        if not self.credentials_path.exists():
            raise ModelOnexError(
                f"no credentials.json at {self.credentials_path}, but config "
                f"references secret '{secret_ref}'. To restore it, {_REMEDIATION}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
            )

        mode = stat.S_IMODE(self.credentials_path.stat().st_mode)
        if mode & 0o077:
            raise ModelOnexError(
                f"{self.credentials_path} is mode {mode:04o}; it must be 0600 "
                "(owner-only). Refusing to read a group- or world-readable "
                "credential file. Fix with: chmod 600 "
                f"{self.credentials_path}",
                error_code=EnumCoreErrorCode.PERMISSION_DENIED,
            )

        raw = self.credentials_path.read_text()
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelOnexError(
                f"{self.credentials_path} is not valid JSON. To rewrite it, "
                f"{_REMEDIATION}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from exc

        if not isinstance(document, dict):
            raise ModelOnexError(
                f"{self.credentials_path} must be a JSON object mapping "
                "secret refs to secret values.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            )
        if secret_ref not in document:
            raise ModelOnexError(
                f"{self.credentials_path} has no entry for secret ref "
                f"'{secret_ref}' named by {self.config_path}. To restore it, "
                f"{_REMEDIATION}.",
                error_code=EnumCoreErrorCode.CONFIGURATION_NOT_FOUND,
            )
        secret = document[secret_ref]
        if not isinstance(secret, str) or not secret:
            raise ModelOnexError(
                f"{self.credentials_path}: entry '{secret_ref}' must be a "
                "non-empty string.",
                error_code=EnumCoreErrorCode.INVALID_CONFIGURATION,
            )
        return secret

    # -- write -------------------------------------------------------------

    def save(
        self,
        *,
        tenant_slug: str,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        base_url: str,
        edge_instance_id: str,
    ) -> None:
        """Write the reference-only config block and the 0600 secret file.

        Every other top-level key in ``config.yaml`` survives the round trip --
        ``onex auth login`` must not be a way to lose someone's ``kafka:``
        settings (OMN-16037: two writers already disagree about this file).
        """
        secret_ref = f"{tenant_slug}-gateway"
        self._onex_home.mkdir(parents=True, exist_ok=True)

        document = self._load_config_document(must_exist=False)
        document[_GATEWAY_BLOCK] = {
            "tenant_slug": tenant_slug,
            "client_id": client_id,
            _SECRET_REF_KEY: secret_ref,
            "token_endpoint": token_endpoint,
            "base_url": base_url,
            "edge_instance_id": edge_instance_id,
        }
        self.config_path.write_text(yaml.safe_dump(document, sort_keys=False))

        secrets = self._load_secret_document()
        secrets[secret_ref] = client_secret
        self._write_secret_document(secrets)

    def clear(self) -> None:
        """Remove both the config block and the referenced secret.

        Order matters: the secret goes first. If the process dies between the
        two writes, what survives is a config that names a missing secret --
        which ``load`` refuses loudly -- rather than an orphaned secret sitting
        on disk with nothing pointing at it.
        """
        document = self._load_config_document(must_exist=False)
        block = document.get(_GATEWAY_BLOCK)
        secret_ref = ""
        if isinstance(block, dict):
            candidate = block.get(_SECRET_REF_KEY)
            if isinstance(candidate, str):
                secret_ref = candidate

        if secret_ref:
            secrets = self._load_secret_document()
            if secret_ref in secrets:
                del secrets[secret_ref]
                self._write_secret_document(secrets)

        if _GATEWAY_BLOCK in document:
            del document[_GATEWAY_BLOCK]
            self.config_path.write_text(yaml.safe_dump(document, sort_keys=False))

    def _load_secret_document(self) -> dict[str, str]:
        if not self.credentials_path.exists():
            return {}
        try:
            document = json.loads(self.credentials_path.read_text())
        except json.JSONDecodeError as exc:
            raise ModelOnexError(
                f"{self.credentials_path} is not valid JSON; refusing to "
                "overwrite it and lose the credentials it may hold.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                f"{self.credentials_path} must be a JSON object.",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            )
        return {str(key): str(value) for key, value in document.items()}

    def _write_secret_document(self, secrets: dict[str, str]) -> None:
        """Write the secret file so it is never briefly world-readable.

        ``touch`` + ``chmod`` before ``write_text``: creating the file at the
        umask default and tightening it afterwards leaves a window in which the
        secret is on disk at 0644.
        """
        self.credentials_path.touch(mode=0o600, exist_ok=True)
        self.credentials_path.chmod(0o600)
        self.credentials_path.write_text(json.dumps(secrets, indent=2, sort_keys=True))
