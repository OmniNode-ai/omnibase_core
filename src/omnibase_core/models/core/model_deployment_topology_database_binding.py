# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Secret-free consumer binding for a deployment database."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelDeploymentTopologyDatabaseBinding"]

_REFERENCE_PATTERN = r"^[a-z_][a-z0-9_]*$"
_ENVIRONMENT_VARIABLE_PATTERN = r"^[A-Z][A-Z0-9_]*$"
# Dotted logical secret name: at least two segments, lower snake per segment.
# The two-segment minimum is what makes a bare word (and, with the character
# class, a DSN literal) unrepresentable here.
_STORE_REFERENCE_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"


class ModelDeploymentTopologyDatabaseBinding(BaseModel):
    """Map a consumer to a LOGIN principal and ONE credential carrier.

    A binding names a workload identity and declares WHERE that identity's DSN
    is sourced from. Exactly one carrier may be declared (OMN-17556):

    ``dsn_env``
        Legacy carrier -- a process environment variable holding the full DSN.
        Delivering it requires materializing the credential into a container
        env, manifest, or host, which ``feedback_no_required_env_secrets_from_
        store_only`` forbids. Retained for the bindings not yet migrated.

    ``secret_ref``
        Store carrier -- a dotted logical secret name the runtime resolves
        through ``SecretResolver`` at the *binding boundary* (connect time),
        never at process-env read time. The checked-in topology carries the
        REF; the store carries the VALUE.

    Neither field is defaulted and neither is optional-by-convenience: a
    defaulted carrier would reintroduce the silent-fallback class OMN-14951
    closed one layer up. Both-set is rejected because two carriers for one
    credential let a stale env var silently shadow the store; neither-set is
    rejected because an unresolvable binding must fail at contract-load time,
    naming the principal, rather than at first connect.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    database_ref: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_REFERENCE_PATTERN,
        description="Logical database reference, never a physical DSN.",
    )
    principal: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=_REFERENCE_PATTERN,
        description="LOGIN workload-principal reference.",
    )
    dsn_env: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=_ENVIRONMENT_VARIABLE_PATTERN,
        description=(
            "Environment-variable name holding the DSN; never the DSN value. "
            "Mutually exclusive with 'secret_ref'."
        ),
    )
    secret_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        pattern=_STORE_REFERENCE_PATTERN,
        description=(
            "Dotted logical secret name resolved from the secret store at the "
            "binding boundary; never the DSN value. Mutually exclusive with "
            "'dsn_env'."
        ),
    )

    @model_validator(mode="after")
    def _require_exactly_one_credential_carrier(
        self,
    ) -> ModelDeploymentTopologyDatabaseBinding:
        """Reject both-set and neither-set, naming the principal either way."""
        declared = [
            name
            for name, value in (
                ("dsn_env", self.dsn_env),
                ("secret_ref", self.secret_ref),
            )
            if value is not None
        ]
        if len(declared) == 1:
            return self
        detail = (
            f"declares both {declared}"
            if declared
            else "declares neither, so its DSN is unresolvable"
        )
        raise ValueError(
            "a topology database binding must declare exactly one credential "
            f"carrier -- 'dsn_env' (env var) or 'secret_ref' (secret store). "
            f"Binding for principal {self.principal!r} on database_ref "
            f"{self.database_ref!r} {detail}."
        )
