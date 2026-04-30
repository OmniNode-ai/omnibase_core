# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import threading

from omnibase_core.agents.prm_course_corrections import (
    HARD_STOP_SENTINEL,
    advisory_for,
    stronger_for,
)
from omnibase_core.models.agents.model_escalation_result import ModelEscalationResult
from omnibase_core.models.agents.model_prm_match import ModelPrmMatch

# Global session state: session_id → {dedup_key → hit_count}
_SESSION_STATE: dict[str, dict[str, int]] = {}
_STATE_LOCK = threading.Lock()


class EscalationTracker:
    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        with _STATE_LOCK:
            if session_id not in _SESSION_STATE:
                _SESSION_STATE[session_id] = {}

    def process(self, match: ModelPrmMatch) -> ModelEscalationResult:
        key = match.dedup_key
        with _STATE_LOCK:
            session = _SESSION_STATE[self._session_id]
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
