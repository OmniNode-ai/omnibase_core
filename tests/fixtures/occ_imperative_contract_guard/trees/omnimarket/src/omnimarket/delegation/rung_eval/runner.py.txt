# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Run one attempt per rung and case, preserving failure rows."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import date
from typing import Protocol

from omnimarket.delegation.rung_eval.graders import grade_classification, grade_grouping
from omnimarket.delegation.rung_eval.models import (
    EnumRungEvalStatus,
    ModelRungEvalCase,
    ModelRungEvalRow,
    ModelRungSpec,
    ModelTransportResult,
)


class RungUnresolvedError(Exception):
    """The rung's endpoint or model environment variable is unset."""


class Transport(Protocol):
    def complete(self, rung: ModelRungSpec, prompt: str) -> ModelTransportResult: ...


def run_night(
    night: date,
    rungs: list[ModelRungSpec],
    cases: list[ModelRungEvalCase],
    transport: Transport,
) -> list[ModelRungEvalRow]:
    rows: list[ModelRungEvalRow] = []
    for rung in rungs:
        for case in cases:
            result: ModelTransportResult | None = None
            score = 0.0
            passed = False
            try:
                result = transport.complete(rung, case.prompt)
                if case.answer_key is not None:
                    grade = grade_classification(result.text, case.answer_key)
                elif case.ticket_ids is not None and case.max_groups is not None:
                    grade = grade_grouping(
                        result.text, case.ticket_ids, case.known_ids, case.max_groups
                    )
                else:
                    raise ValueError(f"No grading specification for {case.case_id}")
                score, passed, detail = grade.score, grade.passed, grade.detail
                status = (
                    EnumRungEvalStatus.PASSED if passed else EnumRungEvalStatus.FAILED
                )
            except RungUnresolvedError as exc:
                status = EnumRungEvalStatus.UNRESOLVED
                detail = str(exc)
            except Exception as exc:
                status = EnumRungEvalStatus.ERROR
                detail = f"{type(exc).__name__}: {exc}"
            rows.append(
                ModelRungEvalRow(
                    night=night,
                    rung_id=rung.rung_id,
                    task_class=case.task_class,
                    case_id=case.case_id,
                    status=status,
                    score=score,
                    passed=passed,
                    latency_ms=result.latency_ms if result is not None else None,
                    model_id=result.model_id if result is not None else None,
                    detail=detail,
                )
            )
    return rows


def _rung_env(name: str) -> str:
    """Read one environment variable whose name a rung spec declares."""
    return os.environ[name]  # ONEX_FLAG_EXEMPT: name declared by the rung spec


class OpenAIChatTransport:
    """Single-attempt chat completions over urllib."""

    def complete(self, rung: ModelRungSpec, prompt: str) -> ModelTransportResult:
        try:
            base_url = _rung_env(rung.base_url_env)
            model = _rung_env(rung.model_env)
            api_key = (
                _rung_env(rung.api_key_env) if rung.api_key_env is not None else None
            )
        except KeyError as exc:
            raise RungUnresolvedError(
                f"{rung.rung_id}: environment variable {exc.args[0]} is unset"
            ) from exc
        headers = {"Content-Type": "application/json"}
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = json.dumps(
            {
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=600) as response:
            body = json.load(response)
        return ModelTransportResult(
            text=body["choices"][0]["message"]["content"],
            model_id=body["model"],
            latency_ms=int((time.monotonic() - started) * 1000),
        )
