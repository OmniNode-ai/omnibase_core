# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Bridge capability_scores rows → ModelAvailableModel for routing policy input."""

from __future__ import annotations

from omnimarket.nodes.node_routing_policy_engine.models.model_routing_policy_request import (
    ModelAvailableModel,
)


def build_available_models_from_scores(
    capability_rows: list[dict[str, object]],
    cost_map: dict[str, float],
) -> list[ModelAvailableModel]:
    """Convert capability_scores rows to routing policy model candidates."""
    models: list[ModelAvailableModel] = []
    for row in capability_rows:
        model_key = str(row["model_key"])
        raw = row.get("success_rate") or 0.0
        score = float(raw) if isinstance(raw, (int, float)) else 0.0
        cost = cost_map.get(model_key, 0.0)
        models.append(
            ModelAvailableModel(
                key=model_key,
                score=score,
                cost_per_token=cost,
                capabilities=frozenset(),
            ),
        )
    return models


__all__: list[str] = ["build_available_models_from_scores"]
