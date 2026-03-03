#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 OmniNode Team
"""One-shot runner for NodeCrossRepoValidationOrchestrator.

Loads onex_validation_policy.yaml, runs cross-repo validation against this
repository, emits lifecycle events to Kafka, then exits.

Intended to be invoked by a scheduler (cron, GitHub Actions) so that omnidash's
event-consumer can project results into the validation_runs table and show the
Validation Dashboard as Live.

Usage:
    uv run python scripts/run_cross_repo_validation.py

    # Validate a specific directory:
    ROOT=/path/to/omnibase_core uv run python scripts/run_cross_repo_validation.py

Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS (optional, default: localhost:19092)
        Kafka bootstrap address. Set to empty string to skip event emission
        (validation still runs locally, no omnidash projection).

    ROOT (optional, default: repo root containing this script)
        Directory to validate. Defaults to the parent of scripts/.

Exit Codes:
    0  Validation passed (or completed with warnings)
    1  Configuration error
    2  Validation found errors

Ticket: OMN-3336
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent

# Allow importing omnibase_core from the repo root when running directly
sys.path.insert(0, str(_REPO_ROOT / "src"))

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from omnibase_core.nodes.node_validation_orchestrator.node_cross_repo_validation_orchestrator import (
    NodeCrossRepoValidationOrchestrator,
)
from omnibase_core.validation.cross_repo import load_policy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("run_cross_repo_validation")

_POLICY_PATH = _REPO_ROOT / "onex_validation_policy.yaml"


class _KafkaEventEmitter:
    """ProtocolEventEmitter backed by AIOKafkaProducer.

    Each validation event carries an event_type field that matches its Kafka topic
    name (e.g. "onex.evt.validation.cross-repo-run-completed.v1"). We use that
    value directly as the topic so no manual mapping is needed.
    """

    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def emit(self, event: object) -> None:
        topic = getattr(event, "event_type", None)
        if not topic:
            logger.debug("Event has no event_type, skipping: %s", type(event).__name__)
            return
        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else {}
        body = json.dumps(payload).encode("utf-8")
        await self._producer.send_and_wait(str(topic), body)
        logger.info("Emitted event to %s", topic)


async def _run() -> int:
    if not _POLICY_PATH.exists():
        logger.error(
            "Policy file not found: %s — create onex_validation_policy.yaml in repo root",
            _POLICY_PATH,
        )
        return 1

    root = Path(os.environ.get("ROOT", str(_REPO_ROOT))).resolve()
    kafka_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092").strip()
    repo_id = "omnibase_core"

    logger.info("Loading policy from %s", _POLICY_PATH)
    try:
        policy = load_policy(_POLICY_PATH)
    except Exception:
        logger.exception("Failed to load validation policy")
        return 1

    producer: AIOKafkaProducer | None = None
    emitter: _KafkaEventEmitter | None = None

    if kafka_servers:
        producer = AIOKafkaProducer(
            bootstrap_servers=kafka_servers,
            acks="all",
            enable_idempotence=True,
        )
        try:
            await producer.start()
            emitter = _KafkaEventEmitter(producer)
            logger.info("Kafka producer connected to %s", kafka_servers)
        except KafkaError:
            logger.warning(
                "Kafka unavailable (%s) — validation will run but no events emitted",
                kafka_servers,
                exc_info=True,
            )
            producer = None

    try:
        orchestrator = NodeCrossRepoValidationOrchestrator(
            policy,
            event_emitter=emitter,  # type: ignore[arg-type]
        )

        logger.info("Running cross-repo validation: root=%s repo_id=%s", root, repo_id)
        result = await orchestrator.validate(
            root=root,
            repo_id=repo_id,
            correlation_id=uuid4(),
        )

        completed = next(
            (e for e in result.events if hasattr(e, "is_valid")),
            None,
        )
        if completed is not None:
            total = getattr(completed, "total_violations", 0)
            is_valid = getattr(completed, "is_valid", True)
            logger.info(
                "Validation complete: is_valid=%s total_violations=%d run_id=%s",
                is_valid,
                total,
                result.run_id,
            )
            return 0 if is_valid else 2

        return 0

    except Exception:
        logger.exception("Cross-repo validation failed")
        return 1

    finally:
        if producer is not None:
            await producer.stop()


def main() -> None:
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
