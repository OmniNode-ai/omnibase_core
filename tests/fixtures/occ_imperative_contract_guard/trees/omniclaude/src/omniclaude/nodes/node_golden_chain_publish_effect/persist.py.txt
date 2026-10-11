# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""Sweep result persistence — inserts per-chain results into golden_chain_sweep_results.

Lives in the EFFECT node so that DB access is correctly scoped outside orchestrator code.
Called by node_golden_chain_sweep_orchestrator after all chains have run.
"""

from __future__ import annotations

import json
import logging

from omniclaude.nodes.node_golden_chain_publish_effect.models.model_chain_result import (
    ModelChainResult,
)
from omniclaude.nodes.node_golden_chain_status_reducer.models.model_sweep_summary import (
    ModelSweepSummary,
)

logger = logging.getLogger(__name__)


async def persist_sweep_results(
    summary: ModelSweepSummary,
    chain_results: list[ModelChainResult],
    *,
    db_dsn: str,
) -> None:
    """Insert per-chain results into golden_chain_sweep_results table.

    Args:
        summary: Sweep summary with sweep_id and timestamps.
        chain_results: Per-chain run results.
        db_dsn: PostgreSQL DSN for omnidash_analytics.
    """
    import psycopg2

    from omniclaude.nodes.node_golden_chain_payload_compute.chain_registry import (
        GOLDEN_CHAIN_DEFINITIONS,
    )

    conn = None
    try:
        conn = psycopg2.connect(db_dsn)
        conn.autocommit = True
        cur = conn.cursor()

        for result in chain_results:
            status = result.projection_status
            if result.publish_status == "error":
                status = "error"

            chain_def = next(
                (c for c in GOLDEN_CHAIN_DEFINITIONS if c.name == result.chain_name),
                None,
            )
            if chain_def is None:
                continue

            cur.execute(
                """
                INSERT INTO golden_chain_sweep_results
                    (sweep_id, chain_name, head_topic, tail_table, status,
                     publish_latency_ms, projection_latency_ms, assertion_results,
                     error_reason, correlation_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    summary.sweep_id,
                    result.chain_name,
                    chain_def.head_topic,
                    chain_def.tail_table,
                    status,
                    result.publish_latency_ms,
                    result.projection_latency_ms,
                    json.dumps(result.assertion_results, default=str),
                    result.error_reason,
                    result.correlation_id,
                ),
            )

        cur.close()
        logger.info(
            "Persisted %d chain results to golden_chain_sweep_results",
            len(chain_results),
        )

    except Exception as exc:  # noqa: BLE001 — best-effort persistence must not crash sweep
        logger.error("Failed to persist sweep results: %s", exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001, S110  # nosec B110
                pass
