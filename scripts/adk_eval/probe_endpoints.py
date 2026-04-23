#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Probe Qwen3-Coder + Gemini + agents-cli endpoints for the ADK eval spike.

Writes a JSON evidence artifact to `.onex_state/evidence/adk-eval/endpoint_probe.json`.
Exits non-zero if any critical probe fails.

Task P1 of docs/plans/2026-04-23-adk-evaluation-tech-debt-agent.md.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

QWEN_BASE_URL = "http://192.168.86.201:8000"  # onex-allow-internal-ip: documented .201 endpoint
QWEN_MODEL = "cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit"
GEMINI_MODEL = "gemini-2.5-flash"


def _curl_json(
    url: str,
    timeout: float,
    method: str = "GET",
    payload: dict[str, object] | None = None,
) -> tuple[int, dict[str, object] | list[object] | str]:
    """Shell out to curl — Python's urllib is blocked on this host's direct socket path."""
    cmd = [
        "curl",
        "-sS",
        "--max-time",
        str(int(timeout)),
        "-w",
        "\n__HTTP_STATUS__%{http_code}",
        "-X",
        method,
    ]
    if payload is not None:
        cmd += [
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload),
        ]
    cmd.append(url)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 0, "timeout"
    stdout = proc.stdout
    status_line_marker = "\n__HTTP_STATUS__"
    if status_line_marker in stdout:
        body, _, status_str = stdout.rpartition(status_line_marker)
        status_str = status_str.strip()
        try:
            status = int(status_str)
        except ValueError:
            status = 0
    else:
        body = stdout
        status = 0
    if not body:
        return status, proc.stderr or "(empty body)"
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, body


def probe_qwen_models() -> dict[str, object]:
    t0 = time.perf_counter()
    status, body = _curl_json(f"{QWEN_BASE_URL}/v1/models", timeout=10)
    elapsed = time.perf_counter() - t0
    model_ids: list[str] = []
    if isinstance(body, dict):
        data_list = body.get("data", [])
        if isinstance(data_list, list):
            for entry in data_list:
                if isinstance(entry, dict):
                    maybe_id = entry.get("id")
                    if isinstance(maybe_id, str):
                        model_ids.append(maybe_id)
    return {
        "status": status,
        "elapsed_seconds": round(elapsed, 3),
        "model_ids": model_ids,
        "expected_model_available": QWEN_MODEL in model_ids,
    }


def probe_qwen_completion() -> dict[str, object]:
    t0 = time.perf_counter()
    status, body = _curl_json(
        f"{QWEN_BASE_URL}/v1/completions",
        timeout=60,
        method="POST",
        payload={
            "model": QWEN_MODEL,
            "prompt": "Respond with only: OK",
            "max_tokens": 5,
            "temperature": 0,
        },
    )
    elapsed = time.perf_counter() - t0
    text: str | None = None
    if isinstance(body, dict):
        choices = body.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                t = first.get("text")
                if isinstance(t, str):
                    text = t
    return {
        "status": status,
        "elapsed_seconds": round(elapsed, 3),
        "text": text,
        "ok": status == 200 and text is not None,
    }


def probe_gemini() -> dict[str, object]:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"status": 0, "error": "GOOGLE_API_KEY/GEMINI_API_KEY not set", "ok": False}
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    t0 = time.perf_counter()
    status, body = _curl_json(
        url,
        timeout=30,
        method="POST",
        payload={"contents": [{"parts": [{"text": "reply only: OK"}]}]},
    )
    elapsed = time.perf_counter() - t0
    text: str | None = None
    if isinstance(body, dict):
        candidates = body.get("candidates", [])
        if isinstance(candidates, list) and candidates:
            cand = candidates[0]
            if isinstance(cand, dict):
                content = cand.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    if isinstance(parts, list) and parts:
                        first = parts[0]
                        if isinstance(first, dict):
                            t = first.get("text")
                            if isinstance(t, str):
                                text = t
    return {
        "status": status,
        "elapsed_seconds": round(elapsed, 3),
        "model": GEMINI_MODEL,
        "text": text,
        "ok": status == 200 and text is not None,
    }


def probe_agents_cli() -> dict[str, object]:
    try:
        ver = subprocess.run(
            ["agents-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        info = subprocess.run(
            ["agents-cli", "info"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return {
            "version_stdout": ver.stdout.strip(),
            "version_exit": ver.returncode,
            "info_stdout": info.stdout.strip(),
            "info_exit": info.returncode,
            "ok": ver.returncode == 0,
        }
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return {"error": repr(e), "ok": False}


def main() -> int:
    evidence = {
        "probed_at": datetime.now(UTC).isoformat(),
        "qwen_models": probe_qwen_models(),
        "qwen_completion": probe_qwen_completion(),
        "gemini": probe_gemini(),
        "agents_cli": probe_agents_cli(),
    }
    # Locate evidence dir relative to repo root (…/omni_worktrees/adk-eval/omnibase_core/)
    evidence_dir = Path(__file__).resolve().parent.parent.parent / ".onex_state" / "evidence" / "adk-eval"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    out = evidence_dir / "endpoint_probe.json"
    out.write_text(json.dumps(evidence, indent=2, sort_keys=True))
    print(f"Wrote {out}")
    # Also mirror to the top-level omni_home evidence dir so callers outside the worktree can find it.
    mirror_root_env = os.environ.get("OMNI_HOME")
    if mirror_root_env:
        mirror_dir = Path(mirror_root_env) / ".onex_state" / "evidence" / "adk-eval"
        mirror_dir.mkdir(parents=True, exist_ok=True)
        (mirror_dir / "endpoint_probe.json").write_text(json.dumps(evidence, indent=2, sort_keys=True))
        print(f"Mirrored to {mirror_dir / 'endpoint_probe.json'}")

    critical_ok = (
        evidence["qwen_models"]["expected_model_available"]
        and evidence["qwen_completion"]["ok"]
        and evidence["agents_cli"]["ok"]
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if critical_ok else 1


if __name__ == "__main__":
    sys.exit(main())
