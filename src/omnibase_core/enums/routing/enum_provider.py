# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Provider enum for routing policy decisions."""

from enum import StrEnum


class EnumProvider(StrEnum):
    """LLM provider identifier used by routing decisions."""

    LOCAL_VLLM = "local_vllm"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL_MLX = "local_mlx"


__all__: list[str] = ["EnumProvider"]
