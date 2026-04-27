# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aliveness probe command contract for runtime liveness verification.

Wave 3 of the runtime-lifecycle-hardening plan. The probe runner (Task 9, lives
in omnibase_infra) consumes ``ModelRuntimeAlivenessProbeCommand`` and emits a
``ModelRuntimeAlivenessProbeReceipt`` (sibling module). The two models are the
shared schema between the runner and any downstream consumer (CI gate, replay,
projection).
"""

from __future__ import annotations

import os
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_TIMEOUT_SECONDS = 30
TIMEOUT_ENV_VAR = "RUNTIME_ALIVENESS_TIMEOUT_SECONDS"

FailureState = Literal[
    "timeout",
    "terminal_failure_emitted",
    "projection_write_failed",
    "lag_above_threshold",
]

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "TIMEOUT_ENV_VAR",
    "FailureState",
    "ModelRuntimeAlivenessProbeCommand",
]


def _resolve_timeout_from_env() -> int:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    if parsed <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return parsed


class ModelRuntimeAlivenessProbeCommand(BaseModel):
    """Typed command published to a target command topic to verify runtime liveness.

    The probe runner publishes an instance of this model as a ModelEventMessage
    payload to ``target_command_topic`` and waits up to ``timeout_seconds`` for a
    matching terminal event on ``expected_terminal_topic`` plus a projection row
    keyed by ``projection_key_template``. Outcome populates ``failure_states`` on
    the receipt, never on the command.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str = Field(
        ...,
        min_length=1,
        description="Probe correlation id; must round-trip end-to-end",
    )
    target_command_topic: str = Field(
        ...,
        min_length=1,
        description="Command topic the probe publishes to (onex.cmd.<service>.<event>.v<N>)",
    )
    target_handler_id: str = Field(
        ...,
        min_length=1,
        description="Fully qualified handler id expected to consume the probe",
    )
    expected_terminal_topic: str = Field(
        ...,
        min_length=1,
        description="Terminal event topic the probe runner waits on (onex.evt.<service>.<event>.v<N>)",
    )
    projection_key_template: str = Field(
        ...,
        min_length=1,
        description="Projection key template, e.g. 'public.build_loop_runs:run_id={correlation_id}'",
    )
    timeout_seconds: int = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        gt=0,
        description="Wall-clock probe budget; default 30, configurable via env RUNTIME_ALIVENESS_TIMEOUT_SECONDS",
    )
    failure_states: tuple[FailureState, ...] = Field(
        default=(),
        description="Always empty on the command; populated only on the receipt outcome",
    )

    @classmethod
    def from_env(cls, **kwargs: Any) -> Self:
        """Construct a probe command, resolving timeout_seconds from the env when not provided.

        ``RUNTIME_ALIVENESS_TIMEOUT_SECONDS`` overrides the 30s default. Invalid or
        non-positive values fall back to the default rather than raising — the env
        is treated as operational tuning, not a hard contract surface.
        """
        if "timeout_seconds" not in kwargs:
            kwargs["timeout_seconds"] = _resolve_timeout_from_env()
        return cls(**kwargs)
