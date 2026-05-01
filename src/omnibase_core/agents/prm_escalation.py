# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import threading
from collections import OrderedDict

from omnibase_core.agents.prm_course_corrections import (
    HARD_STOP_SENTINEL,
    advisory_for,
    stronger_for,
)
from omnibase_core.models.agents.model_escalation_result import ModelEscalationResult
from omnibase_core.models.agents.model_prm_match import ModelPrmMatch

# Global session state: session_id → {dedup_key → hit_count}
_MAX_SESSION_STATE_ENTRIES = 1024
_SESSION_STATE: OrderedDict[str, dict[str, int]] = OrderedDict()
_STATE_LOCK = threading.Lock()


def _session_state_for_locked(session_id: str) -> dict[str, int]:
    session = _SESSION_STATE.get(session_id)
    if session is not None:
        _SESSION_STATE.move_to_end(session_id)
        return session

    if len(_SESSION_STATE) >= _MAX_SESSION_STATE_ENTRIES:
        _SESSION_STATE.popitem(last=False)

    session = {}
    _SESSION_STATE[session_id] = session
    return session


class EscalationTracker:
    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        with _STATE_LOCK:
            _session_state_for_locked(session_id)

    @staticmethod
    def reset_session(session_id: str) -> None:
        with _STATE_LOCK:
            _SESSION_STATE.pop(session_id, None)

    @staticmethod
    def reset_all_sessions() -> None:
        with _STATE_LOCK:
            _SESSION_STATE.clear()

    def process(self, match: ModelPrmMatch) -> ModelEscalationResult:
        key = match.dedup_key
        with _STATE_LOCK:
            session = _session_state_for_locked(self._session_id)
            session[key] = session.get(key, 0) + 1
            count = session[key]

        if count == 1:
            return ModelEscalationResult(
                severity_level=1,
                guidance=advisory_for(match.pattern),
                telemetry=None,
            )
        if count == 2:
            telemetry: dict[str, object] = {
                "dedup_key": key,
                "severity_level": 2,
                "pattern": match.pattern,
                "session_id": self._session_id,
                "affected_agents": list(match.affected_agents),
                "affected_targets": list(match.affected_targets),
                "step_range": list(match.step_range),
            }
            return ModelEscalationResult(
                severity_level=2,
                guidance=stronger_for(match.pattern),
                telemetry=telemetry,
            )
        # count >= 3
        return ModelEscalationResult(
            severity_level=3,
            guidance=HARD_STOP_SENTINEL,
            telemetry=None,
        )
