# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
User-local ONEX configuration model (``~/.onex/config.yaml``).

This is the single schema for the file. Before OMN-16037 two commands wrote it
with incompatible shapes: ``onex config init`` emitted
``{mode: standalone, kafka, logging}`` while ``onex init --user-config`` emitted
``{version, mode, credentials, paths}``. Whichever ran last silently redefined
the file. The surviving schema is the union, keyed on the richer
``version``/``mode``/``credentials``/``paths`` shape and retaining the
operational ``kafka``/``logging`` sections the standalone writer owned.

This model describes only the sections ONEX *manages*. The file is user-editable
and other commands (``onex refresh-credentials``) append sections of their own,
so callers must go through :mod:`omnibase_core.cli.cli_user_config`, which
merges validated managed sections back over the raw mapping instead of replacing
it. That is what keeps an unknown ``aws:`` block — or a hand-added credential
key — from being dropped on the next write.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_user_config_mode import EnumUserConfigMode
from omnibase_core.models.cli.model_cli_user_config_credentials import (
    ModelCliUserConfigCredentials,
)
from omnibase_core.models.cli.model_cli_user_config_kafka import (
    ModelCliUserConfigKafka,
)
from omnibase_core.models.cli.model_cli_user_config_logging import (
    ModelCliUserConfigLogging,
)
from omnibase_core.models.cli.model_cli_user_config_paths import (
    ModelCliUserConfigPaths,
)

# Schema version written into every managed config file. Bump only alongside a
# migration step in ``cli_user_config.normalize_user_config``.
USER_CONFIG_VERSION = 1


class ModelCliUserConfig(BaseModel):
    """The managed sections of ``~/.onex/config.yaml``.

    Field declaration order is the on-disk key order — ``yaml.dump`` is called
    with ``sort_keys=False`` so the rendered file stays readable and stable
    across rewrites.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        frozen=True,
    )

    version: int = Field(
        default=USER_CONFIG_VERSION, description="Config schema version"
    )
    mode: EnumUserConfigMode = Field(
        default=EnumUserConfigMode.LOCAL, description="local (Mode A) or cloud (Mode B)"
    )
    credentials: ModelCliUserConfigCredentials = Field(
        default_factory=ModelCliUserConfigCredentials
    )
    paths: ModelCliUserConfigPaths = Field(default_factory=ModelCliUserConfigPaths)
    kafka: ModelCliUserConfigKafka = Field(default_factory=ModelCliUserConfigKafka)
    logging: ModelCliUserConfigLogging = Field(
        default_factory=ModelCliUserConfigLogging
    )


# Section names ONEX manages. Anything else in the file is user- or
# command-owned and is preserved verbatim across rewrites.
MANAGED_SECTIONS: tuple[str, ...] = tuple(ModelCliUserConfig.model_fields)


__all__ = [
    "MANAGED_SECTIONS",
    "USER_CONFIG_VERSION",
    "ModelCliUserConfig",
]
